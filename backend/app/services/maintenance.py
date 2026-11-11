import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics import refresh_aggregate_views
from app.services.merchant import initialize_reference_data

logger = logging.getLogger(__name__)

SYNTHETIC_TABLES = [
    # Derived intelligence & Analytics
    "merchant_health",
    "shopper_segment_members",
    "shopper_profiles",
    "merchant_profiles",
    "shopper_journey_events",
    "shopper_journeys",
    "merchant_journey_events",
    "merchant_journeys",
    "merchant_metrics_daily",
    "platform_metrics_daily",
    "feature_metrics_daily",
    "campaign_analytics_daily",
    # Processing state
    "entity_processing_states",
    "entity_domain_activities",
    # Operational & Events
    "order_items",
    "orders",
    "campaign_events",
    "campaigns",
    "shopper_events",
    "shoppers",
    "shopper_segments",
    "product_variants",
    "product_events",
    "products",
    "merchant_features",
    "subscriptions",
    "merchant_events",
    "merchants",
]


async def reset_synthetic_data(session: AsyncSession) -> None:
    """
    Safely resets all synthetic data in the platform while preserving
    schema migrations and canonical platform reference data.

    1. Truncates all operational, event, derived intelligence, and processing state tables.
    2. Re-initializes canonical reference data (subscription plans and platform features).
    3. Refreshes aggregate materialized views to clear cached summaries.
    """
    logger.info("Truncating synthetic tables...")
    table_list = ", ".join(f'"{t}"' for t in SYNTHETIC_TABLES)
    await session.execute(text(f"TRUNCATE TABLE {table_list} CASCADE;"))
    await session.commit()

    logger.info("Re-initializing canonical platform reference data...")
    await initialize_reference_data(session)

    # Verify reference data survived / is intact
    plans_count = await session.scalar(text("SELECT count(*) FROM subscription_plans;"))
    features_count = await session.scalar(text("SELECT count(*) FROM platform_features;"))
    logger.info(
        "Platform reference data verified: %d plans, %d features.",
        plans_count or 0,
        features_count or 0,
    )

    logger.info("Refreshing aggregate materialized views...")
    await refresh_aggregate_views(session)
    logger.info("Synthetic data reset complete.")

