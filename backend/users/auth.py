from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class KeyRotationRefreshToken(RefreshToken):
    """
    Custom RefreshToken that includes a 'jwt_key' in the payload.
    This key is checked during authentication to support immediate token invalidation.
    """
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        # Ensure profile exists and has a key
        profile = getattr(user, "profile", None)
        if profile:
            if not profile.jwt_key:
                profile.rotate_jwt_key()
            token["jwt_key"] = profile.jwt_key
        return token


class KeyRotationJWTAuthentication(JWTAuthentication):
    """
    Custom JWTAuthentication that verifies the 'jwt_key' in the token payload
    matches the current 'jwt_key' in the user's profile.
    """
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user:
            return None

        profile = getattr(user, "profile", None)
        if profile and profile.jwt_key:
            token_key = validated_token.get("jwt_key")
            if token_key != profile.jwt_key:
                raise AuthenticationFailed(
                    "This token has been invalidated (a newer login has occurred).",
                    code="token_invalidated"
                )
        return user
