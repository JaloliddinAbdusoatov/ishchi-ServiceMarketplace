"""Live nginx/API authorization probe; existing synthetic fixtures, GET only.
No password login, refresh/session records, JWT revocation, fixtures or cleanup.
Short-lived access tokens exist only in process memory and are never printed.
"""
import os, json, hashlib
from datetime import timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local_postgres")
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from rest_framework_simplejwt.tokens import AccessToken
from apps.chat.models import Message


def main():
    db=settings.DATABASES["default"]
    if (db["HOST"],str(db["PORT"]),db["NAME"],db["USER"]) != ("postgres-work","5432","ishchi_marketplace_local","ishchi_local_app"):
        raise RuntimeError("Unexpected target")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        User=get_user_model()
        outsider=User.objects.get(full_name="Browser QA Outsider mwk4qurf")
        worker=User.objects.get(full_name="Browser QA Worker mwk4qurf")
        message=Message.objects.select_related("conversation__worker").get(pk="89c3543f-d49e-4579-b574-228836a47638")
        assert message.conversation.worker.user_id == worker.pk
        assert outsider.pk not in (worker.pk,message.conversation.employer.user_id)
        with message.attachment.open("rb") as file:
            expected_hash=hashlib.sha256(file.read()).hexdigest()
        principals=[(worker,"participant"),(outsider,"unrelated")]
        tokens={}
        for user,label in principals:
            assert user.is_active and not user.is_anonymized and user.account_status=="ACTIVE"
            # AccessToken (not RefreshToken) performs no OutstandingToken INSERT.
            token=AccessToken.for_user(user)
            token.set_exp(lifetime=timedelta(seconds=60))
            token["token_version"]=user.token_version
            tokens[label]=str(token)
    def get(path,token=None):
        request=Request("http://127.0.0.1:8080"+path,headers={"Authorization":"Bearer "+token} if token else {})
        try:
            with urlopen(request,timeout=15) as response:
                return response.status,response.headers,response.read()
        except HTTPError as response:
            return response.code,response.headers,response.read()
    path="/api/v1/chat/messages/"+str(message.pk)+"/attachment/"
    results={}
    for user,label in principals:
        status,headers,body=get("/api/v1/auth/me/",tokens[label])
        assert status==200 and json.loads(body)["data"]["id"]==str(user.pk), "Authentication control failed"
        results[label+"_authenticated_me"]=status
        status,headers,body=get(path,tokens[label])
        if label=="participant":
            assert status==200 and hashlib.sha256(body).hexdigest()==expected_hash
            assert "attachment" in headers.get("Content-Disposition","")
            assert headers.get("Cache-Control")=="private, no-store"
        else:
            assert status==403 and json.loads(body)["error"]["code"]=="chat_access_denied"
            assert not headers.get("Content-Disposition")
            assert hashlib.sha256(body).hexdigest()!=expected_hash
        results[label+"_attachment"]=status
    status,headers,body=get(path)
    assert status==401
    results["guest_attachment"]=status
    print(json.dumps({"status":"PASS","transport":"live nginx HTTP -> Django/PostgreSQL/Redis","access_tokens":"60-second in-memory signed test access tokens; no password login or refresh records","results":results}))

if __name__=="__main__":
    main()
