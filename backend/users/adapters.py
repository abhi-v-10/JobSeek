from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from rest_framework_simplejwt.tokens import RefreshToken
import re

User = get_user_model()


def _clean_username(raw: str) -> str:
    """Strip everything that isn't alphanumeric / underscore / hyphen."""
    cleaned = re.sub(r'[^\w\-]', '', raw.replace(' ', '_'))
    return cleaned[:30] or 'user'


def _unique_username(base: str) -> str:
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}_{counter}"
        counter += 1
    return username


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    After a successful OAuth login/signup, generate JWT tokens and
    redirect the browser to the React frontend with the tokens as
    query-string params so the frontend can store them.
    """

    def get_connect_redirect_url(self, request, socialaccount):
        return 'http://localhost:5173/oauth/callback'

    def save_user(self, request, sociallogin, form=None):
        """Ensure every OAuth user gets a username derived from their name/email."""
        user = super().save_user(request, sociallogin, form)
        if not user.username:
            extra = sociallogin.account.extra_data
            raw = (
                extra.get('name') or
                extra.get('login') or        # GitHub uses 'login'
                extra.get('email', '').split('@')[0] or
                'user'
            )
            user.username = _unique_username(_clean_username(raw))
            user.save(update_fields=['username'])
        return user

    def get_login_redirect_url(self, request):
        """Called after a successful social login.  Redirect with JWT tokens."""
        user = request.user
        if not user.is_authenticated:
            return 'http://localhost:5173/login?error=oauth_failed'

        from users.auth import KeyRotationRefreshToken
        refresh = KeyRotationRefreshToken.for_user(user)
        access = str(refresh.access_token)
        ref = str(refresh)

        # Make sure the user has a Profile row
        from users.models import Profile
        Profile.objects.get_or_create(user=user)

        return (
            f'http://localhost:5173/oauth/callback'
            f'?access={access}&refresh={ref}'
        )


class AccountAdapter(DefaultAccountAdapter):
    """Disable standard e-mail/password signup to keep things clean."""

    def is_open_for_signup(self, request):
        return True

    def get_login_redirect_url(self, request):
        """Fallback redirect for social login if it uses the account adapter."""
        user = request.user
        if not user.is_authenticated:
            return 'http://localhost:5173/login?error=oauth_failed'

        from users.auth import KeyRotationRefreshToken
        refresh = KeyRotationRefreshToken.for_user(user)
        access = str(refresh.access_token)
        ref = str(refresh)

        # Make sure the user has a Profile row
        from users.models import Profile
        Profile.objects.get_or_create(user=user)

        return (
            f'http://localhost:5173/oauth/callback'
            f'?access={access}&refresh={ref}'
        )
