from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from app.ai.llm.fake import FakeLLMProvider
from app.ai.prompts.summarization import build_summarization_prompt
from app.schemas.knowledge import (
    CampaignSummaryFacts,
    KnowledgeAccessScope,
    KnowledgeFactPayload,
    KnowledgeMetadata,
    KnowledgeType,
    MerchantPerformanceFacts,
    MerchantSummaryFacts,
    PlatformPerformanceFacts,
    ShopperBehaviourFacts,
    ShopperJourneyFacts,
    SourceReference,
)
from app.services.knowledge import generate_knowledge_point_id
from app.services.summarization import (
    SummaryValidationError,
    clean_summary_text,
    generate_knowledge_summary,
    validate_summary_text,
)


def make_sample_payload(facts, knowledge_type: KnowledgeType, **metadata_kwargs):
    entity_id = uuid.uuid4()
    p_start = metadata_kwargs.get("period_start")
    p_end = metadata_kwargs.get("period_end")

    if knowledge_type == KnowledgeType.PLATFORM_PERFORMANCE:
        point_id = generate_knowledge_point_id(knowledge_type, period_start=p_start, period_end=p_end)
    elif knowledge_type == KnowledgeType.MERCHANT_PERFORMANCE:
        point_id = generate_knowledge_point_id(knowledge_type, entity_id, period_start=p_start, period_end=p_end)
    else:
        point_id = generate_knowledge_point_id(knowledge_type, entity_id)

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=knowledge_type,
        entity_type="test_entity",
        entity_id=entity_id,
        merchant_id=uuid.uuid4(),
        as_of=datetime.now(timezone.utc),
        is_current=metadata_kwargs.get("is_current", True),
        access_scope=metadata_kwargs.get("access_scope", KnowledgeAccessScope.MERCHANT),
        source_references=[
            SourceReference(source_type="secret_internal_table", source_reference="internal_locator_12345")
        ],
        period_start=p_start,
        period_end=p_end,
    )
    return KnowledgeFactPayload(metadata=metadata, facts=facts)


def test_clean_summary_text_strips_preamble_and_fences():
    """Verify clean_summary_text strips conversational filler and markdown wrappers."""
    raw1 = "Here is a summary: Apex Footwear generated $14,000 in revenue."
    assert clean_summary_text(raw1) == "Apex Footwear generated $14,000 in revenue."

    raw2 = "Here is a concise factual summary:\nApex Footwear generated $14,000 in revenue."
    assert clean_summary_text(raw2) == "Apex Footwear generated $14,000 in revenue."

    raw3 = "```markdown\nApex Footwear generated $14,000 in revenue.\n```"
    assert clean_summary_text(raw3) == "Apex Footwear generated $14,000 in revenue."

    raw4 = "```text\nHere is a summary: Apex Footwear generated $14,000 in revenue.\n```"
    assert clean_summary_text(raw4) == "Apex Footwear generated $14,000 in revenue."


def test_validate_summary_text_bounds_and_pii():
    """Verify validation boundaries and PII checks."""
    with pytest.raises(SummaryValidationError, match="empty or whitespace"):
        validate_summary_text("   \n  ")

    with pytest.raises(SummaryValidationError, match="too short"):
        validate_summary_text("Short text.")

    with pytest.raises(SummaryValidationError, match="exceeds maximum"):
        validate_summary_text("A" * 4000)

    # Valid text passes
    valid_text = "This is a completely valid factual summary that meets all required length constraints."
    assert validate_summary_text(valid_text) == valid_text

    # Shopper behaviour email PII check
    pii_text = (
        "This shopper made 5 orders and their email is customer@domain.com with total spend of $500."
    )
    with pytest.raises(SummaryValidationError, match="prohibited PII"):
        validate_summary_text(pii_text, knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR)


def test_prompt_isolation_excludes_platform_metadata_and_lineage():
    """Verify that build_summarization_prompt strictly excludes point IDs and lineage."""
    facts = MerchantSummaryFacts(
        merchant_name="Apex Footwear",
        store_currency="USD",
        country="US",
        timezone="UTC",
        app_install_status="installed",
        subscription_plan="GROWTH",
        total_shoppers=100,
        total_products=25,
        total_orders=150,
        total_revenue=Decimal("15000.00"),
        average_order_value=Decimal("100.00"),
        conversion_rate=Decimal("0.045"),
        active_campaign_count=2,
        enabled_feature_count=3,
        health_score=Decimal("88.0"),
        health_status="HEALTHY",
        churn_risk_score=Decimal("10.0"),
        engagement_score=Decimal("90.0"),
        feature_adoption_score=Decimal("85.0"),
        business_performance_score=Decimal("89.0"),
        active_features=["automated_discounts", "abandoned_cart"],
    )
    payload = make_sample_payload(facts, KnowledgeType.MERCHANT_SUMMARY)
    messages = build_summarization_prompt(payload)

    assert len(messages) == 2
    system_msg, user_msg = messages[0], messages[1]

    # Verify system message has grounding instructions
    assert "STRICT GROUNDING RULES" in system_msg.content
    assert "Apex Footwear" not in system_msg.content

    # Verify user message has facts JSON
    assert "Apex Footwear" in user_msg.content
    assert "15000.00" in user_msg.content

    # Strict isolation: platform metadata and lineage MUST NOT appear in the user prompt
    assert str(payload.metadata.point_id) not in user_msg.content
    assert "secret_internal_table" not in user_msg.content
    assert "internal_locator_12345" not in user_msg.content
    assert "source_references" not in user_msg.content


