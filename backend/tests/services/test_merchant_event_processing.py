"""Integration tests against a live local Postgres for Merchant event routing/processing.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable, mirroring tests/services/test_merchant.py.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select, text

from app.config.settings import settings
from app.data_access.merchant import get_active_subscription, get_merchant_by_id
from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant, MerchantFeature, PlatformFeature, Subscription, SubscriptionPlan
from app.reference_data.plans import PlanKey
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.services.merchant import (
    UnresolvedReferenceError,
    UnsupportedConfigurationFieldError,
    initialize_reference_data,
    process_merchant_event,
    resolve_plan,
)


@pytest.fixture
async def db_session():
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first so a stale
    # connection bound to a previous test's loop is never reused here.
    await engine.dispose()

    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable at {settings.postgres_host}:{settings.postgres_port}: {exc}")

    await session.execute(delete(SubscriptionPlan))
    await session.execute(delete(PlatformFeature))
    await session.commit()
    await initialize_reference_data(session)

    yield session

    await session.execute(delete(SubscriptionPlan))
    await session.execute(delete(PlatformFeature))
    await session.commit()
    await session.close()


async def _cleanup_merchant(session, merchant_id: uuid.UUID) -> None:
    await session.execute(delete(MerchantFeature).where(MerchantFeature.merchant_id == merchant_id))
    await session.execute(delete(Subscription).where(Subscription.merchant_id == merchant_id))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await session.commit()


def _envelope(merchant_id: uuid.UUID, event_type: MerchantEventType, payload: dict) -> MerchantEventEnvelope:
    return MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        payload=payload,
        source="test",
    )


async def test_full_merchant_lifecycle_produces_expected_operational_state(db_session):
    merchant_id = uuid.uuid4()
    try:
        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.MERCHANT_CREATED,
                {
                    "shopify_store_id": f"store-{merchant_id.hex[:8]}",
                    "merchant_name": "Acme",
                    "email": "acme@example.com",
                    "country": "US",
                    "timezone": "America/New_York",
                    "store_currency": "USD",
                },
            ),
        )
        merchant = await get_merchant_by_id(db_session, merchant_id)
        assert merchant is not None
        assert merchant.app_install_status == "pending_install"

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.APP_INSTALLED, {"install_channel": "shopify_app_store"})
        )
        merchant = await get_merchant_by_id(db_session, merchant_id)
        assert merchant.app_install_status == "installed"
        assert merchant.last_install_status_updated_at is not None

        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.SUBSCRIPTION_STARTED,
                {"plan_key": "starter", "billing_cycle": "monthly", "amount_paid": 19},
            ),
        )
        subscription = await get_active_subscription(db_session, merchant_id)
        assert subscription is not None
        assert float(subscription.amount_paid) == 19

        renewal_at = datetime.now(timezone.utc)
        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.SUBSCRIPTION_RENEWED,
                {
                    "plan_key": "starter",
                    "billing_cycle": "monthly",
                    "amount_paid": 19,
                    "renewal_at": renewal_at.isoformat(),
                },
            ),
        )
        subscription = await get_active_subscription(db_session, merchant_id)
        assert subscription.renewal_at is not None

        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.SUBSCRIPTION_UPGRADED,
                {"previous_plan_key": "starter", "new_plan_key": "pro", "billing_cycle": "monthly", "amount_paid": 49},
            ),
        )
        subscription = await get_active_subscription(db_session, merchant_id)
        pro_plan = await resolve_plan(db_session, PlanKey.PRO)
        assert subscription.plan_id == pro_plan.plan_id

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.FEATURE_ENABLED, {"feature_key": "wishlist"})
        )

        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id, MerchantEventType.MERCHANT_CONFIGURATION_UPDATED, {"changed_values": {"country": "CA"}}
            ),
        )
        merchant = await get_merchant_by_id(db_session, merchant_id)
        assert merchant.country == "CA"

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.MERCHANT_LOGIN, {"login_channel": "admin_dashboard"})
        )
        merchant = await get_merchant_by_id(db_session, merchant_id)
        assert merchant.last_active_at is not None

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.FEATURE_DISABLED, {"feature_key": "wishlist"})
        )

        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id, MerchantEventType.SUBSCRIPTION_CANCELLED, {"plan_key": "pro", "cancellation_reason": "too_expensive"}
            ),
        )
        result = await db_session.execute(select(Subscription).where(Subscription.merchant_id == merchant_id))
        subscription = result.scalar_one()
        assert subscription.status == "cancelled"
        assert subscription.cancelled_at is not None

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.APP_UNINSTALLED, {"reason": "too_expensive"})
        )
        merchant = await get_merchant_by_id(db_session, merchant_id)
        assert merchant.app_install_status == "uninstalled"

        await db_session.commit()
    finally:
        await _cleanup_merchant(db_session, merchant_id)


async def test_feature_enable_then_disable_updates_merchant_feature_row(db_session):
    merchant_id = uuid.uuid4()
    try:
        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.MERCHANT_CREATED,
                {
                    "shopify_store_id": f"store-{merchant_id.hex[:8]}",
                    "merchant_name": "Acme",
                    "email": "acme@example.com",
                    "country": "US",
                    "timezone": "America/New_York",
                    "store_currency": "USD",
                },
            ),
        )
        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.FEATURE_ENABLED, {"feature_key": "wishlist"})
        )
        result = await db_session.execute(select(MerchantFeature).where(MerchantFeature.merchant_id == merchant_id))
        merchant_feature = result.scalar_one()
        assert merchant_feature.is_enabled is True

        await process_merchant_event(
            db_session, _envelope(merchant_id, MerchantEventType.FEATURE_DISABLED, {"feature_key": "wishlist"})
        )
        await db_session.refresh(merchant_feature)
        assert merchant_feature.is_enabled is False

        await db_session.commit()
    finally:
        await _cleanup_merchant(db_session, merchant_id)


async def test_subscription_started_is_replay_safe(db_session):
    merchant_id = uuid.uuid4()
    try:
        await process_merchant_event(
            db_session,
            _envelope(
                merchant_id,
                MerchantEventType.MERCHANT_CREATED,
                {
                    "shopify_store_id": f"store-{merchant_id.hex[:8]}",
                    "merchant_name": "Acme",
                    "email": "acme@example.com",
                    "country": "US",
                    "timezone": "America/New_York",
                    "store_currency": "USD",
                },
            ),
        )
        started_envelope = _envelope(
            merchant_id, MerchantEventType.SUBSCRIPTION_STARTED, {"plan_key": "starter", "billing_cycle": "monthly", "amount_paid": 19}
        )
        await process_merchant_event(db_session, started_envelope)
        await process_merchant_event(db_session, started_envelope)
        await db_session.commit()

        result = await db_session.execute(select(Subscription).where(Subscription.merchant_id == merchant_id))
        assert len(result.scalars().all()) == 1
    finally:
        await _cleanup_merchant(db_session, merchant_id)


async def test_merchant_created_is_idempotent(db_session):
    merchant_id = uuid.uuid4()
    try:
        created_envelope = _envelope(
            merchant_id,
            MerchantEventType.MERCHANT_CREATED,
            {
                "shopify_store_id": f"store-{merchant_id.hex[:8]}",
                "merchant_name": "Acme",
                "email": "acme@example.com",
                "country": "US",
                "timezone": "America/New_York",
                "store_currency": "USD",
            },
        )
        await process_merchant_event(db_session, created_envelope)
        await process_merchant_event(db_session, created_envelope)
        await db_session.commit()

        result = await db_session.execute(select(Merchant).where(Merchant.merchant_id == merchant_id))
        assert len(result.scalars().all()) == 1
    finally:
        await _cleanup_merchant(db_session, merchant_id)


async def test_unresolved_plan_key_raises(db_session):
    merchant_id = uuid.uuid4()
    try:
        with pytest.raises(UnresolvedReferenceError):
            await process_merchant_event(
                db_session,
                _envelope(
                    merchant_id,
                    MerchantEventType.SUBSCRIPTION_RENEWED,
                    {"plan_key": "starter", "billing_cycle": "monthly", "amount_paid": 19, "renewal_at": datetime.now(timezone.utc).isoformat()},
                ),
            )
    finally:
        await _cleanup_merchant(db_session, merchant_id)


async def test_unresolved_feature_key_raises(db_session):
    await db_session.execute(delete(PlatformFeature))
    await db_session.commit()
    merchant_id = uuid.uuid4()
    try:
        with pytest.raises(UnresolvedReferenceError):
            await process_merchant_event(
                db_session, _envelope(merchant_id, MerchantEventType.FEATURE_ENABLED, {"feature_key": "wishlist"})
            )
    finally:
        await _cleanup_merchant(db_session, merchant_id)
        await initialize_reference_data(db_session)


async def test_unsupported_configuration_field_raises(db_session):
    merchant_id = uuid.uuid4()
    try:
        with pytest.raises(UnsupportedConfigurationFieldError):
            await process_merchant_event(
                db_session,
                _envelope(
                    merchant_id, MerchantEventType.MERCHANT_CONFIGURATION_UPDATED, {"changed_values": {"notification_email": "test@example.com"}}
                ),
            )
    finally:
        await _cleanup_merchant(db_session, merchant_id)
