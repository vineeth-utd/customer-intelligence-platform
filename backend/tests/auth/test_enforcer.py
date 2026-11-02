import uuid
import pytest

from app.auth.enforcer import enforce_merchant_access, enforce_platform_access
from app.auth.exceptions import AuthorizationError
from app.schemas.auth import AccessScope, Principal


def test_enforce_platform_access_internal():
    principal = Principal(user_id="usr_admin", scope=AccessScope.INTERNAL)
    # Should not raise
    enforce_platform_access(principal)


def test_enforce_platform_access_merchant_forbidden():
    merchant_id = uuid.uuid4()
    principal = Principal(
        user_id="usr_merchant",
        scope=AccessScope.MERCHANT,
        merchant_id=merchant_id,
    )
    with pytest.raises(AuthorizationError) as exc_info:
        enforce_platform_access(principal)
    assert exc_info.value.status_code == 403
    assert "Platform-wide access requires INTERNAL scope" in exc_info.value.message


def test_enforce_merchant_access_internal_allows_any_merchant():
    principal = Principal(user_id="usr_admin", scope=AccessScope.INTERNAL)
    merchant_1 = uuid.uuid4()
    merchant_2 = uuid.uuid4()

    # Internal principal can access any merchant
    enforce_merchant_access(principal, merchant_1)
    enforce_merchant_access(principal, merchant_2)


def test_enforce_merchant_access_matching_merchant_allowed():
    merchant_id = uuid.uuid4()
    principal = Principal(
        user_id="usr_store_1",
        scope=AccessScope.MERCHANT,
        merchant_id=merchant_id,
    )

    # Allowed with UUID
    enforce_merchant_access(principal, merchant_id)
    # Allowed with string representation
    enforce_merchant_access(principal, str(merchant_id))


def test_enforce_merchant_access_cross_merchant_forbidden():
    merchant_1 = uuid.uuid4()
    merchant_2 = uuid.uuid4()
    principal = Principal(
        user_id="usr_store_1",
        scope=AccessScope.MERCHANT,
        merchant_id=merchant_1,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        enforce_merchant_access(principal, merchant_2)
    assert exc_info.value.status_code == 403
    assert "Cross-merchant access forbidden" in exc_info.value.message

