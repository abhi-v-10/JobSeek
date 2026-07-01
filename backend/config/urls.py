"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views import (
    ChangePasswordAPIView,
    ForgotPasswordSendOTPAPIView,
    ResetPasswordAPIView,
    VerifyOTPAPIView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/forgot-password/send-otp/", ForgotPasswordSendOTPAPIView.as_view(), name="forgot-password-send-otp"),
    path("api/auth/forgot-password/verify-otp/", VerifyOTPAPIView.as_view(), name="forgot-password-verify-otp"),
    path("api/auth/forgot-password/reset/", ResetPasswordAPIView.as_view(), name="forgot-password-reset"),
    path("api/profile/change-password/", ChangePasswordAPIView.as_view(), name="profile-change-password"),
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/jobs/", include("apps.jobs.urls", namespace="jobs")),
    path("api/chat/", include("apps.ai_chat.urls", namespace="chat")),
    path("api/messages/", include("apps.messaging.urls", namespace="messaging")),
    path("api/applications/", include("apps.applications.urls", namespace="applications")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
