"""Interactive owner-approved action. Default is a no-query dry run."""
import getpass
import sys
import uuid
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import AccountStatus, User
from apps.accounts.services.local_security import rotate_local_admin_password


class Command(BaseCommand):
    help = "Prepare/perform a single local admin password rotation; --apply requires independent owner approval."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--account", type=uuid.UUID, required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--verify", action="store_true", help="Interactively check old/new login and session revocation; requires --apply.")
        parser.add_argument("--previous-password-unknown", action="store_true", help="Owner-approved reset: verify JWT/session revocation and new login; old-password login test remains NOT RUN.")

    def handle(self, *args, **options):
        if options["previous_password_unknown"]:
            options["verify"] = True
        if getattr(settings, "IS_PRODUCTION", False) or getattr(settings, "LOCAL_TARGET_KIND", "") != "work":
            raise CommandError("Use explicit local working settings only; production rotation is prohibited.")
        if not options["apply"]:
            self.stdout.write(f"DRY RUN: account {options['account']}; no account query, password change or session revocation.")
            return
        if not sys.stdin.isatty():
            raise CommandError("An interactive terminal is required; never pipe passwords or pass them in arguments/files/environment.")
        first = second = previous = verification = None
        try:
            user = User.objects.get(pk=options["account"])
            if not user.is_admin_user or not user.is_active or user.is_anonymized or user.account_status != AccountStatus.ACTIVE:
                raise CommandError("The target must be an active, non-anonymized local administrator.")
            if options["verify"] and not options["previous_password_unknown"]:
                previous = getpass.getpass("Previous exposed password (hidden, verification only): ")
                if not previous or not user.check_password(previous):
                    raise CommandError("Previous credential validation failed; no account change was made.")
            for attempt in range(3):
                first = getpass.getpass("New administrator password (hidden): ")
                second = getpass.getpass("Repeat new password (hidden): ")
                if first != second:
                    self.stderr.write("Passwords did not match. Re-enter both new-password fields; nothing changed.")
                else:
                    try:
                        validate_password(first, user=user)
                        if user.check_password(first):
                            raise ValidationError("The new password must differ from the exposed password.")
                    except ValidationError as exc:
                        self.stderr.write("Password rejected: " + "; ".join(exc.messages) + " Nothing changed; try again.")
                    else:
                        break
                first = second = None
            else:
                raise CommandError("Three unsuccessful entries; no rotation or verification session was created.")
            # Prepare test sessions only after matching, valid password input.
            if options["verify"]:
                from apps.accounts.services.local_rotation_verification import prepare_verification
                verification = prepare_verification(options["account"], previous,
                    allow_unknown_previous=options["previous_password_unknown"])
                previous = None
            rotate_local_admin_password(options["account"], first)
            if verification is not None:
                verification(first)
        except User.DoesNotExist:
            raise CommandError("The specified administrator does not exist.") from None
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from None
        finally:
            first = second = previous = verification = None
        self.stdout.write("PASS: single administrator password rotated and its existing JWTs revoked; global keys and application data unchanged.")
        if options["verify"]:
            if options["previous_password_unknown"]:
                self.stdout.write("PASS: old access/refresh/admin session rejected; new API/admin login works; other account security state unchanged.")
                self.stdout.write("NOT RUN: old-password login rejection (previous password unknown).")
            else:
                self.stdout.write("PASS: old password/access/refresh/admin session rejected; new API/admin login works; other account security state unchanged.")
