import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.profile import get_merchant_profile_source_data, upsert_merchant_profile


async def generate_merchant_profile_callback(session: AsyncSession, merchant_id: uuid.UUID) -> None:
    """
    Incremental processor callback for regenerating a Merchant Profile.
    Calculates derived metrics and upserts the profile.
    """
    # 1. Fetch raw operational aggregates
    data = await get_merchant_profile_source_data(session, merchant_id)
    
    # 2. Calculate dependent derived fields
    total_orders = data["total_orders"]
    total_revenue = data["total_revenue"]
    
    if total_orders > 0:
        data["average_order_value"] = total_revenue / total_orders
    else:
        data["average_order_value"] = 0.0

    total_sessions = data["total_sessions"]
    converted_sessions = data["converted_sessions"]
    
    if total_sessions > 0:
        data["conversion_rate"] = converted_sessions / total_sessions
    else:
        data["conversion_rate"] = 0.0

    # 3. Upsert Profile
    generated_at = datetime.now(timezone.utc)
    await upsert_merchant_profile(session, merchant_id, data, generated_at)
