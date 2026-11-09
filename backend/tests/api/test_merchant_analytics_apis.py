from datetime import date
from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.schemas.analytics import (
    ConversionFunnelResult,
    ConversionFunnelStage,
    CustomerRevenueBreakdown,
    JourneyEntrySourcePerformance,
    PriorPeriodComparison,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
)
from app.schemas.auth import AccessScope

client = TestClient(app)

MERCHANT_A_ID = uuid.uuid4()
MERCHANT_B_ID = uuid.uuid4()


@pytest.fixture
def internal_headers():
    token = create_access_token(user_id="test_admin", scope=AccessScope.INTERNAL)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def merchant_a_headers():
    token = create_access_token(
        user_id="merchant_a", scope=AccessScope.MERCHANT, merchant_id=MERCHANT_A_ID
    )
    return {"Authorization": f"Bearer {token}"}


def test_merchant_analytics_unauthenticated():
    endpoints = [
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/funnel?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/journeys?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/behavior?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/revenue?start_date=2026-01-01&end_date=2026-01-31",
    ]
    for url in endpoints:
        response = client.get(url)
        assert response.status_code == 401, f"Expected 401 for {url}"


def test_merchant_analytics_cross_merchant_forbidden(merchant_a_headers):
    endpoints = [
        f"/api/v1/merchants/{MERCHANT_B_ID}/analytics/funnel?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/analytics/journeys?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/analytics/behavior?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/analytics/revenue?start_date=2026-01-01&end_date=2026-01-31",
    ]
    for url in endpoints:
        response = client.get(url, headers=merchant_a_headers)
        assert response.status_code == 403, f"Expected 403 for {url}"
        assert "Cross-merchant access forbidden" in response.json()["detail"]


def test_merchant_analytics_invalid_date_range(merchant_a_headers):
    endpoints = [
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/funnel?start_date=2026-02-01&end_date=2026-01-01",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/journeys?start_date=2026-02-01&end_date=2026-01-01",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/behavior?start_date=2026-02-01&end_date=2026-01-01",
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/revenue?start_date=2026-02-01&end_date=2026-01-01",
    ]
    for url in endpoints:
        response = client.get(url, headers=merchant_a_headers)
        assert response.status_code == 400, f"Expected 400 for {url}"
        assert "cannot be after" in response.json()["detail"]


@patch("app.api.merchants.get_conversion_funnel")
def test_conversion_funnel_not_found(mock_get, merchant_a_headers):
    mock_get.return_value = None
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/funnel?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Merchant not found"


@patch("app.api.merchants.get_conversion_funnel")
def test_conversion_funnel_success(mock_get, merchant_a_headers):
    mock_get.return_value = ConversionFunnelResult(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        stages=[
            ConversionFunnelStage(stage_name="Sessions", count=1000),
            ConversionFunnelStage(stage_name="Purchases", count=50, step_conversion_rate=Decimal("0.05")),
        ],
        overall_conversion_rate=Decimal("0.05"),
        cart_abandonment_rate=Decimal("0.65"),
        checkout_abandonment_rate=Decimal("0.35"),
        secondary_engagement={"wishlist_adds": 40},
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/funnel?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == str(MERCHANT_A_ID)
    assert len(data["stages"]) == 2
    assert data["overall_conversion_rate"] == "0.05"
    assert data["secondary_engagement"]["wishlist_adds"] == 40


@patch("app.api.merchants.get_shopper_journey_analytics")
def test_shopper_journey_analytics_success(mock_get, internal_headers):
    mock_get.return_value = ShopperJourneyAnalyticsResult(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        total_journeys=500,
        converted_journeys=100,
        non_converting_journeys=350,
        open_journeys=50,
        journey_conversion_rate=Decimal("0.2222"),
        average_conversion_duration_seconds=3600.0,
        drop_off_stages={"CHECKOUT_STARTED": 120},
        by_entry_source=[
            JourneyEntrySourcePerformance(
                entry_source="email",
                total_journeys=200,
                converted_journeys=60,
                non_converting_journeys=120,
                open_journeys=20,
                conversion_rate=Decimal("0.3333"),
            )
        ],
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/journeys?start_date=2026-01-01&end_date=2026-01-31",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_journeys"] == 500
    assert data["drop_off_stages"]["CHECKOUT_STARTED"] == 120
    assert len(data["by_entry_source"]) == 1


@patch("app.api.merchants.get_shopper_behavior_analytics")
def test_shopper_behavior_analytics_success(mock_get, merchant_a_headers):
    mock_get.return_value = ShopperBehaviorAnalyticsResult(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        total_active_shoppers=800,
        new_shoppers=600,
        returning_shoppers=200,
        total_purchasing_shoppers=150,
        repeat_purchasing_shoppers=45,
        repeat_purchase_rate=Decimal("0.3"),
        average_order_value=Decimal("75.50"),
        secondary_engagement={"save_for_later": 25},
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/behavior?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_active_shoppers"] == 800
    assert data["repeat_purchase_rate"] == "0.3"


@patch("app.api.merchants.get_revenue_analytics")
def test_revenue_analytics_success(mock_get, merchant_a_headers):
    mock_get.return_value = RevenueAnalyticsResult(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        total_revenue=Decimal("15000.00"),
        total_orders=200,
        average_order_value=Decimal("75.00"),
        prior_period_comparison=PriorPeriodComparison(
            prior_start_date=date(2025, 12, 1),
            prior_end_date=date(2025, 12, 31),
            prior_revenue=Decimal("12000.00"),
            prior_orders=180,
            prior_average_order_value=Decimal("66.67"),
            revenue_growth_pct=Decimal("25.0"),
            order_growth_pct=Decimal("11.11"),
            aov_growth_pct=Decimal("12.49"),
        ),
        customer_revenue_breakdown=CustomerRevenueBreakdown(
            new_customer_revenue=Decimal("9000.00"),
            new_customer_order_count=120,
            repeat_customer_revenue=Decimal("6000.00"),
            repeat_customer_order_count=80,
        ),
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/analytics/revenue?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == "15000.00"
    assert data["prior_period_comparison"]["revenue_growth_pct"] == "25.0"
    assert data["customer_revenue_breakdown"]["new_customer_revenue"] == "9000.00"

