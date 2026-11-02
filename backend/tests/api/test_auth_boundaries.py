import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.schemas.analytics import PlatformSummaryResult
from app.schemas.auth import AccessScope
from app.schemas.merchant import MerchantDetailResponse, MerchantSummaryResponse

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


@pytest.fixture
def merchant_b_headers():
    token = create_access_token(
        user_id="usr_merchant_b",
        scope=AccessScope.MERCHANT,
        merchant_id=MERCHANT_B_ID,
        email="owner_b@store.com",
    )
    return {"Authorization": f"Bearer {token}"}


def test_public_health_endpoint_unauthenticated():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unauthenticated_request_rejected():
    response = client.get("/api/v1/analytics/platform/summary")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_bearer_token_rejected():
    response = client.get(
        "/api/v1/analytics/platform/summary",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
    assert 'error="invalid_token"' in response.headers.get("WWW-Authenticate", "")


def test_expired_token_rejected():
    expired_token = create_access_token(
        user_id="usr_admin",
        scope=AccessScope.INTERNAL,
        expires_delta_seconds=-60,
    )
    response = client.get(
        "/api/v1/analytics/platform/summary",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@patch("app.api.analytics.get_platform_summary")
def test_platform_analytics_allowed_for_internal(mock_get, internal_headers):
    mock_get.return_value = PlatformSummaryResult(
        total_merchants=5,
        active_merchants=3,
        total_revenue=Decimal("500.00"),
        total_orders=10,
        active_shoppers=8,
        active_subscriptions=2,
    )
    response = client.get("/api/v1/analytics/platform/summary", headers=internal_headers)
    assert response.status_code == 200


def test_platform_analytics_forbidden_for_merchant(merchant_a_headers):
    response = client.get("/api/v1/analytics/platform/summary", headers=merchant_a_headers)
    assert response.status_code == 403
    assert "Platform-wide access requires INTERNAL scope" in response.json()["detail"]

    trend_response = client.get(
        "/api/v1/analytics/platform/trend?start_date=2023-01-01&end_date=2023-01-31",
        headers=merchant_a_headers,
    )
    assert trend_response.status_code == 403

    features_response = client.get(
        "/api/v1/analytics/features",
        headers=merchant_a_headers,
    )
    assert features_response.status_code == 403


@patch("app.api.merchants.list_merchants")
def test_merchant_list_allowed_for_internal(mock_list, internal_headers):
    mock_list.return_value = ([], 0)
    response = client.get("/api/v1/merchants", headers=internal_headers)
    assert response.status_code == 200


def test_merchant_list_forbidden_for_merchant(merchant_a_headers):
    # GET /api/v1/merchants is a platform-wide endpoint, merchants cannot list all merchants
    response = client.get("/api/v1/merchants", headers=merchant_a_headers)
    assert response.status_code == 403
    assert "Platform-wide access requires INTERNAL scope" in response.json()["detail"]


@patch("app.api.merchants.get_merchant_detail")
def test_merchant_scoped_access_allowed_for_own_merchant(mock_get, merchant_a_headers):
    mock_get.return_value = MerchantDetailResponse(
        merchant_id=MERCHANT_A_ID,
        merchant_name="Store A",
        shopify_store_id="store-a.myshopify.com",
        email="owner_a@store.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
        active_subscription=None,
    )
    response = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}", headers=merchant_a_headers)
    assert response.status_code == 200
    assert response.json()["merchant_name"] == "Store A"


@patch("app.api.merchants.get_merchant_detail")
def test_cross_merchant_access_strictly_forbidden(mock_get, merchant_a_headers):
    # Merchant A attempting to access Merchant B
    response = client.get(f"/api/v1/merchants/{MERCHANT_B_ID}", headers=merchant_a_headers)
    assert response.status_code == 403
    assert "Cross-merchant access forbidden" in response.json()["detail"]

    # Authorization check must execute before service/DAL lookup (no info disclosure)
    mock_get.assert_not_called()


@patch("app.api.merchants.list_shoppers")
def test_cross_merchant_subresources_forbidden(mock_shoppers, merchant_a_headers):
    response = client.get(f"/api/v1/merchants/{MERCHANT_B_ID}/shoppers", headers=merchant_a_headers)
    assert response.status_code == 403
    assert "Cross-merchant access forbidden" in response.json()["detail"]
    mock_shoppers.assert_not_called()


@patch("app.api.merchants.get_merchant_detail")
def test_internal_scope_can_access_any_merchant(mock_get, internal_headers):
    mock_get.return_value = MerchantDetailResponse(
        merchant_id=MERCHANT_A_ID,
        merchant_name="Store A",
        shopify_store_id="store-a.myshopify.com",
        email="owner_a@store.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
        active_subscription=None,
    )
    response_a = client.get(f"/api/v1/merchants/{MERCHANT_A_ID}", headers=internal_headers)
    assert response_a.status_code == 200

    mock_get.return_value = MerchantDetailResponse(
        merchant_id=MERCHANT_B_ID,
        merchant_name="Store B",
        shopify_store_id="store-b.myshopify.com",
        email="owner_b@store.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
        active_subscription=None,
    )
    response_b = client.get(f"/api/v1/merchants/{MERCHANT_B_ID}", headers=internal_headers)
    assert response_b.status_code == 200

