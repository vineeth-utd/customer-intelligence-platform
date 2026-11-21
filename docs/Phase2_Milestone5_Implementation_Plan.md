# Phase 2 Milestone 5 — AI Knowledge Pipeline Implementation Plan

## Purpose

This document defines the implementation decisions and execution units for **Phase 2, Milestone 5 — AI Knowledge Pipeline**.

It supplements `Implementation_Plan.md` and the finalized design documents. Those documents remain the architectural source of truth.

Milestone 5 transforms deterministic business intelligence into retrieval-oriented semantic knowledge:

```text
Deterministic Business Products
        ↓
Structured Knowledge Facts
        ↓
LLM Summary Generation
        ↓
BGE Embedding
        ↓
Qdrant AI Knowledge Layer
```

PostgreSQL and deterministic Business Services remain authoritative. Qdrant is a retrieval optimization layer, not a source of business truth.

Semantic retrieval, AI business tools, the AI Gateway, hybrid retrieval, and Investigation Agent behavior remain later milestones.

---

# 1. Finalized Knowledge Types

## Merchant Summary

**Identity:** One current summary per Merchant.

Represents the merchant's current overall platform and business state using deterministic information including Merchant Profile, Merchant Health, subscription/features, and relevant recent business-performance context.

**Lifecycle:** Current-state knowledge. Replaced/upserted when relevant deterministic intelligence changes.

---

## Shopper Behaviour Summary

**Identity:** One current summary per Shopper.

Represents the shopper's overall value, preferences, engagement, Segment Membership, and aggregate Journey behavior using existing deterministic products.

It does not calculate new shopper analytics from raw events.

**Lifecycle:** Current-state knowledge. Replaced/upserted when relevant shopper intelligence changes.

---

## Shopper Journey Summary

**Identity:** One summary per completed Shopper Journey.

Represents one bounded interaction episode, including entry source, ordered interactions, relevant product/cart/checkout context, and final outcome.

Only `CONVERTED` and `NON_CONVERTING` Journeys are summarized. `OPEN` Journeys remain excluded because they are incomplete and mutable.

**Lifecycle:** Historical knowledge. Completed Journey summaries are preserved.

---

## Campaign Summary

**Identity:** One summary per Campaign.

Represents campaign configuration, performance, deterministic attribution, audience response, and correlated Shopper Journey outcomes.

**Lifecycle:** Current while the Campaign is active and refreshed as deterministic analytics change. Once completed and deterministic campaign intelligence stabilizes, the final summary becomes preserved historical knowledge.

---

## Merchant Performance Summary

**Identity:** Merchant + closed calendar month.

Represents monthly deterministic business performance including revenue/orders/AOV changes, shopper composition, conversion/funnel behavior, and aggregate Journey outcomes.

**Lifecycle:** Historical knowledge. Closed monthly summaries are preserved.

---

## Platform Performance Summary

**Identity:** Platform + closed calendar month.

Represents platform-level merchant growth, subscription movement, commerce performance, active shoppers, and relevant deterministic trends.

**Lifecycle:** Historical knowledge. Closed monthly summaries are preserved.

Feature-specific and rolling-window summaries are deferred.

---

# 2. Structured Fact & Summary Builder Contract

Knowledge generation uses a common typed envelope with knowledge-specific typed facts.

```text
KnowledgeFactPayload
│
├── Common metadata
│   ├── knowledge type
│   ├── entity/business scope
│   ├── temporal context
│   └── deterministic lineage
│
└── Typed facts
    ├── MerchantSummaryFacts
    ├── ShopperBehaviourFacts
    ├── ShopperJourneyFacts
    ├── CampaignSummaryFacts
    ├── MerchantPerformanceFacts
    └── PlatformPerformanceFacts
```

Dedicated Fact Builders compose existing Business Services.

Fact Builders may:

- Select and normalize deterministic facts.
- Compose existing Business Service outputs.
- Apply data minimization.
- Construct deterministic source references.

They must not:

- Access databases through direct SQL/DAL calls.
- Calculate new business intelligence.
- Infer unsupported conclusions.
- Generate AI findings or recommendations.

Only minimized AI-safe facts are sent to the LLM.

Sensitive information such as shopper names/emails, merchant email, credentials, unnecessary internal identifiers, session identifiers, sensitive URL parameters, and unnecessarily precise location must not be included in LLM facts.

Platform identifiers and lineage may remain outside the LLM prompt for filtering and authoritative resolution.

