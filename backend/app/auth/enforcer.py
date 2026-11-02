from typing import Union
from uuid import UUID

from app.auth.exceptions import AuthorizationError
from app.schemas.auth import AccessScope, Principal


def enforce_platform_access(principal: Principal) -> None:
    """
    Enforce that the principal has platform-wide access permission.
    Only INTERNAL principals are permitted platform-wide access.
    """
    if principal.scope != AccessScope.INTERNAL:
        raise AuthorizationError(
            "Access denied: Platform-wide access requires INTERNAL scope",
            status_code=403,
        )


def enforce_merchant_access(principal: Principal, merchant_id: Union[UUID, str]) -> None:
    """
    Enforce that the principal is authorized to access the specified merchant's resources.
    - INTERNAL principals are permitted access to any merchant.
    - MERCHANT principals are permitted access ONLY to their own associated merchant_id.
    - Any attempt by a merchant to access another merchant's resources is strictly forbidden (403).
    """
    target_uuid = merchant_id if isinstance(merchant_id, UUID) else UUID(str(merchant_id))

    if principal.scope == AccessScope.INTERNAL:
        return

    if principal.scope == AccessScope.MERCHANT:
        if principal.merchant_id != target_uuid:
            raise AuthorizationError(
                "Access denied: Cross-merchant access forbidden",
                status_code=403,
            )
        return

    raise AuthorizationError("Access denied: Unauthorized access scope", status_code=403)

