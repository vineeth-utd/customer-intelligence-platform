from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.schemas.analytics import (
    FeatureMetricsResult,
    PlatformSummaryResult,
    PlatformTrendResult,
)
from app.schemas.auth import AccessScope

client = TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id="test_admin", scope=AccessScope.INTERNAL)
    return {"Authorization": f"Bearer {token}"}


@patch("app.api.analytics.get_platform_summary")
def test_read_platform_summary_success(mock_get, auth_headers):
    mock_get.return_value = PlatformSummaryResult(
        total_merchants=10,
        active_merchants=5,
        total_revenue=Decimal("1000.00"),
        total_orders=100,
        active_shoppers=50,
        active_subscriptions=8,
    )

    response = client.get("/api/v1/analytics/platform/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_merchants"] == 10
    assert data["total_revenue"] == "1000.00"


@patch("app.api.analytics.get_platform_summary")
def test_read_platform_summary_not_found(mock_get, auth_headers):
    mock_get.return_value = None

    response = client.get("/api/v1/analytics/platform/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_merchants"] == 0
    assert data["total_revenue"] == "0"


@patch("app.api.analytics.get_platform_metrics_trend")
def test_read_platform_trend_success(mock_get, auth_headers):
    mock_get.return_value = [
        PlatformTrendResult(
            metric_date=date(2023, 10, 1),
            active_merchants=5,
            new_merchants=1,
            installed_merchants=10,
            uninstalled_merchants=0,
            new_subscriptions=1,
            subscription_upgrades=0,
            subscription_downgrades=0,
            subscription_cancellations=0,
            total_revenue=Decimal("100.00"),
            total_orders=10,
            active_shoppers=5,
        )
    ]

    response = client.get(
        "/api/v1/analytics/platform/trend?start_date=2023-10-01&end_date=2023-10-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["active_merchants"] == 5


def test_read_platform_trend_invalid_dates(auth_headers):
    response = client.get(
        "/api/v1/analytics/platform/trend?start_date=2023-10-31&end_date=2023-10-01",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"]


@patch("app.api.analytics.get_feature_metrics_summary")
def test_read_feature_metrics_success(mock_get, auth_headers):
    mock_get.return_value = [
        FeatureMetricsResult(
            feature_id="123e4567-e89b-12d3-a456-426614174000",
            feature_key="test_feature",
            feature_name="Test Feature",
            feature_category="test",
            eligible_merchant_count=10,
            enabled_merchant_count=5,
            active_merchant_count=2,
            total_feature_events=100,
            adoption_rate=Decimal("0.5"),
            usage_rate=Decimal("0.4"),
        )
    ]

    response = client.get("/api/v1/analytics/features", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["feature_key"] == "test_feature"
    assert data[0]["adoption_rate"] == "0.5"


@patch("app.api.analytics.get_feature_metrics_summary")
def test_read_feature_metrics_empty(mock_get, auth_headers):
    mock_get.return_value = []

    response = client.get("/api/v1/analytics/features", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
