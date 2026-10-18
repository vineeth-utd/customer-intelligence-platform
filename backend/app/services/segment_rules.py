import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.profile import ShopperProfile
from app.schemas.events.event_types import ShopperEventType

logger = logging.getLogger(__name__)


def _compare_values(actual: float, operator: str, target: float) -> bool:
    """Evaluate standard comparison operators deterministically."""
    if operator == ">=":
        return actual >= target
    if operator == ">":
        return actual > target
    if operator == "<=":
        return actual <= target
    if operator == "<":
        return actual < target
    if operator in ("==", "="):
        return actual == target
    if operator == "!=":
        return actual != target
    logger.warning(f"Unsupported comparison operator: {operator}")
    return False


async def evaluate_segment_rule(
    session: AsyncSession,
    shopper_id: uuid.UUID,
    definition: dict[str, Any],
    evaluation_time: datetime | None = None,
) -> bool:
    """
    Deterministically evaluate a segment rule against its authoritative source.

    Rules must specify their type and parameters explicitly:
    1. behavioral / has_recent_session:
       Requires 'days' parameter. Evaluates against ShopperEvent (SESSION_STARTED).
    2. transactional / total_spend:
       Evaluates against ShopperProfile.total_spend using standard comparison operators.
    3. behavioral / abandoned_cart_24h:
       Evaluates against ShopperJourney and ShopperJourneyEvent for unconverted cart/checkout
       activity >= 24 hours old within that same unconverted journey.
    """
    if not isinstance(definition, dict):
        logger.warning(f"Malformed segment definition (not a dict): {definition}")
        return False

    rule_type = definition.get("type")
    now = evaluation_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if rule_type == "behavioral":
        condition = definition.get("condition")

        if condition == "has_recent_session":
            days = definition.get("days")
            if days is None or not isinstance(days, (int, float)) or days <= 0:
                logger.warning(
                    f"Segment definition for has_recent_session missing valid required 'days' parameter: {definition}"
                )
                return False

            cutoff = now - timedelta(days=float(days))
            stmt = select(ShopperEvent.event_id).where(
                ShopperEvent.shopper_id == shopper_id,
                ShopperEvent.event_type == ShopperEventType.SESSION_STARTED.value,
                ShopperEvent.event_timestamp >= cutoff,
            ).limit(1)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

        if condition == "abandoned_cart_24h":
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(ShopperJourney.journey_id)
                .join(ShopperJourneyEvent, ShopperJourney.journey_id == ShopperJourneyEvent.journey_id)
                .where(
                    ShopperJourney.shopper_id == shopper_id,
                    ShopperJourney.converted.is_(False),
                    ShopperJourneyEvent.event_type.in_(
                        [
                            ShopperEventType.ADD_TO_CART.value,
                            ShopperEventType.CHECKOUT_STARTED.value,
                        ]
                    ),
                    ShopperJourneyEvent.event_timestamp <= cutoff,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

        logger.warning(f"Unknown or unsupported behavioral condition: {condition}")
        return False

    if rule_type == "transactional":
        metric = definition.get("metric")
        operator = definition.get("operator")
        value = definition.get("value")

        if metric != "total_spend":
            logger.warning(f"Unsupported transactional metric: {metric}")
            return False

        if operator is None or value is None:
            logger.warning(f"Transactional rule missing operator or value: {definition}")
            return False

        try:
            target_value = float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid target value in transactional rule: {value}")
            return False

        stmt = select(ShopperProfile.total_spend).where(ShopperProfile.shopper_id == shopper_id)
        result = await session.execute(stmt)
        spend_val = result.scalar_one_or_none()
        actual_spend = float(spend_val) if spend_val is not None else 0.0

        return _compare_values(actual_spend, str(operator), target_value)

    logger.warning(f"Unknown segment rule type: {rule_type}")
    return False
