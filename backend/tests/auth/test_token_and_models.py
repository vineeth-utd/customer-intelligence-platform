import time
import uuid
import pytest
from pydantic import ValidationError

from app.auth.exceptions import AuthenticationError
from app.auth.token import (
    MVPTokenService,
    create_access_token,
    decode_access_token,
)
from app.schemas.auth import AccessScope, Principal


def test_principal_internal_creation_valid():
    principal = Principal(
        user_id="usr_internal_1",
        scope=AccessScope.INTERNAL,
        email="analyst@cip.internal",
        roles=["analyst", "admin"],
    )
    assert principal.user_id == "usr_internal_1"
    assert principal.scope == AccessScope.INTERNAL
    assert principal.merchant_id is None
    assert principal.email == "analyst@cip.internal"
    assert principal.roles == ["analyst", "admin"]


def test_principal_merchant_creation_valid():
    merchant_id = uuid.uuid4()
    principal = Principal(
        user_id="usr_merchant_1",
        scope=AccessScope.MERCHANT,
        merchant_id=merchant_id,
        email="merchant@store.com",
    )
    assert principal.user_id == "usr_merchant_1"
    assert principal.scope == AccessScope.MERCHANT
    assert principal.merchant_id == merchant_id


def test_principal_merchant_without_merchant_id_fails():
    with pytest.raises(ValidationError) as exc_info:
        Principal(
            user_id="usr_merchant_1",
            scope=AccessScope.MERCHANT,
            merchant_id=None,
        )
    assert "Merchant principals must be associated with a valid merchant_id" in str(exc_info.value)


def test_token_roundtrip_internal():
    token = create_access_token(
        user_id="usr_admin",
        scope=AccessScope.INTERNAL,
        email="admin@cip.internal",
        roles=["admin"],
    )
    principal = decode_access_token(token)
    assert principal.user_id == "usr_admin"
    assert principal.scope == AccessScope.INTERNAL
    assert principal.merchant_id is None
    assert principal.email == "admin@cip.internal"
    assert principal.roles == ["admin"]


def test_token_roundtrip_merchant():
    merchant_id = uuid.uuid4()
    token = create_access_token(
        user_id="usr_store_owner",
        scope=AccessScope.MERCHANT,
        merchant_id=merchant_id,
        email="owner@teststore.com",
    )
    principal = decode_access_token(token)
    assert principal.user_id == "usr_store_owner"
    assert principal.scope == AccessScope.MERCHANT
    assert principal.merchant_id == merchant_id
    assert principal.email == "owner@teststore.com"


def test_token_tampering_rejected():
    token = create_access_token(
        user_id="usr_admin",
        scope=AccessScope.INTERNAL,
    )
    parts = token.split(".")
    # Tamper with signature
    tampered_sig = parts[0] + "." + parts[1] + "." + parts[2][:-2] + "xx"
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(tampered_sig)
    assert "Invalid token signature" in str(exc_info.value)

    # Tamper with payload
    tampered_payload = parts[0] + "." + parts[1][:-2] + "xx." + parts[2]
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(tampered_payload)
    assert "signature" in str(exc_info.value).lower() or "malformed" in str(exc_info.value).lower()


def test_token_expiration_rejected():
    token = create_access_token(
        user_id="usr_admin",
        scope=AccessScope.INTERNAL,
        expires_delta_seconds=-10,  # Expired 10 seconds ago
    )
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token)
    assert "Token has expired" in str(exc_info.value)


def test_token_malformed_structure():
    with pytest.raises(AuthenticationError) as exc:
        decode_access_token("not-a-token")
    assert "Malformed token structure" in str(exc.value)

    with pytest.raises(AuthenticationError) as exc:
        decode_access_token("part1.part2")
    assert "Malformed token structure" in str(exc.value)

    with pytest.raises(AuthenticationError) as exc:
        decode_access_token("")
    assert "Missing or invalid token format" in str(exc.value)


def test_token_custom_secret_key_isolation():
    service_a = MVPTokenService(secret_key="secret-key-alpha")
    service_b = MVPTokenService(secret_key="secret-key-beta")

    principal = Principal(user_id="usr_1", scope=AccessScope.INTERNAL)
    token_a = service_a.create_token(principal)

    # Should succeed with service A
    assert service_a.decode_token(token_a).user_id == "usr_1"

    # Should fail with service B due to signature mismatch
    with pytest.raises(AuthenticationError) as exc:
        service_b.decode_token(token_a)
    assert "Invalid token signature" in str(exc.value)

