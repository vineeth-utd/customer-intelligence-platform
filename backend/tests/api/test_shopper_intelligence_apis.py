from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.order import Order
from app.models.profile import ShopperProfile
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.schemas.auth import AccessScope
from app.schemas.shopper import ShopperActivityEventResponse

client = TestClient(app)

MERCHANT_A_ID = uuid.uuid4()
MERCHANT_B_ID = uuid.uuid4()
SHOPPER_1_ID = uuid.uuid4()
SHOPPER_2_ID = uuid.uuid4()


@pytest.fixture
def internal_headers():
    token = create_access_token(
        user_id="usr_internal_admin",
        scope=AccessScope.INTERNAL,
        email="admin@cip.internal",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def merchant_a_headers():
    token = create_access_token(
        user_id="usr_merchant_a",
        scope=AccessScope.MERCHANT,
        merchant_id=MERCHANT_A_ID,
        email="owner_a@store.com",
    )
    return {"Authorization": f"Bearer {token}"}


@patch("app.api.shoppers.get_shopper")
def test_read_shopper_success(mock_get_shopper, internal_headers):
    now = datetime.now(timezone.utc)
    mock_get_shopper.return_value = Shopper(
        shopper_id=SHOPPER_1_ID,
        merchant_id=MERCHANT_A_ID,
        email="shopper1@test.com",
        first_name="Jane",
        last_name="Doe",
        country="US",
        timezone="America/New_York",
        first_seen_at=now,
        last_seen_at=now,
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["shopper_id"] == str(SHOPPER_1_ID)
    assert data["email"] == "shopper1@test.com"


@patch("app.api.shoppers.get_shopper")
def test_read_shopper_not_found(mock_get_shopper, internal_headers):
    mock_get_shopper.return_value = None
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}",
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Shopper not found"


def test_read_shopper_cross_merchant_forbidden(merchant_a_headers):
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_B_ID}/shoppers/{SHOPPER_1_ID}",
        headers=merchant_a_headers,
    )
    assert response.status_code == 403
    assert "Cross-merchant access forbidden" in response.json()["detail"]


@patch("app.api.shoppers.get_shopper_profile")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_profile_success(mock_get_shopper, mock_profile, internal_headers):
    now = datetime.now(timezone.utc)
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_profile.return_value = ShopperProfile(
        shopper_id=SHOPPER_1_ID,
        total_orders=5,
        total_spend=Decimal("250.00"),
        average_order_value=Decimal("50.00"),
        customer_lifetime_value=Decimal("300.00"),
        purchase_frequency=Decimal("2.5"),
        wishlist_item_count=3,
        save_for_later_item_count=1,
        cart_abandonment_count=1,
        campaign_engagement_count=2,
        preferred_category="Footwear",
        preferred_size="M",
        last_purchase_at=now,
        last_activity_at=now,
        lifecycle_stage="REPEAT_CUSTOMER",
        generated_at=now,
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/profile",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["shopper_id"] == str(SHOPPER_1_ID)
    assert data["total_orders"] == 5
    assert data["total_spend"] == 250.0
    assert data["preferred_category"] == "Footwear"


@patch("app.api.shoppers.get_shopper_profile")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_profile_not_found(mock_get_shopper, mock_profile, internal_headers):
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_profile.return_value = None

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/profile",
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Shopper profile not found"


@patch("app.api.shoppers.get_shopper")
def test_read_shopper_profile_shopper_not_found(mock_get_shopper, internal_headers):
    mock_get_shopper.return_value = None
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/profile",
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Shopper not found"


@patch("app.api.shoppers.get_shopper_journeys_for_shopper")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_journeys_success(mock_get_shopper, mock_journeys, internal_headers):
    now = datetime.now(timezone.utc)
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_journeys.return_value = [
        ShopperJourney(
            journey_id=uuid.uuid4(),
            merchant_id=MERCHANT_A_ID,
            shopper_id=SHOPPER_1_ID,
            started_at=now,
            ended_at=now,
            journey_status="CONVERTED",
            converted=True,
            order_id=uuid.uuid4(),
            entry_source="google.com",
            generated_at=now,
        )
    ]

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/journeys",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["converted"] is True
    assert data[0]["entry_source"] == "google.com"


@patch("app.api.shoppers.get_shopper_journeys_for_shopper")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_journeys_empty(mock_get_shopper, mock_journeys, internal_headers):
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_journeys.return_value = []

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/journeys",
        headers=internal_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@patch("app.api.shoppers.get_shopper_journey")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_journey_detail_success(mock_get_shopper, mock_get_journey, internal_headers):
    now = datetime.now(timezone.utc)
    journey_id = uuid.uuid4()
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)

    journey = ShopperJourney(
        journey_id=journey_id,
        merchant_id=MERCHANT_A_ID,
        shopper_id=SHOPPER_1_ID,
        started_at=now,
        ended_at=now,
        journey_status="CONVERTED",
        converted=True,
        generated_at=now,
    )
    journey.events = [
        ShopperJourneyEvent(
            journey_event_id=uuid.uuid4(),
            journey_id=journey_id,
            source_event_category="shopper",
            source_event_id=uuid.uuid4(),
            event_type="product_viewed",
            event_timestamp=now,
            sequence_number=1,
        )
    ]
    mock_get_journey.return_value = journey

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/journeys/{journey_id}",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["journey_id"] == str(journey_id)
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "product_viewed"