---

# 3. LLM Summary Generation

Milestone 5 introduces a minimal low-level LLM provider abstraction.

Groq is the development provider.

The model receives:

```text
Shared Grounding Instructions
        +
Knowledge-Type Instructions
        +
AI-Safe Structured Facts
```

and returns only a concise retrieval-oriented summary.

The model must not:

- Calculate business metrics.
- Invent missing information.
- Introduce unsupported causality.
- Perform investigations.
- Recommend actions.
- Generate lineage.

Generation should be bounded and low-variance.

The provider abstraction remains separate from, but reusable by, the Milestone 6 AI Gateway.

---

# 4. Embedding Boundary

A reusable embedding service converts generated summaries into vectors using BGE.

```text
Summary Text
     ↓
Embedding Service
     ↓
BGE
     ↓
Vector
```

Only semantic summary text is embedded.

Identifiers, lineage, authorization metadata, and filtering timestamps remain Qdrant metadata rather than embedding content.

The same canonical BGE model/configuration will later be reused for query embeddings.

The exact BGE checkpoint and model-specific configuration will be selected during implementation.

---

# 5. Qdrant Knowledge Storage

Use one shared collection:

```text
cip_knowledge
```

All initial knowledge types use the same embedding space and are differentiated through metadata.

One knowledge item corresponds to:

```text
1 Summary
=
1 Embedding
=
1 Qdrant Point
```

No summary chunking is required for Milestone 5.

## Knowledge Identity

Use deterministic RFC 4122 UUIDs generated using the repository's existing `uuid.uuid5` convention.

Logical identities are:

| Knowledge Type | Logical Identity |
|---|---|
| Merchant Summary | `merchant_summary + merchant_id` |
| Shopper Behaviour | `shopper_behaviour + shopper_id` |
| Shopper Journey | `shopper_journey + stable journey_id` |
| Campaign Summary | `campaign_summary + campaign_id` |
| Merchant Performance | `merchant_id + start_date + end_date` |
| Platform Performance | `start_date + end_date` |

This allows current-state knowledge to safely overwrite the same point while historical knowledge receives distinct stable points.

## Payload Metadata

Knowledge payloads should contain the applicable fields from:

- `knowledge_type`
- `entity_type`
- `entity_id`
- `merchant_id`
- `shopper_id`
- `campaign_id`
- `journey_id`
- Human-readable entity name where useful and non-sensitive
- `as_of`
- `period_start`
- `period_end`
- `is_current`
- `summary`
- `access_scope`
- `source_references`
- Knowledge generation timestamp
- Knowledge schema version
- Embedding model
- Summary/prompt version where required for re-indexing

`source_references` may contain multiple deterministic sources because one knowledge item may combine several derived products.

---

# 6. Authorization & Lineage

Authorization-relevant metadata must be stored at indexing time so unauthorized knowledge can be filtered in Qdrant before results reach the LLM.

Merchant principals are restricted to their own `merchant_id`.

Platform-wide/internal knowledge is restricted to internal principals.

Qdrant stores source locators rather than authoritative business records.

```text
Semantic Knowledge
        ↓
Source References
        ↓
Controlled Resolver / Tool
        ↓
Business Service
        ↓
Data Access Layer
        ↓
PostgreSQL
```

Runtime resolution belongs to later retrieval/tool milestones. Milestone 5 must store sufficient lineage to enable it.

---

# 7. Knowledge Processing State

Introduce a dedicated PostgreSQL `KnowledgeProcessingState` ledger keyed by deterministic knowledge `point_id`.

This remains separate from `EntityProcessingState`, which continues to manage deterministic derived products.

The knowledge ledger should track the information required for:

- Knowledge identity.
- Processing status.
- Successful generation watermark.
- Failures and retries.
- Embedding/model version.
- Knowledge schema/version.
- Historical/time-window identity where applicable.

`EntityDomainActivity` remains the source-change mechanism for determining whether current-state knowledge has become stale.

---

# 8. Knowledge Lifecycle

| Knowledge | Behavior |
|---|---|
| Merchant Summary | Replace/upsert |
| Shopper Behaviour | Replace/upsert |
| Completed Shopper Journey | Preserve |
| Active Campaign | Replace/upsert |
| Finalized Campaign | Preserve |
| Merchant monthly performance | Preserve |
| Platform monthly performance | Preserve |

Historical knowledge remains valid when later entity activity occurs.

---

# 9. Required Deterministic-Platform Refinements

