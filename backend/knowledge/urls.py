from django.urls import path
from . import views

urlpatterns = [
    path(
        "embeddings/search/", views.SemanticSearchView.as_view(), name="semantic-search"
    ),
    path("embeddings/ingest/", views.ManualIngestView.as_view(), name="manual-ingest"),
]
