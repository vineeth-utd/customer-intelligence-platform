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

