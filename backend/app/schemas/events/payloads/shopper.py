from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.registry import register_event_payload


@register_event_payload(ShopperEventType.SESSION_STARTED.value, 1)
class SessionStartedPayload(BaseModel):
    referrer: str | None = None
    email: str | None = None


@register_event_payload(ShopperEventType.SESSION_ENDED.value, 1)
class SessionEndedPayload(BaseModel):
    pass


@register_event_payload(ShopperEventType.PRODUCT_VIEWED.value, 1)
class ProductViewedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.PRODUCT_SEARCHED.value, 1)
class ProductSearchedPayload(BaseModel):
    search_query: str
    result_count: int | None = None


@register_event_payload(ShopperEventType.WISHLIST_ADDED.value, 1)
class WishlistAddedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.WISHLIST_REMOVED.value, 1)
class WishlistRemovedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.SAVE_FOR_LATER_ADDED.value, 1)
class SaveForLaterAddedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.SAVE_FOR_LATER_REMOVED.value, 1)
class SaveForLaterRemovedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.ADD_TO_CART.value, 1)
class AddToCartPayload(BaseModel):
    product_id: UUID
    variant_id: UUID
    quantity: int
    unit_price: Decimal


@register_event_payload(ShopperEventType.REMOVE_FROM_CART.value, 1)
class RemoveFromCartPayload(BaseModel):
    product_id: UUID
    variant_id: UUID
    quantity: int  # The quantity being removed, allowing partial removal


class CartItem(BaseModel):
    product_id: UUID
    variant_id: UUID
    quantity: int
    unit_price: Decimal


@register_event_payload(ShopperEventType.CHECKOUT_STARTED.value, 1)
class CheckoutStartedPayload(BaseModel):
    cart_value: Decimal
    items: list[CartItem]
    email: str | None = None


class OrderItemPayload(BaseModel):
    product_id: UUID
    variant_id: UUID
    quantity: int
    unit_price: Decimal


@register_event_payload(ShopperEventType.PURCHASE_COMPLETED.value, 1)
class PurchaseCompletedPayload(BaseModel):
    order_id: UUID
    total_amount: Decimal
    items: list[OrderItemPayload]
    email: str | None = None


@register_event_payload(ShopperEventType.RECOMMENDATION_VIEWED.value, 1)
class RecommendationViewedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@register_event_payload(ShopperEventType.RECOMMENDATION_CLICKED.value, 1)
class RecommendationClickedPayload(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None