Milestone 5 exposed several gaps in the existing deterministic platform.

## Stable Shopper Journey Identity

Shopper Journeys are currently deterministically reconstructed but receive new random UUIDs during regeneration.

Retain full deterministic Journey reconstruction while introducing stable deterministic `uuid5` identities for Shopper Journeys and Journey Events.

The exact stable Journey key should be based on canonical source-event identity after implementation inspection confirms the correct Journey boundary.

## Derived-Product Activity Signals

Add downstream activity recording after successful generation of:

- Merchant Health → merchant `"health"` activity.
- Shopper Segment Membership → shopper `"segment"` activity.
- Campaign Analytics → campaign `"analytics"` activity.

This allows knowledge invalidation to depend on completed deterministic products rather than racing against their raw upstream activity.

---

# 10. Knowledge Generation & Orchestration

All knowledge types use one shared generation pipeline:

```text
KnowledgeWorkItem
        ↓
Fact Builder
        ↓
LLM Summary
        ↓
Validation
        ↓
BGE Embedding
        ↓
Qdrant Upsert
        ↓
KnowledgeProcessingState
```

Work discovery remains separate from work execution.

## Current-State Discovery

Current knowledge becomes eligible when relevant `EntityDomainActivity` is newer than the source watermark represented by its successful knowledge generation.

## Historical Discovery

Historical knowledge is discovered from stable semantic units such as:

- Completed Shopper Journeys.
- Closed merchant-month periods.
- Closed platform-month periods.
- Finalized Campaigns.

Their deterministic knowledge identity prevents duplicate generation.

---

# 11. Scheduling & Failure Handling

Continue using APScheduler.

```text
APScheduler
     ↓
Knowledge Orchestrator
```

Airflow is not required for the MVP because application-level scheduling and processing-state orchestration already solve the current workflow requirements.

Processing should support:

- Controlled batching.
- Bounded concurrency.
- Per-item failure isolation.
- Small bounded retries/backoff for transient provider/infrastructure errors.
- Later scheduled retry for persistent failures.

External LLM, embedding, and Qdrant operations must not hold long-running PostgreSQL transactions.

The PostgreSQL success state is committed only after Qdrant persistence succeeds.

Deterministic point IDs make retries safe if Qdrant succeeds but the process fails before PostgreSQL records success.

Each generation attempt must represent the source/evaluation watermark actually processed so newer concurrent activity remains eligible.

---

# 12. Historical Knowledge Bootstrap

AI Knowledge bootstrap remains separate from deterministic historical bootstrap.

```text
run_historical_bootstrap()
        ↓
Deterministic Platform Complete
        ↓
run_ai_knowledge_bootstrap()
```

The knowledge bootstrap generates the initial corpus from already-settled deterministic data:

- Current Merchant Summaries.
- Current Shopper Behaviour Summaries.
- Applicable Campaign Summaries.
- Completed Shopper Journey Summaries.
- Merchant Performance Summaries for closed historical months.
- Platform Performance Summaries for closed historical months.

Knowledge bootstrap reuses the same Fact Builders and generation pipeline used by incremental processing.

AI bootstrap failure must not invalidate deterministic bootstrap success.

---

# 13. Re-indexing

Knowledge may become stale because:

1. Underlying business information changed.
2. Knowledge-generation configuration changed.

Explicit re-indexing must therefore support changes such as:

- Embedding-model upgrades.
- Knowledge fact-schema changes.
- Summary-template/prompt changes.

Re-indexing must not require artificial business-domain activity.

---

# 14. Testing & Hardening Strategy

Normal automated tests remain offline and hermetic using:

- Fake LLM provider.
- Fake deterministic embedding service.
- Controlled Qdrant test infrastructure or repository doubles where appropriate.

Tests should verify:

- Typed Fact Builder output.
- PII/data-minimization boundaries.
- Deterministic source lineage.
- Deterministic knowledge IDs.
- Stable Shopper Journey/JourneyEvent IDs.
- Current-state replacement.
- Historical preservation.
- Processing-state success/failure.
- Retry/idempotency.
- Source-watermark race safety.
- Incremental eligibility.
- Historical bootstrap corpus generation.

Focused integration/smoke validation should verify:

- Real Groq summary generation.
- Real BGE embedding generation.
- Real Qdrant persistence.

LLM-as-a-judge and retrieval-quality/RAG evaluation are deferred until retrieval and investigation capabilities exist.

---

# 15. Implementation Units

