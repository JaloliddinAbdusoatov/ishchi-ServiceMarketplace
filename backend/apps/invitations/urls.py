from django.urls import path
from apps.invitations.views import (
    InvitationAcceptView,
    InvitationCancelView,
    InvitationListCreateView,
    InvitationRejectView,
)

urlpatterns = [
    path("", InvitationListCreateView.as_view(), name="invitations-list-create"),
    path("<uuid:invitation_id>/accept/", InvitationAcceptView.as_view(), name="invitations-accept"),
    path("<uuid:invitation_id>/reject/", InvitationRejectView.as_view(), name="invitations-reject"),
    path("<uuid:invitation_id>/cancel/", InvitationCancelView.as_view(), name="invitations-cancel"),
]
