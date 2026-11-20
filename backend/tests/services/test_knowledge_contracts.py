from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.knowledge import (
    CampaignSummaryFacts,
    KnowledgeAccessScope,
    KnowledgeFactPayload,
    KnowledgeMetadata,
    KnowledgeQdrantPayload,
    KnowledgeStatus,
    KnowledgeType,
    MerchantPerformanceFacts,
    MerchantSummaryFacts,
    PlatformPerformanceFacts,
    ShopperBehaviourFacts,
    ShopperJourneyFacts,
    SourceReference,
)
from app.services.knowledge import CIP_KNOWLEDGE_NAMESPACE, generate_knowledge_point_id


def test_knowledge_point_id_deterministic_and_unique():
    """Verify that generate_knowledge_point_id produces deterministic, collision-free RFC 4122 UUIDv5s."""
    merchant_id_1 = uuid.uuid4()
    merchant_id_2 = uuid.uuid4()
    shopper_id = uuid.uuid4()
    journey_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    d_start = date(2026, 10, 1)
    d_end = date(2026, 10, 31)

    # 1. Deterministic repeatability
    id_m1_a = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant_id_1)
    id_m1_b = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant_id_1)
    assert id_m1_a == id_m1_b
    assert id_m1_a.version == 5

    # 2. Distinct across different entities
    id_m2 = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant_id_2)
    assert id_m1_a != id_m2

    # 3. Shopper behaviour
    id_sh1 = generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR, shopper_id)
    id_sh2 = generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR, shopper_id)
    assert id_sh1 == id_sh2

    # 4. Shopper journey
    id_j1 = generate_knowledge_point_id(KnowledgeType.SHOPPER_JOURNEY, journey_id)
    id_j2 = generate_knowledge_point_id(KnowledgeType.SHOPPER_JOURNEY, journey_id)
    assert id_j1 == id_j2

    # 5. Campaign summary
    id_c1 = generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY, campaign_id)
    id_c2 = generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY, campaign_id)
    assert id_c1 == id_c2

    # 6. Merchant performance (closed month)
    id_mp1 = generate_knowledge_point_id(KnowledgeType.MERCHANT_PERFORMANCE, merchant_id_1, d_start, d_end)
    id_mp2 = generate_knowledge_point_id(KnowledgeType.MERCHANT_PERFORMANCE, merchant_id_1, d_start, d_end)
    assert id_mp1 == id_mp2

    # Distinct month produces distinct ID
    id_mp_next = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE, merchant_id_1, date(2026, 11, 1), date(2026, 11, 30)
    )
    assert id_mp1 != id_mp_next

    # 7. Platform performance (closed month, no entity_id)
    id_pp1 = generate_knowledge_point_id(KnowledgeType.PLATFORM_PERFORMANCE, period_start=d_start, period_end=d_end)
    id_pp2 = generate_knowledge_point_id(KnowledgeType.PLATFORM_PERFORMANCE, period_start=d_start, period_end=d_end)
    assert id_pp1 == id_pp2
    assert id_pp1 != id_mp1

    # Verify all generated IDs are distinct across types
    all_ids = {id_m1_a, id_m2, id_sh1, id_j1, id_c1, id_mp1, id_pp1}
    assert len(all_ids) == 7


def test_knowledge_point_id_validation_errors():
    """Verify that missing required arguments raise ValueError."""
    with pytest.raises(ValueError, match="merchant_summary requires merchant_id"):
        generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY)

    with pytest.raises(ValueError, match="shopper_behaviour requires shopper_id"):
        generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR)

    with pytest.raises(ValueError, match="shopper_journey requires stable journey_id"):
        generate_knowledge_point_id(KnowledgeType.SHOPPER_JOURNEY)

    with pytest.raises(ValueError, match="campaign_summary requires campaign_id"):
        generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY)

    with pytest.raises(ValueError, match="merchant_performance requires"):
        generate_knowledge_point_id(KnowledgeType.MERCHANT_PERFORMANCE, entity_id=uuid.uuid4())

    with pytest.raises(ValueError, match="platform_performance requires"):
        generate_knowledge_point_id(KnowledgeType.PLATFORM_PERFORMANCE)


