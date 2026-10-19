import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def calculate_feature_adoption_score(
    entitled_feature_keys: list[str],
    enabled_feature_keys: list[str],
) -> tuple[float, dict[str, Any]]:
    """
    Evaluates feature adoption strictly relative to features entitled under the merchant's plan.
    Returns (score, factors_breakdown).
    """
    if not entitled_feature_keys:
        return 0.0, {
            "entitled_features": [],
            "enabled_features": enabled_feature_keys,
            "entitled_count": 0,
            "enabled_count": len(enabled_feature_keys),
            "adopted_count": 0,
            "adoption_ratio": 0.0,
        }

    entitled_set = set(entitled_feature_keys)
    enabled_set = set(enabled_feature_keys)
    adopted = entitled_set.intersection(enabled_set)

    adoption_ratio = len(adopted) / len(entitled_set)
    score = round(adoption_ratio * 100.0, 2)

    factors = {
        "entitled_features": sorted(list(entitled_set)),
        "enabled_features": sorted(list(enabled_set)),
        "entitled_count": len(entitled_set),
        "enabled_count": len(enabled_set),
        "adopted_count": len(adopted),
        "adoption_ratio": round(adoption_ratio, 4),
    }
    return score, factors


def calculate_engagement_score(
    app_install_status: str,
    journey_status: str | None,
    last_active_at: datetime | None,
    active_campaign_count: int,
    total_campaigns: int,
    evaluation_time: datetime,
    created_at: datetime | None = None,
) -> tuple[float, dict[str, Any]]:
    """
    Calculates engagement score based on operational installation presence,
    platform activity recency, and marketing utilization as a positive contributor.
    Returns (score, factors_breakdown).
    """
    # 1. Platform Installation & Lifecycle Presence (40 pts)
    if app_install_status == "uninstalled" or journey_status == "COMPLETED":
        presence_pts = 0.0
    else:
        presence_pts = 40.0

    # 2. Platform Activity Recency (40 pts)
    activity_recency_days: float | None = None
    if last_active_at is not None:
        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)
        activity_recency_days = (evaluation_time - last_active_at).total_seconds() / 86400.0
        if activity_recency_days <= 7.0:
            activity_pts = 40.0
        elif activity_recency_days <= 30.0:
            activity_pts = 25.0
        else:
            activity_pts = 0.0
    else:
        # Check newly created store grace period (<= 14 days)
        if created_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            store_age_days = (evaluation_time - created_at).total_seconds() / 86400.0
            activity_pts = 20.0 if store_age_days <= 14.0 else 0.0
        else:
            activity_pts = 0.0

    # 3. Campaign & Marketing Utilization (20 pts)
    if active_campaign_count > 0:
        campaign_pts = 20.0
    elif total_campaigns > 0:
        campaign_pts = 10.0
    else:
        campaign_pts = 0.0

    total_score = round(presence_pts + activity_pts + campaign_pts, 2)
    factors = {
        "app_install_status": app_install_status,
        "journey_status": journey_status,
        "presence_points": presence_pts,
        "last_active_at": last_active_at.isoformat() if last_active_at else None,
        "activity_recency_days": round(activity_recency_days, 1) if activity_recency_days is not None else None,
        "activity_points": activity_pts,
        "active_campaign_count": active_campaign_count,
        "total_campaigns": total_campaigns,
        "campaign_points": campaign_pts,
    }
    return total_score, factors


