from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.token import create_access_token
from app.main import app
from app.models.campaign import Campaign
from app.schemas.analytics import (
    AttributionModelMetric,
    CampaignAttributionResult,
    CampaignAudienceAnalysisResult,
    CampaignDailyTrendPoint,
    CampaignJourneyCorrelationResult,
    CampaignPerformanceDetailResult,
    CurrentSegmentAudienceMetric,
)
from app.schemas.auth import AccessScope
from app.schemas.campaign import CampaignDetailResponse, CampaignSummaryResponse

client = TestClient(app)

MERCHANT_A_ID = uuid.uuid4()
MERCHANT_B_ID = uuid.uuid4()
CAMPAIGN_A_ID = uuid.uuid4()
CAMPAIGN_B_ID = uuid.uuid4()
SEGMENT_1_ID = uuid.uuid4()


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


def test_campaign_apis_unauthenticated():
    endpoints = [
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/performance?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/attribution?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/journey-correlation?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/audience",
    ]
    for url in endpoints:
        response = client.get(url)
        assert response.status_code == 401, f"Expected 401 for {url}"


def test_campaign_apis_cross_merchant_forbidden(merchant_a_headers):
    endpoints = [
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns",
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_B_ID}",
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_B_ID}/performance?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_B_ID}/attribution?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_B_ID}/journey-correlation?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_B_ID}/audience",
    ]
    for url in endpoints:
        response = client.get(url, headers=merchant_a_headers)
        assert response.status_code == 403, f"Expected 403 for {url}"
        assert "Cross-merchant access forbidden" in response.json()["detail"]


@patch("app.api.campaigns.verify_campaign_ownership")
def test_campaign_apis_tenant_isolation_not_found(mock_ownership, merchant_a_headers):
    # When requesting a campaign not belonging to Merchant A under Merchant A's path,
    # verify_campaign_ownership returns None -> 404 (no 403, no leak of existence).
    mock_ownership.return_value = None

    endpoints = [
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_B_ID}/performance?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_B_ID}/attribution?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_B_ID}/journey-correlation?start_date=2026-01-01&end_date=2026-01-31",
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_B_ID}/audience",
    ]
    for url in endpoints:
        response = client.get(url, headers=merchant_a_headers)
        assert response.status_code == 404, f"Expected 404 for {url}"
        assert response.json()["detail"] == "Campaign not found"


@patch("app.api.campaigns.list_campaigns")
def test_read_campaigns_success(mock_list, internal_headers):
    now = datetime.now(timezone.utc)
    mock_list.return_value = (
        [
            CampaignSummaryResponse(
                campaign_id=CAMPAIGN_A_ID,
                merchant_id=MERCHANT_A_ID,
                segment_id=SEGMENT_1_ID,
                campaign_name="Spring Launch",
                campaign_type="email",
                campaign_medium="email",
                status="active",
                start_at=now,
                end_at=None,
                created_at=now,
                updated_at=now,
            )
        ],
        1,
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns?limit=10&offset=0&status=active",
        headers=internal_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["items"][0]["campaign_name"] == "Spring Launch"
    mock_list.assert_called_once_with(
        mock_list.call_args[0][0], MERCHANT_A_ID, limit=10, offset=0, status="active"
    )


@patch("app.api.campaigns.list_campaigns")
def test_read_campaigns_empty(mock_list, merchant_a_headers):
    mock_list.return_value = ([], 0)

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_read_campaigns_validation_errors(merchant_a_headers):
    # Invalid limit
    resp = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns?limit=0",
        headers=merchant_a_headers,
    )
    assert resp.status_code == 422

    resp = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns?limit=101",
        headers=merchant_a_headers,
    )
    assert resp.status_code == 422

    # Invalid offset
    resp = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns?offset=-1",
        headers=merchant_a_headers,
    )
    assert resp.status_code == 422

    # Invalid status enum
    resp = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns?status=not_a_valid_status",
        headers=merchant_a_headers,
    )
    assert resp.status_code == 422


