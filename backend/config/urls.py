"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from users.views import (
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
    path("api/users/", include("users.urls", namespace="users")),
    path("api/jobs/", include("jobs.urls", namespace="jobs")),
    path("api/chat/", include("ai_chat.urls", namespace="chat")),
    path("api/messages/", include("messaging.urls", namespace="messaging")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
