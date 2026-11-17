from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.migrate import Command as DjangoMigrate


class Command(DjangoMigrate):
    def execute(self, *args, **options):
        if getattr(settings, "LOCAL_TARGET_KIND", "") == "work":
            raise CommandError("Runtime migrations are prohibited; select the separately approved local migration operator.")
        if getattr(settings, "LOCAL_TARGET_KIND", "") == "migration":
            from django.db import connections
            from apps.common.db_authorization import authorize
            authorize(connections[options.get("database", "default")].get_connection_params(), "local_migrate")
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        if getattr(settings, "IS_PRODUCTION", False):
            raise CommandError("PostgreSQL migrations require a separately approved release plan. No migration was executed.")
        return super().handle(*args, **options)
