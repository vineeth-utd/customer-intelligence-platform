from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    ConversionFunnelResult,
    CustomerRevenueBreakdown,
    FeatureMetricsResult,
    MerchantMetricsSummaryResult,
    PlatformSummaryResult,
    PlatformTrendResult,
    PriorPeriodComparison,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
)
from app.schemas.auth import AccessScope
from app.schemas.dashboard import (
    MerchantDashboardResponse,
    PlatformDashboardResponse,
)
from app.schemas.merchant import (
    MerchantDetailResponse,
    MerchantHealthFactorsResponse,
    MerchantHealthResponse,
)

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


def test_dashboard_apis_unauthenticated():
    endpoints = [
        "/api/v1/dashboard/platform?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/dashboard/merchants/{MERCHANT_A_ID}?start_date=2026-01-01&end_date=2026-01-31",
    ]
    for url in endpoints:
        response = client.get(url)
        assert response.status_code == 401, f"Expected 401 for {url}"


def test_platform_dashboard_merchant_forbidden(merchant_a_headers):
    response = client.get(
        "/api/v1/dashboard/platform?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 403


def test_merchant_dashboard_cross_merchant_forbidden(merchant_a_headers):
    response = client.get(
        f"/api/v1/dashboard/merchants/{MERCHANT_B_ID}?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 403
    assert "Cross-merchant access forbidden" in response.json()["detail"]


def test_dashboard_invalid_date_range(internal_headers, merchant_a_headers):
    # Platform dashboard invalid dates
    resp1 = client.get(
        "/api/v1/dashboard/platform?start_date=2026-02-01&end_date=2026-01-01",
        headers=internal_headers,
    )
    assert resp1.status_code == 400
    assert "cannot be after" in resp1.json()["detail"]

    # Merchant dashboard invalid dates
    resp2 = client.get(
        f"/api/v1/dashboard/merchants/{MERCHANT_A_ID}?start_date=2026-02-01&end_date=2026-01-01",
        headers=merchant_a_headers,
    )
    assert resp2.status_code == 400
    assert "cannot be after" in resp2.json()["detail"]


@patch("app.api.dashboard.get_platform_dashboard")
def test_platform_dashboard_success(mock_get, internal_headers):
    mock_get.return_value = PlatformDashboardResponse(
        summary=PlatformSummaryResult(
            total_merchants=10,
            active_merchants=8,
            total_revenue=Decimal("50000.00"),
            total_orders=1200,
            active_shoppers=4000,
            active_subscriptions=7,
        ),
        trends=[
            PlatformTrendResult(
                metric_date=date(2026, 1, 15),
                active_merchants=8,
                new_merchants=1,
                installed_merchants=10,
                uninstalled_merchants=0,
                new_subscriptions=1,
                subscription_upgrades=0,
                subscription_downgrades=0,
                subscription_cancellations=0,
                total_revenue=Decimal("1500.00"),
                total_orders=40,
                active_shoppers=120,
            )
        ],
        features=[
            FeatureMetricsResult(
                feature_id=uuid.uuid4(),
                feature_key="automated_campaigns",
                feature_name="Automated Campaigns",
                feature_category="marketing",
                eligible_merchant_count=10,
                enabled_merchant_count=5,
                active_merchant_count=3,
                total_feature_events=120,
                adoption_rate=Decimal("0.5"),
                usage_rate=Decimal("0.3"),
            )
        ],
    )

    response = client.get(
        "/api/v1/dashboard/platform?start_date=2026-01-01&end_date=2026-01-31",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_merchants"] == 10
    assert len(data["trends"]) == 1
    assert data["features"][0]["feature_key"] == "automated_campaigns"


@patch("app.api.dashboard.get_merchant_dashboard")
def test_merchant_dashboard_not_found(mock_get, merchant_a_headers):
    mock_get.return_value = None
    response = client.get(
        f"/api/v1/dashboard/merchants/{MERCHANT_A_ID}?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Merchant not found"


@patch("app.api.dashboard.get_merchant_dashboard")
def test_merchant_dashboard_success(mock_get, merchant_a_headers):
    now = datetime.now(timezone.utc)
    mock_get.return_value = MerchantDashboardResponse(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        merchant=MerchantDetailResponse(
            merchant_id=MERCHANT_A_ID,
            shopify_store_id="store-a.myshopify.com",
            merchant_name="Store A",
            email="owner@store-a.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
            created_at=now,
            updated_at=now,
        ),
        health=MerchantHealthResponse(
            merchant_id=MERCHANT_A_ID,
            health_score=85.0,
            health_status="HEALTHY",
            churn_risk_score=15.0,
            engagement_score=90.0,
            feature_adoption_score=80.0,
            business_performance_score=85.0,
            calculated_at=now,
            contributing_factors=MerchantHealthFactorsResponse(
                feature_adoption={"score": 80.0},
                engagement={"score": 90.0},
                business_performance={"score": 85.0},
                subscription={"status": "active"},
                risk_alerts=[],
            ),
        ),
        summary=MerchantMetricsSummaryResult(
            merchant_id=MERCHANT_A_ID,
            revenue=Decimal("15000.00"),
            order_count=200,
            unique_shoppers=800,
            new_shoppers=600,
            session_count=3000,
            converted_session_count=200,
            product_view_count=5000,
            wishlist_add_count=100,
            save_for_later_count=50,
            add_to_cart_count=400,
            checkout_count=250,
            purchase_count=200,
            conversion_rate=Decimal("0.0667"),
            average_order_value=Decimal("75.00"),
            platform_login_count=15,
            campaign_created_count=2,
            feature_enable_count=1,
            feature_disable_count=0,
        ),
        revenue=RevenueAnalyticsResult(
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
        ),
        funnel=ConversionFunnelResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            stages=[],
            overall_conversion_rate=Decimal("0.0667"),
            cart_abandonment_rate=Decimal("0.375"),
            checkout_abandonment_rate=Decimal("0.2"),
            secondary_engagement={},
        ),
        journeys=ShopperJourneyAnalyticsResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            total_journeys=400,
            converted_journeys=100,
            non_converting_journeys=250,
            open_journeys=50,
            journey_conversion_rate=Decimal("0.2857"),
            average_conversion_duration_seconds=7200.0,
            drop_off_stages={},
            by_entry_source=[],
        ),
        behavior=ShopperBehaviorAnalyticsResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            total_active_shoppers=800,
            new_shoppers=600,
            returning_shoppers=200,
            total_purchasing_shoppers=180,
            repeat_purchasing_shoppers=50,
            repeat_purchase_rate=Decimal("0.2778"),
            average_order_value=Decimal("75.00"),
            secondary_engagement={},
        ),
        campaigns=[
            CampaignAnalyticsResult(
                campaign_id=uuid.uuid4(),
                campaign_name="Winter Sale",
                campaign_type="email",
                campaign_medium="email",
                status="active",
                delivered_count=1000,
                opened_count=400,
                clicked_count=150,
                converted_count=30,
                attributed_order_count=30,
                attributed_revenue=Decimal("2500.00"),
                open_rate=Decimal("0.4"),
                click_through_rate=Decimal("0.15"),
                conversion_rate=Decimal("0.03"),
            )
        ],
    )

    response = client.get(
        f"/api/v1/dashboard/merchants/{MERCHANT_A_ID}?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == str(MERCHANT_A_ID)
    assert data["merchant"]["merchant_name"] == "Store A"
    assert data["health"]["health_score"] == 85.0
    assert data["revenue"]["total_revenue"] == "15000.00"
    assert data["journeys"]["total_journeys"] == 400
    assert len(data["campaigns"]) == 1


@patch("app.api.dashboard.get_merchant_dashboard")
def test_merchant_dashboard_internal_access(mock_get, internal_headers):
    now = datetime.now(timezone.utc)
    mock_get.return_value = MerchantDashboardResponse(
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        merchant=MerchantDetailResponse(
            merchant_id=MERCHANT_A_ID,
            shopify_store_id="store-a.myshopify.com",
            merchant_name="Store A",
            email="owner@store-a.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
            created_at=now,
            updated_at=now,
        ),
        health=None,
        summary=MerchantMetricsSummaryResult(
            merchant_id=MERCHANT_A_ID,
            revenue=Decimal("0"),
            order_count=0,
            unique_shoppers=0,
            new_shoppers=0,
            session_count=0,
            converted_session_count=0,
            product_view_count=0,
            wishlist_add_count=0,
            save_for_later_count=0,
            add_to_cart_count=0,
            checkout_count=0,
            purchase_count=0,
            conversion_rate=Decimal("0"),
            average_order_value=Decimal("0"),
            platform_login_count=0,
            campaign_created_count=0,
            feature_enable_count=0,
            feature_disable_count=0,
        ),
        revenue=RevenueAnalyticsResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            total_revenue=Decimal("0"),
            total_orders=0,
            average_order_value=Decimal("0"),
            prior_period_comparison=PriorPeriodComparison(
                prior_start_date=date(2025, 12, 1),
                prior_end_date=date(2025, 12, 31),
                prior_revenue=Decimal("0"),
                prior_orders=0,
                prior_average_order_value=Decimal("0"),
            ),
            customer_revenue_breakdown=CustomerRevenueBreakdown(
                new_customer_revenue=Decimal("0"),
                new_customer_order_count=0,
                repeat_customer_revenue=Decimal("0"),
                repeat_customer_order_count=0,
            ),
        ),
        funnel=ConversionFunnelResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            stages=[],
            overall_conversion_rate=Decimal("0"),
            cart_abandonment_rate=Decimal("0"),
            checkout_abandonment_rate=Decimal("0"),
            secondary_engagement={},
        ),
        journeys=ShopperJourneyAnalyticsResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            total_journeys=0,
            converted_journeys=0,
            non_converting_journeys=0,
            open_journeys=0,
            journey_conversion_rate=Decimal("0"),
            drop_off_stages={},
            by_entry_source=[],
        ),
        behavior=ShopperBehaviorAnalyticsResult(
            merchant_id=MERCHANT_A_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            total_active_shoppers=0,
            new_shoppers=0,
            returning_shoppers=0,
            total_purchasing_shoppers=0,
            repeat_purchasing_shoppers=0,
            repeat_purchase_rate=Decimal("0"),
            average_order_value=Decimal("0"),
            secondary_engagement={},
        ),
        campaigns=[],
    )

    response = client.get(
        f"/api/v1/dashboard/merchants/{MERCHANT_A_ID}?start_date=2026-01-01&end_date=2026-01-31",
        headers=internal_headers,
    )
    assert response.status_code == 200
    assert response.json()["merchant"]["merchant_name"] == "Store A"
