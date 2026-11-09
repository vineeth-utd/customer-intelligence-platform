from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AccessScope(str, Enum):
    INTERNAL = "INTERNAL"
    MERCHANT = "MERCHANT"


class Principal(BaseModel):
    user_id: str
    scope: AccessScope
    merchant_id: Optional[UUID] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_merchant_association(self) -> "Principal":
        if self.scope == AccessScope.MERCHANT and self.merchant_id is None:
            raise ValueError("Merchant principals must be associated with a valid merchant_id")
        return self


class TokenPayload(BaseModel):
    sub: str
    scope: AccessScope
    merchant_id: Optional[UUID] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    iat: int
    exp: int


class DevTokenRequest(BaseModel):
    user_id: Optional[str] = None
    scope: AccessScope = AccessScope.INTERNAL
    merchant_id: Optional[UUID] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    principal: Principal


class DevMerchantOption(BaseModel):
    merchant_id: UUID
    merchant_name: str
    shopify_store_id: str


class DevPrincipalsResponse(BaseModel):
    internal: Principal
    merchants: List[DevMerchantOption]


