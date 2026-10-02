import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant import (
    create_merchant,
    get_active_subscription,
    get_feature_by_key,
    get_merchant_by_id,
    get_plan_by_key,
    list_merchants_paginated,
    update_merchant_fields,
    update_merchant_install_status,
    update_merchant_last_active_at,
    update_merchant_business_activity,
    update_subscription_plan,
    update_subscription_renewal,
    upsert_active_subscription,
    upsert_feature,
    upsert_merchant_feature,
    upsert_plan,
    cancel_subscription,
)
from app.models.merchant import Merchant, PlanFeature, PlatformFeature, SubscriptionPlan
from app.reference_data.features import FEATURE_CATALOG, FeatureKey
from app.reference_data.plans import PLAN_CATALOG, PlanKey
from app.schemas.merchant import MerchantDetailResponse, MerchantSummaryResponse, SubscriptionResponse
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.payloads.merchant import (
    AppInstalledPayload,
    AppUninstalledPayload,
    FeatureDisabledPayload,
    FeatureEnabledPayload,
    MerchantConfigurationUpdatedPayload,
    MerchantCreatedPayload,
    MerchantLoginPayload,
    SubscriptionCancelledPayload,
    SubscriptionDowngradedPayload,
    SubscriptionRenewedPayload,
    SubscriptionStartedPayload,
    SubscriptionUpgradedPayload,
)

_SUPPORTED_CONFIGURATION_FIELDS = {"timezone", "country", "store_currency"}


class UnresolvedReferenceError(RuntimeError):
    """Raised when a plan_key/feature_key, or an expected active subscription, cannot be found."""


class UnsupportedConfigurationFieldError(ValueError):
    """Raised when MERCHANT_CONFIGURATION_UPDATED references a field the Merchant model does not support."""


async def resolve_plan(session: AsyncSession, plan_key: PlanKey) -> SubscriptionPlan | None:
    return await get_plan_by_key(session, plan_key)


async def resolve_feature(session: AsyncSession, feature_key: FeatureKey) -> PlatformFeature | None:
    return await get_feature_by_key(session, feature_key)


async def initialize_reference_data(session: AsyncSession) -> None:
    """Seed subscription_plans and platform_features from the canonical code catalogs.

    Idempotent (upsert by natural key) and safe to re-run. Owns the
    transaction for the whole initialization as one unit; the Data Access
    functions it calls operate on the session without committing.
    """
    for entry in FEATURE_CATALOG.values():
        await upsert_feature(session, entry)
    for entry in PLAN_CATALOG.values():
        await upsert_plan(session, entry)
    await session.commit()


