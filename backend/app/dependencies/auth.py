from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.enforcer import enforce_merchant_access, enforce_platform_access
from app.auth.exceptions import AuthenticationError, AuthorizationError
from app.auth.token import decode_access_token
from app.schemas.auth import Principal

# auto_error=False allows us to return a customized 401 response with WWW-Authenticate header
security = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Principal:
    """
    Extract and validate the Bearer token from the Authorization header.
    Returns the authenticated Principal or raises HTTP 401 Unauthorized.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication scheme must be Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_access_token(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )


async def require_internal_principal(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """
    Enforce that the authenticated caller has INTERNAL (platform-wide) scope.
    Returns the Principal if permitted or raises HTTP 403 Forbidden.
    """
    try:
        enforce_platform_access(principal)
        return principal
    except AuthorizationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


async def require_merchant_access(
    merchant_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """
    Enforce that the authenticated caller is authorized to access the given merchant's resources.
    - INTERNAL principals are permitted access to any merchant.
    - MERCHANT principals are permitted access ONLY to their own associated merchant_id.
    Raises HTTP 403 Forbidden before any resource retrieval occurs if unauthorized.
    """
    try:
        enforce_merchant_access(principal, merchant_id)
        return principal
    except AuthorizationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )

