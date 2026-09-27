import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.payloads.campaign import (
    CampaignCreatedPayload,
    CampaignUpdatedPayload,
    EmailDeliveredPayload,
    EmailOpenedPayload,
    EmailClickedPayload,
    SmsDeliveredPayload,
    SmsClickedPayload,
    PushDeliveredPayload,
    PushOpenedPayload,
    AdViewedPayload,
    AdClickedPayload,
    CampaignConvertedPayload,
)

_CAMPAIGN_TYPES = ["promotional", "newsletter", "abandoned_cart", "winback"]
_CAMPAIGN_MEDIUMS = ["email", "sms", "push", "ad"]


@dataclass
class OrderContext:
    order_id: uuid.UUID
    shopper_id: uuid.UUID
    placed_at: datetime


@dataclass
class MerchantContext:
    merchant_id: uuid.UUID
    segment_ids: list[uuid.UUID]
    shopper_ids: list[uuid.UUID]
    orders: list[OrderContext]


@dataclass
class CampaignState:
    campaign_id: uuid.UUID
    merchant_id: uuid.UUID
    segment_id: uuid.UUID
    campaign_type: str
    campaign_medium: str
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    
    # Targeting & Engagement
    targeted_shoppers: set[uuid.UUID] = field(default_factory=set)
    delivered_to: set[uuid.UUID] = field(default_factory=set)
    opened_by: set[uuid.UUID] = field(default_factory=set)
    clicked_by: set[uuid.UUID] = field(default_factory=set)
    
    # Conversion
    attributed_orders: set[uuid.UUID] = field(default_factory=set)
    
    # Time/Tick management
    ticks_active: int = 0
    max_active_ticks: int = 5


