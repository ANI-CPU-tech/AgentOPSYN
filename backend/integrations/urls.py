from django.urls import path
from . import views

urlpatterns = [
    # Webhook receivers — one URL handles all 5 sources
    path(
        "webhooks/<str:source>/",
        views.WebhookReceiverView.as_view(),
        name="webhook-receiver",
    ),
    # Integration management
    path(
        "integrations/",
        views.IntegrationListCreateView.as_view(),
        name="integration-list",
    ),
    path(
        "integrations/<uuid:pk>/",
        views.IntegrationDetailView.as_view(),
        name="integration-detail",
    ),
    # Events
    path("events/", views.EventListView.as_view(), name="event-list"),
    path("events/<uuid:pk>/", views.EventDetailView.as_view(), name="event-detail"),
]
