from django.urls import path

from .views import (
    CreateUserAPIView,
    CurrentProfileAPIView,
    ChangePasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    ResumeAPIView,
    SkillCreateAPIView,
    SkillDeleteAPIView,
    BulkSkillUpdateAPIView,
    SwitchUserRoleAPIView,
    DashboardAPIView,
)

app_name = "users"

urlpatterns = [
    path("register/", CreateUserAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("profile/", CurrentProfileAPIView.as_view(), name="profile"),
    path("me/resume/", ResumeAPIView.as_view(), name="resume"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    path("skills/", SkillCreateAPIView.as_view(), name="skill-create"),
    path("skills/bulk/", BulkSkillUpdateAPIView.as_view(), name="skills-bulk"),
    path("skills/<int:pk>/", SkillDeleteAPIView.as_view(), name="skill-delete"),
    path("switch-role/", SwitchUserRoleAPIView.as_view(), name="switch-role"),
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
]
