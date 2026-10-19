from datetime import datetime, timedelta, timezone

from app.services.merchant_health_rules import (
    calculate_business_performance_score,
    calculate_engagement_score,
    calculate_feature_adoption_score,
    calculate_overall_health,
)


def test_feature_adoption_score():
    # 1. 2 of 3 entitled features enabled -> 66.67%
    entitled = ["wishlist", "save_for_later", "recommendations"]
    enabled = ["wishlist", "save_for_later"]
    score, factors = calculate_feature_adoption_score(entitled, enabled)
    assert score == 66.67
    assert factors["adopted_count"] == 2
    assert factors["entitled_count"] == 3

    # 2. All entitled enabled (even if extra non-entitled features exist) -> 100.0%
    enabled_all = ["wishlist", "save_for_later", "recommendations", "unentitled_feature"]
    score_all, factors_all = calculate_feature_adoption_score(entitled, enabled_all)
    assert score_all == 100.0
    assert factors_all["adopted_count"] == 3

    # 3. Empty entitled set -> explicit deterministic fallback: 0.0%
    score_empty, factors_empty = calculate_feature_adoption_score([], ["wishlist"])
    assert score_empty == 0.0
    assert factors_empty["adopted_count"] == 0
    assert factors_empty["entitled_count"] == 0


def test_engagement_score():
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Uninstalled merchant -> 0 points presence
    score_uninstalled, factors_uninstalled = calculate_engagement_score(
        app_install_status="uninstalled",
        journey_status="COMPLETED",
        last_active_at=now - timedelta(days=1),
        active_campaign_count=2,
        total_campaigns=5,
        evaluation_time=now,
    )
    # presence = 0, activity = 40, campaign = 20 -> 60.0
    assert factors_uninstalled["presence_points"] == 0.0
    assert score_uninstalled == 60.0

    # 2. Installed merchant with active logins but NO campaigns
    # Must NOT be inherently low-engagement: gets 40 (presence) + 40 (activity) = 80.0
    score_no_campaigns, factors_no_campaigns = calculate_engagement_score(
        app_install_status="installed",
        journey_status="OPEN",
        last_active_at=now - timedelta(days=2),
        active_campaign_count=0,
        total_campaigns=0,
        evaluation_time=now,
    )
    assert factors_no_campaigns["presence_points"] == 40.0
    assert factors_no_campaigns["activity_points"] == 40.0
    assert factors_no_campaigns["campaign_points"] == 0.0
    assert score_no_campaigns == 80.0

    # 3. Activity recency tiers
    # 15 days ago -> 25 points
    score_mid, factors_mid = calculate_engagement_score(
        app_install_status="installed",
        journey_status="OPEN",
        last_active_at=now - timedelta(days=15),
        active_campaign_count=1,
        total_campaigns=1,
        evaluation_time=now,
    )
    assert factors_mid["activity_points"] == 25.0
    assert factors_mid["campaign_points"] == 20.0
    assert score_mid == 85.0

    # > 30 days ago -> 0 points activity
    score_old, factors_old = calculate_engagement_score(
        app_install_status="installed",
        journey_status="OPEN",
        last_active_at=now - timedelta(days=45),
        active_campaign_count=0,
        total_campaigns=1,
        evaluation_time=now,
    )
    assert factors_old["activity_points"] == 0.0
    assert factors_old["campaign_points"] == 10.0
    assert score_old == 50.0

    # 4. Onboarding store grace (installed 5 days ago, no last_active_at yet)
    score_new, factors_new = calculate_engagement_score(
        app_install_status="installed",
        journey_status="OPEN",
        last_active_at=None,
        active_campaign_count=0,
        total_campaigns=0,
        evaluation_time=now,
        created_at=now - timedelta(days=5),
    )
    assert factors_new["activity_points"] == 20.0
    assert score_new == 60.0


