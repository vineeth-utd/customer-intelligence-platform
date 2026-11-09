from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import decode_access_token
from app.main import app
from app.schemas.auth import AccessScope

client = TestClient(app)


def test_create_dev_token_internal():
    payload = {
        "scope": "INTERNAL",
        "user_id": "custom-admin",
        "email": "custom-admin@cip.local",
        "roles": ["admin", "superadmin"],
    }
    response = client.post("/api/v1/auth/dev-token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["principal"]["scope"] == "INTERNAL"
    assert data["principal"]["user_id"] == "custom-admin"
    assert data["principal"]["email"] == "custom-admin@cip.local"
    assert data["principal"]["roles"] == ["admin", "superadmin"]

    # Verify token can be decoded by auth service
    principal = decode_access_token(data["access_token"])
    assert principal.scope == AccessScope.INTERNAL
    assert principal.user_id == "custom-admin"


def test_create_dev_token_merchant_success():
    merchant_id = str(uuid.uuid4())
    payload = {
        "scope": "MERCHANT",
        "merchant_id": merchant_id,
    }
    response = client.post("/api/v1/auth/dev-token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["principal"]["scope"] == "MERCHANT"
    assert data["principal"]["merchant_id"] == merchant_id

    principal = decode_access_token(data["access_token"])
    assert principal.scope == AccessScope.MERCHANT
    assert str(principal.merchant_id) == merchant_id


def test_create_dev_token_merchant_missing_merchant_id():
    payload = {
        "scope": "MERCHANT",
    }
    response = client.post("/api/v1/auth/dev-token", json=payload)
    assert response.status_code == 400
    assert "merchant_id is required" in response.json()["detail"]


def test_dev_token_rejected_in_non_development_env():
    with patch("app.api.auth.settings.environment", "production"):
        payload = {"scope": "INTERNAL"}
        response = client.post("/api/v1/auth/dev-token", json=payload)
        assert response.status_code == 404

        response = client.get("/api/v1/auth/dev-principals")
        assert response.status_code == 404


def test_get_dev_principals():
    with patch("app.api.auth.list_merchants") as mock_list:
        from unittest.mock import MagicMock
        mock_merchant = MagicMock()
        mock_merchant.merchant_id = uuid.uuid4()
        mock_merchant.merchant_name = "Acme Store"
        mock_merchant.shopify_store_id = "acme.myshopify.com"
        mock_list.return_value = ([mock_merchant], 1)

        response = client.get("/api/v1/auth/dev-principals")
        assert response.status_code == 200
        data = response.json()
        assert "internal" in data
        assert data["internal"]["scope"] == "INTERNAL"
        assert "merchants" in data
        assert len(data["merchants"]) == 1
        assert data["merchants"][0]["merchant_name"] == "Acme Store"



def test_dev_token_can_access_protected_api():
    # Generate token
    res = client.post("/api/v1/auth/dev-token", json={"scope": "INTERNAL"})
    token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.api.analytics.get_platform_summary") as mock_summary:
        from app.schemas.analytics import PlatformSummaryResult
        from decimal import Decimal

        mock_summary.return_value = PlatformSummaryResult(
            total_merchants=5,
            active_merchants=4,
            total_revenue=Decimal("1000.00"),
            total_orders=50,
            active_shoppers=30,
            active_subscriptions=4,
        )
        api_res = client.get("/api/v1/analytics/platform/summary", headers=headers)
        assert api_res.status_code == 200
