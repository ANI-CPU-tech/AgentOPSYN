from django.urls import path
from . import views

urlpatterns = [
    path("runbooks/", views.RunbookListView.as_view(), name="runbook-list"),
    path("runbooks/search/", views.RunbookSearchView.as_view(), name="runbook-search"),
    path(
        "runbooks/<uuid:pk>/", views.RunbookDetailView.as_view(), name="runbook-detail"
    ),
    path(
        "runbooks/<uuid:pk>/versions/",
        views.RunbookVersionsView.as_view(),
        name="runbook-versions",
    ),
]
