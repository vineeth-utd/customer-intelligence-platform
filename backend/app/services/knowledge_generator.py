from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embedding import EmbeddingProvider, get_embedding_provider
from app.ai.llm import LLMProvider, get_llm_provider
from app.data_access.qdrant import KnowledgeRepository, get_qdrant_client
from app.db.session import AsyncSessionLocal
from app.schemas.knowledge import (
    KnowledgeFactPayload,
    KnowledgeGenerationResult,
    KnowledgeQdrantPayload,
    KnowledgeStatus,
    KnowledgeType,
    KnowledgeWorkItem,
)
from app.services.embedding import embed_knowledge_summary
from app.services.fact_builders import (
    build_campaign_summary_facts,
    build_merchant_performance_facts,
    build_merchant_summary_facts,
    build_platform_performance_facts,
    build_shopper_behaviour_facts,
    build_shopper_journey_facts,
)
from app.services.knowledge import (
    record_knowledge_attempt,
    record_knowledge_failure,
    record_knowledge_success,
)
from app.services.summarization import generate_knowledge_summary

logger = logging.getLogger(__name__)

# Registry mapping KnowledgeType to its entity category and default is_current lifecycle
KNOWLEDGE_TYPE_REGISTRY = {
    KnowledgeType.MERCHANT_SUMMARY: {
        "entity_type": "merchant",
        "default_is_current": True,
    },
    KnowledgeType.SHOPPER_BEHAVIOUR: {
        "entity_type": "shopper",
        "default_is_current": True,
    },
    KnowledgeType.SHOPPER_JOURNEY: {
        "entity_type": "journey",
        "default_is_current": False,
    },
    KnowledgeType.CAMPAIGN_SUMMARY: {
        "entity_type": "campaign",
        "default_is_current": True,
    },
    KnowledgeType.MERCHANT_PERFORMANCE: {
        "entity_type": "merchant",
        "default_is_current": False,
    },
    KnowledgeType.PLATFORM_PERFORMANCE: {
        "entity_type": "platform",
        "default_is_current": False,
    },
}


async def _dispatch_fact_builder(
    session: AsyncSession,
    work_item: KnowledgeWorkItem,
    as_of: datetime,
) -> KnowledgeFactPayload:
    """Dispatches the appropriate fact builder based on the work item's knowledge type."""
    k_type = work_item.knowledge_type

    if k_type == KnowledgeType.MERCHANT_SUMMARY:
        return await build_merchant_summary_facts(
            session=session,
            merchant_id=work_item.entity_id,  # type: ignore[arg-type]
            as_of=as_of,
        )
    elif k_type == KnowledgeType.SHOPPER_BEHAVIOUR:
        return await build_shopper_behaviour_facts(
            session=session,
            shopper_id=work_item.entity_id,  # type: ignore[arg-type]
            as_of=as_of,
        )
    elif k_type == KnowledgeType.SHOPPER_JOURNEY:
        return await build_shopper_journey_facts(
            session=session,
            journey_id=work_item.entity_id,  # type: ignore[arg-type]
            as_of=as_of,
        )
    elif k_type == KnowledgeType.CAMPAIGN_SUMMARY:
        return await build_campaign_summary_facts(
            session=session,
            campaign_id=work_item.entity_id,  # type: ignore[arg-type]
            as_of=as_of,
        )
    elif k_type == KnowledgeType.MERCHANT_PERFORMANCE:
        return await build_merchant_performance_facts(
            session=session,
            merchant_id=work_item.entity_id,  # type: ignore[arg-type]
            period_start=work_item.period_start,  # type: ignore[arg-type]
            period_end=work_item.period_end,  # type: ignore[arg-type]
            as_of=as_of,
        )
    elif k_type == KnowledgeType.PLATFORM_PERFORMANCE:
        return await build_platform_performance_facts(
            session=session,
            period_start=work_item.period_start,  # type: ignore[arg-type]
            period_end=work_item.period_end,  # type: ignore[arg-type]
            as_of=as_of,
        )
    else:
        raise ValueError(f"Unsupported knowledge type: {k_type}")


