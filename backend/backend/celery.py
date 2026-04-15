import os
from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "backend.settings"
)  # 🔥 change if needed

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