def calculate_business_performance_score(
    recent_orders: int,
    prior_orders: int,
    recent_sessions: int,
    recent_converted: int,
    prior_sessions: int,
    prior_converted: int,
    total_orders_all_time: int,
    last_order_at: datetime | None,
    evaluation_time: datetime,
    created_at: datetime | None = None,
) -> tuple[float, dict[str, Any]]:
    """
    Evaluates business performance using normalized, merchant-relative trend and recency signals:
    - Relative order momentum (14d recent vs 14d prior): 50 pts
    - Relative conversion trend (14d recent vs 14d prior): 25 pts
    - Order recency: 25 pts
    Returns (score, factors_breakdown).
    """
    # 1. Order Momentum (50 pts)
    if prior_orders > 0:
        momentum_ratio = recent_orders / prior_orders
        momentum_pts = min(50.0, momentum_ratio * 50.0)
    else:
        if recent_orders > 0:
            momentum_ratio = 1.0
            momentum_pts = 50.0
        else:
            momentum_ratio = 0.0
            momentum_pts = 0.0 if total_orders_all_time > 0 else 25.0

    # 2. Conversion Trend (25 pts)
    c_recent = (recent_converted / recent_sessions) if recent_sessions > 0 else 0.0
    c_prior = (prior_converted / prior_sessions) if prior_sessions > 0 else 0.0

    if prior_sessions > 0 and c_prior > 0:
        conv_ratio = c_recent / c_prior
        conversion_pts = min(25.0, conv_ratio * 25.0)
    else:
        if c_recent > 0:
            conv_ratio = 1.0
            conversion_pts = 25.0
        else:
            conv_ratio = 0.0
            conversion_pts = 0.0 if total_orders_all_time > 0 else 12.5

    # 3. Order Recency (25 pts)
    order_recency_days: float | None = None
    if last_order_at is not None:
        if last_order_at.tzinfo is None:
            last_order_at = last_order_at.replace(tzinfo=timezone.utc)
        order_recency_days = (evaluation_time - last_order_at).total_seconds() / 86400.0
        if order_recency_days <= 14.0:
            recency_pts = 25.0
        elif order_recency_days <= 30.0:
            recency_pts = 15.0
        else:
            recency_pts = 0.0
    else:
        if created_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            store_age_days = (evaluation_time - created_at).total_seconds() / 86400.0
            recency_pts = 15.0 if store_age_days <= 14.0 else 0.0
        else:
            recency_pts = 0.0

    total_score = round(momentum_pts + conversion_pts + recency_pts, 2)
    factors = {
        "recent_orders_14d": recent_orders,
        "prior_orders_14d": prior_orders,
        "order_momentum_ratio": round(momentum_ratio, 4),
        "order_momentum_points": round(momentum_pts, 2),
        "recent_conversion_rate": round(c_recent, 4),
        "prior_conversion_rate": round(c_prior, 4),
        "conversion_trend_ratio": round(conv_ratio, 4),
        "conversion_trend_points": round(conversion_pts, 2),
        "last_order_at": last_order_at.isoformat() if last_order_at else None,
        "order_recency_days": round(order_recency_days, 1) if order_recency_days is not None else None,
        "order_recency_points": recency_pts,
    }
    return total_score, factors


def calculate_overall_health(
    engagement_score: float,
    feature_adoption_score: float,
    business_performance_score: float,
    app_install_status: str,
    subscription_status: str | None,
) -> tuple[float, str, float, list[str]]:
    """
    Composites sub-scores equally into overall health_score, applies deterministic
    subscription/install modifiers, and derives deterministic churn_risk_score and health_status.
    Returns (health_score, health_status, churn_risk_score, risk_alerts).
    """
    alerts: list[str] = []

    # Uninstalled override
    if app_install_status == "uninstalled":
        alerts.append("Application is uninstalled")
        return 0.0, "AT_RISK", 100.0, alerts

    base_health = (engagement_score + feature_adoption_score + business_performance_score) / 3.0

    # Subscription overrides
    if subscription_status in ("cancelled", "expired"):
        health_score = min(base_health, 25.0)
        alerts.append(f"Subscription is {subscription_status}")
    elif subscription_status == "past_due":
        health_score = min(base_health, 50.0)
        alerts.append("Subscription payment is past due")
    else:
        health_score = base_health

    health_score = round(max(0.0, min(100.0, health_score)), 2)
    # Churn risk is explicitly a deterministic risk indicator derived from Merchant Health
    churn_risk_score = round(max(0.0, min(100.0, 100.0 - health_score)), 2)

    # Classification into balanced tertiles
    if health_score >= 67.0 and subscription_status == "active":
        health_status = "HEALTHY"
    elif health_score >= 33.0 and subscription_status not in ("cancelled", "expired"):
        health_status = "NEEDS_ATTENTION"
    else:
        health_status = "AT_RISK"

    return health_score, health_status, churn_risk_score, alerts
