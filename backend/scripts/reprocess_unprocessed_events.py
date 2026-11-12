"""Generic safe recovery script to reprocess unprocessed events across platform domains.

Reprocesses events through the canonical Business Service layer in dependency-safe order:
    merchant -> product -> shopper -> campaign

Usage (from backend/):
    python -m scripts.reprocess_unprocessed_events --all
    python -m scripts.reprocess_unprocessed_events --domain campaign
"""

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import sys
from typing import Any, Awaitable, Callable
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.campaign_events import get_campaign_event, mark_campaign_event_processed
from app.data_access.merchant_events import get_merchant_event, mark_merchant_event_processed
from app.data_access.product_events import get_product_event, mark_product_event_processed
from app.data_access.shopper_events import get_shopper_event, mark_shopper_event_processed
from app.db.session import AsyncSessionLocal
from app.models.event import CampaignEvent, MerchantEvent, ProductEvent, ShopperEvent
from app.schemas.events.envelope import (
    CampaignEventEnvelope,
    MerchantEventEnvelope,
    ProductEventEnvelope,
    ShopperEventEnvelope,
)
from app.schemas.events.event_types import (
    CampaignEventType,
    MerchantEventType,
    ProductEventType,
    ShopperEventType,
)
from app.services.campaign import process_campaign_event
from app.services.merchant import process_merchant_event
from app.services.product import process_product_event
from app.services.shopper import process_shopper_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("reprocess_events")


@dataclass
class DomainReprocessor:
    domain: str
    model_cls: type[Any]
    get_fn: Callable[[AsyncSession, uuid.UUID], Awaitable[Any]]
    mark_fn: Callable[[AsyncSession, uuid.UUID, datetime], Awaitable[None]]
    process_fn: Callable[[AsyncSession, Any], Awaitable[None]]
    to_envelope: Callable[[Any], Any]


DOMAIN_REPROCESSORS: dict[str, DomainReprocessor] = {
    "merchant": DomainReprocessor(
        domain="merchant",
        model_cls=MerchantEvent,
        get_fn=get_merchant_event,
        mark_fn=mark_merchant_event_processed,
        process_fn=process_merchant_event,
        to_envelope=lambda r: MerchantEventEnvelope(
            event_id=r.event_id,
            event_type=MerchantEventType(r.event_type),
            event_version=r.event_version,
            event_timestamp=r.event_timestamp,
            merchant_id=r.merchant_id,
            payload=r.payload,
            source=r.source,
        ),
    ),
    "product": DomainReprocessor(
        domain="product",
        model_cls=ProductEvent,
        get_fn=get_product_event,
        mark_fn=mark_product_event_processed,
        process_fn=process_product_event,
        to_envelope=lambda r: ProductEventEnvelope(
            event_id=r.event_id,
            event_type=ProductEventType(r.event_type),
            event_version=r.event_version,
            event_timestamp=r.event_timestamp,
            merchant_id=r.merchant_id,
            product_id=r.product_id,
            payload=r.payload,
            source=r.source,
        ),
    ),
    "shopper": DomainReprocessor(
        domain="shopper",
        model_cls=ShopperEvent,
        get_fn=get_shopper_event,
        mark_fn=mark_shopper_event_processed,
        process_fn=process_shopper_event,
        to_envelope=lambda r: ShopperEventEnvelope(
            event_id=r.event_id,
            event_type=ShopperEventType(r.event_type),
            event_version=r.event_version,
            event_timestamp=r.event_timestamp,
            merchant_id=r.merchant_id,
            shopper_id=r.shopper_id,
            session_id=r.session_id,
            payload=r.payload,
            source=r.source,
        ),
    ),
    "campaign": DomainReprocessor(
        domain="campaign",
        model_cls=CampaignEvent,
        get_fn=get_campaign_event,
        mark_fn=mark_campaign_event_processed,
        process_fn=process_campaign_event,
        to_envelope=lambda r: CampaignEventEnvelope(
            event_id=r.event_id,
            event_type=CampaignEventType(r.event_type),
            event_version=r.event_version,
            event_timestamp=r.event_timestamp,
            campaign_id=r.campaign_id,
            merchant_id=r.merchant_id,
            shopper_id=r.shopper_id,
            session_id=r.session_id,
            payload=r.payload,
            source=r.source,
        ),
    ),
}

