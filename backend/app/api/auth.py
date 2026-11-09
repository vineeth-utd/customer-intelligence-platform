from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import create_access_token
from app.config.settings import settings
from app.dependencies.db import get_db
from app.schemas.auth import (
    AccessScope,
    DevMerchantOption,
    DevPrincipalsResponse,
    DevTokenRequest,
    DevTokenResponse,
    Principal,
)
from app.services.merchant import list_merchants

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _check_development_env() -> None:
    if settings.environment != "development":
        raise HTTPException(
            status_code=404,
            detail="Development auth endpoints are only available in development environment",
        )


@router.post("/dev-token", response_model=DevTokenResponse)
async def create_dev_token(request: DevTokenRequest) -> DevTokenResponse:
    """
    Generate a signed MVP Bearer token for local development.
    Only available when settings.environment == 'development'.
    """
    _check_development_env()

    if request.scope == AccessScope.INTERNAL:
        user_id = request.user_id or "dev-admin"
        email = request.email or "admin@cip.local"
        roles = request.roles if request.roles is not None else ["admin"]
        merchant_id = None
    elif request.scope == AccessScope.MERCHANT:
        if not request.merchant_id:
            raise HTTPException(
                status_code=400,
                detail="merchant_id is required for MERCHANT scope",
            )
        user_id = request.user_id or f"dev-merchant-{str(request.merchant_id)[:8]}"
        email = request.email or "merchant@cip.local"
        roles = request.roles if request.roles is not None else ["merchant"]
        merchant_id = request.merchant_id
    else:
        raise HTTPException(status_code=400, detail="Invalid access scope")

    principal = Principal(
        user_id=user_id,
        scope=request.scope,
        merchant_id=merchant_id,
        email=email,
        roles=roles,
    )

    token = create_access_token(
        user_id=user_id,
        scope=request.scope,
        merchant_id=merchant_id,
        email=email,
        roles=roles,
    )

    return DevTokenResponse(
        access_token=token,
        token_type="bearer",
        principal=principal,
    )


@router.get("/dev-principals", response_model=DevPrincipalsResponse)
async def list_dev_principals(session: AsyncSession = Depends(get_db)) -> DevPrincipalsResponse:
    """
    Retrieve convenient development identity presets and available merchants
    for the local frontend identity selector.
    """
    _check_development_env()

    merchants, _total = await list_merchants(session, limit=20, offset=0)

    return DevPrincipalsResponse(
        internal=Principal(
            user_id="dev-admin",
            scope=AccessScope.INTERNAL,
            email="admin@cip.local",
            roles=["admin"],
        ),
        merchants=[
            DevMerchantOption(
                merchant_id=m.merchant_id,
                merchant_name=m.merchant_name,
                shopify_store_id=m.shopify_store_id,
            )
            for m in merchants
        ],
    )

