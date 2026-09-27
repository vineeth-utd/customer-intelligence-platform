import pytest
from pydantic import ValidationError

from app.reference_data.features import FeatureKey
from app.reference_data.plans import BillingCycle, PlanKey
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.payloads.merchant import (
    FeatureEnabledPayload,
    MerchantCreatedPayload,
    SubscriptionStartedPayload,
    SubscriptionUpgradedPayload,
)
from app.schemas.events.registry import get_payload_schema


@pytest.mark.parametrize(
    "event_type",
    [
        MerchantEventType.MERCHANT_CREATED,
        MerchantEventType.APP_INSTALLED,
        MerchantEventType.APP_UNINSTALLED,
        MerchantEventType.SUBSCRIPTION_STARTED,
        MerchantEventType.SUBSCRIPTION_RENEWED,
        MerchantEventType.SUBSCRIPTION_UPGRADED,
        MerchantEventType.SUBSCRIPTION_DOWNGRADED,
        MerchantEventType.SUBSCRIPTION_CANCELLED,
        MerchantEventType.FEATURE_ENABLED,
        MerchantEventType.FEATURE_DISABLED,
        MerchantEventType.MERCHANT_CONFIGURATION_UPDATED,
        MerchantEventType.MERCHANT_LOGIN,
    ],
)
def test_every_generated_event_type_has_a_registered_v1_payload(event_type):
    assert get_payload_schema(event_type.value, 1) is not None


def test_merchant_created_payload_registered_under_its_event_type():
    assert get_payload_schema(MerchantEventType.MERCHANT_CREATED.value, 1) is MerchantCreatedPayload


def test_subscription_started_payload_accepts_plan_key_and_billing_cycle():
    payload = SubscriptionStartedPayload(plan_key=PlanKey.STARTER, billing_cycle=BillingCycle.MONTHLY, amount_paid=19)
    assert payload.plan_key is PlanKey.STARTER
    assert payload.billing_cycle is BillingCycle.MONTHLY


def test_subscription_started_payload_rejects_unknown_plan_key():
    with pytest.raises(ValidationError):
        SubscriptionStartedPayload(plan_key="not_a_plan", billing_cycle=BillingCycle.MONTHLY, amount_paid=19)


def test_subscription_upgraded_payload_carries_previous_and_new_plan_keys():
    payload = SubscriptionUpgradedPayload(
        previous_plan_key=PlanKey.STARTER, new_plan_key=PlanKey.PRO, billing_cycle=BillingCycle.ANNUAL, amount_paid=490
    )
    assert payload.previous_plan_key is PlanKey.STARTER
    assert payload.new_plan_key is PlanKey.PRO


def test_feature_enabled_payload_accepts_feature_key():
    payload = FeatureEnabledPayload(feature_key=FeatureKey.WISHLIST)
    assert payload.feature_key is FeatureKey.WISHLIST


def test_feature_enabled_payload_rejects_unknown_feature_key():
    with pytest.raises(ValidationError):
        FeatureEnabledPayload(feature_key="not_a_feature")
