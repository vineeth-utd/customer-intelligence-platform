"""Unified historical timeline simulation orchestrator.

Generates a single globally interleaved, causally coherent historical business timeline
covering Merchants, Products, Campaigns, and Shoppers across [start_datetime, end_datetime].

All event envelopes are emitted using canonical platform schemas and sorted chronologically
before publishing to Kafka.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
import uuid

from app.generators.config import HistoricalSimulationConfig
from app.generators.context import SimulationContext, SimulationMode
from app.reference_data.features import FeatureKey
from app.reference_data.plans import PLAN_CATALOG, BillingCycle, PlanKey
from app.reference_data.segments import SEGMENT_CATALOG
from app.schemas.events.envelope import (
    BaseEventEnvelope,
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
from app.schemas.events.payloads.campaign import (
    AdClickedPayload,
    AdViewedPayload,
    CampaignConvertedPayload,
    CampaignCreatedPayload,
    CampaignUpdatedPayload,
    EmailClickedPayload,
    EmailDeliveredPayload,
    EmailOpenedPayload,
    PushDeliveredPayload,
    PushOpenedPayload,
    SmsClickedPayload,
    SmsDeliveredPayload,
)
from app.schemas.events.payloads.merchant import (
    AppInstalledPayload,
    FeatureEnabledPayload,
    MerchantConfigurationUpdatedPayload,
    MerchantCreatedPayload,
    MerchantLoginPayload,
    SubscriptionRenewedPayload,
    SubscriptionStartedPayload,
)
from app.schemas.events.payloads.product import (
    ProductCreatedPayload,
    ProductVariantCreatedPayload,
    ProductVariantUpdatedPayload,
)
from app.schemas.events.payloads.shopper import (
    AddToCartPayload,
    CartItem,
    CheckoutStartedPayload,
    OrderItemPayload,
    ProductSearchedPayload,
    ProductViewedPayload,
    PurchaseCompletedPayload,
    SessionEndedPayload,
    SessionStartedPayload,
    WishlistAddedPayload,
)

_COUNTRIES = ("US", "CA", "GB", "AU", "DE")
_TIMEZONES = ("America/New_York", "America/Los_Angeles", "Europe/London", "Australia/Sydney", "Europe/Berlin")
_CURRENCIES = ("USD", "CAD", "GBP", "AUD", "EUR")
_INSTALL_CHANNELS = ("shopify_app_store", "partner_referral", "direct_signup")
_LOGIN_CHANNELS = ("admin_dashboard", "mobile_app")
_STARTING_PLANS = (PlanKey.FREE, PlanKey.STARTER, PlanKey.PRO)

_CATEGORIES = ("Apparel", "Electronics", "Home & Garden", "Beauty", "Sports", "Toys", "Books", "Food & Beverage")
_VENDORS = ("BrandCo", "SupplyHouse", "MegaMfg", "LocalMaker", "GlobalSource")
_SIZES = ("XS", "S", "M", "L", "XL", "XXL", "One Size")
_COLORS = ("Red", "Blue", "Green", "Black", "White", "Grey", "Yellow", "Purple")

_CAMPAIGN_TYPES = ["promotional", "newsletter", "abandoned_cart", "winback"]
_CAMPAIGN_MEDIUMS = ["email", "sms", "push", "ad"]


@dataclass
class _VariantRecord:
    variant_id: uuid.UUID
    product_id: uuid.UUID
    price: Decimal
    inventory: int


@dataclass
class _MerchantSimState:
    merchant_id: uuid.UUID
    shopify_store_id: str
    merchant_name: str
    email: str
    country: str
    timezone: str
    store_currency: str
    plan_key: PlanKey
    billing_cycle: BillingCycle
    install_time: datetime
    variants: list[_VariantRecord] = field(default_factory=list)


@dataclass
class _CampaignSimState:
    campaign_id: uuid.UUID
    merchant_id: uuid.UUID
    segment_id: uuid.UUID
    campaign_type: str
    campaign_medium: str
    start_time: datetime
    end_time: datetime


@dataclass
class _ShopperSimState:
    shopper_id: uuid.UUID
    merchant_id: uuid.UUID
    persona: str
    arrival_time: datetime
    email: str


def _event_priority(envelope: BaseEventEnvelope) -> int:
    """Deterministic tie-breaker for identical timestamps.
    Never overrides chronological ordering.
    """
    et = envelope.event_type
    if et == MerchantEventType.MERCHANT_CREATED:
        return 10
    if et == MerchantEventType.APP_INSTALLED:
        return 20
    if et == MerchantEventType.SUBSCRIPTION_STARTED:
        return 30
    if isinstance(et, MerchantEventType):
        return 40

    if et == ProductEventType.PRODUCT_CREATED:
        return 100
    if et == ProductEventType.PRODUCT_VARIANT_CREATED:
        return 110
    if isinstance(et, ProductEventType):
        return 120

    if et == CampaignEventType.CAMPAIGN_CREATED:
        return 200
    if et == CampaignEventType.CAMPAIGN_UPDATED:
        return 210
    if et in (
        CampaignEventType.EMAIL_DELIVERED,
        CampaignEventType.SMS_DELIVERED,
        CampaignEventType.PUSH_DELIVERED,
        CampaignEventType.AD_VIEWED,
    ):
        return 220
    if et in (CampaignEventType.EMAIL_OPENED, CampaignEventType.PUSH_OPENED):
        return 230
    if et in (CampaignEventType.EMAIL_CLICKED, CampaignEventType.SMS_CLICKED, CampaignEventType.AD_CLICKED):
        return 240

    if et == ShopperEventType.SESSION_STARTED:
        return 300
    if et in (ShopperEventType.PRODUCT_SEARCHED, ShopperEventType.PRODUCT_VIEWED):
        return 310
    if et == ShopperEventType.WISHLIST_ADDED:
        return 315
    if et == ShopperEventType.ADD_TO_CART:
        return 320
    if et == ShopperEventType.CHECKOUT_STARTED:
        return 330
    if et == ShopperEventType.PURCHASE_COMPLETED:
        return 340
    if et == CampaignEventType.CAMPAIGN_CONVERTED:
        return 350
    if et == ShopperEventType.SESSION_ENDED:
        return 360

    return 999


class HistoricalSimulationOrchestrator:
    """Orchestrates an interleaved historical simulation across a calendar interval."""

    def __init__(self, config: HistoricalSimulationConfig) -> None:
        self._config = config
        self._sim_context = SimulationContext(
            mode=SimulationMode.HISTORICAL,
            start_time=config.start_datetime,
            end_time=config.end_datetime,
            seed=config.seed,
        )
        self._rng = self._sim_context.rng

    def generate_timeline(self) -> list[BaseEventEnvelope]:
        """Generates all synthetic envelopes across the configured date range,
        sorted in strict chronological order with priority tie-breaking.
        """
        all_envelopes: list[BaseEventEnvelope] = []

        # 1. Generate Merchant populations and catalog structures
        merchants = self._generate_merchants(all_envelopes)
        self._generate_catalogs(merchants, all_envelopes)

        # 2. Generate Shopper cohorts per merchant
        shoppers = self._generate_shoppers(merchants)

        # 3. Generate Campaigns per merchant and schedule delivery/engagement
        campaigns = self._generate_campaigns(merchants, all_envelopes)

        # 4. Generate causally linked Campaign Touches and Shopper Sessions
        self._generate_shopper_activity(merchants, shoppers, campaigns, all_envelopes)

        # 5. Global chronological sort
        all_envelopes.sort(key=lambda env: (env.event_timestamp, _event_priority(env), str(env.event_id)))

        return all_envelopes

    def _generate_merchants(self, envelopes: list[BaseEventEnvelope]) -> list[_MerchantSimState]:
        merchants: list[_MerchantSimState] = []
        total_seconds = (self._config.end_datetime - self._config.start_datetime).total_seconds()

        for m_idx in range(self._config.merchant_count):
            merchant_id = uuid.uuid4()
            shopify_store_id = f"store-{m_idx:05d}-{merchant_id.hex[:8]}"
            merchant_name = f"Merchant {m_idx:05d}"
            email = f"merchant{m_idx:05d}@example.com"
            country = self._rng.choice(_COUNTRIES)
            tz_name = self._rng.choice(_TIMEZONES)
            currency = self._rng.choice(_CURRENCIES)
            plan_key = self._rng.choice(_STARTING_PLANS)
            billing_cycle = self._rng.choice(list(BillingCycle))

            # Stagger install time
            if m_idx == 0:
                install_time = self._config.start_datetime
            else:
                fraction = m_idx / max(1, self._config.merchant_count)
                offset = int(fraction * total_seconds * 0.4) + self._rng.randint(0, 3600)
                install_time = self._config.start_datetime + timedelta(seconds=offset)
                if install_time > self._config.end_datetime - timedelta(days=14):
                    install_time = self._config.end_datetime - timedelta(days=14)

            state = _MerchantSimState(
                merchant_id=merchant_id,
                shopify_store_id=shopify_store_id,
                merchant_name=merchant_name,
                email=email,
                country=country,
                timezone=tz_name,
                store_currency=currency,
                plan_key=plan_key,
                billing_cycle=billing_cycle,
                install_time=install_time,
            )
            merchants.append(state)

            # 1. MERCHANT_CREATED
            envelopes.append(
                MerchantEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=MerchantEventType.MERCHANT_CREATED,
                    event_version=1,
                    event_timestamp=install_time,
                    merchant_id=merchant_id,
                    payload=MerchantCreatedPayload(
                        shopify_store_id=shopify_store_id,
                        merchant_name=merchant_name,
                        email=email,
                        country=country,
                        timezone=tz_name,
                        store_currency=currency,
                    ).model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            # 2. APP_INSTALLED
            app_installed_time = install_time + timedelta(seconds=2)
            envelopes.append(
                MerchantEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=MerchantEventType.APP_INSTALLED,
                    event_version=1,
                    event_timestamp=app_installed_time,
                    merchant_id=merchant_id,
                    payload=AppInstalledPayload(install_channel=self._rng.choice(_INSTALL_CHANNELS)).model_dump(
                        mode="json"
                    ),
                    source="historical-simulation",
                )
            )

            # 3. SUBSCRIPTION_STARTED
            sub_started_time = install_time + timedelta(seconds=5)
            amount_paid = self._amount_for(plan_key, billing_cycle)
            envelopes.append(
                MerchantEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=MerchantEventType.SUBSCRIPTION_STARTED,
                    event_version=1,
                    event_timestamp=sub_started_time,
                    merchant_id=merchant_id,
                    payload=SubscriptionStartedPayload(
                        plan_key=plan_key,
                        billing_cycle=billing_cycle,
                        amount_paid=amount_paid,
                    ).model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            # 4. FEATURE_ENABLED (within first 7 days)
            for feat_key in PLAN_CATALOG[plan_key].features:
                if self._rng.random() < 0.8:
                    feat_time = install_time + timedelta(hours=self._rng.randint(4, 120))
                    if feat_time <= self._config.end_datetime:
                        envelopes.append(
                            MerchantEventEnvelope(
                                event_id=uuid.uuid4(),
                                event_type=MerchantEventType.FEATURE_ENABLED,
                                event_version=1,
                                event_timestamp=feat_time,
                                merchant_id=merchant_id,
                                payload=FeatureEnabledPayload(feature_key=feat_key).model_dump(mode="json"),
                                source="historical-simulation",
                            )
                        )

            # 5. Periodic MERCHANT_LOGIN
            t_login = install_time + timedelta(days=self._rng.randint(1, 3))
            while t_login <= self._config.end_datetime:
                envelopes.append(
                    MerchantEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=MerchantEventType.MERCHANT_LOGIN,
                        event_version=1,
                        event_timestamp=t_login,
                        merchant_id=merchant_id,
                        payload=MerchantLoginPayload(login_channel=self._rng.choice(_LOGIN_CHANNELS)).model_dump(
                            mode="json"
                        ),
                        source="historical-simulation",
                    )
                )
                t_login += timedelta(days=self._rng.randint(2, 6), seconds=self._rng.randint(0, 3600))

            # 6. SUBSCRIPTION_RENEWED (monthly / annual boundaries)
            cycle_days = 30 if billing_cycle == BillingCycle.MONTHLY else 365
            t_renew = install_time + timedelta(days=cycle_days)
            while t_renew <= self._config.end_datetime:
                envelopes.append(
                    MerchantEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=MerchantEventType.SUBSCRIPTION_RENEWED,
                        event_version=1,
                        event_timestamp=t_renew,
                        merchant_id=merchant_id,
                        payload=SubscriptionRenewedPayload(
                            plan_key=plan_key,
                            billing_cycle=billing_cycle,
                            amount_paid=amount_paid,
                            renewal_at=t_renew,
                        ).model_dump(mode="json"),
                        source="historical-simulation",
                    )
                )
                t_renew += timedelta(days=cycle_days)

        return merchants

    def _generate_catalogs(self, merchants: list[_MerchantSimState], envelopes: list[BaseEventEnvelope]) -> None:
        for m_idx, m in enumerate(merchants):
            cat_time = m.install_time + timedelta(minutes=30)
            for p_idx in range(self._config.products_per_merchant):
                product_id = uuid.uuid4()
                prod_name = f"Product-{m_idx:03d}-{p_idx:03d}"
                category = self._rng.choice(_CATEGORIES)
                vendor = self._rng.choice(_VENDORS)
                prod_time = cat_time + timedelta(seconds=p_idx * 5)

                envelopes.append(
                    ProductEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=ProductEventType.PRODUCT_CREATED,
                        event_version=1,
                        event_timestamp=prod_time,
                        merchant_id=m.merchant_id,
                        product_id=product_id,
                        payload=ProductCreatedPayload(
                            product_name=prod_name,
                            category=category,
                            vendor=vendor,
                            status="active",
                        ).model_dump(mode="json"),
                        source="historical-simulation",
                    )
                )

                for v_idx in range(self._config.variants_per_product):
                    var_id = uuid.uuid4()
                    price = Decimal(self._rng.randint(99, 49999)) / Decimal("100")
                    qty = self._rng.randint(100, 1000)
                    var_time = prod_time + timedelta(seconds=v_idx + 1)

                    envelopes.append(
                        ProductEventEnvelope(
                            event_id=uuid.uuid4(),
                            event_type=ProductEventType.PRODUCT_VARIANT_CREATED,
                            event_version=1,
                            event_timestamp=var_time,
                            merchant_id=m.merchant_id,
                            product_id=product_id,
                            payload=ProductVariantCreatedPayload(
                                variant_id=var_id,
                                variant_name=f"Variant-{var_id.hex[:6]}",
                                sku=f"SKU-{product_id.hex[:6]}-{var_id.hex[:6]}",
                                price=price,
                                size=self._rng.choice(_SIZES),
                                color=self._rng.choice(_COLORS),
                                inventory_quantity=qty,
                                status="active",
                            ).model_dump(mode="json"),
                            source="historical-simulation",
                        )
                    )

                    m.variants.append(_VariantRecord(variant_id=var_id, product_id=product_id, price=price, inventory=qty))

    def _generate_shoppers(self, merchants: list[_MerchantSimState]) -> list[_ShopperSimState]:
        shoppers: list[_ShopperSimState] = []
        personas = ["browser", "cart_abandoner", "single_buyer", "repeat_buyer"]
        weights = [
            self._config.personas.browser,
            self._config.personas.cart_abandoner,
            self._config.personas.single_buyer,
            self._config.personas.repeat_buyer,
        ]

        for m in merchants:
            total_window = (self._config.end_datetime - m.install_time).total_seconds()
            for _ in range(self._config.shoppers_per_merchant):
                shopper_id = uuid.uuid4()
                persona = self._rng.choices(personas, weights=weights, k=1)[0]
                offset = int(self._rng.random() * total_window * 0.85)
                arrival_time = m.install_time + timedelta(hours=1) + timedelta(seconds=offset)
                if arrival_time > self._config.end_datetime - timedelta(days=2):
                    arrival_time = self._config.end_datetime - timedelta(days=2)

                shoppers.append(
                    _ShopperSimState(
                        shopper_id=shopper_id,
                        merchant_id=m.merchant_id,
                        persona=persona,
                        arrival_time=arrival_time,
                        email=f"shopper_{shopper_id.hex[:6]}@synthetic.com",
                    )
                )

        return shoppers

    def _generate_campaigns(
        self, merchants: list[_MerchantSimState], envelopes: list[BaseEventEnvelope]
    ) -> list[_CampaignSimState]:
        campaigns: list[_CampaignSimState] = []

        for m in merchants:
            # Generate deterministic segment IDs per merchant
            merchant_segment_ids = [uuid.uuid5(m.merchant_id, entry.segment_name) for entry in SEGMENT_CATALOG]
            merchant_window = (self._config.end_datetime - m.install_time).total_seconds()
            for c_idx in range(self._config.campaigns_per_merchant):
                camp_id = uuid.uuid4()
                seg_id = self._rng.choice(merchant_segment_ids)
                c_type = self._rng.choice(_CAMPAIGN_TYPES)
                c_medium = self._rng.choice(_CAMPAIGN_MEDIUMS)

                offset = int((c_idx + 1) / (self._config.campaigns_per_merchant + 1) * merchant_window * 0.7)
                start_time = m.install_time + timedelta(days=3) + timedelta(seconds=offset)
                if start_time > self._config.end_datetime - timedelta(days=10):
                    start_time = self._config.end_datetime - timedelta(days=10)

                duration_days = self._rng.randint(7, 21)
                end_time = min(start_time + timedelta(days=duration_days), self._config.end_datetime)

                campaign = _CampaignSimState(
                    campaign_id=camp_id,
                    merchant_id=m.merchant_id,
                    segment_id=seg_id,
                    campaign_type=c_type,
                    campaign_medium=c_medium,
                    start_time=start_time,
                    end_time=end_time,
                )
                campaigns.append(campaign)

                # CAMPAIGN_CREATED (draft)
                envelopes.append(
                    CampaignEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=CampaignEventType.CAMPAIGN_CREATED,
                        event_version=1,
                        event_timestamp=start_time,
                        merchant_id=m.merchant_id,
                        campaign_id=camp_id,
                        payload=CampaignCreatedPayload(
                            campaign_name=f"{c_type.title()} {c_medium.title()} - {camp_id.hex[:6]}",
                            campaign_type=c_type,
                            campaign_medium=c_medium,
                            segment_id=seg_id,
                            status="draft",
                            start_at=None,
                            end_at=None,
                        ).model_dump(mode="json"),
                        source="historical-simulation",
                    )
                )

                # CAMPAIGN_UPDATED (active)
                active_time = start_time + timedelta(minutes=10)
                envelopes.append(
                    CampaignEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=CampaignEventType.CAMPAIGN_UPDATED,
                        event_version=1,
                        event_timestamp=active_time,
                        merchant_id=m.merchant_id,
                        campaign_id=camp_id,
                        payload=CampaignUpdatedPayload(
                            changed_values={"status": "active", "start_at": start_time.isoformat()}
                        ).model_dump(mode="json"),
                        source="historical-simulation",
                    )
                )

                # CAMPAIGN_UPDATED (completed, if within window)
                if end_time < self._config.end_datetime:
                    envelopes.append(
                        CampaignEventEnvelope(
                            event_id=uuid.uuid4(),
                            event_type=CampaignEventType.CAMPAIGN_UPDATED,
                            event_version=1,
                            event_timestamp=end_time,
                            merchant_id=m.merchant_id,
                            campaign_id=camp_id,
                            payload=CampaignUpdatedPayload(
                                changed_values={"status": "completed", "end_at": end_time.isoformat()}
                            ).model_dump(mode="json"),
                            source="historical-simulation",
                        )
                    )

        return campaigns

    def _generate_shopper_activity(
        self,
        merchants: list[_MerchantSimState],
        shoppers: list[_ShopperSimState],
        campaigns: list[_CampaignSimState],
        envelopes: list[BaseEventEnvelope],
    ) -> None:
        merchants_by_id = {m.merchant_id: m for m in merchants}

        for shopper in shoppers:
            m = merchants_by_id[shopper.merchant_id]
            if not m.variants:
                continue

            # Check if this shopper is touched by a campaign
            eligible_camps = [c for c in campaigns if c.merchant_id == shopper.merchant_id and c.start_time >= shopper.arrival_time - timedelta(days=2)]
            camp_touch = self._rng.choice(eligible_camps) if eligible_camps and self._rng.random() < 0.4 else None

            if camp_touch:
                self._generate_campaign_influenced_journey(m, shopper, camp_touch, envelopes)
            else:
                self._generate_organic_journey(m, shopper, envelopes)

    def _generate_campaign_influenced_journey(
        self,
        m: _MerchantSimState,
        shopper: _ShopperSimState,
        camp: _CampaignSimState,
        envelopes: list[BaseEventEnvelope],
    ) -> None:
        deliv_time = camp.start_time + timedelta(hours=self._rng.randint(2, 48))
        if deliv_time > self._config.end_datetime:
            return

        # Delivery event
        deliv_type = {
            "email": CampaignEventType.EMAIL_DELIVERED,
            "sms": CampaignEventType.SMS_DELIVERED,
            "push": CampaignEventType.PUSH_DELIVERED,
            "ad": CampaignEventType.AD_VIEWED,
        }[camp.campaign_medium]
        deliv_payload = {
            "email": EmailDeliveredPayload(),
            "sms": SmsDeliveredPayload(),
            "push": PushDeliveredPayload(),
            "ad": AdViewedPayload(),
        }[camp.campaign_medium]

        envelopes.append(
            CampaignEventEnvelope(
                event_id=uuid.uuid4(),
                event_type=deliv_type,
                event_version=1,
                event_timestamp=deliv_time,
                merchant_id=m.merchant_id,
                campaign_id=camp.campaign_id,
                shopper_id=shopper.shopper_id,
                payload=deliv_payload.model_dump(mode="json"),
                source="historical-simulation",
            )
        )

        # Engagement: Open
        if self._rng.random() > self._config.campaign_influence.open_rate:
            return

        open_time = deliv_time + timedelta(minutes=self._rng.randint(5, 120))
        if open_time > self._config.end_datetime:
            return

        if camp.campaign_medium in ("email", "push"):
            open_type = CampaignEventType.EMAIL_OPENED if camp.campaign_medium == "email" else CampaignEventType.PUSH_OPENED
            open_payload = EmailOpenedPayload() if camp.campaign_medium == "email" else PushOpenedPayload()
            envelopes.append(
                CampaignEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=open_type,
                    event_version=1,
                    event_timestamp=open_time,
                    merchant_id=m.merchant_id,
                    campaign_id=camp.campaign_id,
                    shopper_id=shopper.shopper_id,
                    payload=open_payload.model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

        # Engagement: Click
        if self._rng.random() > self._config.campaign_influence.click_rate:
            return

        click_time = open_time + timedelta(seconds=self._rng.randint(15, 180))
        if click_time > self._config.end_datetime:
            return

        click_type = {
            "email": CampaignEventType.EMAIL_CLICKED,
            "sms": CampaignEventType.SMS_CLICKED,
            "push": CampaignEventType.PUSH_OPENED,  # Push click maps to interaction
            "ad": CampaignEventType.AD_CLICKED,
        }[camp.campaign_medium]
        url = f"https://example.com/campaign/{camp.campaign_id.hex}?utm_source={camp.campaign_medium}"
        click_payload = (
            PushOpenedPayload(action="open_url")
            if camp.campaign_medium == "push"
            else EmailClickedPayload(url=url)
            if camp.campaign_medium == "email"
            else SmsClickedPayload(url=url)
            if camp.campaign_medium == "sms"
            else AdClickedPayload(url=url)
        )

        # Determine if direct-session or cross-session
        is_direct = self._rng.random() < self._config.campaign_influence.direct_session_ratio
        converts = shopper.persona in ("single_buyer", "repeat_buyer")

        if is_direct:
            # DIRECT SESSION: campaign click shares session_id with storefront session
            session_id = uuid.uuid4()
            envelopes.append(
                CampaignEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=click_type,
                    event_version=1,
                    event_timestamp=click_time,
                    merchant_id=m.merchant_id,
                    campaign_id=camp.campaign_id,
                    shopper_id=shopper.shopper_id,
                    session_id=session_id,
                    payload=click_payload.model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            # Storefront session
            t_sess = click_time + timedelta(seconds=5)
            self._emit_session(
                m=m,
                shopper=shopper,
                session_id=session_id,
                start_time=t_sess,
                referrer=url,
                converts=converts,
                campaign_id=camp.campaign_id if converts else None,
                envelopes=envelopes,
            )

        else:
            # CROSS SESSION: campaign click session does not convert; later session within 7 days converts
            sess_1 = uuid.uuid4()
            envelopes.append(
                CampaignEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=click_type,
                    event_version=1,
                    event_timestamp=click_time,
                    merchant_id=m.merchant_id,
                    campaign_id=camp.campaign_id,
                    shopper_id=shopper.shopper_id,
                    session_id=sess_1,
                    payload=click_payload.model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            # Session 1: browse only
            t_sess1 = click_time + timedelta(seconds=5)
            self._emit_session(
                m=m,
                shopper=shopper,
                session_id=sess_1,
                start_time=t_sess1,
                referrer=url,
                converts=False,
                campaign_id=None,
                envelopes=envelopes,
            )

            if converts:
                # Session 2: return 1-4 days later and purchase
                sess_2 = uuid.uuid4()
                t_sess2 = t_sess1 + timedelta(days=self._rng.randint(1, 4), hours=self._rng.randint(1, 10))
                if t_sess2 < self._config.end_datetime:
                    self._emit_session(
                        m=m,
                        shopper=shopper,
                        session_id=sess_2,
                        start_time=t_sess2,
                        referrer="direct",
                        converts=True,
                        campaign_id=camp.campaign_id,
                        envelopes=envelopes,
                    )

    def _generate_organic_journey(
        self,
        m: _MerchantSimState,
        shopper: _ShopperSimState,
        envelopes: list[BaseEventEnvelope],
    ) -> None:
        if shopper.persona == "browser":
            # 1-2 browse-only sessions
            sess_id = uuid.uuid4()
            self._emit_session(m, shopper, sess_id, shopper.arrival_time, "google.com", False, None, envelopes)

        elif shopper.persona == "cart_abandoner":
            # Session with cart addition but no checkout completion
            sess_id = uuid.uuid4()
            self._emit_session(
                m, shopper, sess_id, shopper.arrival_time, "direct", False, None, envelopes, add_cart=True
            )

        elif shopper.persona == "single_buyer":
            # 1 session with purchase
            sess_id = uuid.uuid4()
            self._emit_session(m, shopper, sess_id, shopper.arrival_time, "google.com", True, None, envelopes)

        elif shopper.persona == "repeat_buyer":
            # Multiple sessions across days/weeks
            sessions_count = self._rng.randint(2, 4)
            curr_time = shopper.arrival_time
            for _ in range(sessions_count):
                if curr_time >= self._config.end_datetime:
                    break
                sess_id = uuid.uuid4()
                self._emit_session(m, shopper, sess_id, curr_time, "direct", True, None, envelopes)
                curr_time += timedelta(days=self._rng.randint(7, 21), hours=self._rng.randint(1, 12))

    def _emit_session(
        self,
        m: _MerchantSimState,
        shopper: _ShopperSimState,
        session_id: uuid.UUID,
        start_time: datetime,
        referrer: str | None,
        converts: bool,
        campaign_id: uuid.UUID | None,
        envelopes: list[BaseEventEnvelope],
        add_cart: bool = False,
    ) -> None:
        if start_time > self._config.end_datetime:
            return

        # 1. SESSION_STARTED
        envelopes.append(
            ShopperEventEnvelope(
                event_id=uuid.uuid4(),
                event_type=ShopperEventType.SESSION_STARTED,
                event_version=1,
                event_timestamp=start_time,
                merchant_id=m.merchant_id,
                shopper_id=shopper.shopper_id,
                session_id=session_id,
                payload=SessionStartedPayload(referrer=referrer, email=shopper.email).model_dump(mode="json"),
                source="historical-simulation",
            )
        )

        curr_t = start_time + timedelta(seconds=self._rng.randint(10, 45))

        # 2. PRODUCT_SEARCHED / PRODUCT_VIEWED
        chosen_var = self._rng.choice(m.variants)
        envelopes.append(
            ShopperEventEnvelope(
                event_id=uuid.uuid4(),
                event_type=ShopperEventType.PRODUCT_VIEWED,
                event_version=1,
                event_timestamp=curr_t,
                merchant_id=m.merchant_id,
                shopper_id=shopper.shopper_id,
                session_id=session_id,
                payload=ProductViewedPayload(
                    product_id=chosen_var.product_id, variant_id=chosen_var.variant_id
                ).model_dump(mode="json"),
                source="historical-simulation",
            )
        )

        # 3. Cart addition
        if converts or add_cart:
            curr_t += timedelta(seconds=self._rng.randint(30, 90))
            envelopes.append(
                ShopperEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=ShopperEventType.ADD_TO_CART,
                    event_version=1,
                    event_timestamp=curr_t,
                    merchant_id=m.merchant_id,
                    shopper_id=shopper.shopper_id,
                    session_id=session_id,
                    payload=AddToCartPayload(
                        product_id=chosen_var.product_id,
                        variant_id=chosen_var.variant_id,
                        quantity=1,
                        unit_price=chosen_var.price,
                    ).model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

        # 4. Checkout & Purchase (only for converting flows)
        if converts:
            curr_t += timedelta(seconds=self._rng.randint(30, 90))
            cart_item = CartItem(
                product_id=chosen_var.product_id,
                variant_id=chosen_var.variant_id,
                quantity=1,
                unit_price=chosen_var.price,
            )
            envelopes.append(
                ShopperEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=ShopperEventType.CHECKOUT_STARTED,
                    event_version=1,
                    event_timestamp=curr_t,
                    merchant_id=m.merchant_id,
                    shopper_id=shopper.shopper_id,
                    session_id=session_id,
                    payload=CheckoutStartedPayload(
                        cart_value=chosen_var.price,
                        items=[cart_item],
                        email=shopper.email,
                    ).model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            order_id = uuid.uuid4()
            curr_t += timedelta(seconds=self._rng.randint(20, 60))
            order_item = OrderItemPayload(
                product_id=chosen_var.product_id,
                variant_id=chosen_var.variant_id,
                quantity=1,
                unit_price=chosen_var.price,
            )
            envelopes.append(
                ShopperEventEnvelope(
                    event_id=uuid.uuid4(),
                    event_type=ShopperEventType.PURCHASE_COMPLETED,
                    event_version=1,
                    event_timestamp=curr_t,
                    merchant_id=m.merchant_id,
                    shopper_id=shopper.shopper_id,
                    session_id=session_id,
                    payload=PurchaseCompletedPayload(
                        order_id=order_id,
                        total_amount=chosen_var.price,
                        items=[order_item],
                        email=shopper.email,
                    ).model_dump(mode="json"),
                    source="historical-simulation",
                )
            )

            # If campaign attributed, emit CAMPAIGN_CONVERTED
            if campaign_id is not None:
                envelopes.append(
                    CampaignEventEnvelope(
                        event_id=uuid.uuid4(),
                        event_type=CampaignEventType.CAMPAIGN_CONVERTED,
                        event_version=1,
                        event_timestamp=curr_t + timedelta(seconds=1),
                        merchant_id=m.merchant_id,
                        campaign_id=campaign_id,
                        shopper_id=shopper.shopper_id,
                        session_id=session_id,
                        payload=CampaignConvertedPayload(order_id=order_id).model_dump(mode="json"),
                        source="historical-simulation",
                    )
                )

        # 5. SESSION_ENDED
        curr_t += timedelta(seconds=self._rng.randint(15, 60))
        envelopes.append(
            ShopperEventEnvelope(
                event_id=uuid.uuid4(),
                event_type=ShopperEventType.SESSION_ENDED,
                event_version=1,
                event_timestamp=curr_t,
                merchant_id=m.merchant_id,
                shopper_id=shopper.shopper_id,
                session_id=session_id,
                payload=SessionEndedPayload().model_dump(mode="json"),
                source="historical-simulation",
            )
        )

    def _amount_for(self, plan_key: PlanKey, billing_cycle: BillingCycle) -> float:
        entry = PLAN_CATALOG[plan_key]
        return entry.monthly_price if billing_cycle == BillingCycle.MONTHLY else entry.annual_price