class CampaignLifecycleGenerator:
    """Deterministic, in-memory campaign lifecycle simulator."""

    def __init__(self, concurrency_per_merchant: int = 2, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._concurrency_per_merchant = concurrency_per_merchant
        self._contexts: dict[uuid.UUID, MerchantContext] = {}
        self._active_campaigns: list[CampaignState] = []
        self._completed_campaigns: list[CampaignState] = []

    def update_contexts(self, contexts: list[MerchantContext]) -> None:
        """Fully replace the merchant context pool with the latest authoritative state.
        
        Active campaigns maintain their own in-flight state independently, 
        so this just updates the pools they draw from for conversions/new spawning.
        """
        self._contexts = {ctx.merchant_id: ctx for ctx in contexts}

    def tick(self) -> list[CampaignEventEnvelope]:
        envelopes: list[CampaignEventEnvelope] = []
        
        # 1. Potentially spawn new campaigns for each merchant if below concurrency limit
        newly_spawned_ids = set()
        for merchant_id, ctx in self._contexts.items():
            if not ctx.segment_ids:
                continue
            active_for_merchant = [c for c in self._active_campaigns if c.merchant_id == merchant_id]
            if len(active_for_merchant) < self._concurrency_per_merchant and self._rng.random() < 0.3:
                new_campaign, env = self._spawn_campaign(ctx)
                if new_campaign:
                    self._active_campaigns.append(new_campaign)
                    newly_spawned_ids.add(new_campaign.campaign_id)
                    if env:
                        envelopes.append(env)
        
        # 2. Advance active campaigns
        for campaign in list(self._active_campaigns):
            if campaign.campaign_id in newly_spawned_ids:
                continue
            envelopes.extend(self._advance_campaign(campaign))
            
        # 3. Cleanup completed campaigns
        completed = [c for c in self._active_campaigns if c.status == "completed"]
        for c in completed:
            self._active_campaigns.remove(c)
            self._completed_campaigns.append(c)

        return envelopes

    def _spawn_campaign(self, ctx: MerchantContext) -> tuple[CampaignState | None, CampaignEventEnvelope | None]:
        if not ctx.segment_ids:
            return None, None
            
        campaign_id = uuid.uuid4()
        segment_id = self._rng.choice(ctx.segment_ids)
        campaign_type = self._rng.choice(_CAMPAIGN_TYPES)
        campaign_medium = self._rng.choice(_CAMPAIGN_MEDIUMS)
        
        # Determine audience
        audience = set()
        if ctx.shopper_ids:
            audience.update(self._rng.sample(ctx.shopper_ids, k=min(10, len(ctx.shopper_ids))))
            
        # If no targeted shoppers, only ads can run fully anonymously
        if not audience and campaign_medium != "ad":
            return None, None

        state = CampaignState(
            campaign_id=campaign_id,
            merchant_id=ctx.merchant_id,
            segment_id=segment_id,
            campaign_type=campaign_type,
            campaign_medium=campaign_medium,
            status="draft",
            targeted_shoppers=audience,
        )
        
        env = self._build_envelope(
            state,
            None,
            CampaignEventType.CAMPAIGN_CREATED,
            CampaignCreatedPayload(
                campaign_name=f"{campaign_type.title()} {campaign_medium.title()} - {campaign_id.hex[:6]}",
                campaign_type=campaign_type,
                campaign_medium=campaign_medium,
                segment_id=segment_id,
                status="draft",
                start_at=None,
                end_at=None,
            )
        )
        return state, env

    def _advance_campaign(self, state: CampaignState) -> list[CampaignEventEnvelope]:
        envelopes = []
        
        if state.status == "draft":
            state.status = "active"
            state.start_at = datetime.now(timezone.utc)
            envelopes.append(self._build_envelope(
                state, None, CampaignEventType.CAMPAIGN_UPDATED, CampaignUpdatedPayload(
                    changed_values={"status": "active", "start_at": state.start_at.isoformat()}
                )
            ))
            return envelopes
            
        if state.status == "active":
            state.ticks_active += 1
            
            # Anonymous ad interactions
            if state.campaign_medium == "ad" and self._rng.random() < 0.8:
                envelopes.append(self._build_envelope(state, None, CampaignEventType.AD_VIEWED, AdViewedPayload()))
                if self._rng.random() < 0.3:
                    url = f"https://example.com/campaign/{state.campaign_id.hex}"
                    envelopes.append(self._build_envelope(state, None, CampaignEventType.AD_CLICKED, AdClickedPayload(url=url)))
            
            # Progress engagement for targeted (known) shoppers
            for shopper_id in list(state.targeted_shoppers):
                env = self._progress_shopper_engagement(state, shopper_id)
                if env:
                    envelopes.append(env)
                    
                # Evaluate conversion for this shopper if they have engaged
                engaged = False
                if state.campaign_medium == "email" and shopper_id in state.clicked_by:
                    engaged = True
                elif state.campaign_medium == "sms" and shopper_id in state.clicked_by:
                    engaged = True
                elif state.campaign_medium == "push" and shopper_id in state.opened_by:
                    engaged = True
                elif state.campaign_medium == "ad" and shopper_id in state.clicked_by:
                    engaged = True

                if engaged and shopper_id is not None and self._rng.random() < 0.2:
                    # Look for eligible order
                    ctx = self._contexts.get(state.merchant_id)
                    if ctx:
                        valid_orders = [
                            o for o in ctx.orders 
                            if o.shopper_id == shopper_id 
                            and state.start_at is not None 
                            and o.placed_at >= state.start_at 
                            and o.order_id not in state.attributed_orders
                        ]
                        if valid_orders:
                            chosen_order = self._rng.choice(valid_orders)
                            state.attributed_orders.add(chosen_order.order_id)
                            envelopes.append(self._build_envelope(
                                state, shopper_id, CampaignEventType.CAMPAIGN_CONVERTED, CampaignConvertedPayload(
                                    order_id=chosen_order.order_id
                                )
                            ))
                            
            if state.ticks_active >= state.max_active_ticks:
                state.status = "completed"
                state.end_at = datetime.now(timezone.utc)
                envelopes.append(self._build_envelope(
                    state, None, CampaignEventType.CAMPAIGN_UPDATED, CampaignUpdatedPayload(
                        changed_values={"status": "completed", "end_at": state.end_at.isoformat()}
                    )
                ))
                
        return envelopes

    def _progress_shopper_engagement(self, state: CampaignState, shopper_id: uuid.UUID) -> CampaignEventEnvelope | None:
        medium = state.campaign_medium
        
        # Delivery/View
        if shopper_id not in state.delivered_to:
            if self._rng.random() < 0.8:
                state.delivered_to.add(shopper_id)
                if medium == "email":
                    return self._build_envelope(state, shopper_id, CampaignEventType.EMAIL_DELIVERED, EmailDeliveredPayload())
                elif medium == "sms":
                    return self._build_envelope(state, shopper_id, CampaignEventType.SMS_DELIVERED, SmsDeliveredPayload())
                elif medium == "push":
                    return self._build_envelope(state, shopper_id, CampaignEventType.PUSH_DELIVERED, PushDeliveredPayload())
                elif medium == "ad":
                    return self._build_envelope(state, shopper_id, CampaignEventType.AD_VIEWED, AdViewedPayload())
            return None
            
        # Open
        if medium in ("email", "push") and shopper_id not in state.opened_by:
            if self._rng.random() < 0.5:
                state.opened_by.add(shopper_id)
                if medium == "email":
                    return self._build_envelope(state, shopper_id, CampaignEventType.EMAIL_OPENED, EmailOpenedPayload())
                elif medium == "push":
                    return self._build_envelope(state, shopper_id, CampaignEventType.PUSH_OPENED, PushOpenedPayload())
            return None
            
        # Click
        can_click = False
        if medium == "email" and shopper_id in state.opened_by:
            can_click = True
        elif medium in ("sms", "ad"):
            can_click = True
            
        if can_click and shopper_id not in state.clicked_by:
            if self._rng.random() < 0.3:
                state.clicked_by.add(shopper_id)
                url = f"https://example.com/campaign/{state.campaign_id.hex}"
                if medium == "email":
                    return self._build_envelope(state, shopper_id, CampaignEventType.EMAIL_CLICKED, EmailClickedPayload(url=url))
                elif medium == "sms":
                    return self._build_envelope(state, shopper_id, CampaignEventType.SMS_CLICKED, SmsClickedPayload(url=url))
                elif medium == "ad":
                    return self._build_envelope(state, shopper_id, CampaignEventType.AD_CLICKED, AdClickedPayload(url=url))
                    
        return None

    def _build_envelope(self, state: CampaignState, shopper_id: uuid.UUID | None, event_type: CampaignEventType, payload) -> CampaignEventEnvelope:
        return CampaignEventEnvelope(
            event_id=uuid.uuid4(),
            event_type=event_type,
            event_version=1,
            event_timestamp=datetime.now(timezone.utc),
            merchant_id=state.merchant_id,
            campaign_id=state.campaign_id,
            shopper_id=shopper_id,
            payload=payload.model_dump(mode="json"),
            source="campaign-generator",
        )
