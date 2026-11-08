from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.models.journey import MerchantJourney, MerchantJourneyEvent
from app.models.profile import MerchantProfile
from app.schemas.auth import AccessScope
from app.schemas.merchant import (
    MerchantFeatureResponse,
    SubscriptionResponse,
)

client = TestClient(app)

MERCHANT_A_ID = uuid.uuid4()
MERCHANT_B_ID = uuid.uuid4()


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


@patch("app.api.merchants.get_merchant_profile")
def test_read_merchant_profile_success(mock_profile, internal_headers):
    now = datetime.now(timezone.utc)
    mock_profile.return_value = MerchantProfile(
        merchant_id=MERCHANT_A_ID,
        total_shoppers=150,
        total_products=25,
        total_orders=300,
        total_revenue=Decimal("15000.50"),
        average_order_value=Decimal("50.00"),
        conversion_rate=Decimal("0.05"),
        total_campaigns=4,
        active_campaign_count=2,
        enabled_feature_count=3,
        last_order_at=now,
        last_campaign_at=now,
        generated_at=now,
    )

    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/profile", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == str(MERCHANT_A_ID)
    assert data["total_shoppers"] == 150
    assert data["total_revenue"] == 15000.5
    assert data["conversion_rate"] == 0.05


@patch("app.api.merchants.get_merchant_profile")
def test_read_merchant_profile_not_found(mock_profile, internal_headers):
    mock_profile.return_value = None
    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/profile", headers=internal_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Merchant profile not found"


def test_read_merchant_profile_cross_merchant_forbidden(merchant_a_headers):
    response = client.get(f"/api/v1/merchants/{MERCHANT_B_ID}/profile", headers=merchant_a_headers)
    assert response.status_code == 403
    assert "Cross-merchant access forbidden" in response.json()["detail"]


@patch("app.api.merchants.get_merchant_health_with_factors")
def test_read_merchant_health_success(mock_health, internal_headers):
    now = datetime.now(timezone.utc)
    mock_health.return_value = {
        "merchant_id": MERCHANT_A_ID,
        "health_score": 85.5,
        "health_status": "Healthy",
        "churn_risk_score": 14.5,
        "engagement_score": 90.0,
        "feature_adoption_score": 80.0,
        "business_performance_score": 86.5,
        "calculated_at": now.isoformat(),
        "contributing_factors": {
            "feature_adoption": {"score": 80.0, "details": "4/5 features"},
            "engagement": {"score": 90.0, "details": "high active frequency"},
            "business_performance": {"score": 86.5, "growth": "+10%"},
            "subscription": {"status": "active", "plan_key": "growth"},
            "risk_alerts": [],
        },
    }

    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/health", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["health_score"] == 85.5
    assert data["churn_risk_score"] == 14.5
    assert data["contributing_factors"]["subscription"]["status"] == "active"


@patch("app.api.merchants.get_merchant_health_with_factors")
def test_read_merchant_health_not_found(mock_health, internal_headers):
    mock_health.return_value = None
    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/health", headers=internal_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Merchant health not found"


@patch("app.api.merchants.get_merchant_journeys_for_merchant")
def test_read_merchant_journeys_success(mock_journeys, internal_headers):
    now = datetime.now(timezone.utc)
    mock_journeys.return_value = [
        MerchantJourney(
            merchant_journey_id=uuid.uuid4(),
            merchant_id=MERCHANT_A_ID,
            started_at=now,
            ended_at=None,
            journey_status="ACTIVE",
            generated_at=now,
        )
    ]

    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/journeys", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["journey_status"] == "ACTIVE"


@patch("app.api.merchants.get_merchant_journeys_for_merchant")
def test_read_merchant_journeys_empty(mock_journeys, internal_headers):
    mock_journeys.return_value = []
    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/journeys", headers=internal_headers)
    assert response.status_code == 200
    assert response.json() == []


@patch("app.api.merchants.get_merchant_journey")
def test_read_merchant_journey_detail_success(mock_get_journey, internal_headers):
    now = datetime.now(timezone.utc)
    journey_id = uuid.uuid4()
    journey = MerchantJourney(
        merchant_journey_id=journey_id,
        merchant_id=MERCHANT_A_ID,
        started_at=now,
        ended_at=None,
        journey_status="ACTIVE",
        generated_at=now,
    )
    journey.events = [
        MerchantJourneyEvent(
            merchant_journey_event_id=uuid.uuid4(),
            merchant_journey_id=journey_id,
            source_event_category="merchant",
            source_event_id=uuid.uuid4(),
            event_type="app_installed",
            event_timestamp=now,
            sequence_number=1,
        )
    ]
    mock_get_journey.return_value = journey

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/journeys/{journey_id}", headers=internal_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_journey_id"] == str(journey_id)
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "app_installed"


@patch("app.api.merchants.get_merchant_journey")
def test_read_merchant_journey_detail_ownership_mismatch(mock_get_journey, internal_headers):
    now = datetime.now(timezone.utc)
    journey_id = uuid.uuid4()
    # Journey belongs to Merchant B
    journey = MerchantJourney(
        merchant_journey_id=journey_id,
        merchant_id=MERCHANT_B_ID,
        started_at=now,
        ended_at=None,
        journey_status="ACTIVE",
        generated_at=now,
    )
    mock_get_journey.return_value = journey

    # Requesting under Merchant A path
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/journeys/{journey_id}", headers=internal_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Merchant journey not found"


@patch("app.api.merchants.get_merchant_features")
def test_read_merchant_features_success(mock_features, internal_headers):
    mock_features.return_value = [
        MerchantFeatureResponse(
            feature_id=uuid.uuid4(),
            feature_key="automated_campaigns",
            feature_name="Automated Campaigns",
            feature_category="marketing",
            description="Run automatic campaigns",
            is_entitled=True,
            is_enabled=False,
        )
    ]

    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/features", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["feature_key"] == "automated_campaigns"
    assert data[0]["is_entitled"] is True
    assert data[0]["is_enabled"] is False


@patch("app.api.merchants.get_merchant_subscription_detail")
def test_read_merchant_subscription_success(mock_sub, internal_headers):
    now = datetime.now(timezone.utc)
    mock_sub.return_value = SubscriptionResponse(
        plan_id=uuid.uuid4(),
        plan_name="Growth",
        status="active",
        billing_cycle="monthly",
        amount_paid=49.99,
        started_at=now,
        renewal_at=now,
        cancelled_at=None,
    )

    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/subscription", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["plan_name"] == "Growth"
    assert data["status"] == "active"
    assert data["amount_paid"] == 49.99


@patch("app.api.merchants.get_merchant_subscription_detail")
def test_read_merchant_subscription_not_found(mock_sub, internal_headers):
    mock_sub.return_value = None
    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}/subscription", headers=internal_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Subscription not found for merchant"


def test_merchant_endpoints_unauthenticated_rejected():
    for endpoint in [
        f"/api/v1/merchants/{MERCHANT_A_ID}/profile",
        f"/api/v1/merchants/{MERCHANT_A_ID}/health",
        f"/api/v1/merchants/{MERCHANT_A_ID}/journeys",
        f"/api/v1/merchants/{MERCHANT_A_ID}/features",
        f"/api/v1/merchants/{MERCHANT_A_ID}/subscription",
    ]:
        resp = client.get(endpoint)
        assert resp.status_code == 401

