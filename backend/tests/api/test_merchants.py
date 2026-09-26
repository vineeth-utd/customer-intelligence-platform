import datetime
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
from app.schemas.merchant import MerchantDetailResponse, MerchantSummaryResponse, SubscriptionResponse
from app.schemas.shopper import ShopperResponse
from app.schemas.order import OrderResponse

client = TestClient(app)

MERCHANT_ID = uuid.uuid4()

@patch("app.api.merchants.list_merchants")
def test_read_merchants(mock_list):
    mock_list.return_value = (
        [
            MerchantSummaryResponse(
                merchant_id=MERCHANT_ID,
                merchant_name="Test Store",
                shopify_store_id="test-store.myshopify.com",
                email="admin@test.com",
                store_currency="USD",
                app_install_status="installed",
                last_active_at=datetime.datetime(2023, 10, 1, tzinfo=datetime.timezone.utc)
            )
        ],
        1
    )
    response = client.get("/api/v1/merchants")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["merchant_name"] == "Test Store"

@patch("app.api.merchants.get_merchant_detail")
def test_read_merchant_detail(mock_get):
    mock_get.return_value = MerchantDetailResponse(
        merchant_id=MERCHANT_ID,
        merchant_name="Test Store",
        shopify_store_id="test-store.myshopify.com",
        email="admin@test.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
        active_subscription=SubscriptionResponse(
            plan_id=uuid.uuid4(),
            status="active",
            billing_cycle="monthly",
            amount_paid=99.99,
            started_at=datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
        )
    )
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_name"] == "Test Store"
    assert data["active_subscription"]["status"] == "active"

@patch("app.api.merchants.get_merchant_detail")
def test_read_merchant_detail_not_found(mock_get):
    mock_get.return_value = None
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}")
    assert response.status_code == 404

@patch("app.api.merchants.list_shoppers")
def test_read_merchant_shoppers(mock_list):
    shopper_id = uuid.uuid4()
    mock_list.return_value = (
        [
            ShopperResponse(
                shopper_id=shopper_id,
                merchant_id=MERCHANT_ID,
                email="shopper@test.com"
            )
        ],
        1
    )
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/shoppers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "shopper@test.com"

@patch("app.api.merchants.list_orders")
def test_read_merchant_orders(mock_list):
    order_id = uuid.uuid4()
    mock_list.return_value = (
        [
            OrderResponse(
                order_id=order_id,
                merchant_id=MERCHANT_ID,
                shopper_id=uuid.uuid4(),
                order_status="completed",
                currency="USD",
                total_amount=100.0,
                placed_at=datetime.datetime(2023, 10, 1, tzinfo=datetime.timezone.utc)
            )
        ],
        1
    )
    response = client.get(f"/api/v1/merchants/{MERCHANT_ID}/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["order_status"] == "completed"



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
    assert response.status_code == 200
    data = response.json()
    assert data["revenue"] == "0"
    assert data["order_count"] == 0

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
