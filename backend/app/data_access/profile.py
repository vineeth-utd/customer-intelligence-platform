import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.profile import MerchantProfile
from app.models.merchant import MerchantFeature
from app.models.shopper import Shopper
from app.models.product import Product
from app.models.order import Order
from app.models.campaign import Campaign
from app.models.metrics import MerchantMetricsDaily


async def get_merchant_profile_source_data(session: AsyncSession, merchant_id: uuid.UUID) -> dict[str, Any]:
    """
    Retrieves the raw aggregates required to build a MerchantProfile.
    """
    # 1. Total Shoppers
    stmt_shoppers = select(func.count(Shopper.shopper_id)).where(Shopper.merchant_id == merchant_id)
    total_shoppers = await session.scalar(stmt_shoppers) or 0

    # 2. Total Products
    stmt_products = select(func.count(Product.product_id)).where(Product.merchant_id == merchant_id)
    total_products = await session.scalar(stmt_products) or 0

    # 3. Order Aggregates (Only completed orders)
    stmt_orders = select(
        func.count(Order.order_id).label("total_orders"),
        func.sum(Order.total_amount).label("total_revenue"),
        func.max(Order.created_at).label("last_order_at")
    ).where(
        and_(Order.merchant_id == merchant_id, Order.order_status == "completed")
    )
    res_orders = await session.execute(stmt_orders)
    row_orders = res_orders.fetchone()
    total_orders = row_orders.total_orders if row_orders and row_orders.total_orders else 0
    total_revenue = float(row_orders.total_revenue) if row_orders and row_orders.total_revenue else 0.0
    last_order_at = row_orders.last_order_at if row_orders else None

    # 4. Campaign Aggregates
    stmt_all_campaigns = select(Campaign.status, Campaign.created_at).where(Campaign.merchant_id == merchant_id)
    res_campaigns = await session.execute(stmt_all_campaigns)
    campaigns = res_campaigns.all()
    
    total_campaigns = len(campaigns)
    active_campaign_count = sum(1 for c in campaigns if c.status.lower() == "active")
    last_campaign_at = max((c.created_at for c in campaigns), default=None)

    # 5. Feature Aggregates
    stmt_features = select(func.count(MerchantFeature.feature_id)).where(
        and_(MerchantFeature.merchant_id == merchant_id, MerchantFeature.is_enabled == True)
    )
    enabled_feature_count = await session.scalar(stmt_features) or 0

    # 6. Conversion Rate from Daily Metrics
    stmt_conversion = select(
        func.sum(MerchantMetricsDaily.converted_session_count).label("converted_sessions"),
        func.sum(MerchantMetricsDaily.session_count).label("total_sessions")
    ).where(MerchantMetricsDaily.merchant_id == merchant_id)
    res_conv = await session.execute(stmt_conversion)
    row_conv = res_conv.fetchone()
    
    converted_sessions = float(row_conv.converted_sessions) if row_conv and row_conv.converted_sessions else 0.0
    total_sessions = float(row_conv.total_sessions) if row_conv and row_conv.total_sessions else 0.0

    return {
        "total_shoppers": total_shoppers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_campaigns": total_campaigns,
        "active_campaign_count": active_campaign_count,
        "enabled_feature_count": enabled_feature_count,
        "last_order_at": last_order_at,
        "last_campaign_at": last_campaign_at,
        "converted_sessions": converted_sessions,
        "total_sessions": total_sessions
    }


async def upsert_merchant_profile(
    session: AsyncSession, merchant_id: uuid.UUID, profile_data: dict[str, Any], generated_at: datetime
) -> None:
    """
    Inserts or updates a MerchantProfile record.
    """
    stmt = insert(MerchantProfile).values(
        merchant_id=merchant_id,
        total_shoppers=profile_data["total_shoppers"],
        total_products=profile_data["total_products"],
        total_orders=profile_data["total_orders"],
        total_revenue=profile_data["total_revenue"],
        average_order_value=profile_data["average_order_value"],
        conversion_rate=profile_data["conversion_rate"],
        total_campaigns=profile_data["total_campaigns"],
        active_campaign_count=profile_data["active_campaign_count"],
        enabled_feature_count=profile_data["enabled_feature_count"],
        last_order_at=profile_data["last_order_at"],
        last_campaign_at=profile_data["last_campaign_at"],
        generated_at=generated_at
    )
    
    update_dict = {
        "total_shoppers": stmt.excluded.total_shoppers,
        "total_products": stmt.excluded.total_products,
        "total_orders": stmt.excluded.total_orders,
        "total_revenue": stmt.excluded.total_revenue,
        "average_order_value": stmt.excluded.average_order_value,
        "conversion_rate": stmt.excluded.conversion_rate,
        "total_campaigns": stmt.excluded.total_campaigns,
        "active_campaign_count": stmt.excluded.active_campaign_count,
        "enabled_feature_count": stmt.excluded.enabled_feature_count,
        "last_order_at": stmt.excluded.last_order_at,
        "last_campaign_at": stmt.excluded.last_campaign_at,
        "generated_at": stmt.excluded.generated_at,
    }
    
    stmt = stmt.on_conflict_do_update(
        index_elements=["merchant_id"],
        set_=update_dict
    )
    
    await session.execute(stmt)
