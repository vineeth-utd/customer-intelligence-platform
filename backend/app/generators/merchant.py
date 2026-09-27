import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.reference_data.features import FeatureKey
from app.reference_data.plans import PLAN_CATALOG, BillingCycle, PlanKey
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

_COUNTRIES = ("US", "CA", "GB", "AU", "DE")
_TIMEZONES = ("America/New_York", "America/Los_Angeles", "Europe/London", "Australia/Sydney", "Europe/Berlin")
_INSTALL_CHANNELS = ("shopify_app_store", "partner_referral", "direct_signup")
_LOGIN_CHANNELS = ("admin_dashboard", "mobile_app")
_UNINSTALL_REASONS = ("too_expensive", "missing_features", "switched_platform", "no_longer_needed")
_CANCELLATION_REASONS = ("too_expensive", "missing_features", "switched_platform", "no_longer_needed")
_CONFIG_FIELDS = ("timezone", "country", "store_currency")
_STARTING_PLANS = (PlanKey.FREE, PlanKey.STARTER, PlanKey.PRO)
_ACTION_TICK_PROBABILITY = 0.6
_ACTIONS = ("login", "feature_enable", "feature_disable", "config_update", "renew", "upgrade", "downgrade", "cancel")
_ACTION_WEIGHTS = (5, 2, 2, 1, 2, 1, 1, 1)

_PLANS_BY_PRICE = [entry.plan_key for entry in sorted(PLAN_CATALOG.values(), key=lambda entry: entry.monthly_price)]

_CURRENCIES = ("USD", "CAD", "GBP", "AUD", "EUR")

