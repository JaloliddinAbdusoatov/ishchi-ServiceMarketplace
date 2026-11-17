"""Shared visibility predicate for secondary APIs that embed order data."""
from django.db.models import Q
from apps.orders.models import OrderStatus, ServiceOrder


def visible_orders(user):
    qs = ServiceOrder.objects.all()
    public = Q(status=OrderStatus.PUBLISHED, employer__user__is_active=True,
        employer__user__account_status="ACTIVE", employer__user__is_anonymized=False)
    if not user.is_authenticated:
        return qs.filter(public)
    if user.is_admin_user:
        return qs
    related = (Q(assigned_worker__user=user) | Q(assigned_workers__user=user)
        | Q(applications__worker__user=user) | Q(invitations__worker__user=user))
    return qs.filter(public | Q(employer__user=user) | (
        ~Q(status__in=[OrderStatus.DRAFT, OrderStatus.PAUSED]) & related)).distinct()
