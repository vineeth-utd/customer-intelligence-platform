from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.reference_data.features import FeatureKey
from app.reference_data.plans import BillingCycle, PlanKey
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.registry import register_event_payload


@register_event_payload(MerchantEventType.MERCHANT_CREATED.value, 1)
class MerchantCreatedPayload(BaseModel):
    shopify_store_id: str
    merchant_name: str
    email: str
    country: str
    timezone: str


@register_event_payload(MerchantEventType.APP_INSTALLED.value, 1)
class AppInstalledPayload(BaseModel):
    install_channel: str


@register_event_payload(MerchantEventType.APP_UNINSTALLED.value, 1)
class AppUninstalledPayload(BaseModel):
    reason: str


@register_event_payload(MerchantEventType.SUBSCRIPTION_STARTED.value, 1)
class SubscriptionStartedPayload(BaseModel):
    plan_key: PlanKey
    billing_cycle: BillingCycle
    amount_paid: float


@register_event_payload(MerchantEventType.SUBSCRIPTION_RENEWED.value, 1)
class SubscriptionRenewedPayload(BaseModel):
    plan_key: PlanKey
    billing_cycle: BillingCycle
    amount_paid: float
    renewal_at: datetime


@register_event_payload(MerchantEventType.SUBSCRIPTION_UPGRADED.value, 1)
class SubscriptionUpgradedPayload(BaseModel):
    previous_plan_key: PlanKey
    new_plan_key: PlanKey
    billing_cycle: BillingCycle
    amount_paid: float


@register_event_payload(MerchantEventType.SUBSCRIPTION_DOWNGRADED.value, 1)
class SubscriptionDowngradedPayload(BaseModel):
    previous_plan_key: PlanKey
    new_plan_key: PlanKey
    billing_cycle: BillingCycle
    amount_paid: float


@register_event_payload(MerchantEventType.SUBSCRIPTION_CANCELLED.value, 1)
class SubscriptionCancelledPayload(BaseModel):
    plan_key: PlanKey
    cancellation_reason: str


@register_event_payload(MerchantEventType.FEATURE_ENABLED.value, 1)
class FeatureEnabledPayload(BaseModel):
    feature_key: FeatureKey


@register_event_payload(MerchantEventType.FEATURE_DISABLED.value, 1)
class FeatureDisabledPayload(BaseModel):
    feature_key: FeatureKey


@register_event_payload(MerchantEventType.MERCHANT_CONFIGURATION_UPDATED.value, 1)
class MerchantConfigurationUpdatedPayload(BaseModel):
    changed_values: dict[str, Any]


@register_event_payload(MerchantEventType.MERCHANT_LOGIN.value, 1)
class MerchantLoginPayload(BaseModel):
    login_channel: str
