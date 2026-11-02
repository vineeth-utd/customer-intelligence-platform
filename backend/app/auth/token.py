import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.auth.exceptions import AuthenticationError
from app.config.settings import settings
from app.schemas.auth import AccessScope, Principal


def _b64_url_encode(data: bytes) -> str:
    """Encode bytes into URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_url_decode(data: str) -> bytes:
    """Decode URL-safe base64 string, adding padding if missing."""
    padded = data + "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


class MVPTokenService:
    """
    Lightweight identity and token service for the Customer Intelligence Platform MVP.
    Uses canonical JSON serialization and HMAC-SHA256 signature verification with
    constant-time comparison.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        default_expire_minutes: Optional[int] = None,
    ):
        self.secret_key = secret_key or settings.auth_secret_key
        self.default_expire_minutes = (
            default_expire_minutes
            if default_expire_minutes is not None
            else settings.auth_token_expire_minutes
        )

    def _sign(self, signing_input: str) -> str:
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return _b64_url_encode(signature)

    def create_token(
        self,
        principal: Principal,
        expires_delta_seconds: Optional[int] = None,
    ) -> str:
        """Create a signed MVP token for a Principal."""
        now = int(time.time())
        if expires_delta_seconds is not None:
            exp = now + expires_delta_seconds
        else:
            exp = now + (self.default_expire_minutes * 60)

        header = {"alg": "HS256", "typ": "JWT"}
        payload: Dict[str, Any] = {
            "sub": principal.user_id,
            "scope": principal.scope.value,
            "iat": now,
            "exp": exp,
            "roles": principal.roles,
        }
        if principal.merchant_id:
            payload["merchant_id"] = str(principal.merchant_id)
        if principal.email:
            payload["email"] = principal.email

        header_json = json.dumps(header, separators=(",", ":"), sort_keys=True)
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        header_b64 = _b64_url_encode(header_json.encode("utf-8"))
        payload_b64 = _b64_url_encode(payload_json.encode("utf-8"))

        signing_input = f"{header_b64}.{payload_b64}"
        signature_b64 = self._sign(signing_input)

        return f"{signing_input}.{signature_b64}"

    def decode_token(self, token: str) -> Principal:
        """
        Validate and decode an MVP token into a Principal.
        Performs constant-time signature comparison and strict expiration validation.
        """
        if not token or not isinstance(token, str):
            raise AuthenticationError("Missing or invalid token format")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed token structure: expected 3 dot-separated segments")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = self._sign(signing_input)

        if not hmac.compare_digest(expected_sig, signature_b64):
            raise AuthenticationError("Invalid token signature")

        try:
            payload_bytes = _b64_url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            raise AuthenticationError(f"Malformed token payload: {e}") from e

        if not isinstance(payload, dict):
            raise AuthenticationError("Invalid token payload: expected JSON object")

        exp = payload.get("exp")
        if exp is None or not isinstance(exp, (int, float)):
            raise AuthenticationError("Token payload missing valid expiration ('exp')")

        if exp < time.time():
            raise AuthenticationError("Token has expired")

        user_id = payload.get("sub")
        if not user_id or not isinstance(user_id, str):
            raise AuthenticationError("Token payload missing valid subject ('sub')")

        raw_scope = payload.get("scope")
        try:
            scope = AccessScope(raw_scope)
        except (ValueError, TypeError):
            raise AuthenticationError(f"Token payload has invalid access scope: '{raw_scope}'")

        merchant_id_raw = payload.get("merchant_id")
        merchant_id: Optional[UUID] = None
        if merchant_id_raw is not None:
            try:
                merchant_id = UUID(str(merchant_id_raw))
            except (ValueError, TypeError) as e:
                raise AuthenticationError(f"Token payload has invalid merchant_id: {merchant_id_raw}") from e

        if scope == AccessScope.MERCHANT and merchant_id is None:
            raise AuthenticationError("Merchant-scoped token must include a valid merchant_id")

        roles = payload.get("roles")
        if not isinstance(roles, list):
            roles = []

        email = payload.get("email")
        if email is not None and not isinstance(email, str):
            email = None

        return Principal(
            user_id=user_id,
            scope=scope,
            merchant_id=merchant_id,
            email=email,
            roles=[str(r) for r in roles],
        )


token_service = MVPTokenService()


def create_access_token(
    user_id: str,
    scope: Union[AccessScope, str],
    merchant_id: Optional[Union[UUID, str]] = None,
    email: Optional[str] = None,
    roles: Optional[List[str]] = None,
    expires_delta_seconds: Optional[int] = None,
) -> str:
    """Convenience helper to create an MVP access token."""
    if isinstance(scope, str):
        scope = AccessScope(scope)
    if isinstance(merchant_id, str):
        merchant_id = UUID(merchant_id)

    principal = Principal(
        user_id=user_id,
        scope=scope,
        merchant_id=merchant_id,
        email=email,
        roles=roles or [],
    )
    return token_service.create_token(principal, expires_delta_seconds=expires_delta_seconds)


def decode_access_token(token: str) -> Principal:
    """Convenience helper to decode and validate an MVP access token."""
    return token_service.decode_token(token)

