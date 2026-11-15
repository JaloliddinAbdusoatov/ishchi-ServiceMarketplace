from django.contrib.auth.backends import ModelBackend


class ActiveAccountBackend(ModelBackend):
    """Apply account restrictions to Django administrator sessions as well as JWT."""
    def user_can_authenticate(self, user):
        return bool(super().user_can_authenticate(user)
                    and not user.is_anonymized and user.account_status == "ACTIVE")
