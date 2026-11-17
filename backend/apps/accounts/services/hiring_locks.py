"""Account rows precede order/profile locks, matching anonymization's lock order."""
from apps.accounts.models import User
from apps.common.exceptions import ForbiddenActionError
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile


def lock_hiring_accounts(order_id, worker_id):
    owner_id = ServiceOrder.objects.values_list("employer__user_id", flat=True).get(pk=order_id)
    worker_user_id = WorkerProfile.objects.values_list("user_id", flat=True).get(pk=worker_id)
    # Protect eligibility updates without blocking unrelated FK key-share checks.
    users = list(User.objects.select_for_update(no_key=True).filter(pk__in=[owner_id, worker_user_id]).order_by("pk"))
    if len(users) != len({owner_id, worker_user_id}) or any(
        not user.is_active or user.is_anonymized or user.account_status != "ACTIVE" for user in users
    ):
        raise ForbiddenActionError("Hiring requires active employer and worker accounts.", code="account_not_active")
