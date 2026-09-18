from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import accounts_status, login_view, me_view, register_view

urlpatterns = [
    path("register/", register_view, name="auth-register"),
    path("login/", login_view, name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", me_view, name="auth-me"),
    path("status/", accounts_status, name="accounts-status"),
]