def test_business_performance_score_merchant_relative():
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Boutique merchant with 1 order in recent 14d and 1 order in prior 14d
    # Momentum is 1.0 (50 pts), conversion trend is 1.0 (25 pts), last order 3d ago (25 pts) -> 100.0 pts
    score_boutique, factors_boutique = calculate_business_performance_score(
        recent_orders=1,
        prior_orders=1,
        recent_sessions=50,
        recent_converted=1,
        prior_sessions=50,
        prior_converted=1,
        total_orders_all_time=10,
        last_order_at=now - timedelta(days=3),
        evaluation_time=now,
    )
    assert factors_boutique["order_momentum_points"] == 50.0
    assert factors_boutique["conversion_trend_points"] == 25.0
    assert factors_boutique["order_recency_points"] == 25.0
    assert score_boutique == 100.0

    # 2. Large merchant whose volume dropped from 200 orders to 20 orders (-90%)
    # Even though 20 orders is high in absolute terms, momentum is 0.10 (5 pts)
    score_declining, factors_declining = calculate_business_performance_score(
        recent_orders=20,
        prior_orders=200,
        recent_sessions=2000,
        recent_converted=20,
        prior_sessions=4000,
        prior_converted=200,
        total_orders_all_time=5000,
        last_order_at=now - timedelta(days=2),
        evaluation_time=now,
    )
    assert factors_declining["order_momentum_points"] == 5.0
    # Conversion rate dropped from 0.05 to 0.01 -> 0.20 ratio -> 25 * 0.20 = 5.0 pts
    assert factors_declining["conversion_trend_points"] == 5.0
    assert factors_declining["order_recency_points"] == 25.0
    assert score_declining == 35.0

    # 3. Established store that completely stalled (0 orders recent, 10 prior)
    score_stalled, factors_stalled = calculate_business_performance_score(
        recent_orders=0,
        prior_orders=10,
        recent_sessions=100,
        recent_converted=0,
        prior_sessions=200,
        prior_converted=10,
        total_orders_all_time=100,
        last_order_at=now - timedelta(days=20),
        evaluation_time=now,
    )
    assert factors_stalled["order_momentum_points"] == 0.0
    assert factors_stalled["conversion_trend_points"] == 0.0
    assert factors_stalled["order_recency_points"] == 15.0  # within 30 days
    assert score_stalled == 15.0

    # 4. Brand new onboarding store (0 orders all time, created 4 days ago)
    score_brand_new, factors_brand_new = calculate_business_performance_score(
        recent_orders=0,
        prior_orders=0,
        recent_sessions=10,
        recent_converted=0,
        prior_sessions=0,
        prior_converted=0,
        total_orders_all_time=0,
        last_order_at=None,
        evaluation_time=now,
        created_at=now - timedelta(days=4),
    )
    assert factors_brand_new["order_momentum_points"] == 25.0
    assert factors_brand_new["conversion_trend_points"] == 12.5
    assert factors_brand_new["order_recency_points"] == 15.0
    assert score_brand_new == 52.5


def test_overall_health_and_churn_risk():
    # 1. Healthy merchant
    # engagement = 80.0, adoption = 100.0, performance = 90.0 -> average = 90.0
    health, status, churn_risk, alerts = calculate_overall_health(
        engagement_score=80.0,
        feature_adoption_score=100.0,
        business_performance_score=90.0,
        app_install_status="installed",
        subscription_status="active",
    )
    assert health == 90.0
    assert status == "HEALTHY"
    assert churn_risk == 10.0
    assert len(alerts) == 0

    # 2. Needs attention merchant (average = 50.0)
    health_na, status_na, churn_na, _ = calculate_overall_health(
        engagement_score=50.0,
        feature_adoption_score=50.0,
        business_performance_score=50.0,
        app_install_status="installed",
        subscription_status="active",
    )
    assert health_na == 50.0
    assert status_na == "NEEDS_ATTENTION"
    assert churn_na == 50.0

    # 3. Uninstalled override -> health = 0.0, churn_risk = 100.0, status = AT_RISK
    health_uninst, status_uninst, churn_uninst, alerts_uninst = calculate_overall_health(
        engagement_score=90.0,
        feature_adoption_score=100.0,
        business_performance_score=90.0,
        app_install_status="uninstalled",
        subscription_status="active",
    )
    assert health_uninst == 0.0
    assert status_uninst == "AT_RISK"
    assert churn_uninst == 100.0
    assert "Application is uninstalled" in alerts_uninst

    # 4. Cancelled subscription override -> capped at 25.0, status = AT_RISK
    health_canc, status_canc, churn_canc, alerts_canc = calculate_overall_health(
        engagement_score=90.0,
        feature_adoption_score=100.0,
        business_performance_score=90.0,
        app_install_status="installed",
        subscription_status="cancelled",
    )
    assert health_canc == 25.0
    assert status_canc == "AT_RISK"
    assert churn_canc == 75.0
    assert "Subscription is cancelled" in alerts_canc

    # 5. Past due subscription override -> capped at 50.0, status = NEEDS_ATTENTION
    health_pd, status_pd, churn_pd, alerts_pd = calculate_overall_health(
        engagement_score=90.0,
        feature_adoption_score=100.0,
        business_performance_score=90.0,
        app_install_status="installed",
        subscription_status="past_due",
    )
    assert health_pd == 50.0
    assert status_pd == "NEEDS_ATTENTION"
    assert churn_pd == 50.0
    assert "Subscription payment is past due" in alerts_pd