@pytest.mark.asyncio
async def test_summarize_all_six_fact_types():
    """Verify generate_knowledge_summary successfully executes and validates across all 6 fact types."""
    d_start = date(2026, 1, 1)
    d_end = date(2026, 1, 31)

    fact_cases = [
        (
            KnowledgeType.MERCHANT_SUMMARY,
            MerchantSummaryFacts(
                merchant_name="Style Hub",
                store_currency="USD",
                country="US",
                timezone="UTC",
                app_install_status="installed",
                subscription_plan="SCALE",
                total_shoppers=500,
                total_products=120,
                total_orders=650,
                total_revenue=Decimal("65000.00"),
                average_order_value=Decimal("100.00"),
                conversion_rate=Decimal("0.05"),
                active_campaign_count=4,
                enabled_feature_count=5,
                health_score=Decimal("92.0"),
                health_status="HEALTHY",
            ),
            {},
        ),
        (
            KnowledgeType.SHOPPER_BEHAVIOUR,
            ShopperBehaviourFacts(
                total_orders=4,
                total_spend=Decimal("380.00"),
                average_order_value=Decimal("95.00"),
                wishlist_item_count=3,
                save_for_later_item_count=1,
                campaign_engagement_count=6,
                preferred_category="Apparel",
                preferred_size="M",
                last_purchase_at=datetime.now(timezone.utc),
                segments=["High Value", "Active 30d"],
                total_journeys=5,
                converted_journeys=4,
            ),
            {},
        ),
        (
            KnowledgeType.SHOPPER_JOURNEY,
            ShopperJourneyFacts(
                journey_status="CONVERTED",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                duration_seconds=1200,
                entry_source="google_ads",
                converted=True,
                touchpoint_count=4,
                touchpoint_event_types=["SESSION_STARTED", "PRODUCT_VIEWED", "ADD_TO_CART", "PURCHASE_COMPLETED"],
                products_viewed=["pid-101", "pid-102"],
                search_queries=["running shoes"],
                cart_add_count=1,
                checkout_started=True,
                order_id=uuid.uuid4(),
                order_total_amount=Decimal("120.00"),
            ),
            {"is_current": False},
        ),
        (
            KnowledgeType.CAMPAIGN_SUMMARY,
            CampaignSummaryFacts(
                campaign_name="Summer Kickoff Sale",
                campaign_type="promotional",
                campaign_medium="email",
                status="active",
                target_segment_name="VIP Customers",
                delivered_count=1000,
                opened_count=450,
                clicked_count=180,
                converted_count=45,
                attributed_order_count=45,
                attributed_revenue=Decimal("4500.00"),
                open_rate=Decimal("0.45"),
                click_through_rate=Decimal("0.18"),
                conversion_rate=Decimal("0.045"),
                first_touch_conversions=20,
                last_touch_conversions=25,
                assisted_conversions=15,
                first_touch_revenue=Decimal("2000.00"),
                last_touch_revenue=Decimal("2500.00"),
                total_journeys_touched=80,
                journey_conversion_rate=Decimal("0.56"),
                audience_reached_count=980,
                audience_engaged_count=450,
                audience_converted_count=45,
            ),
            {},
        ),
        (
            KnowledgeType.MERCHANT_PERFORMANCE,
            MerchantPerformanceFacts(
                period_start=d_start,
                period_end=d_end,
                total_revenue=Decimal("45000.00"),
                order_count=450,
                average_order_value=Decimal("100.00"),
                unique_shoppers=380,
                new_shoppers=120,
                returning_shoppers=260,
                conversion_rate=Decimal("0.038"),
                cart_abandonment_rate=Decimal("0.65"),
                total_journeys=500,
                converted_journeys=450,
                journey_conversion_rate=Decimal("0.90"),
            ),
            {"is_current": False, "period_start": d_start, "period_end": d_end},
        ),
        (
            KnowledgeType.PLATFORM_PERFORMANCE,
            PlatformPerformanceFacts(
                period_start=d_start,
                period_end=d_end,
                active_merchants=85,
                new_merchants=12,
                installed_merchants=15,
                uninstalled_merchants=3,
                new_subscriptions=14,
                total_revenue=Decimal("250000.00"),
                total_orders=2500,
                active_shoppers=18000,
            ),
            {"is_current": False, "access_scope": KnowledgeAccessScope.INTERNAL, "period_start": d_start, "period_end": d_end},
        ),
    ]

    for k_type, facts, meta_kwargs in fact_cases:
        payload = make_sample_payload(facts, k_type, **meta_kwargs)
        fake_response = (
            f"Here is a summary: This is a verified, dense factual summary for {k_type.value} "
            f"covering all structured fields and metrics accurately."
        )
        fake_provider = FakeLLMProvider(responses=[fake_response])

        summary = await generate_knowledge_summary(payload, provider=fake_provider)

        assert isinstance(summary, str)
        assert len(summary) >= 40
        assert not summary.startswith("Here is a summary:")
        assert k_type.value in summary
        assert len(fake_provider.calls) == 1
        assert fake_provider.calls[0]["temperature"] == 0.0