class _Stage(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    UNINSTALLED = "uninstalled"


@dataclass
class MerchantState:
    merchant_id: uuid.UUID
    shopify_store_id: str
    merchant_name: str
    email: str
    country: str
    timezone: str
    store_currency: str
    plan_key: PlanKey
    billing_cycle: BillingCycle
    enabled_features: set[FeatureKey] = field(default_factory=set)
    stage: _Stage = _Stage.ACTIVE


class MerchantLifecycleGenerator:
    """Deterministic, in-memory merchant lifecycle simulator.

    Holds no database or Kafka dependency - it only builds validated
    MerchantEventEnvelope objects for a caller to publish. A fresh instance
    always starts a brand-new synthetic population (no state is resumed
    across instances/runs), and the same population_size + seed always
    produces the same sequence of event types.
    """

    def __init__(self, population_size: int, seed: int | None = None, start_index: int = 0) -> None:
        self._rng = random.Random(seed)
        self._merchants: list[MerchantState] = []
        self._population_size = population_size
        self._start_index = start_index

    def generate_population(self) -> list[MerchantEventEnvelope]:
        envelopes: list[MerchantEventEnvelope] = []
        for offset in range(self._population_size):
            index = self._start_index + offset
            merchant_id = uuid.uuid4()
            shopify_store_id = f"store-{index:05d}-{merchant_id.hex[:8]}"
            merchant_name = f"Merchant {index:05d}"
            email = f"merchant{index:05d}@example.com"
            country = self._rng.choice(_COUNTRIES)
            timezone_name = self._rng.choice(_TIMEZONES)
            store_currency = self._rng.choice(_CURRENCIES)
            plan_key = self._rng.choice(_STARTING_PLANS)
            billing_cycle = self._rng.choice(list(BillingCycle))

            state = MerchantState(
                merchant_id=merchant_id,
                shopify_store_id=shopify_store_id,
                merchant_name=merchant_name,
                email=email,
                country=country,
                timezone=timezone_name,
                store_currency=store_currency,
                plan_key=plan_key,
                billing_cycle=billing_cycle,
            )
            self._merchants.append(state)

            envelopes.append(
                self._build_envelope(
                    state,
                    MerchantEventType.MERCHANT_CREATED,
                    MerchantCreatedPayload(
                        shopify_store_id=shopify_store_id,
                        merchant_name=merchant_name,
                        email=email,
                        country=country,
                        timezone=timezone_name,
                        store_currency=store_currency,
                    ),
                )
            )
            envelopes.append(
                self._build_envelope(
                    state,
                    MerchantEventType.APP_INSTALLED,
                    AppInstalledPayload(install_channel=self._rng.choice(_INSTALL_CHANNELS)),
                )
            )
            envelopes.append(
                self._build_envelope(
                    state,
                    MerchantEventType.SUBSCRIPTION_STARTED,
                    SubscriptionStartedPayload(
                        plan_key=plan_key,
                        billing_cycle=billing_cycle,
                        amount_paid=self._amount_for(plan_key, billing_cycle),
                    ),
                )
            )
        return envelopes

    def tick(self) -> list[MerchantEventEnvelope]:
        envelopes: list[MerchantEventEnvelope] = []
        for state in self._merchants:
            envelopes.extend(self._advance(state))
        return envelopes

    def all_terminal(self) -> bool:
        return all(state.stage == _Stage.UNINSTALLED for state in self._merchants)

    def _advance(self, state: MerchantState) -> list[MerchantEventEnvelope]:
        if state.stage == _Stage.UNINSTALLED:
            return []

        if state.stage == _Stage.CANCELLED:
            state.stage = _Stage.UNINSTALLED
            return [
                self._build_envelope(
                    state,
                    MerchantEventType.APP_UNINSTALLED,
                    AppUninstalledPayload(reason=self._rng.choice(_UNINSTALL_REASONS)),
                )
            ]

        if self._rng.random() > _ACTION_TICK_PROBABILITY:
            return []

        action = self._rng.choices(population=_ACTIONS, weights=_ACTION_WEIGHTS, k=1)[0]
        return self._perform_action(state, action)

    def _perform_action(self, state: MerchantState, action: str) -> list[MerchantEventEnvelope]:
        if action == "login":
            return [
                self._build_envelope(
                    state, MerchantEventType.MERCHANT_LOGIN, MerchantLoginPayload(login_channel=self._rng.choice(_LOGIN_CHANNELS))
                )
            ]

        if action == "feature_enable":
            plan_features = PLAN_CATALOG[state.plan_key].features
            available = [key for key in plan_features if key not in state.enabled_features]
            if not available:
                return []
            feature_key = self._rng.choice(available)
            state.enabled_features.add(feature_key)
            return [self._build_envelope(state, MerchantEventType.FEATURE_ENABLED, FeatureEnabledPayload(feature_key=feature_key))]

        if action == "feature_disable":
            if not state.enabled_features:
                return []
            feature_key = self._rng.choice(sorted(state.enabled_features, key=lambda key: key.value))
            state.enabled_features.discard(feature_key)
            return [self._build_envelope(state, MerchantEventType.FEATURE_DISABLED, FeatureDisabledPayload(feature_key=feature_key))]

        if action == "config_update":
            field_name = self._rng.choice(_CONFIG_FIELDS)
            new_value = self._new_config_value(field_name, state)
            if field_name == "timezone":
                state.timezone = new_value
            elif field_name == "country":
                state.country = new_value
            elif field_name == "store_currency":
                state.store_currency = new_value
            return [
                self._build_envelope(
                    state,
                    MerchantEventType.MERCHANT_CONFIGURATION_UPDATED,
                    MerchantConfigurationUpdatedPayload(changed_values={field_name: new_value}),
                )
            ]

        if action == "renew":
            return [
                self._build_envelope(
                    state,
                    MerchantEventType.SUBSCRIPTION_RENEWED,
                    SubscriptionRenewedPayload(
                        plan_key=state.plan_key,
                        billing_cycle=state.billing_cycle,
                        amount_paid=self._amount_for(state.plan_key, state.billing_cycle),
                        renewal_at=datetime.now(timezone.utc),
                    ),
                )
            ]

        if action in ("upgrade", "downgrade"):
            return self._change_plan(state, upgrade=(action == "upgrade"))

        if action == "cancel":
            state.stage = _Stage.CANCELLED
            return [
                self._build_envelope(
                    state,
                    MerchantEventType.SUBSCRIPTION_CANCELLED,
                    SubscriptionCancelledPayload(
                        plan_key=state.plan_key, cancellation_reason=self._rng.choice(_CANCELLATION_REASONS)
                    ),
                )
            ]

        return []

    def _change_plan(self, state: MerchantState, *, upgrade: bool) -> list[MerchantEventEnvelope]:
        new_plan_key = self._adjacent_plan(state.plan_key, upgrade=upgrade)
        if new_plan_key is None:
            return []
        previous_plan_key = state.plan_key
        state.plan_key = new_plan_key
        
        events = []
        new_plan_features = PLAN_CATALOG[new_plan_key].features
        for feature_key in list(state.enabled_features):
            if feature_key not in new_plan_features:
                state.enabled_features.discard(feature_key)
                events.append(self._build_envelope(state, MerchantEventType.FEATURE_DISABLED, FeatureDisabledPayload(feature_key=feature_key)))
                
        event_type = MerchantEventType.SUBSCRIPTION_UPGRADED if upgrade else MerchantEventType.SUBSCRIPTION_DOWNGRADED
        payload_cls = SubscriptionUpgradedPayload if upgrade else SubscriptionDowngradedPayload
        events.append(self._build_envelope(
                state,
                event_type,
                payload_cls(
                    previous_plan_key=previous_plan_key,
                    new_plan_key=new_plan_key,
                    billing_cycle=state.billing_cycle,
                    amount_paid=self._amount_for(new_plan_key, state.billing_cycle),
                ),
            ))
        return events

    def _amount_for(self, plan_key: PlanKey, billing_cycle: BillingCycle) -> float:
        entry = PLAN_CATALOG[plan_key]
        return entry.monthly_price if billing_cycle == BillingCycle.MONTHLY else entry.annual_price

    def _adjacent_plan(self, current: PlanKey, *, upgrade: bool) -> PlanKey | None:
        index = _PLANS_BY_PRICE.index(current)
        new_index = index + 1 if upgrade else index - 1
        if new_index < 0 or new_index >= len(_PLANS_BY_PRICE):
            return None
        return _PLANS_BY_PRICE[new_index]

    def _new_config_value(self, field_name: str, state: MerchantState) -> str:
        if field_name == "timezone":
            return self._rng.choice([tz for tz in _TIMEZONES if tz != state.timezone] or list(_TIMEZONES))
        if field_name == "store_currency":
            return self._rng.choice([c for c in _CURRENCIES if c != state.store_currency] or list(_CURRENCIES))
        return self._rng.choice([country for country in _COUNTRIES if country != state.country] or list(_COUNTRIES))

    def _build_envelope(self, state: MerchantState, event_type: MerchantEventType, payload) -> MerchantEventEnvelope:
        return MerchantEventEnvelope(
            event_id=uuid.uuid4(),
            event_type=event_type,
            event_version=1,
            event_timestamp=datetime.now(timezone.utc),
            merchant_id=state.merchant_id,
            payload=payload.model_dump(mode="json"),
            source="merchant-generator",
        )