DEPENDENCY_ORDER: tuple[str, ...] = ("merchant", "product", "shopper", "campaign")


async def reprocess_domain(domain_name: str) -> dict[str, int]:
    """Reprocess all currently unprocessed records for a single domain in event_timestamp order.

    Idempotent: skips any record already marked processed.
    Returns:
        {"attempted": int, "succeeded": int, "failed": int}
    """
    if domain_name not in DOMAIN_REPROCESSORS:
        raise ValueError(f"Unknown domain: {domain_name}. Valid domains: {list(DOMAIN_REPROCESSORS.keys())}")

    reprocessor = DOMAIN_REPROCESSORS[domain_name]

    async with AsyncSessionLocal() as read_session:
        stmt = (
            select(reprocessor.model_cls)
            .where(reprocessor.model_cls.processed == False)
            .order_by(reprocessor.model_cls.event_timestamp.asc())
        )
        unprocessed_records = (await read_session.scalars(stmt)).all()

    total = len(unprocessed_records)
    logger.info("[%s] Found %d unprocessed events to reprocess.", domain_name, total)

    stats = {"attempted": total, "succeeded": 0, "failed": 0}
    if total == 0:
        return stats

    for idx, rec in enumerate(unprocessed_records, start=1):
        event_id = rec.event_id
        async with AsyncSessionLocal() as session:
            existing = await reprocessor.get_fn(session, event_id)
            if existing is None:
                logger.warning("[%s %d/%d] Event %s not found in database; skipping", domain_name, idx, total, event_id)
                stats["failed"] += 1
                continue

            if existing.processed:
                logger.info("[%s %d/%d] Event %s is already processed; skipping", domain_name, idx, total, event_id)
                stats["succeeded"] += 1
                continue

            try:
                envelope = reprocessor.to_envelope(existing)
                await reprocessor.process_fn(session, envelope)
                await reprocessor.mark_fn(session, event_id, datetime.now(timezone.utc))
                await session.commit()
                stats["succeeded"] += 1
                logger.info(
                    "[%s %d/%d] Successfully processed event %s (%s)",
                    domain_name, idx, total, event_id, getattr(rec, "event_type", "UNKNOWN")
                )
            except Exception as e:
                await session.rollback()
                stats["failed"] += 1
                logger.error(
                    "[%s %d/%d] Failed to reprocess event %s (%s): %s",
                    domain_name, idx, total, event_id, getattr(rec, "event_type", "UNKNOWN"), e, exc_info=True
                )

    logger.info(
        "[%s] Reprocessing complete. Attempted: %d, Succeeded: %d, Failed: %d",
        domain_name, stats["attempted"], stats["succeeded"], stats["failed"]
    )
    return stats


async def reprocess_all_domains() -> dict[str, dict[str, int]]:
    """Reprocess all domains in dependency-safe order (merchant -> product -> shopper -> campaign)."""
    results: dict[str, dict[str, int]] = {}
    for domain in DEPENDENCY_ORDER:
        results[domain] = await reprocess_domain(domain)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic recovery script to reprocess unprocessed events across platform domains."
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--domain",
        choices=["merchant", "product", "shopper", "campaign"],
        help="Specify a single domain to reprocess.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Reprocess all domains in dependency-safe order (default).",
    )

    args = parser.parse_args()

    if args.domain:
        stats = asyncio.run(reprocess_domain(args.domain))
        if stats["failed"] > 0:
            sys.exit(1)
    else:
        results = asyncio.run(reprocess_all_domains())
        total_failed = sum(s["failed"] for s in results.values())
        if total_failed > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
