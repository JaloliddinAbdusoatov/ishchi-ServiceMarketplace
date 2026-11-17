"""Default is a no-query plan; execution needs an independent exact approval."""
import json
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.services.local_demotion import SYNTHETIC, OWNER, demote_local_verification_admin

class Command(BaseCommand):
    requires_system_checks=[]
    def add_arguments(self,parser):
        parser.add_argument("--apply",action="store_true")
        parser.add_argument("--approval-file")
    def handle(self,*args,**options):
        if not options["apply"]:
            self.stdout.write(f"REQUIRES APPROVAL: demote {SYNTHETIC}; preserve {OWNER}; role WORKER; revoke JWT/refresh/Django sessions; no password change. No queries executed.")
            return
        try:
            doc=json.loads(Path(options["approval_file"]).read_text(encoding="utf-8"))
            db=settings.DATABASES["default"]
            expected={"host":"postgres-work","port":"5432","dbname":"ishchi_marketplace_local","user":"ishchi_local_app"}
            actual={"host":db["HOST"],"port":str(db["PORT"]),"dbname":db["NAME"],"user":db["USER"]}
            if doc["target"]!=expected or actual!=expected or doc["account"]!=str(SYNTHETIC) or doc["owner"]!=str(OWNER):raise ValueError()
            if not doc["approved_by"].strip() or datetime.fromisoformat(doc["expires_at"].replace("Z","+00:00"))<=datetime.now(timezone.utc):raise ValueError()
            if set(doc["operations"])!={"demote_exact_synthetic_admin","clear_permission_memberships","revoke_exact_account_sessions","append_admin_audit"}:raise ValueError()
        except (OSError,ValueError,TypeError,KeyError):
            raise CommandError("Separate exact-account, unexpired owner approval required; no changes made.") from None
        result=demote_local_verification_admin(SYNTHETIC,OWNER,owner_approved=True)
        self.stdout.write(json.dumps(result))
