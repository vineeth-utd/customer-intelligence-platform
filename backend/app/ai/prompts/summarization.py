import json
from typing import Dict

from app.ai.llm.base import LLMMessage
from app.ai.prompts.grounding import SHARED_GROUNDING_POLICY
from app.schemas.knowledge import KnowledgeFactPayload, KnowledgeType

KNOWLEDGE_TYPE_INSTRUCTIONS: Dict[KnowledgeType, str] = {
    KnowledgeType.MERCHANT_SUMMARY: (
        "Summarize this merchant's store profile, operational scale, active features, and composite health diagnostics. "
        "Explicitly mention the merchant name, store currency, timezone, country, app install status, and subscription tier. "
        "State the total shopper count, product count, order volume, total revenue, average order value, conversion rate, "
        "and active campaign count. Detail the composite health status, overall health score, churn risk score, engagement score, "
        "feature adoption score, business performance score, and currently enabled features."
    ),
    KnowledgeType.SHOPPER_BEHAVIOUR: (
        "Summarize this shopper's lifetime purchasing activity, shopping intent, and engagement profile in a strictly PII-free manner. "
        "State the total orders placed, total spend, average order value, and date of last purchase. "
        "Highlight their shopping preferences including preferred category and preferred size, along with intent signals such as "
        "wishlist item count and save-for-later item count. State their campaign engagement frequency, total and converted journey counts, "
        "and all active segment memberships."
    ),
    KnowledgeType.SHOPPER_JOURNEY: (
        "Summarize this completed shopper interaction episode. State the final journey status (CONVERTED or NON_CONVERTING), "
        "start time, end time, duration in seconds, and entry source. "
        "Describe the touchpoint sequence and count, mentioning specific products viewed, search queries conducted, cart additions, "
        "and whether checkout was started. If converted, state the converted order total amount."
    ),
    KnowledgeType.CAMPAIGN_SUMMARY: (
        "Summarize this marketing campaign's configuration, execution performance, multi-touch attribution, journey correlation, and audience response. "
        "State the campaign name, type, medium, target segment name, status, and active date range. "
        "Report core delivery metrics including delivered, opened, clicked, and converted counts, with open, click-through, and conversion rates. "
        "Detail multi-touch attribution metrics (first-touch, last-touch, and assisted conversions and revenues), total journeys touched, "
        "journey conversion rate, top drop-off stages, and audience reached, engaged, and converted counts."
    ),
    KnowledgeType.MERCHANT_PERFORMANCE: (
        "Summarize this merchant's business performance scorecard over the specified closed calendar period. "
        "State the period start and end dates. Report total revenue, total orders, average order value, unique shoppers, "
        "and the breakdown between new and returning shoppers. "
        "Include conversion funnel efficiency (overall store conversion rate and cart abandonment rate) and journey metrics "
        "(total journeys, converted journeys, and journey conversion rate) for this specific closed period."
    ),
    KnowledgeType.PLATFORM_PERFORMANCE: (
        "Summarize platform-wide operational and financial performance over the specified closed calendar period. "
        "State the period start and end dates. Report active merchant count, new merchant additions, app installations versus uninstalls, "
        "new subscription additions, platform-wide gross revenue, total order volume, and total active shoppers across all merchants."
    ),
}


def build_summarization_prompt(fact_payload: KnowledgeFactPayload) -> list[LLMMessage]:
    """
    Constructs the LLM prompt messages from a KnowledgeFactPayload.
    Guarantees that ONLY AI-safe facts are passed in the user prompt,
    excluding all platform metadata, point IDs, and source references.
    """
    k_type = fact_payload.metadata.knowledge_type
    type_instruction = KNOWLEDGE_TYPE_INSTRUCTIONS.get(k_type)
    if not type_instruction:
        raise ValueError(f"No summarization instruction defined for knowledge type: {k_type}")

    system_prompt = f"{SHARED_GROUNDING_POLICY}\n\nKNOWLEDGE TYPE INSTRUCTIONS:\n{type_instruction}"

    # Extract ONLY the facts, serializing to JSON without platform metadata/lineage
    facts_dict = fact_payload.facts.model_dump(mode="json")
    user_prompt = f"FACTS TO SUMMARIZE:\n{json.dumps(facts_dict, indent=2, sort_keys=True)}"

    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]