@patch("app.api.campaigns.get_campaign_detail")
def test_read_campaign_detail_success(mock_detail, merchant_a_headers):
    now = datetime.now(timezone.utc)
    mock_detail.return_value = CampaignDetailResponse(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_A_ID,
        segment_id=SEGMENT_1_ID,
        campaign_name="VIP Rewards",
        campaign_type="sms",
        campaign_medium="sms",
        status="active",
        start_at=now,
        end_at=None,
        created_at=now,
        updated_at=now,
        target_segment_name="High Value VIPs",
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_name"] == "VIP Rewards"
    assert data["target_segment_name"] == "High Value VIPs"


@patch("app.api.campaigns.get_campaign_detail")
def test_read_campaign_detail_not_found(mock_detail, merchant_a_headers):
    mock_detail.return_value = None

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}",
        headers=merchant_a_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Campaign not found"


@patch("app.api.campaigns.get_campaign_performance")
@patch("app.api.campaigns.verify_campaign_ownership")
def test_read_campaign_performance_success(mock_ownership, mock_perf, merchant_a_headers):
    mock_ownership.return_value = Campaign(campaign_id=CAMPAIGN_A_ID, merchant_id=MERCHANT_A_ID)
    mock_perf.return_value = CampaignPerformanceDetailResult(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_A_ID,
        campaign_name="VIP Rewards",
        campaign_type="sms",
        campaign_medium="sms",
        status="active",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        delivered_count=1000,
        opened_count=500,
        clicked_count=150,
        open_rate=Decimal("0.5"),
        click_through_rate=Decimal("0.15"),
        trends=[
            CampaignDailyTrendPoint(
                metric_date=date(2026, 1, 10),
                delivered_count=100,
                opened_count=50,
                clicked_count=15,
                converted_count=2,
                attributed_order_count=2,
                attributed_revenue=Decimal("150.0"),
                open_rate=Decimal("0.5"),
                click_through_rate=Decimal("0.15"),
                conversion_rate=Decimal("0.02"),
            )
        ],
        prior_period_delivered=800,
        prior_period_opened=350,
        prior_period_clicked=100,
        delivered_growth_pct=Decimal("25.0"),
        opened_growth_pct=Decimal("42.86"),
        clicked_growth_pct=Decimal("50.0"),
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/performance?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["delivered_count"] == 1000
    assert data["open_rate"] == "0.5"
    assert data["trends"][0]["attributed_revenue"] == "150.0"


def test_read_campaign_performance_date_validation(merchant_a_headers):
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/performance?start_date=2026-02-01&end_date=2026-01-01",
        headers=merchant_a_headers,
    )
    assert response.status_code == 400
    assert "start_date cannot be after end_date" in response.json()["detail"]


@patch("app.api.campaigns.get_campaign_attribution")
@patch("app.api.campaigns.verify_campaign_ownership")
def test_read_campaign_attribution_success(mock_ownership, mock_attrib, merchant_a_headers):
    mock_ownership.return_value = Campaign(campaign_id=CAMPAIGN_A_ID, merchant_id=MERCHANT_A_ID)
    mock_attrib.return_value = CampaignAttributionResult(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        direct_session=AttributionModelMetric(
            conversions_count=5,
            attributed_revenue=Decimal("500.0"),
            average_order_value=Decimal("100.0"),
        ),
        first_touch_journey=AttributionModelMetric(
            conversions_count=8,
            attributed_revenue=Decimal("800.0"),
            average_order_value=Decimal("100.0"),
        ),
        last_touch_journey=AttributionModelMetric(
            conversions_count=6,
            attributed_revenue=Decimal("600.0"),
            average_order_value=Decimal("100.0"),
        ),
        assisted_journey=AttributionModelMetric(
            conversions_count=12,
            attributed_revenue=Decimal("1200.0"),
            average_order_value=Decimal("100.0"),
        ),
        explicit_recorded=AttributionModelMetric(
            conversions_count=4,
            attributed_revenue=Decimal("400.0"),
            average_order_value=Decimal("100.0"),
        ),
        direct_vs_cross_session_journeys={
            "direct_session": 5,
            "cross_session": 7,
        },
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/attribution?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["direct_session"]["conversions_count"] == 5
    assert data["first_touch_journey"]["attributed_revenue"] == "800.0"
    assert data["assisted_journey"]["conversions_count"] == 12
    assert data["direct_vs_cross_session_journeys"]["cross_session"] == 7


def test_read_campaign_attribution_date_validation(merchant_a_headers):
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/attribution?start_date=2026-02-01&end_date=2026-01-01",
        headers=merchant_a_headers,
    )
    assert response.status_code == 400
    assert "start_date cannot be after end_date" in response.json()["detail"]


