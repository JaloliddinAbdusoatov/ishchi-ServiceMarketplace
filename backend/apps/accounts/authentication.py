from django.core.cache import cache
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from apps.accounts.models import AccountStatus


class MarketplaceJWTAuthentication(JWTAuthentication):
    """
    Extends SimpleJWT authentication to enforce:
    - Active, non-anonymized account status
    - Token version match (immediate global invalidation on logout-all / password reset / deletion)
    - Access token JTI blacklist check in Redis (immediate single-session logout invalidation)
    """

    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        session_id = validated_token.get("session_id")
        if session_id and cache.get(f"revoked_session:{session_id}"):
            raise InvalidToken("Session has been revoked.")
        jti = validated_token.get("jti")
        if jti and cache.get(f"revoked_access_jti:{jti}"):
            raise InvalidToken("Access token has been revoked.")
        return validated_token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active or user.is_anonymized or user.account_status != AccountStatus.ACTIVE:
            raise AuthenticationFailed("User account is suspended, deleted, or inactive.", code="account_inactive")

        token_version = validated_token.get("token_version")
        if token_version != user.token_version:
            raise AuthenticationFailed("Session has been invalidated. Please log in again.", code="token_invalidated")

        return user


class MarketplaceJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.MarketplaceJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
