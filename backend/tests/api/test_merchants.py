from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import uuid

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
)

client = TestClient(app)

MERCHANT_ID = uuid.uuid4()

@patch("app.api.merchants.get_merchant_metrics_summary")
def test_read_merchant_metrics_summary_success(mock_get):
    mock_get.return_value = MerchantMetricsSummaryResult(
        merchant_id=MERCHANT_ID,
        revenue=Decimal("500.00"),
        order_count=50,
        unique_shoppers=25,
        new_shoppers=10,
        session_count=100,
        converted_session_count=50,
        product_view_count=200,
        wishlist_add_count=10,
        save_for_later_count=5,
        add_to_cart_count=60,
        checkout_count=55,
        purchase_count=50,
        conversion_rate=Decimal("0.5"),
        average_order_value=Decimal("10.00"),
        platform_login_count=5,
        campaign_created_count=2,
        feature_enable_count=1,
        feature_disable_count=0
    )
    
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/analytics/summary?start_date=2023-10-01&end_date=2023-10-31")
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == str(MERCHANT_ID)
    assert data["revenue"] == "500.00"

@patch("app.api.merchants.get_merchant_metrics_summary")
def test_read_merchant_metrics_summary_not_found(mock_get):
    mock_get.return_value = None
    
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/analytics/summary?start_date=2023-10-01&end_date=2023-10-31")
    assert response.status_code == 404

def test_read_merchant_metrics_summary_invalid_dates():
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/analytics/summary?start_date=2023-10-31&end_date=2023-10-01")
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"]

@patch("app.api.merchants.get_merchant_metrics_trend")
def test_read_merchant_metrics_trend_success(mock_get):
    mock_get.return_value = [
        MerchantMetricsTrendResult(
            metric_date=date(2023, 10, 1),
            merchant_id=MERCHANT_ID,
            revenue=Decimal("100.00"),
            order_count=10,
            unique_shoppers=5,
            new_shoppers=2,
            session_count=20,
            converted_session_count=10,
            product_view_count=40,
            wishlist_add_count=2,
            save_for_later_count=1,
            add_to_cart_count=12,
            checkout_count=11,
            purchase_count=10,
            conversion_rate=Decimal("0.5"),
            average_order_value=Decimal("10.00"),
            platform_login_count=1,
            campaign_created_count=0,
            feature_enable_count=0,
            feature_disable_count=0
        )
    ]
    
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/analytics/trend?start_date=2023-10-01&end_date=2023-10-31")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["revenue"] == "100.00"

def test_read_merchant_metrics_trend_invalid_dates():
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/analytics/trend?start_date=2023-10-31&end_date=2023-10-01")
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"]

@patch("app.api.merchants.get_campaign_analytics_for_merchant")
def test_read_campaign_analytics_success(mock_get):
    mock_get.return_value = [
        CampaignAnalyticsResult(
            campaign_id=uuid.uuid4(),
            campaign_name="Test Campaign",
            campaign_type="marketing",
            campaign_medium="email",
            status="active",
            delivered_count=1000,
            opened_count=500,
            clicked_count=100,
            converted_count=10,
            attributed_order_count=10,
            attributed_revenue=Decimal("500.00"),
            open_rate=Decimal("0.5"),
            click_through_rate=Decimal("0.1"),
            conversion_rate=Decimal("0.01")
        )
    ]
    
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/campaigns/analytics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["campaign_name"] == "Test Campaign"

@patch("app.api.merchants.get_campaign_analytics_for_merchant")
def test_read_campaign_analytics_empty(mock_get):
    mock_get.return_value = []
    
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/campaigns/analytics")
    assert response.status_code == 200
    assert response.json() == []