async def generate_knowledge_item(
    work_item: KnowledgeWorkItem,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    qdrant_repo: Optional[KnowledgeRepository] = None,
    llm_provider: Optional[LLMProvider] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
) -> KnowledgeGenerationResult:
    """
    Executes end-to-end knowledge generation for a single KnowledgeWorkItem.
    Pipeline: Fact Builder -> LLM Summary -> Validation -> BGE Embedding -> Qdrant Upsert -> KnowledgeProcessingState.

    Enforces discrete short-lived database transactions:
    - Session 1: Record processing attempt in PostgreSQL.
    - Session 2: Read facts from PostgreSQL via registered Fact Builder.
    - External: LLM summarization, ONNX embedding, and Qdrant network I/O run with NO open database transaction.
    - Session 3: Record success (or failure) in PostgreSQL.
    """
    session_maker = session_factory or AsyncSessionLocal
    active_llm = llm_provider or get_llm_provider()
    active_embedding = embedding_provider or get_embedding_provider()
    active_qdrant = qdrant_repo or KnowledgeRepository(client=get_qdrant_client())

    point_id = work_item.point_id
    k_type = work_item.knowledge_type
    cfg = KNOWLEDGE_TYPE_REGISTRY.get(k_type)
    if not cfg:
        raise ValueError(f"Unknown knowledge type in registry: {k_type}")

    entity_type = cfg["entity_type"]
    is_current = work_item.is_current if work_item.is_current is not None else cfg["default_is_current"]
    now = datetime.now(timezone.utc)
    as_of = work_item.as_of or now
    merchant_id = work_item.merchant_id or (work_item.entity_id if entity_type == "merchant" else None)

    # 1. Session 1: Record Attempt in PostgreSQL
    try:
        async with session_maker() as session:
            await record_knowledge_attempt(
                session=session,
                point_id=point_id,
                knowledge_type=k_type.value,
                entity_type=entity_type,
                entity_id=work_item.entity_id,
                merchant_id=merchant_id,
                period_start=work_item.period_start,
                period_end=work_item.period_end,
                is_current=is_current,
                attempt_time=now,
            )
            await session.commit()
    except Exception as attempt_exc:
        logger.error("Failed to record attempt for knowledge item %s: %s", point_id, attempt_exc)
        return KnowledgeGenerationResult(
            point_id=point_id,
            knowledge_type=k_type,
            status=KnowledgeStatus.FAILED,
            error_message=str(attempt_exc),
            retry_count=0,
        )

    # 2. Pipeline Execution (Fact Builder -> LLM -> Embedding -> Qdrant)
    try:
        # Session 2: Read authoritative facts from PostgreSQL (Read-Only)
        async with session_maker() as session:
            fact_payload = await _dispatch_fact_builder(session, work_item, as_of)

        # Database session is now closed. External AI and vector operations run with no DB locks.
        summary = await generate_knowledge_summary(fact_payload, provider=active_llm)
        vector = await embed_knowledge_summary(summary, provider=active_embedding)

        meta = fact_payload.metadata
        resolved_merchant_id = meta.merchant_id or merchant_id
        qdrant_payload = KnowledgeQdrantPayload(
            point_id=str(point_id),
            knowledge_type=k_type.value,
            entity_type=entity_type,
            entity_id=str(work_item.entity_id) if work_item.entity_id else None,
            merchant_id=str(resolved_merchant_id) if resolved_merchant_id else None,
            shopper_id=str(meta.shopper_id) if meta.shopper_id else None,
            campaign_id=str(meta.campaign_id) if meta.campaign_id else None,
            journey_id=str(meta.journey_id) if meta.journey_id else None,
            entity_name=meta.entity_name,
            as_of=meta.as_of.isoformat(),
            period_start=work_item.period_start.isoformat() if work_item.period_start else None,
            period_end=work_item.period_end.isoformat() if work_item.period_end else None,
            is_current=is_current,
            summary=summary,
            access_scope=meta.access_scope.value,
            source_references=[ref.model_dump(mode="json") for ref in meta.source_references],
            generated_at=datetime.now(timezone.utc).isoformat(),
            schema_version=1,
            embedding_model=active_embedding.model_name,
        )

        # Idempotent collection check & deterministic point upsert
        await active_qdrant.ensure_collection(vector_size=active_embedding.dimension)
        await active_qdrant.upsert_knowledge_point(
            point_id=point_id,
            vector=vector,
            payload=qdrant_payload,
        )

        # 3. Session 3: Record Success in PostgreSQL
        completion_time = datetime.now(timezone.utc)
        async with session_maker() as session:
            state = await record_knowledge_success(
                session=session,
                point_id=point_id,
                knowledge_type=k_type.value,
                entity_type=entity_type,
                source_watermark=work_item.source_watermark,
                entity_id=work_item.entity_id,
                merchant_id=resolved_merchant_id,
                period_start=work_item.period_start,
                period_end=work_item.period_end,
                is_current=is_current,
                schema_version=1,
                embedding_model=active_embedding.model_name,
                generated_at=completion_time,
            )
            await session.commit()

        return KnowledgeGenerationResult(
            point_id=point_id,
            knowledge_type=k_type,
            status=KnowledgeStatus.SUCCESS,
            source_watermark=state.source_watermark,
            summary=summary,
            generated_at=completion_time,
            retry_count=state.retry_count,
        )

    except Exception as exc:
        logger.error("Failed to generate knowledge item %s (%s): %s", point_id, k_type.value, exc)
        failed_time = datetime.now(timezone.utc)
        retry_cnt = 0

        # Session 4: Record Failure in PostgreSQL
        try:
            async with session_maker() as session:
                state = await record_knowledge_failure(
                    session=session,
                    point_id=point_id,
                    knowledge_type=k_type.value,
                    entity_type=entity_type,
                    error_message=str(exc),
                    entity_id=work_item.entity_id,
                    merchant_id=merchant_id,
                    period_start=work_item.period_start,
                    period_end=work_item.period_end,
                    is_current=is_current,
                    failed_at=failed_time,
                )
                await session.commit()
                retry_cnt = state.retry_count
        except Exception as state_exc:
            logger.error("Failed to record failure state for point %s: %s", point_id, state_exc)

        return KnowledgeGenerationResult(
            point_id=point_id,
            knowledge_type=k_type,
            status=KnowledgeStatus.FAILED,
            error_message=str(exc),
            retry_count=retry_cnt,
        )
