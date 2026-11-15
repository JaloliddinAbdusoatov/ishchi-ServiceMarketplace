class PendingSchemaApprovalRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Django also calls routers during read-only system checks. The command
        # and schema-editor guards reject execution before migration recording.
        return False