@patch("app.api.shoppers.get_shopper_journey")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_journey_detail_ownership_mismatch(mock_get_shopper, mock_get_journey, internal_headers):
    now = datetime.now(timezone.utc)
    journey_id = uuid.uuid4()
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)

    # Journey belongs to Shopper 2
    journey = ShopperJourney(
        journey_id=journey_id,
        merchant_id=MERCHANT_A_ID,
        shopper_id=SHOPPER_2_ID,
        started_at=now,
        ended_at=now,
        journey_status="CONVERTED",
        converted=True,
        generated_at=now,
    )
    mock_get_journey.return_value = journey

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/journeys/{journey_id}",
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Shopper journey not found"


@patch("app.api.shoppers.list_shopper_orders")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_orders_success(mock_get_shopper, mock_orders, internal_headers):
    now = datetime.now(timezone.utc)
    order_id = uuid.uuid4()
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_orders.return_value = (
        [
            Order(
                order_id=order_id,
                merchant_id=MERCHANT_A_ID,
                shopper_id=SHOPPER_1_ID,
                order_status="completed",
                currency="USD",
                total_amount=Decimal("89.99"),
                placed_at=now,
            )
        ],
        1,
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/orders",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["order_id"] == str(order_id)
    assert data["items"][0]["total_amount"] == 89.99


@patch("app.api.shoppers.list_shopper_orders")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_orders_empty(mock_get_shopper, mock_orders, internal_headers):
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)
    mock_orders.return_value = ([], 0)

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/orders",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@patch("app.api.shoppers.get_segments_for_shopper")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_segments_success(mock_get_shopper, mock_segments, internal_headers):
    now = datetime.now(timezone.utc)
    segment_id = uuid.uuid4()
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)

    member = ShopperSegmentMember(
        segment_id=segment_id,
        shopper_id=SHOPPER_1_ID,
        generated_at=now,
    )
    member.segment = ShopperSegment(
        segment_id=segment_id,
        merchant_id=MERCHANT_A_ID,
        segment_name="High Value Shoppers",
        segment_definition={},
    )
    mock_segments.return_value = [member]

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/segments",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["segment_id"] == str(segment_id)
    assert data[0]["segment_name"] == "High Value Shoppers"


@patch("app.api.shoppers.list_shopper_activity")
@patch("app.api.shoppers.get_shopper")
def test_read_shopper_activity_success(mock_get_shopper, mock_activity, internal_headers):
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()
    session_id = uuid.uuid4()
    mock_get_shopper.return_value = Shopper(shopper_id=SHOPPER_1_ID, merchant_id=MERCHANT_A_ID)

    mock_activity.return_value = (
        [
            ShopperActivityEventResponse(
                event_id=event_id,
                session_id=session_id,
                event_type="product_viewed",
                event_timestamp=now,
                source="storefront-web",
                activity_details={
                    "product_id": str(uuid.uuid4()),
                    "product_name": "Leather Boots",
                    "price": 120.0,
                },
            )
        ],
        1,
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/activity",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "product_viewed"
    assert data["items"][0]["activity_details"]["product_name"] == "Leather Boots"


def test_read_shopper_activity_invalid_date_range(internal_headers):
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/activity?start_date=2023-10-31&end_date=2023-10-01",
        headers=internal_headers,
    )
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"]


def test_shopper_endpoints_unauthenticated_rejected():
    for endpoint in [
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}",
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/profile",
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/journeys",
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/orders",
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/segments",
        f"/api/v1/merchants/{MERCHANT_A_ID}/shoppers/{SHOPPER_1_ID}/activity",
    ]:
        resp = client.get(endpoint)
        assert resp.status_code == 401

