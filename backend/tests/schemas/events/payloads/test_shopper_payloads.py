from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import (
    AddToCartPayload,
    CartItem,
    CheckoutStartedPayload,
    OrderItemPayload,
    ProductSearchedPayload,
    ProductViewedPayload,
    PurchaseCompletedPayload,
    RecommendationClickedPayload,
    RecommendationViewedPayload,
    RemoveFromCartPayload,
    SaveForLaterAddedPayload,
    SaveForLaterRemovedPayload,
    SessionEndedPayload,
    SessionStartedPayload,
    WishlistAddedPayload,
    WishlistRemovedPayload,
)
from app.schemas.events.registry import get_payload_schema


def test_shopper_payload_registry_mappings():
    assert get_payload_schema(ShopperEventType.SESSION_STARTED.value, 1) == SessionStartedPayload
    assert get_payload_schema(ShopperEventType.SESSION_ENDED.value, 1) == SessionEndedPayload
    assert get_payload_schema(ShopperEventType.PRODUCT_VIEWED.value, 1) == ProductViewedPayload
    assert get_payload_schema(ShopperEventType.PRODUCT_SEARCHED.value, 1) == ProductSearchedPayload
    assert get_payload_schema(ShopperEventType.WISHLIST_ADDED.value, 1) == WishlistAddedPayload
    assert get_payload_schema(ShopperEventType.WISHLIST_REMOVED.value, 1) == WishlistRemovedPayload
    assert get_payload_schema(ShopperEventType.SAVE_FOR_LATER_ADDED.value, 1) == SaveForLaterAddedPayload
    assert get_payload_schema(ShopperEventType.SAVE_FOR_LATER_REMOVED.value, 1) == SaveForLaterRemovedPayload
    assert get_payload_schema(ShopperEventType.ADD_TO_CART.value, 1) == AddToCartPayload
    assert get_payload_schema(ShopperEventType.REMOVE_FROM_CART.value, 1) == RemoveFromCartPayload
    assert get_payload_schema(ShopperEventType.CHECKOUT_STARTED.value, 1) == CheckoutStartedPayload
    assert get_payload_schema(ShopperEventType.PURCHASE_COMPLETED.value, 1) == PurchaseCompletedPayload
    assert get_payload_schema(ShopperEventType.RECOMMENDATION_VIEWED.value, 1) == RecommendationViewedPayload
    assert get_payload_schema(ShopperEventType.RECOMMENDATION_CLICKED.value, 1) == RecommendationClickedPayload


def test_shopper_event_envelope_requires_session_id():
    # Missing session_id
    with pytest.raises(ValueError):
        ShopperEventEnvelope(
            event_id=uuid4(),
            event_version=1,
            event_timestamp="2024-01-01T00:00:00Z",
            source="test",
            event_type=ShopperEventType.SESSION_STARTED,
            merchant_id=uuid4(),
            shopper_id=uuid4(),
            payload={"referrer": "google.com"},
        )

    # With session_id
    envelope = ShopperEventEnvelope(
        event_id=uuid4(),
        event_version=1,
        event_timestamp="2024-01-01T00:00:00Z",
        source="test",
        event_type=ShopperEventType.SESSION_STARTED,
        merchant_id=uuid4(),
        shopper_id=uuid4(),
        session_id=uuid4(),
        payload={"referrer": "google.com"},
    )
    assert envelope.session_id is not None


def test_purchase_completed_payload_serialization():
    # Test decimal serialization and multi-item lists
    payload_data = {
        "order_id": str(uuid4()),
        "total_amount": "99.99",
        "items": [
            {
                "product_id": str(uuid4()),
                "variant_id": str(uuid4()),
                "quantity": 2,
                "unit_price": "29.99",
            },
            {
                "product_id": str(uuid4()),
                "variant_id": str(uuid4()),
                "quantity": 1,
                "unit_price": "40.01",
            },
        ],
        "email": "test@example.com",
    }

    payload = PurchaseCompletedPayload(**payload_data)
    assert payload.total_amount == Decimal("99.99")
    assert len(payload.items) == 2
    assert payload.items[0].unit_price == Decimal("29.99")
    assert payload.items[1].unit_price == Decimal("40.01")
    
    # Test email is optional
    payload_no_email = PurchaseCompletedPayload(
        order_id=payload.order_id,
        total_amount=payload.total_amount,
        items=payload.items,
        email=None,
    )
    assert payload_no_email.email is None


def test_checkout_started_payload_serialization():
    payload = CheckoutStartedPayload(
        cart_value=Decimal("50.00"),
        items=[
            CartItem(
                product_id=uuid4(),
                variant_id=uuid4(),
                quantity=1,
                unit_price=Decimal("50.00"),
            )
        ]
    )
    assert payload.cart_value == Decimal("50.00")
    assert payload.email is None

