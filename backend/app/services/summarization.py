import re
from typing import Optional

from app.ai.llm import get_llm_provider
from app.ai.llm.base import LLMProvider
from app.ai.prompts.summarization import build_summarization_prompt
from app.schemas.knowledge import KnowledgeFactPayload, KnowledgeType


class SummaryValidationError(ValueError):
    """Raised when an LLM-generated summary fails structural or grounding validation."""
    pass


def clean_summary_text(raw_text: str) -> str:
    """
    Cleans raw LLM output by stripping conversational prefixes, markdown code fences,
    and unnecessary bounding whitespace.
    """
    text = raw_text.strip()
    # Strip markdown codeblock wrapper if model wrapped its response in ```
    text = re.sub(r"^```(?:markdown|text)?\s*(.*?)\s*```$", r"\1", text, flags=re.DOTALL)
    text = text.strip()

    # Strip conversational greetings/preambles (e.g. "Here is a summary:")
    text = re.sub(
        r"^(?:here is (?:a |the )?(?:[a-z]+ )*summary:?|summary:?)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def validate_summary_text(
    text: str,
    knowledge_type: Optional[KnowledgeType] = None,
    min_chars: int = 40,
    max_chars: int = 3500,
) -> str:
    """
    Validates the generated summary string:
    - Cleans conversational filler and markdown wrappers.
    - Asserts non-empty and length within allowable character bounds.
    - Enforces PII-safety rules for shopper-level knowledge.
    """
    cleaned = clean_summary_text(text)

    if not cleaned:
        raise SummaryValidationError("Generated summary is empty or whitespace only.")

    if len(cleaned) < min_chars:
        raise SummaryValidationError(
            f"Generated summary is too short ({len(cleaned)} chars, minimum required: {min_chars})."
        )

    if len(cleaned) > max_chars:
        raise SummaryValidationError(
            f"Generated summary exceeds maximum allowed length ({len(cleaned)} chars, maximum: {max_chars})."
        )

    if knowledge_type == KnowledgeType.SHOPPER_BEHAVIOUR:
        # PII safety check: ensure no email addresses or prohibited token patterns slipped through
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cleaned):
            raise SummaryValidationError(
                "Shopper behaviour summary contains prohibited PII (email address detected)."
            )

    return cleaned


async def generate_knowledge_summary(
    fact_payload: KnowledgeFactPayload,
    provider: Optional[LLMProvider] = None,
    max_tokens: int = 768,
) -> str:
    """
    Verbalizes structured, AI-safe business facts into a dense, retrieval-oriented summary.
    Focuses on prompt assembly, provider invocation, and deterministic output validation.
    """
    active_provider = provider or get_llm_provider()
    messages = build_summarization_prompt(fact_payload)

    response = await active_provider.complete(
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
    )

    k_type = fact_payload.metadata.knowledge_type
    return validate_summary_text(response.content, knowledge_type=k_type)
