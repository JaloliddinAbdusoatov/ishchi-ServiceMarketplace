"""Approved local read-only inventory / ordinary stop-start preservation check.

No credential-file consumption, account mutations, migrations, reset, role changes
or backup/restore. --restart creates NEW harmless cache/media markers and retains
them; it stops/starts only the four approved working services, never removes data.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]

SERVER_CODE = r'''
import json,sys,os,hashlib,hmac
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local_postgres')
import django
django.setup()
from django.conf import settings
from django.db import connection,transaction
from django.core.cache import cache
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from apps.accounts.models import User
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
p=json.load(sys.stdin)
assert not settings.IS_PRODUCTION and settings.LOCAL_TARGET_KIND=='work'
db=settings.DATABASES['default']
assert (db['HOST'],str(db['PORT']),db['NAME'],db['USER'])==('postgres-work','5432','ishchi_marketplace_local','ishchi_local_app')
if p['mode']=='probe':
    folder=Path(settings.MEDIA_ROOT)/'.local-verification'
    if folder.is_symlink(): raise RuntimeError('Unexpected probe directory link')
    folder.mkdir(exist_ok=True)
    with (folder/(p['probe']+'.txt')).open('xb') as f: f.write(b'Synthetic local persistence marker\n')
    cache.set('local_stability:'+p['probe'],True,timeout=3600)
    print(json.dumps({'probe_created':True}))
elif p['mode']=='permissions':
    with transaction.atomic():
        with connection.cursor() as c:
            c.execute('SET TRANSACTION READ ONLY')
            c.execute("SELECT current_database(),current_user,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user")
            row=c.fetchone()
            roles=dict(zip(('database','role','superuser','createdb','createrole','replication','bypassrls'),row))
            c.execute("SELECT pg_get_userbyid(nspowner),has_schema_privilege(current_user,oid,'CREATE') FROM pg_namespace WHERE nspname='public'")
            owner,create=c.fetchone()
            c.execute("SELECT c.relname,pg_get_userbyid(c.relowner),has_table_privilege(current_user,c.oid,'SELECT'),has_table_privilege(current_user,c.oid,'INSERT'),has_table_privilege(current_user,c.oid,'UPDATE'),has_table_privilege(current_user,c.oid,'DELETE'),has_table_privilege(current_user,c.oid,'TRUNCATE') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('accounts_deletion_audit','django_admin_log') ORDER BY c.relname")
            audits=[dict(zip(('table','owner','select','insert','update','delete','truncate'),r)) for r in c.fetchall()]
            c.execute("SELECT c.relname,c.relkind,pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','S','v','m') ORDER BY c.relname")
            objects=[dict(zip(('name','kind','owner'),r)) for r in c.fetchall()]
            c.execute("SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_userbyid(p.proowner),p.prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' ORDER BY p.proname")
            functions=[dict(zip(('name','arguments','owner','security_definer'),r)) for r in c.fetchall()]
            c.execute("SELECT conrelid::regclass::text,conname,confrelid::regclass::text,confdeltype FROM pg_constraint WHERE contype='f' AND conrelid IN ('public.accounts_deletion_audit'::regclass,'public.django_admin_log'::regclass) ORDER BY conname")
            audit_fks=[dict(zip(('table','constraint','references','delete_action'),r)) for r in c.fetchall()]
            c.execute("SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname")
            triggers=[dict(zip(('table','name','definition'),r)) for r in c.fetchall()]
            c.execute("SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname IN ('ishchi_local_app','ishchi_local_owner','ishchi_local_migrator') ORDER BY rolname")
            role_inventory=[dict(zip(('name','login','superuser','createdb','createrole','bypassrls'),r)) for r in c.fetchall()]
            c.execute("SELECT parent.rolname,member.rolname,m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles parent ON parent.oid=m.roleid JOIN pg_roles member ON member.oid=m.member WHERE member.rolname IN ('ishchi_local_app','ishchi_local_migrator') ORDER BY member.rolname,parent.rolname")
            memberships=[dict(zip(('role','member','admin','inherit','set'),r)) for r in c.fetchall()]
        admins=list(User.objects.filter(role='ADMIN').values('id','is_active','token_version'))
    print(json.dumps({'postgres_role':roles,'public_schema_owner':owner,'schema_create':create,'audit_tables':audits,'administrators':admins,'objects':objects,'functions':functions,'audit_foreign_keys':audit_fks,'triggers':triggers,'role_inventory':role_inventory,'memberships':memberships},cls=DjangoJSONEncoder))
else:
    key=bytes.fromhex(p['key'])
    counts={}; digests={}
    with transaction.atomic():
        with connection.cursor() as c: c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        for model in apps.get_models(include_auto_created=True):
            if not model._meta.managed or model._meta.proxy: continue
            rows=list(model._default_manager.order_by('pk').values())
            label=model._meta.label_lower
            counts[label]=len(rows)
            digests[label]=hmac.new(key,json.dumps(rows,sort_keys=True,cls=DjangoJSONEncoder).encode(),hashlib.sha256).hexdigest()
        phones=list(User.objects.exclude(phone_number=None).values_list('phone_number',flat=True))
        jtis=list(OutstandingToken.objects.values_list('jti',flat=True))
    keys=['local_stability:'+p['probe']]
    for phone in phones:
        keys += ['login_lockout:'+phone,'login_fail:'+phone,'otp_rate:phone:'+phone,'otp_session:VERIFY_PHONE:'+phone,'otp_session:PASSWORD_RESET:'+phone]
    keys += ['revoked_session:'+jti for jti in jtis]
    values=cache.get_many(keys)
    security=hmac.new(key,json.dumps(values,sort_keys=True,cls=DjangoJSONEncoder).encode(),hashlib.sha256).hexdigest()
    media=[]
    for file in sorted(Path(settings.MEDIA_ROOT).rglob('*')):
        if file.is_symlink(): raise RuntimeError('Media link requires separate review')
        if file.is_file(): media.append((str(file.relative_to(settings.MEDIA_ROOT)),hashlib.sha256(file.read_bytes()).hexdigest()))
    print(json.dumps({'row_counts':counts,'table_digests':digests,'media_files':len(media),'media_digest':hmac.new(key,json.dumps(media).encode(),hashlib.sha256).hexdigest(),'security_digest':security,'security_keys_present':len(values),'probe_present':values.get('local_stability:'+p['probe']) is True}))
'''


def docker_prefix(context):
    prefix = ["docker", "--context", context]
    endpoint = json.loads(subprocess.check_output(prefix + ["context", "inspect", "--format", "{{json .Endpoints.docker.Host}}", context], text=True, timeout=10))
    if not endpoint.startswith(("npipe://", "unix://")):
        raise ValueError("Refusing a remote Docker context")
    return prefix


def classify_permissions(permissions):
    role = permissions["postgres_role"]
    inventory = {row['name']: row for row in permissions.get('role_inventory', [])}
    separated = (
        permissions['public_schema_owner'] == 'ishchi_local_owner' and not permissions['schema_create']
        and inventory.get('ishchi_local_owner', {}).get('login') is False
        and inventory.get('ishchi_local_migrator', {}).get('login') is True
        and permissions.get('memberships') == [{'role':'ishchi_local_owner','member':'ishchi_local_migrator','admin':False,'inherit':False,'set':True}]
        and bool(permissions.get('objects'))
        and all(row['owner'] == 'ishchi_local_owner' for row in permissions['objects'])
        and all(not row['security_definer'] and row['owner'] == 'ishchi_local_owner' for row in permissions.get('functions', []))
    )
    return {
        "non_superuser_runtime": "PASS" if not any(role[name] for name in (
            "superuser", "createdb", "createrole", "replication", "bypassrls")) else "FAIL",
        "runtime_migration_role_separation": "PASS" if separated else "FAIL" if permissions["public_schema_owner"] == role["role"] or permissions["schema_create"] else "NOT VERIFIED",
        "append_only_database_audit": "FAIL" if any(row[operation] for row in permissions["audit_tables"]
            for operation in ("update", "delete", "truncate")) else "PASS" if len(permissions["audit_tables"]) == 2 else "NOT VERIFIED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default="desktop-linux")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--report", type=Path, default=ROOT / "deploy/.local/stabilization.json")
    args = parser.parse_args(argv)
    prefix = docker_prefix(args.context)
    compose = prefix + ["compose", "--env-file", "deploy/.env.local", "-f", "deploy/compose.local.yml", "--profile", "work"]

    def server(payload):
        result = subprocess.run(compose + ["exec", "-T", "backend", "python", "-c", SERVER_CODE],
            input=json.dumps(payload), text=True, capture_output=True, cwd=ROOT, timeout=40)
        if result.returncode:
            raise RuntimeError("Local inventory failed; no account/role change attempted. Inspect restricted local logs.")
        return json.loads(result.stdout)

    permissions = server({"mode": "permissions"})
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "permissions": permissions,
              "control_status": classify_permissions(permissions),
              "account_modified": False, "role_grants_modified": False, "backup_or_restore_executed": False}
    if args.restart:
        payload = {"mode": "snapshot", "key": secrets.token_hex(32), "probe": uuid.uuid4().hex}
        server({"mode": "probe", "probe": payload["probe"]})
        before = server(payload)
        services = ["backend", "gateway", "postgres-work", "redis-work"]
        try:
            subprocess.run(compose + ["stop", *services], cwd=ROOT, check=True, timeout=60)
        finally:
            subprocess.run(compose + ["up", "-d", "postgres-work", "redis-work", "backend", "gateway"], cwd=ROOT, check=True, timeout=60)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 30
        while True:
            try:
                with opener.open("http://127.0.0.1:8080/api/v1/health/ready/", timeout=3) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("Local readiness did not recover after ordinary restart")
            time.sleep(0.2)
        after = server(payload)
        report.update(restart_executed=True, data_preserved=before == after,
            row_counts=after["row_counts"], media_files=after["media_files"],
            security_keys_present=after["security_keys_present"], probe_preserved=after["probe_present"],
            retained_synthetic_marker=payload["probe"])
    else:
        report["restart_executed"] = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.restart and not report["data_preserved"]:
        raise RuntimeError("FAIL: before/after inventory differs; no reset or repair was attempted")
    print("PASS: read-only role/audit inventory" + ("; ordinary stop/start preserved database, Redis marker/security values and media" if args.restart else ""))


if __name__ == "__main__":
    main()
