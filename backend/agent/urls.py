from django.urls import path
from . import views

urlpatterns = [
    path("query/", views.QueryView.as_view(), name="query"),
    path("query/history/", views.QueryHistoryView.as_view(), name="query-history"),
    path("query/<uuid:pk>/", views.QueryDetailView.as_view(), name="query-detail"),
    path(
        "query/<uuid:pk>/generate-runbook/",
        views.GenerateRunbookFromQueryView.as_view(),
        name="query-generate-runbook",
    ),
]