## Unit 5.1 — Stable Shopper Journey Identity

### Goal

Fix the deterministic-platform identity gap before persistent AI knowledge references Shopper Journeys.

### Scope

- Replace random Shopper Journey IDs with deterministic stable IDs.
- Replace random Shopper Journey Event IDs with deterministic stable IDs.
- Preserve existing full deterministic Journey reconstruction.
- Ensure identical source history produces identical Journey/JourneyEvent identities across regeneration.
- Preserve existing Journey behavior and API contracts.
- Add focused regression tests.

### Definition of Done

Repeated Journey regeneration from identical authoritative events produces identical Journey and JourneyEvent IDs without changing Journey semantics.

### Status

**COMPLETED**: Unit 5.1 is complete. Deterministic RFC 4122 UUIDv5 identities implemented for `ShopperJourney` and `ShopperJourneyEvent`, total event stream tie-breaking (`event_timestamp`, `source_event_category`, `source_event_id`) established, and regression verified.

---

## Unit 5.2 — Knowledge Contracts & Processing Foundation

### Goal

Establish the common contracts, identity model, and PostgreSQL state foundation required by all AI knowledge.

### Scope

- Knowledge type definitions.
- Common Knowledge Fact envelope.
- Knowledge-specific typed fact schemas.
- Qdrant payload/metadata contracts.
- Deterministic knowledge point-ID helpers.
- `KnowledgeProcessingState` model, migration, DAL, and service capabilities.
- Processing status, failure, watermark, and version semantics.

### Definition of Done

Every planned knowledge type has a typed identity/fact contract and can be represented by a deterministic knowledge point with persistent processing state.

### Status

**COMPLETED**: Unit 5.2 is complete. Knowledge type enums, flexible source lineage contracts (`source_type` + structured `source_reference`), deterministic RFC 4122 UUIDv5 point ID generator (`generate_knowledge_point_id`), typed facts schemas with strict PII exclusion, Qdrant payload contracts, `KnowledgeProcessingState` SQLAlchemy model, Alembic migration `a7e4b91d2f08`, DAL query primitives, and service lifecycle transitions (attempt, success, failure, watermark preservation/advancement) are fully implemented and verified.

---

## Unit 5.3 — Deterministic Fact Builders & Dependency Signals

### Goal

Create the deterministic bridge from existing business intelligence to AI-safe structured facts.

### Scope

Implement Fact Builders for:

- Merchant Summary.
- Shopper Behaviour.
- Shopper Journey.
- Campaign Summary.
- Merchant Performance.
- Platform Performance.

Also:

- Apply data minimization.
- Construct source lineage.
- Add `health`, `segment`, and campaign `analytics` activity signals.
- Add deterministic tests for facts and PII exclusion.

### Definition of Done

All initial knowledge types can be represented as validated, minimized, lineage-aware structured facts without calling an LLM.

**COMPLETED**: Unit 5.3 is complete. The six deterministic Fact Builders (Merchant Summary, Shopper Behaviour, Shopper Journey, Campaign Summary, Merchant Performance, Platform Performance) are implemented in `app.services.fact_builders`, strictly composed through existing Business Services without direct SQL/DAL queries or computing new aggregations. Strict PII exclusion and data minimization are enforced. Downstream dependency signals (`merchant` health, `shopper` segment, `campaign` analytics) are recorded in their respective service callbacks. All unit and regression test suites pass cleanly.

---

## Unit 5.4 — LLM Summarization Infrastructure

### Goal

Convert structured deterministic facts into grounded retrieval-oriented summaries.

### Scope

- Low-level provider abstraction.
- Groq implementation/configuration.
- Shared grounding policy.
- Knowledge-type-specific summarization instructions.
- Summary generation and deterministic validation.
- Bounded retry/backoff.
- Fake provider for tests.

### Definition of Done

Every knowledge fact type can produce a validated retrieval-oriented summary through the provider abstraction without introducing AI Gateway/tool functionality.

### Status

**COMPLETED**: Unit 5.4 is complete. Implemented `LLMProvider` abstraction (`LLMMessage`, `LLMResponse`, `LLMProvider`) and `GroqLLMProvider` using native `httpx.AsyncClient` with bounded exponential backoff retries for transient HTTP errors (429, 5xx, timeouts) and fail-fast for invalid configs. Implemented deterministic `FakeLLMProvider` for offline testing. Created shared grounding policy enforcing strict fidelity, anti-speculation, anti-recommendation, and fact isolation (stripping metadata/lineage before LLM prompting). Implemented knowledge-type-specific prompt instructions for all six knowledge types. Implemented `generate_knowledge_summary` service with deterministic output validation (stripping markdown fences, conversational preambles, verifying length bounds and shopper PII boundaries). Added comprehensive unit tests and regression verified against the broader suite.

