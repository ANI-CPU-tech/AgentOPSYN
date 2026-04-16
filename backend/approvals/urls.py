from django.urls import path
from . import views

urlpatterns = [
    path(
        "actions/pending/", views.PendingActionsView.as_view(), name="actions-pending"
    ),
    path("actions/audit-log/", views.AuditLogView.as_view(), name="actions-audit-log"),
    path("actions/<uuid:pk>/", views.ActionDetailView.as_view(), name="action-detail"),
    path(
        "actions/<uuid:pk>/approve/",
        views.ApproveActionView.as_view(),
        name="action-approve",
    ),
    path(
        "actions/<uuid:pk>/reject/",
        views.RejectActionView.as_view(),
        name="action-reject",
    ),
    path(
        "actions/<uuid:pk>/status/",
        views.ActionStatusView.as_view(),
        name="action-status",
    ),
]