@patch("app.api.campaigns.get_campaign_journey_correlation")
@patch("app.api.campaigns.verify_campaign_ownership")
def test_read_campaign_journey_correlation_success(mock_ownership, mock_jc, merchant_a_headers):
    mock_ownership.return_value = Campaign(campaign_id=CAMPAIGN_A_ID, merchant_id=MERCHANT_A_ID)
    mock_jc.return_value = CampaignJourneyCorrelationResult(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_A_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        total_journeys_touched=100,
        converted_journeys=25,
        non_converting_journeys=60,
        open_journeys=15,
        journey_conversion_rate=Decimal("0.2941"),
        average_touch_to_conversion_seconds=86400.0,
        drop_off_stages={
            "CHECKOUT_STARTED": 30,
            "PRODUCT_VIEWED": 20,
            "CART_UPDATED": 10,
        },
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/journey-correlation?start_date=2026-01-01&end_date=2026-01-31",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_journeys_touched"] == 100
    assert data["converted_journeys"] == 25
    assert data["drop_off_stages"]["CHECKOUT_STARTED"] == 30


def test_read_campaign_journey_correlation_date_validation(merchant_a_headers):
    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/journey-correlation?start_date=2026-02-01&end_date=2026-01-01",
        headers=merchant_a_headers,
    )
    assert response.status_code == 400
    assert "start_date cannot be after end_date" in response.json()["detail"]


@patch("app.api.campaigns.get_campaign_audience_analysis")
@patch("app.api.campaigns.verify_campaign_ownership")
def test_read_campaign_audience_success(mock_ownership, mock_audience, merchant_a_headers):
    mock_ownership.return_value = Campaign(campaign_id=CAMPAIGN_A_ID, merchant_id=MERCHANT_A_ID)
    mock_audience.return_value = CampaignAudienceAnalysisResult(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_A_ID,
        target_segment_id=SEGMENT_1_ID,
        target_segment_name="High Value VIPs",
        target_segment_current_members=200,
        unique_shoppers_reached=300,
        unique_shoppers_engaged=180,
        unique_shoppers_converted=45,
        target_segment_current_members_reached=150,
        target_segment_current_members_engaged=110,
        target_segment_current_members_converted=35,
        non_target_current_shoppers_reached=150,
        non_target_current_shoppers_engaged=70,
        non_target_current_shoppers_converted=10,
        current_segments_breakdown=[
            CurrentSegmentAudienceMetric(
                segment_id=SEGMENT_1_ID,
                segment_name="High Value VIPs",
                current_members_count=200,
                reached_shoppers_count=150,
                engaged_shoppers_count=110,
                converted_shoppers_count=35,
                conversion_rate=Decimal("0.2333"),
            )
        ],
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_A_ID}/campaigns/{CAMPAIGN_A_ID}/audience",
        headers=merchant_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_segment_name"] == "High Value VIPs"
    assert data["unique_shoppers_reached"] == 300
    assert data["current_segments_breakdown"][0]["converted_shoppers_count"] == 35


@patch("app.api.campaigns.get_campaign_detail")
def test_internal_principal_can_access_any_merchant(mock_detail, internal_headers):
    now = datetime.now(timezone.utc)
    mock_detail.return_value = CampaignDetailResponse(
        campaign_id=CAMPAIGN_A_ID,
        merchant_id=MERCHANT_B_ID,
        segment_id=SEGMENT_1_ID,
        campaign_name="Merchant B Campaign",
        campaign_type="email",
        campaign_medium="email",
        status="active",
        start_at=now,
        end_at=None,
        created_at=now,
        updated_at=now,
        target_segment_name="Segment B",
    )

    response = client.get(
        f"/api/v1/merchants/{MERCHANT_B_ID}/campaigns/{CAMPAIGN_A_ID}",
        headers=internal_headers,
    )
    assert response.status_code == 200
    assert response.json()["campaign_name"] == "Merchant B Campaign"
