from datetime import datetime, timezone
import uuid

from app.generators.config import HistoricalSimulationConfig, PersonaWeights, CampaignInfluenceWeights
from app.generators.historical_orchestrator import HistoricalSimulationOrchestrator, _event_priority
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


def _sample_config(seed: int = 42) -> HistoricalSimulationConfig:
    return HistoricalSimulationConfig(
        start_datetime=datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_datetime=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
        seed=seed,
        merchant_count=3,
        products_per_merchant=5,
        variants_per_product=2,
        shoppers_per_merchant=25,
        campaigns_per_merchant=2,
        personas=PersonaWeights(browser=0.4, cart_abandoner=0.3, single_buyer=0.2, repeat_buyer=0.1),
        campaign_influence=CampaignInfluenceWeights(
            delivery_rate=1.0,
            open_rate=0.8,
            click_rate=0.7,
            conversion_rate=0.5,
            direct_session_ratio=0.5,
        ),
    )


def test_global_chronological_monotonicity():
    config = _sample_config(seed=10)
    orchestrator = HistoricalSimulationOrchestrator(config)
    timeline = orchestrator.generate_timeline()

    assert len(timeline) > 0

    # Ensure strictly monotonic timestamps
    for i in range(len(timeline) - 1):
        prev_env = timeline[i]
        next_env = timeline[i + 1]
        assert prev_env.event_timestamp <= next_env.event_timestamp
        if prev_env.event_timestamp == next_env.event_timestamp:
            assert _event_priority(prev_env) <= _event_priority(next_env)

    # Ensure all timestamps fall within the configured window
    for env in timeline:
        assert config.start_datetime <= env.event_timestamp <= config.end_datetime


def test_deterministic_generation_under_same_seed():
    config_1 = _sample_config(seed=99)
    config_2 = _sample_config(seed=99)
    config_3 = _sample_config(seed=100)

    timeline_1 = HistoricalSimulationOrchestrator(config_1).generate_timeline()
    timeline_2 = HistoricalSimulationOrchestrator(config_2).generate_timeline()
    timeline_3 = HistoricalSimulationOrchestrator(config_3).generate_timeline()

    assert len(timeline_1) == len(timeline_2)
    types_1 = [e.event_type.value for e in timeline_1]
    types_2 = [e.event_type.value for e in timeline_2]
    types_3 = [e.event_type.value for e in timeline_3]

    assert types_1 == types_2
    assert types_1 != types_3


def test_causal_ordering_merchant_and_catalog():
    config = _sample_config(seed=77)
    timeline = HistoricalSimulationOrchestrator(config).generate_timeline()

    merchant_installs: dict[uuid.UUID, datetime] = {}
    for env in timeline:
        if isinstance(env, MerchantEventEnvelope):
            if env.event_type == MerchantEventType.APP_INSTALLED:
                merchant_installs[env.merchant_id] = env.event_timestamp

    assert len(merchant_installs) == config.merchant_count

    # Verify all products are created after the merchant was installed
    for env in timeline:
        if isinstance(env, ProductEventEnvelope):
            install_time = merchant_installs[env.merchant_id]
            assert env.event_timestamp >= install_time


def test_campaign_shopper_causality_direct_session():
    config = _sample_config(seed=42)
    timeline = HistoricalSimulationOrchestrator(config).generate_timeline()

    # Find campaign clicks with session_id
    campaign_clicks = [
        e
        for e in timeline
        if isinstance(e, CampaignEventEnvelope)
        and e.event_type
        in (CampaignEventType.EMAIL_CLICKED, CampaignEventType.SMS_CLICKED, CampaignEventType.AD_CLICKED)
        and e.session_id is not None
    ]
    assert len(campaign_clicks) > 0

    session_starts_by_id = {
        e.session_id: e
        for e in timeline
        if isinstance(e, ShopperEventEnvelope) and e.event_type == ShopperEventType.SESSION_STARTED
    }

    # Verify each stamped campaign click corresponds to a storefront session
    direct_session_clicks = [c for c in campaign_clicks if c.session_id in session_starts_by_id]
    assert len(direct_session_clicks) > 0

    for click in direct_session_clicks:
        session_start = session_starts_by_id[click.session_id]
        # Session must start at or after the campaign click
        assert session_start.event_timestamp >= click.event_timestamp
        assert session_start.merchant_id == click.merchant_id
        assert session_start.shopper_id == click.shopper_id


def test_campaign_converted_references_valid_order():
    config = _sample_config(seed=42)
    timeline = HistoricalSimulationOrchestrator(config).generate_timeline()

    campaign_conversions = [
        e
        for e in timeline
        if isinstance(e, CampaignEventEnvelope) and e.event_type == CampaignEventType.CAMPAIGN_CONVERTED
    ]
    assert len(campaign_conversions) > 0

    purchase_order_ids = {
        uuid.UUID(e.payload["order_id"]): e
        for e in timeline
        if isinstance(e, ShopperEventEnvelope) and e.event_type == ShopperEventType.PURCHASE_COMPLETED
    }

    for conv in campaign_conversions:
        conv_order_id = uuid.UUID(conv.payload["order_id"])
        assert conv_order_id in purchase_order_ids
        purchase_env = purchase_order_ids[conv_order_id]
        # CAMPAIGN_CONVERTED must occur at or after the purchase completed
        assert conv.event_timestamp >= purchase_env.event_timestamp
        assert conv.merchant_id == purchase_env.merchant_id
        assert conv.shopper_id == purchase_env.shopper_id


def test_personas_produce_varied_behavior():
    config = _sample_config(seed=42)
    timeline = HistoricalSimulationOrchestrator(config).generate_timeline()

    orders_per_shopper: dict[uuid.UUID, int] = {}
    carts_per_shopper: dict[uuid.UUID, int] = {}
    sessions_per_shopper: dict[uuid.UUID, int] = {}

    for env in timeline:
        if isinstance(env, ShopperEventEnvelope):
            if env.event_type == ShopperEventType.SESSION_STARTED:
                sessions_per_shopper[env.shopper_id] = sessions_per_shopper.get(env.shopper_id, 0) + 1
            elif env.event_type == ShopperEventType.ADD_TO_CART:
                carts_per_shopper[env.shopper_id] = carts_per_shopper.get(env.shopper_id, 0) + 1
            elif env.event_type == ShopperEventType.PURCHASE_COMPLETED:
                orders_per_shopper[env.shopper_id] = orders_per_shopper.get(env.shopper_id, 0) + 1

    # Browsers: have sessions, 0 orders, 0 carts
    browsers = [
        s for s, count in sessions_per_shopper.items()
        if orders_per_shopper.get(s, 0) == 0 and carts_per_shopper.get(s, 0) == 0
    ]
    assert len(browsers) > 0

    # Abandoners: have carts, 0 orders
    abandoners = [
        s for s, count in carts_per_shopper.items()
        if orders_per_shopper.get(s, 0) == 0
    ]
    assert len(abandoners) > 0

    # Single buyers: exactly 1 order
    single_buyers = [s for s, count in orders_per_shopper.items() if count == 1]
    assert len(single_buyers) > 0

    # Repeat buyers: 2+ orders
    repeat_buyers = [s for s, count in orders_per_shopper.items() if count >= 2]
    assert len(repeat_buyers) > 0

