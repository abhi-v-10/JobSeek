from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile, Skill

# Register your models here.
User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	list_display = ("username", "email", "is_staff", "is_active")
	search_fields = ("username", "email")
	fieldsets = (
		(None, {"fields": ("username", "password")}),
		("Personal info", {"fields": ("email",)}),
		(
			"Permissions",
			{"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
		),
		("Important dates", {"fields": ("last_login", "date_joined")}),
	)
	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("username", "email", "password1", "password2", "is_staff", "is_active"),
			},
		),
	)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "role", "user_type", "created_at")
    list_filter = ("role", "user_type")
    search_fields = ("user__username", "user__email", "full_name", "mobile_number")
    readonly_fields = ("created_at", "updated_at", "parsed_resume")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "get_username", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "profile__user__username", "profile__full_name")

    def get_username(self, obj):
        return obj.profile.user.username
    get_username.short_description = "Username"
    get_username.admin_order_field = "profile__user__username"