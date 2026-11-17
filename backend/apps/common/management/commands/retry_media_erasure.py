from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.common.media_erasure import process_media_erasure
from apps.common.models import MediaDeletionTask


class Command(BaseCommand):
    help = "Inspect pending erasure count; --apply requires an explicit media-root match."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-media-root")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        # Existing production DB authorization still blocks this command's queries.
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("limit must be between 1 and 1000")
        if options["apply"]:
            supplied = options["confirm_media_root"]
            if not supplied or Path(supplied).resolve() != Path(settings.MEDIA_ROOT).resolve():
                raise CommandError("An explicit exact --confirm-media-root is required before deletion")
            result = process_media_erasure(limit=options["limit"])
            self.stdout.write(str(result))
            if result["failed"]:
                raise CommandError("Media erasure tasks remain pending; inspect restricted operational logs")
        else:
            count = MediaDeletionTask.objects.filter(completed_at=None, next_attempt_at__lte=timezone.now()).count()
            self.stdout.write(f"DRY RUN: {count} due media erasure tasks; no files deleted.")
