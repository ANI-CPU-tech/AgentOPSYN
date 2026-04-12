from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("api-keys/", views.APIKeyListCreateView.as_view(), name="apikey-list-create"),
    path("api-keys/<uuid:pk>/", views.APIKeyRevokeView.as_view(), name="apikey-revoke"),
]