---

## Unit 5.5 — BGE Embedding & Qdrant Knowledge Repository

### Goal

Persist semantic knowledge in the AI Knowledge Layer.

### Scope

- Select/configure canonical BGE checkpoint.
- Reusable embedding abstraction.
- Fake embedding implementation for tests.
- Qdrant configuration/client.
- Create/validate `cip_knowledge`.
- Required payload indexes.
- Deterministic point upsert.
- Metadata, authorization, lifecycle, and lineage persistence.
- Repository integration tests.

### Definition of Done

A generated summary can be embedded and persisted as a correctly identified, metadata-rich Qdrant knowledge point.

---

## Unit 5.6 — End-to-End Knowledge Generator

### Goal

Connect contracts, Fact Builders, summarization, embeddings, Qdrant, and processing state into one safe processing operation.

### Scope

- `KnowledgeWorkItem`.
- Knowledge-type registry.
- Shared generator.
- Source/evaluation watermark handling.
- Success/failure state transitions.
- Idempotent retry behavior.
- Per-item failure isolation.

### Definition of Done

Any single supported knowledge item can be generated end-to-end through:

```text
Facts → LLM → Validation → BGE → Qdrant → SUCCESS
```

with safe failure and retry semantics.

---

## Unit 5.7 — Incremental Discovery & Scheduled Processing

### Goal

Automatically keep current semantic knowledge fresh.

### Scope

- Current-state work discovery from domain activity.
- Knowledge dependency definitions.
- Merchant Summary invalidation.
- Shopper Behaviour invalidation.
- Active Campaign Summary invalidation.
- Historical-unit discovery where appropriate.
- Batch processing and bounded concurrency.
- Retry of failed knowledge.
- APScheduler integration.
- Prevent unnecessary regeneration.

### Definition of Done

Changed deterministic business intelligence causes only affected knowledge to regenerate, while unchanged knowledge is skipped and failures remain retryable.

---

## Unit 5.8 — Historical Knowledge & AI Knowledge Bootstrap

### Goal

Generate the initial historical semantic corpus from the existing deterministic platform.

### Scope

- Discover completed Shopper Journeys.
- Discover closed merchant-month periods.
- Discover closed platform-month periods.
- Handle finalized Campaign knowledge.
- Implement `run_ai_knowledge_bootstrap`.
- Reuse the shared generation pipeline.
- Support restart/retry without duplicate knowledge.

### Definition of Done

A historically bootstrapped deterministic platform can produce the expected current and historical AI knowledge corpus without altering deterministic business state.

---

## Unit 5.9 — Re-indexing, Integration Verification & Milestone Hardening

### Goal

Verify the complete Milestone 5 contract and close operational gaps.

### Scope

- Explicit re-indexing for embedding/schema/prompt changes.
- Stable Journey-ID regression verification.
- Current-state replacement tests.
- Historical preservation tests.
- Failure/retry matrix.
- Source-watermark race tests.
- Authorization/PII metadata verification.
- Bootstrap corpus verification.
- Real Qdrant integration.
- Focused BGE validation.
- Optional/manual Groq smoke validation.
- Full regression suite.

### Definition of Done

All Milestone 5 Definition-of-Done requirements in `Implementation_Plan.md` are satisfied and the knowledge pipeline is ready for downstream semantic retrieval.

---

# 16. Implementation Sequence

```text
5.1 Stable Shopper Journey Identity
        ↓
5.2 Knowledge Contracts & Processing Foundation
        ↓
5.3 Deterministic Fact Builders & Dependency Signals
        ↓
5.4 LLM Summarization Infrastructure
        ↓
5.5 BGE Embedding & Qdrant Repository
        ↓
5.6 End-to-End Knowledge Generator
        ↓
5.7 Incremental Discovery & Scheduling
        ↓
5.8 Historical Knowledge Bootstrap
        ↓
5.9 Re-indexing & Milestone Hardening
```

Each unit should be implemented and verified independently before moving to the next unit.

Implementation prompts should direct the coding agent to inspect the current repository and relevant source-of-truth specifications before modifying code, and should not permit redesign beyond the approved unit scope.