def test_shopper_behaviour_facts_pii_exclusion():
    """Verify that ShopperBehaviourFacts excludes and rejects PII fields."""
    facts = ShopperBehaviourFacts(
        total_orders=5,
        total_spend=Decimal("450.00"),
        average_order_value=Decimal("90.00"),
        wishlist_item_count=3,
        save_for_later_item_count=1,
        campaign_engagement_count=8,
        preferred_category="Apparel",
        preferred_size="M",
        last_purchase_at=datetime.now(timezone.utc),
        segments=["High Spenders", "Active 30d"],
        total_journeys=6,
        converted_journeys=5,
    )
    assert facts.total_orders == 5
    assert "High Spenders" in facts.segments

    # Attempting to supply forbidden PII fields must raise ValidationError
    with pytest.raises(ValidationError):
        ShopperBehaviourFacts(
            total_orders=1,
            total_spend=Decimal("10.00"),
            average_order_value=Decimal("10.00"),
            wishlist_item_count=0,
            save_for_later_item_count=0,
            campaign_engagement_count=0,
            email="shopper@test.com",  # FORBIDDEN PII
        )


def test_source_reference_flexible_locator():
    """Verify that SourceReference accommodates string and structured dictionary locators."""
    ref_str = SourceReference(
        source_type="shopper_journey",
        source_reference=str(uuid.uuid4()),
        description="Completed converting journey",
    )
    assert isinstance(ref_str.source_reference, str)

    ref_dict = SourceReference(
        source_type="merchant_metrics_daily",
        source_reference={
            "merchant_id": str(uuid.uuid4()),
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
        },
        description="Monthly aggregated metrics",
    )
    assert isinstance(ref_dict.source_reference, dict)
    assert ref_dict.source_reference["start_date"] == "2026-10-01"


def test_knowledge_fact_payload_envelope_validation():
    """Verify KnowledgeFactPayload packaging metadata and typed facts."""
    merchant_id = uuid.uuid4()
    point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant_id)
    now = datetime.now(timezone.utc)

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_type="merchant",
        entity_id=merchant_id,
        merchant_id=merchant_id,
        entity_name="Test Store",
        as_of=now,
        is_current=True,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=[
            SourceReference(
                source_type="merchant_profile",
                source_reference=str(merchant_id),
            )
        ],
    )

    facts = MerchantSummaryFacts(
        merchant_name="Test Store",
        store_currency="USD",
        country="US",
        timezone="UTC",
        app_install_status="installed",
        subscription_plan="growth",
        total_shoppers=250,
        total_products=45,
        total_orders=620,
        total_revenue=Decimal("45000.00"),
        average_order_value=Decimal("72.58"),
        conversion_rate=Decimal("0.042"),
        active_campaign_count=3,
        enabled_feature_count=5,
        health_score=Decimal("88.5"),
        health_status="HEALTHY",
        active_features=["campaigns", "segments"],
    )

    payload = KnowledgeFactPayload(metadata=metadata, facts=facts)
    assert payload.metadata.point_id == point_id
    assert payload.facts.merchant_name == "Test Store"
    assert payload.facts.health_status == "HEALTHY"


def test_knowledge_qdrant_payload_contract():
    """Verify serialized Qdrant vector payload contract."""
    point_id = uuid.uuid4()
    q_payload = KnowledgeQdrantPayload(
        point_id=str(point_id),
        knowledge_type="shopper_journey",
        entity_type="shopper_journey",
        entity_id=str(point_id),
        merchant_id=str(uuid.uuid4()),
        shopper_id=str(uuid.uuid4()),
        journey_id=str(point_id),
        as_of="2026-11-18T20:00:00Z",
        is_current=False,
        summary="Shopper converted via organic search after browsing 3 items.",
        access_scope="merchant",
        source_references=[{"source_type": "shopper_journey", "source_reference": str(point_id)}],
        generated_at="2026-11-18T20:00:05Z",
        schema_version=1,
        embedding_model="BAAI/bge-large-en-v1.5",
    )
    assert q_payload.point_id == str(point_id)
    assert q_payload.is_current is False
    assert q_payload.embedding_model == "BAAI/bge-large-en-v1.5"