async def _handle_merchant_created(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = MerchantCreatedPayload.model_validate(envelope.payload)
    await create_merchant(
        session,
        merchant_id=envelope.merchant_id,
        shopify_store_id=payload.shopify_store_id,
        merchant_name=payload.merchant_name,
        email=payload.email,
        country=payload.country,
        timezone=payload.timezone,
        store_currency=payload.store_currency,
        app_install_status="pending_install",
    )


async def _handle_app_installed(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    AppInstalledPayload.model_validate(envelope.payload)
    await update_merchant_install_status(session, envelope.merchant_id, "installed", envelope.event_timestamp)


async def _handle_app_uninstalled(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    AppUninstalledPayload.model_validate(envelope.payload)
    await update_merchant_install_status(session, envelope.merchant_id, "uninstalled", envelope.event_timestamp)


async def _handle_subscription_started(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = SubscriptionStartedPayload.model_validate(envelope.payload)
    plan = await resolve_plan(session, payload.plan_key)
    if plan is None:
        raise UnresolvedReferenceError(f"Unknown plan_key: {payload.plan_key}")
    await upsert_active_subscription(
        session,
        merchant_id=envelope.merchant_id,
        plan_id=plan.plan_id,
        billing_cycle=payload.billing_cycle.value,
        amount_paid=payload.amount_paid,
        started_at=envelope.event_timestamp,
    )


async def _handle_subscription_renewed(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = SubscriptionRenewedPayload.model_validate(envelope.payload)
    subscription = await get_active_subscription(session, envelope.merchant_id)
    if subscription is None:
        raise UnresolvedReferenceError(f"No active subscription for merchant {envelope.merchant_id}")
    update_subscription_renewal(
        subscription,
        renewal_at=payload.renewal_at,
        amount_paid=payload.amount_paid,
        billing_cycle=payload.billing_cycle.value,
    )


async def _apply_subscription_plan_change(
    session: AsyncSession, merchant_id, new_plan_key: PlanKey, billing_cycle, amount_paid: float
) -> None:
    plan = await resolve_plan(session, new_plan_key)
    if plan is None:
        raise UnresolvedReferenceError(f"Unknown plan_key: {new_plan_key}")
    subscription = await get_active_subscription(session, merchant_id)
    if subscription is None:
        raise UnresolvedReferenceError(f"No active subscription for merchant {merchant_id}")
    update_subscription_plan(subscription, plan_id=plan.plan_id, billing_cycle=billing_cycle.value, amount_paid=amount_paid)


async def _handle_subscription_upgraded(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = SubscriptionUpgradedPayload.model_validate(envelope.payload)
    await _apply_subscription_plan_change(session, envelope.merchant_id, payload.new_plan_key, payload.billing_cycle, payload.amount_paid)


async def _handle_subscription_downgraded(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = SubscriptionDowngradedPayload.model_validate(envelope.payload)
    await _apply_subscription_plan_change(session, envelope.merchant_id, payload.new_plan_key, payload.billing_cycle, payload.amount_paid)


async def _handle_subscription_cancelled(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = SubscriptionCancelledPayload.model_validate(envelope.payload)
    subscription = await get_active_subscription(session, envelope.merchant_id)
    if subscription is None:
        raise UnresolvedReferenceError(f"No active subscription for merchant {envelope.merchant_id}")
    cancel_subscription(subscription, cancelled_at=envelope.event_timestamp)


class FeatureNotEntitledError(ValueError):
    """Raised when a merchant attempts to enable a feature not included in their active plan."""


async def _handle_feature_enabled(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = FeatureEnabledPayload.model_validate(envelope.payload)
    feature = await resolve_feature(session, payload.feature_key)
    if feature is None:
        raise UnresolvedReferenceError(f"Unknown feature_key: {payload.feature_key}")
    
    merchant = await get_merchant_by_id(session, envelope.merchant_id)
    if not merchant or merchant.app_install_status != "installed":
        raise FeatureNotEntitledError(f"Merchant {envelope.merchant_id} is not installed.")
        
    subscription = await get_active_subscription(session, envelope.merchant_id)
    if not subscription:
        raise FeatureNotEntitledError(f"Merchant {envelope.merchant_id} has no active subscription.")
        
    stmt = select(PlanFeature).where(
        PlanFeature.plan_id == subscription.plan_id,
        PlanFeature.feature_id == feature.feature_id
    )
    entitled = await session.scalar(stmt)
    if not entitled:
        raise FeatureNotEntitledError(
            f"Merchant {envelope.merchant_id}'s active plan is not entitled to feature {payload.feature_key}."
        )
        
    await upsert_merchant_feature(session, merchant_id=envelope.merchant_id, feature_id=feature.feature_id, is_enabled=True)


async def _handle_feature_disabled(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = FeatureDisabledPayload.model_validate(envelope.payload)
    feature = await resolve_feature(session, payload.feature_key)
    if feature is None:
        raise UnresolvedReferenceError(f"Unknown feature_key: {payload.feature_key}")
    await upsert_merchant_feature(session, merchant_id=envelope.merchant_id, feature_id=feature.feature_id, is_enabled=False)


async def _handle_merchant_configuration_updated(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    payload = MerchantConfigurationUpdatedPayload.model_validate(envelope.payload)
    unsupported = set(payload.changed_values) - _SUPPORTED_CONFIGURATION_FIELDS
    if unsupported:
        raise UnsupportedConfigurationFieldError(f"Unsupported configuration field(s): {sorted(unsupported)}")
    await update_merchant_fields(session, envelope.merchant_id, dict(payload.changed_values))


async def _handle_merchant_login(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    MerchantLoginPayload.model_validate(envelope.payload)
    await update_merchant_last_active_at(session, envelope.merchant_id, envelope.event_timestamp)


_HANDLERS: dict[MerchantEventType, Callable[[AsyncSession, MerchantEventEnvelope], Awaitable[None]]] = {
    MerchantEventType.MERCHANT_CREATED: _handle_merchant_created,
    MerchantEventType.APP_INSTALLED: _handle_app_installed,
    MerchantEventType.APP_UNINSTALLED: _handle_app_uninstalled,
    MerchantEventType.SUBSCRIPTION_STARTED: _handle_subscription_started,
    MerchantEventType.SUBSCRIPTION_RENEWED: _handle_subscription_renewed,
    MerchantEventType.SUBSCRIPTION_UPGRADED: _handle_subscription_upgraded,
    MerchantEventType.SUBSCRIPTION_DOWNGRADED: _handle_subscription_downgraded,
    MerchantEventType.SUBSCRIPTION_CANCELLED: _handle_subscription_cancelled,
    MerchantEventType.FEATURE_ENABLED: _handle_feature_enabled,
    MerchantEventType.FEATURE_DISABLED: _handle_feature_disabled,
    MerchantEventType.MERCHANT_CONFIGURATION_UPDATED: _handle_merchant_configuration_updated,
    MerchantEventType.MERCHANT_LOGIN: _handle_merchant_login,
}


async def process_merchant_event(session: AsyncSession, envelope: MerchantEventEnvelope) -> None:
    """Route a validated Merchant event to its operational mutation.

    Performs the mutation only: does not commit, does not persist the raw
    event, and does not touch processed-state or Kafka offsets. Composing
    this with event persistence, transaction boundaries, redelivery
    handling, and offset commits is Unit 3.4C's responsibility.
    """
    handler = _HANDLERS[envelope.event_type]
    await handler(session, envelope)
    await update_merchant_business_activity(session, envelope.merchant_id, envelope.event_timestamp)

async def list_merchants(session: AsyncSession, limit: int, offset: int) -> tuple[list[Merchant], int]:
    return await list_merchants_paginated(session, limit, offset)

async def get_merchant_detail(session: AsyncSession, merchant_id: uuid.UUID) -> MerchantDetailResponse | None:
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None
        
    subscription = await get_active_subscription(session, merchant_id)
    
    sub_response = None
    if subscription:
        sub_response = SubscriptionResponse(
            plan_id=subscription.plan_id,
            plan_name=subscription.plan.plan_name,
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            amount_paid=subscription.amount_paid,
            started_at=subscription.started_at,
            renewal_at=subscription.renewal_at,
            cancelled_at=subscription.cancelled_at
        )
        
    return MerchantDetailResponse(
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.merchant_name,
        shopify_store_id=merchant.shopify_store_id,
        email=merchant.email,
        country=merchant.country,
        timezone=merchant.timezone,
        store_currency=merchant.store_currency,
        app_install_status=merchant.app_install_status,
        last_active_at=merchant.last_active_at,
        active_subscription=sub_response
    )
