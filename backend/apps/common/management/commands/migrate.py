from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.migrate import Command as DjangoMigrate


class Command(DjangoMigrate):
    def handle(self, *args, **options):
        if getattr(settings, "IS_PRODUCTION", False):
            raise CommandError("PostgreSQL migrations require a separately approved release plan. No migration was executed.")
        return super().handle(*args, **options)
