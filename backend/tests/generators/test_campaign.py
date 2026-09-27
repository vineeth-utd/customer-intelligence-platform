import uuid
from datetime import datetime, timezone, timedelta

from app.generators.campaign import (
    CampaignLifecycleGenerator,
    MerchantContext,
    OrderContext,
)
from app.schemas.events.event_types import CampaignEventType


def test_campaign_tick_separation():
    merchant_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    
    ctx = MerchantContext(merchant_id=merchant_id, segment_ids=[segment_id], shopper_ids=[shopper_id], orders=[])

    generator = CampaignLifecycleGenerator(concurrency_per_merchant=1, seed=42)
    generator.update_contexts([ctx])

    # Find the tick where a campaign is spawned
    spawn_envs = []
    for _ in range(50):
        spawn_envs = generator.tick()
        if spawn_envs:
            break
            
    assert len(spawn_envs) == 1
    assert spawn_envs[0].event_type == CampaignEventType.CAMPAIGN_CREATED
    assert spawn_envs[0].payload["status"] == "draft"
    
    # Tick 2 should activate it
    activation_envs = generator.tick()
    assert len(activation_envs) == 1
    assert activation_envs[0].event_type == CampaignEventType.CAMPAIGN_UPDATED
    assert activation_envs[0].payload["changed_values"]["status"] == "active"


def test_anonymous_ad_behavior():
    merchant_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()
    placed_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Known order for known shopper
    ctx = MerchantContext(
        merchant_id=merchant_id, 
        segment_ids=[segment_id], 
        shopper_ids=[shopper_id], 
        orders=[OrderContext(order_id=order_id, shopper_id=shopper_id, placed_at=placed_at)]
    )

    generator = CampaignLifecycleGenerator(concurrency_per_merchant=10, seed=1)
    generator.update_contexts([ctx])
    
    # Force the generator to spawn an Ad campaign
    # We can just inject one manually into active_campaigns for the test
    generator.tick()  # normal init stuff
    
    # Let's run a loop until we naturally spawn an ad campaign
    envelopes = []
    for _ in range(100):
        envelopes.extend(generator.tick())
        
    ad_events = [e for e in envelopes if e.event_type in (CampaignEventType.AD_VIEWED, CampaignEventType.AD_CLICKED)]
    conversions = [e for e in envelopes if e.event_type == CampaignEventType.CAMPAIGN_CONVERTED]
    
    # Ensure some anonymous ad events occurred (shopper_id=None)
    anonymous_ads = [e for e in ad_events if e.shopper_id is None]
    assert len(anonymous_ads) > 0, "Should generate anonymous ad events"
    
    # Known ad events might also occur
    known_ads = [e for e in ad_events if e.shopper_id == shopper_id]
    
    for conv in conversions:
        assert conv.shopper_id is not None, "Anonymous engagements must never convert"
        assert conv.payload["order_id"] == str(order_id)
        

def test_context_refresh():
    merchant_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    
    ctx = MerchantContext(merchant_id=merchant_id, segment_ids=[segment_id], shopper_ids=[shopper_id], orders=[])

    generator = CampaignLifecycleGenerator(concurrency_per_merchant=1, seed=42)
    generator.update_contexts([ctx])
    
    # Tick until a campaign is spawned
    for _ in range(50):
        envs = generator.tick()
        if generator._active_campaigns:
            break
            
    campaign_id = generator._active_campaigns[0].campaign_id
    
    # Introduce a new merchant context
    merchant_id_2 = uuid.uuid4()
    segment_id_2 = uuid.uuid4()
    shopper_id_2 = uuid.uuid4()
    ctx2 = MerchantContext(merchant_id=merchant_id_2, segment_ids=[segment_id_2], shopper_ids=[shopper_id_2], orders=[])
    
    generator.update_contexts([ctx, ctx2])
    
    # Existing active campaign should remain
    assert any(c.campaign_id == campaign_id for c in generator._active_campaigns)
    
    # Tick enough to see campaigns from both merchants
    merchants_seen = set()
    for _ in range(50):
        envs = generator.tick()
        for e in envs:
            merchants_seen.add(e.merchant_id)
            
    assert merchant_id in merchants_seen
    assert merchant_id_2 in merchants_seen
