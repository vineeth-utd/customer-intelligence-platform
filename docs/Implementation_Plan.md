# Customer Intelligence Platform - Implementation Plan

## Purpose

This document tracks the implementation plan and current development progress for the Customer Intelligence Platform.

The product, architecture, technology, backend, database, and frontend designs are already defined within the project documentation under `docs/`. Those documents remain the source of truth for architectural and implementation decisions.

This document does not duplicate those designs. Its purpose is to translate them into an executable development sequence and provide continuity across development sessions and tools.

The implementation plan is intentionally maintained as a living document. Milestones may be refined as implementation progresses, but architectural changes should first be evaluated against the existing design documents rather than introduced silently.

---

# Implementation Strategy

The platform will be implemented incrementally through three phases:

```text
Phase 1
End-to-End Prototype
        │
        ▼
Phase 2
Minimum Viable Product
        │
        ▼
Phase 3
Version 1
```

The Prototype is not a throwaway implementation.

It represents the first working vertical slice of the actual platform. Infrastructure, database schemas, backend structure, and other foundational components created during Phase 1 should be production-inspired implementations that continue directly into the MVP.

The objective is to validate integration early while avoiding duplicate implementation work.

---

# Phase 1 - End-to-End Prototype

## Goal

Validate the complete core data flow of the Customer Intelligence Platform using the real application architecture.

The Prototype should demonstrate that realistic merchant and shopper activity can be generated, streamed through Kafka, processed into PostgreSQL, transformed into basic business metrics, exposed through FastAPI, and visualized through React.

```text
Synthetic Business Events
          │
          ▼
        Kafka
          │
          ▼
   Event Processing
          │
          ▼
     PostgreSQL
          │
          ▼
 Operational Business Data
          │
          ▼
   Basic Derived Metrics
          │
          ▼
       FastAPI
          │
          ▼
    React Dashboard
```

AI capabilities are intentionally excluded from the Prototype. The first phase validates that the underlying business and data platform provides meaningful value independently of AI.

---

## Milestone 1 - Project & Infrastructure Foundation

### Goal

Establish the real application structure and local development environment that will be used throughout the project.

### Scope

* Initialize the Python and FastAPI backend within the existing repository.
* Create the backend package structure defined in `10_Backend_Design.md`.
* Initialize the React and TypeScript frontend.
* Create the frontend structure defined in `12_Frontend_Design.md`.
* Configure Python dependency management using `uv`.
* Configure frontend dependencies.
* Create environment configuration.
* Configure Docker for application components.
* Create Docker Compose for local infrastructure.
* Configure PostgreSQL.
* Configure Apache Kafka.
* Configure Redis.
* Configure Qdrant.
* Configure OpenSearch.
* Verify connectivity between required services.
* Establish basic backend and frontend application startup.

### Definition of Done

* Backend application starts successfully.
* Frontend application starts successfully.
* Required infrastructure services run through Docker Compose.
* Application configuration is environment-driven.
* The repository follows the finalized backend and frontend project structures.
* Local development environment can be reproduced consistently.

---

## Milestone 2 - Database Foundation

### Goal

Implement the complete PostgreSQL schema defined in `11_Database_Design.md` so later milestones can build directly on the finalized data model.

### Scope

* Configure PostgreSQL connectivity and database sessions.
* Introduce SQLAlchemy models.
* Configure Alembic migrations.
* Implement operational tables.
* Implement event tables.
* Implement derived tables.
* Implement investigation tables.
* Implement required relationships and foreign keys.
* Implement uniqueness and integrity constraints.
* Implement indexes defined by the database design.
* Implement materialized views defined for analytical summaries.
* Establish UUID-based identifiers and event identity conventions.
* Create required reference data such as subscription plans and platform features where appropriate.
* Validate schema creation through migrations.

Not every table needs to be actively populated during the Prototype, but the complete database foundation should be established once so that the MVP can build on the same schema without unnecessary restructuring.

### Definition of Done

* The complete designed PostgreSQL schema can be created from migrations.
* Relationships and constraints are correctly enforced.
* Materialized views can be created successfully.
* Required reference data can be initialized.
* The database can be recreated consistently from an empty environment.

---

## Milestone 3 - Event Generation & Ingestion

### Goal

Implement the first real event-driven data flow through the platform.

### Scope

* Define versioned event contracts.
* Implement producer-generated UUID `event_id`.
* Implement merchant event generator.
* Implement shopper event generator.
* Introduce campaign event generation where required by the Prototype flow.
* Bootstrap minimal Segment prerequisite data for Campaign generation to bypass full profile/segmentation pipeline dependencies in V1.
* Align Product/Product Variant operational schema and define Product event contracts required by the Shopper flow.
* Configure domain-specific Kafka topics.
* Implement Kafka producers.
* Implement domain-specific Kafka consumers.
* Validate incoming event structure.
* Persist incoming events into the corresponding event tables.
* Route events deterministically using `event_type`.
* Delegate business processing to the Business Service Layer.
* Update event processing state after successful processing.
* Commit Kafka offsets only after successful persistence and processing.
* Handle duplicate events using `event_id`.
* Introduce basic retry and failure logging.

Synthetic generators should model coherent business behaviour rather than produce unrelated random records.

### Definition of Done

* Synthetic business events are successfully published to Kafka.
* Consumers receive and validate events.
* Events are persisted in the correct event tables.
* Duplicate delivery does not create duplicate business processing.
* Event types are routed deterministically.
* Successfully processed events update their processing state.
* Failed processing can be identified through logs.

---

## Milestone 4 - Basic Business Processing & Analytics

### Goal

Transform operational business data into the derived analytical data required by the Prototype.

### Context

Operational business-state processing originally anticipated in Milestone 4 was completed as part of the Milestone 3 domain event verticals. Merchant, Product, Shopper, Order, Campaign, Subscription, Feature, and related operational state is already maintained through event-driven business processing.

Milestone 4 therefore focuses on derived business data products, scheduled analytical processing, materialized summaries, and Analytics Service capabilities.

### Scope

Implement the analytical processing required by the Prototype, including:

* Merchant Metrics Daily.
* Platform Metrics Daily.
* Feature Metrics Daily.
* Campaign Analytics Daily, building on the event-driven processing already implemented in Milestone 3.
* Required aggregate materialized views, including Platform Metrics, Feature Metrics, and Campaign Analytics.
* Scheduled background processing for generating and refreshing derived analytical data.
* Analytics Data Access Layer operations required to generate and retrieve analytical data.
* Analytics Service capabilities required by the Prototype dashboard.
* Verification that derived metrics can be reproduced from their underlying operational source data.

Full Merchant Profiles, Shopper Profiles, Customer Journeys, Shopper Segment Membership, and Merchant Health remain deferred to the MVP phase.

The implementation should use the real Business Service and Data Access layers rather than Prototype-specific shortcuts.

### Definition of Done

* Scheduled analytical processing generates the required daily metric data from operational source-of-truth records.
* Daily metric generation is idempotent and can safely recompute the current analytical period.
* Required materialized analytical views can be refreshed from their underlying daily metric tables.
* Campaign analytics produced during event processing integrate correctly with the broader analytical layer.
* Analytical results can be reproduced from underlying operational business data.
* Analytics Service capabilities can retrieve the data required by the Prototype APIs and dashboard.
* Analytics processing remains independent of the synchronous Kafka event-processing transaction path.

---

## Milestone 5 - API & Dashboard Vertical Slice

### Goal

Complete the first visible end-to-end Customer Intelligence Platform experience.

### Backend Scope

* Implement the FastAPI endpoints required by the Prototype.
* Expose basic platform metrics.
* Expose merchant information required by the dashboard.
* Expose basic shopper and business activity where useful.
* Implement consistent request and response schemas.
* Connect APIs through the Business Service and Data Access layers.

### Frontend Scope

* Implement the basic internal dashboard.
* Connect the frontend to FastAPI.
* Use TanStack Query for server state.
* Display key business KPIs.
* Display at least one meaningful time-series visualization.
* Display basic merchant or shopper business information.
* Implement loading, error, and empty states.

### Definition of Done

A complete business flow can be demonstrated from synthetic activity to visible business intelligence:

```text
Generated Event
      │
      ▼
Kafka
      │
      ▼
Event Table
      │
      ▼
Business Processing
      │
      ▼
Operational Data
      │
      ▼
Derived Metric
      │
      ▼
FastAPI
      │
      ▼
React Dashboard
```

At this point, the core architecture has been validated through working software rather than documentation alone.

---

# Phase 1 Completion Criteria

Phase 1 is complete when:

* The real backend and frontend structures are established.
* The complete PostgreSQL schema is implemented.
* Local infrastructure runs reproducibly.
* Merchant and shopper events are generated and streamed through Kafka.
* Events are persisted and processed deterministically.
* Operational business state is maintained correctly.
* Basic derived business metrics are generated.
* Backend APIs expose meaningful business information.
* A React dashboard visualizes information produced by the complete data pipeline.
* The implementation created during Phase 1 can continue directly into the MVP without being rewritten as a separate architecture.

## Phase 1 Implementation Outcome

Phase 1 was completed successfully and validated the intended end-to-end architecture through working software.

The implemented foundation now includes:

- Coherent Merchant, Product, Shopper, and Campaign synthetic event generation.
- Kafka-based event ingestion with versioned contracts, duplicate protection, controlled offset handling, and Dead Letter Queue isolation.
- Deterministic operational processing for Merchant, Subscription, Feature, Product, Variant, Shopper, Order, and Campaign state.
- PostgreSQL event history, operational data, reference data, derived daily metrics, and aggregate materialized views.
- Idempotent scheduled analytics for Merchant, Platform, Feature, and Campaign metrics.
- Historical subscription and feature-state reconstruction for analytical correctness.
- FastAPI operational and analytics endpoints.
- React and TypeScript dashboards using TanStack Query and ECharts.
- End-to-end validation from synthetic business activity through Kafka, PostgreSQL, analytics, APIs, and the React dashboard.

Implementation also refined several details without changing the core architecture, including explicit Plan-to-Feature entitlements, Event-to-Feature usage mappings, context-aware synthetic generation, asynchronous analytical processing, and historical point-in-time reconstruction.

The Phase 1 implementation is the working foundation for Phase 2 and should be extended rather than replaced.

---

# Phase 2 - Minimum Viable Product

## Goal

Expand the completed End-to-End Prototype into the first usable Customer Intelligence Platform for internal teams.

Phase 2 builds on the operational data platform, analytics foundation, APIs, and internal dashboard established during Phase 1. The MVP introduces richer customer intelligence data products, deeper business analytics and drill-down experiences, retrieval-oriented AI knowledge, controlled business tools, and evidence-grounded AI-assisted investigations.

The MVP should allow an internal user to move from observing business performance to understanding the underlying merchants, shoppers, campaigns, and customer journeys, and then investigate business questions using controlled AI capabilities grounded in authoritative platform data.

The target MVP flow is:

```text
Synthetic Business Activity
        │
        ▼
Kafka & Event Processing
        │
        ▼
Operational Business Data
        │
        ▼
Profiles • Journeys • Segments • Health
        │
        ▼
Business Metrics & Analytics
        │
        ├───────────────────────┐
        ▼                       ▼
Internal Dashboards       AI Knowledge Pipeline
& Drill-Downs                    │
        │                        ▼
        │                Semantic Knowledge
        │                        │
        └───────────┬────────────┘
                    ▼
                AI Gateway
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Business Tools        AI Retrieval
          │                   │
          └─────────┬─────────┘
                    ▼
          Investigation Agent
                    │
                    ▼
       Evidence-Grounded Findings
```

---

## Phase 2 Context

Phase 2 extends the completed Phase 1 implementation rather than rebuilding it.

Phase 1 already established:

* Merchant, Product, Shopper, Order, Campaign, Subscription, Feature, and related operational business processing.
* Versioned event contracts and coherent synthetic business event generation.
* Kafka ingestion, deterministic event routing, duplicate protection, offset handling, and Dead Letter Queue processing.
* PostgreSQL event history and operational source-of-truth data.
* Merchant Metrics Daily.
* Platform Metrics Daily.
* Feature Metrics Daily.
* Campaign Analytics Daily and existing campaign analytical summaries.
* Materialized analytical views.
* Historical subscription and feature-state reconstruction.
* Idempotent analytical recomputation.
* APScheduler-based scheduled analytical processing.
* Typed operational and analytics APIs.
* The internal React dashboard using TanStack Query and Apache ECharts.

These capabilities remain the foundation for the MVP and should be extended where required rather than reimplemented.

Phase 2 therefore focuses primarily on:

* Incremental generation of richer derived business data.
* Merchant and Shopper Profiles.
* Customer and Merchant Journeys.
* Shopper Segment Membership.
* Merchant Health.
* Complete MVP business analytics and campaign attribution.
* Richer internal dashboards and business drill-downs.
* AI-oriented business knowledge generation.
* Exact, semantic, and hybrid retrieval.
* Controlled AI access to platform business capabilities.
* Evidence-grounded AI-assisted investigations.
* Dashboard-to-investigation workflows.
* Integration testing and MVP hardening.

Any missing operational-domain behaviour discovered while implementing these capabilities should be added to the existing Phase 1 business-processing architecture rather than introducing a parallel processing path.

---

## MVP Scope Boundaries

The MVP intentionally establishes the architectural foundations required for future versions without implementing the complete Version 1 product experience.

### Investigation Depth

The MVP implements a bounded LangGraph investigation workflow capable of:

* Understanding the investigation objective.
* Selecting and executing controlled business tools.
* Retrieving relevant semantic knowledge.
* Gathering supporting evidence.
* Determining whether sufficient evidence exists.
* Performing additional bounded evidence gathering when required.
* Generating grounded findings and recommendations when supported by evidence.
* Communicating insufficient evidence rather than inventing unsupported conclusions.

Richer working memory, reflection, advanced evidence validation, and more sophisticated multi-step investigation behaviour remain Version 1 enhancements.

### Investigation Persistence

The MVP persists the investigation information required for grounding, auditability, and basic continuation, including:

* Investigation metadata.
* Investigation messages.
* Tool executions.
* Supporting evidence.
* Generated findings and responses where appropriate.

A richer searchable investigation-history experience and enhanced conversational continuity remain Version 1 capabilities.

### Authentication & Authorization

Phase 2 establishes lightweight identity/principal handling and authorization boundaries for the platform's two primary access scopes:

* `INTERNAL` users may access platform-wide information and merchant-scoped information.
* `MERCHANT` users are restricted to information belonging to their associated merchant.

The authorization model should be reusable across REST APIs and AI-assisted investigations so that AI tools cannot bypass normal platform access boundaries.

Production authentication providers and the complete merchant-facing dashboard and AI-assistant experience remain outside the MVP.

### Merchant Journeys

Merchant Journeys remain part of the MVP derived-data layer and are implemented alongside Customer Journeys.

They provide deterministic merchant lifecycle context that supports merchant health, internal merchant intelligence, Customer Success workflows, and later AI knowledge generation and investigations.

---

## Milestone 1 - Incremental Derived-Data Foundation

### Goal

Extend the existing scheduled-processing architecture so that MVP derived business data products can be generated incrementally, reliably, and reproducibly as new business activity arrives.

### Context

Phase 1 already established APScheduler-based analytical processing and idempotent daily analytical recomputation.

The MVP introduces additional derived products such as Profiles, Journeys, Segment Membership, Merchant Health, and AI Knowledge. Regenerating all derived data after every event would be unnecessary and inefficient.

Phase 2 therefore introduces incremental processing based on business-entity processing state while preserving the ability to safely recompute derived data when required.

### Scope

* Implement or activate the designed processing-state capabilities required for incremental derived-data generation.
* Track relevant business activity timestamps for entities such as Merchants, Shoppers, and Campaigns.
* Track generation timestamps for derived products where required.
* Determine which entities have changed since their corresponding derived data was last generated.
* Introduce reusable scheduled-processing patterns for processing changed entities.
* Integrate incremental processing with the existing APScheduler infrastructure.
* Preserve idempotent regeneration of derived data.
* Ensure processing state advances only after successful generation.
* Support safe retries after failed derived-data generation.
* Preserve the ability to regenerate historical or stale derived data when required.
* Introduce platform processing events where required by the established data architecture.
* Add appropriate service and Data Access Layer capabilities for processing-state management.

### Definition of Done

* Scheduled jobs can identify entities whose source business data has changed.
* Unchanged entities are not unnecessarily regenerated.
* Changed entities can be processed through reusable scheduled-processing workflows.
* Processing state is updated only after successful generation.
* Failed generation can be retried without corrupting processing state.
* Derived-data generation remains reproducible from authoritative source data.
* Existing Phase 1 scheduled analytics continue to operate correctly.
* The incremental-processing foundation can be reused by Profiles, Journeys, Segments, Merchant Health, and AI Knowledge generation.

---

## Milestone 2 - Profiles & Business Journeys

### Goal

Generate the core derived business representations that consolidate merchant and shopper behaviour into analytics-ready Profiles and traceable business Journeys.

### Scope

#### Merchant Profiles

* Generate Merchant Profiles from operational merchant data and relevant business activity.
* Incorporate subscription state and history.
* Incorporate platform feature adoption and usage.
* Incorporate campaign activity.
* Incorporate relevant merchant business-performance information.
* Maintain lineage to authoritative source data.
* Regenerate Merchant Profiles incrementally when relevant merchant activity changes.

#### Shopper Profiles

* Generate Shopper Profiles from operational shopper information and behavioural activity.
* Incorporate browsing and engagement behaviour.
* Incorporate Wishlist, Save for Later, cart, checkout, and purchase behaviour where applicable.
* Incorporate purchase history and relevant value/engagement indicators defined by the existing data model.
* Incorporate campaign engagement where applicable.
* Maintain lineage to authoritative source data.
* Regenerate Shopper Profiles incrementally when relevant shopper activity changes.

#### Shopper Journeys

* Generate Shopper Journeys from shopper behavioural events.
* Maintain ordered Shopper Journey Events.
* Represent relevant stages of shopper behaviour across browsing, engagement, cart, checkout, purchase, and campaign interactions.
* Allow journeys to represent both converting and non-converting shopper behaviour; a Shopper Journey is not required to end in a purchase.
* Preserve deterministic event ordering and source-event lineage.
* Support regeneration from underlying shopper activity.

`Shopper Journey` is the preferred implementation terminology for the business data product previously referred to as `Customer Journey` in the design documents. Both terms refer to the same concept. During Phase 2 implementation, the existing Customer Journey database/model naming should be renamed to Shopper Journey for consistency with the platform's Merchant/Shopper terminology.

#### Merchant Journeys

* Generate Merchant Journeys from merchant lifecycle and platform-usage activity.
* Maintain ordered Merchant Journey Events.
* Represent relevant lifecycle activity such as onboarding, application state, subscription changes, feature adoption, configuration changes, campaigns, and platform activity.
* Preserve deterministic event ordering and source-event lineage.
* Support regeneration from underlying merchant activity.

#### Shared Processing

* Integrate Profiles and Journeys with the Milestone 1 incremental-processing foundation.
* Implement required Business Service and Data Access Layer capabilities.
* Add focused tests for deterministic generation, idempotency, ordering, and lineage.

### Definition of Done

* Merchant Profiles can be generated reproducibly from authoritative platform data.
* Shopper Profiles can be generated reproducibly from authoritative platform data.
* Shopper Journeys accurately represent ordered shopper behaviour, including both converting and non-converting journeys.
* Merchant Journeys accurately represent ordered merchant lifecycle activity.
* Profiles and Journeys maintain traceability to their underlying business data.
* New relevant activity causes affected Profiles and Journeys to become eligible for regeneration.
* Regeneration is idempotent and does not create duplicate derived records.
* Business Service and Data Access Layer capabilities expose the derived products for downstream use.

---

## Milestone 3 - Segmentation, Merchant Health & Complete MVP Analytics

### Goal

Complete the deterministic customer-intelligence and business-analytics layer required by the MVP before introducing AI-assisted investigation.

### Scope

#### Shopper Segment Membership

* Generate Shopper Segment Membership from existing Shopper Segment definitions and relevant shopper business data.
* Evaluate membership using deterministic business rules.
* Refresh affected memberships when relevant shopper information changes.
* Preserve the distinction between operational Segment definitions and derived Segment Membership.
* Support retrieval of a shopper's segments and the shoppers belonging to a segment.

#### Merchant Health

* Generate Merchant Health from relevant deterministic merchant signals.
* Incorporate merchant activity and engagement.
* Incorporate subscription behaviour where relevant.
* Incorporate feature adoption and usage.
* Incorporate campaign activity and performance.
* Incorporate shopper/business performance signals where defined by the existing design.
* Maintain explainable health factors rather than an opaque AI-generated health assessment.
* Refresh Merchant Health incrementally as relevant business information changes.

#### Shopper & Business Analytics

* Complete the MVP analytical capabilities required to understand shopper behaviour.
* Support Shopper Journey and conversion-funnel analysis.
* Support relevant shopper engagement and purchase analytics.
* Complete revenue and conversion analytical capabilities required by MVP workflows.
* Build on existing Merchant, Platform, and Feature daily metrics rather than recreating them.

#### Campaign Analytics & Attribution

* Extend the Phase 1 campaign analytical foundation where required by MVP workflows.
* Correlate campaign engagement with shopper behaviour, Journeys, Orders, and conversions where required.
* Support campaign audience and segment analysis.
* Support deterministic campaign attribution according to the established data model and business rules.
* Preserve reproducibility from underlying campaign and shopper activity.

#### Scheduled Processing

* Integrate Segment Membership, Merchant Health, and new analytical products with incremental scheduled processing.
* Preserve idempotent recomputation where analytical periods need to be regenerated.
* Refresh affected materialized views where required.

### Definition of Done

* Shopper Segment Membership can be generated and refreshed deterministically.
* Merchant Health can be reproduced from explicit underlying business signals.
* Shopper Journey and conversion-funnel analytics are available.
* Required shopper and revenue analytics are available.
* Campaign performance and attribution can be traced to underlying campaign, shopper, and order activity.
* Existing Platform, Feature, Merchant, and Campaign analytics continue to operate correctly.
* Derived analytical products remain reproducible from authoritative platform data.
* The deterministic platform can answer the primary MVP business-intelligence questions without requiring the AI layer.

---

## Milestone 4 - MVP Business APIs & Internal Intelligence Experience

### Goal

Expose the complete deterministic MVP business-intelligence layer through reusable backend APIs and richer internal dashboard and drill-down experiences.

### Backend Scope

* Extend Merchant APIs to expose:
  * Merchant Profiles.
  * Merchant Health.
  * Merchant Journeys.
  * Subscription and feature-adoption information required by MVP workflows.
* Extend Shopper APIs to expose:
  * Shopper Profiles.
  * Shopper Journeys.
  * Purchase history.
  * Segment Membership.
  * Shopper activity required by drill-down experiences.
* Extend Campaign APIs to expose:
  * Campaign details.
  * Campaign performance.
  * Campaign engagement.
  * Campaign audience and segment information.
  * Attribution information required by the MVP.
* Extend Analytics APIs to expose:
  * Revenue metrics.
  * Conversion metrics.
  * Shopper analytics.
  * Merchant analytics.
  * Campaign analytics.
  * Platform and feature analytics.
* Introduce or extend consolidated Dashboard API capabilities where justified by frontend access patterns.
* Reuse Business Services and Data Access Layer capabilities rather than implementing dashboard-specific business logic.

### Authentication & Authorization Foundation

* Introduce lightweight MVP identity/principal handling.
* Represent `INTERNAL` and `MERCHANT` access scopes.
* Associate merchant principals with their permitted `merchant_id`.
* Enforce platform-wide versus merchant-scoped access boundaries.
* Prevent merchant principals from accessing other merchants' data.
* Keep authorization concerns outside core business calculations.
* Establish authorization capabilities that can later be reused by AI tools and investigations.
* Keep production authentication-provider integration outside the MVP.

### Frontend Scope

* Expand the internal dashboard beyond the Phase 1 vertical slice.
* Support platform-wide business intelligence.
* Add merchant-level drill-down experiences.
* Add Shopper Profile and activity drill-downs.
* Add Shopper Journey visualization.
* Add Merchant Journey visualization where useful to internal workflows.
* Add Merchant Health presentation.
* Add shopper-segment views.
* Expand campaign-performance and attribution views.
* Add conversion-funnel and relevant business-analytics visualizations.
* Support relevant filters and date-range selection.
* Preserve loading, error, empty, and responsive states.
* Continue using TanStack Query for server state and Apache ECharts for analytical visualization.

The MVP frontend remains primarily an internal-team experience. A complete merchant-facing dashboard remains deferred to Version 1.

### Definition of Done

* Internal users can monitor platform-wide business performance.
* Internal users can drill from platform-level information into individual merchants.
* Merchant detail views expose relevant Profiles, Health, Journeys, Features, Campaigns, and business analytics.
* Users can drill into relevant Shoppers, Customer Journeys, Segments, and Campaigns.
* REST APIs expose the business capabilities required by these experiences through typed contracts.
* Internal and merchant authorization boundaries are represented and enforced.
* Merchant-scoped principals cannot access another merchant's business information.
* The deterministic Customer Intelligence Platform is useful through dashboards and APIs without requiring AI capabilities.
* The resulting Business Services can later be reused directly by AI tools.

---

## Milestone 5 - AI Knowledge Pipeline

### Goal

Transform deterministic business intelligence into retrieval-oriented semantic knowledge while preserving PostgreSQL and the platform's derived business products as the authoritative sources of truth.

### Scope

#### Knowledge Generation

* Implement the AI Knowledge Pipeline defined by the AI and Data Architecture.
* Build structured fact payloads from deterministic business data products.
* Introduce the Summary Builder responsible for preparing business facts for summarization.
* Generate concise retrieval-oriented natural-language summaries using the configured LLM provider.
* Keep deterministic business calculations outside the language model.
* Generate initial knowledge types required by MVP investigations, including appropriate:
  * Merchant summaries.
  * Shopper behaviour summaries.
  * Shopper Journey summaries.
  * Campaign summaries.
  * Business-performance or metric summaries.
* Preserve the ability to introduce additional knowledge types later without changing the source-of-truth architecture.

#### Embeddings

* Integrate the selected BGE embedding model.
* Generate embeddings from retrieval-oriented business summaries.
* Keep embedding generation independent of deterministic business processing.

#### Qdrant Knowledge Storage

* Integrate the existing Qdrant infrastructure with the backend.
* Store semantic knowledge and embeddings in the designed collection structure.
* Store retrieval metadata required to resolve knowledge back to authoritative business information.
* Include relevant metadata such as entity type, entity identifier, source reference, merchant context, and time window where applicable.
* Preserve source lineage between semantic knowledge and underlying business data.

#### Incremental Knowledge Generation

* Integrate knowledge generation with entity processing state.
* Regenerate knowledge only when changes to the relevant underlying business information make that knowledge stale.
* Refresh or replace current-state semantic knowledge records when their underlying business information changes so obsolete current-state knowledge does not remain active in Qdrant.
* Preserve historical or time-bounded knowledge that remains valid for its original context, such as completed investigation summaries or summaries representing a specific historical period; such knowledge should not be replaced merely because the entity later changes.
* Determine refresh behaviour according to the knowledge type and its source/time-window semantics rather than treating all knowledge associated with an entity identically.
* Update knowledge-generation state only after successful summary, embedding, and vector-storage processing.
* Support safe regeneration when refresh or generation fails.

### Definition of Done

* Deterministic business products can be transformed into retrieval-oriented summaries.
* Summary generation does not become a source of business truth.
* BGE embeddings are generated successfully.
* Knowledge records and embeddings are stored in Qdrant.
* Every knowledge item contains sufficient metadata to trace it back to authoritative platform data.
* Current-state knowledge is refreshed when relevant source changes make it stale, while valid historical or time-bounded knowledge is preserved according to its knowledge type and context.
* Unchanged entities are not unnecessarily regenerated.
* Failed knowledge generation can be safely retried.
* Semantic knowledge is available for downstream retrieval without duplicating the platform's source of truth.

---

## Milestone 6 - AI Gateway & Controlled Business Tools

### Goal

Establish the controlled backend boundary through which AI-assisted investigations access platform business capabilities.

### Scope

#### AI Gateway

* Implement the AI Gateway within the established backend architecture.
* Integrate the configured LLM provider behind the gateway.
* Centralize model interaction through the AI Gateway rather than allowing AI components to call the provider independently.
* Establish investigation-context assembly.
* Apply data minimization before business information is provided to the model.
* Apply sensitive-data masking where required.
* Propagate user/principal authorization context into AI operations.
* Establish guardrail and response-validation boundaries required by the existing AI design.

#### Tool Layer

* Implement the controlled AI tool registry.
* Define typed and validated tool contracts.
* Execute tools through reusable Business Service capabilities.
* Prevent tools from exposing direct SQL or unrestricted database access.
* Implement the minimum business tools required by MVP investigations, including appropriate:
  * Merchant Profile retrieval.
  * Merchant Health retrieval.
  * Shopper Profile retrieval.
  * Shopper Journey retrieval.
  * Merchant Journey retrieval where relevant.
  * Business Metrics retrieval.
  * Campaign Analytics retrieval.
  * Segment information retrieval.
  * Order or purchase-history retrieval where required.
* Record sufficient execution metadata for later investigation persistence and auditability.

#### Exact Entity Retrieval

* Support deterministic retrieval of known Merchants, Shoppers, Campaigns, Orders, and other required entities through controlled tools.
* Resolve entity identifiers using authoritative business services.
* Apply authorization before returning business information.
* Ensure merchant principals cannot use AI tools to access another merchant's data.

### Definition of Done

* All LLM communication required by investigations is routed through the AI Gateway.
* AI-facing tools expose business capabilities rather than databases.
* Tools reuse existing Business Services.
* Tool inputs and outputs use explicit validated contracts.
* Exact entity retrieval returns authoritative business information.
* Authorization context is propagated into tool execution.
* Data minimization and masking boundaries are established.
* Merchant-scoped AI requests cannot retrieve another merchant's business information.
* Tool execution can be traced for later investigation persistence.
* The AI layer cannot bypass the platform's normal business and access-control boundaries.

---

## Milestone 7 - Semantic & Hybrid Retrieval

### Goal

Enable investigations to discover relevant business knowledge semantically and combine that knowledge with authoritative exact business retrieval.

### Scope

#### Semantic Retrieval

* Implement semantic search over the AI Knowledge Layer in Qdrant.
* Generate query embeddings using the selected BGE model.
* Retrieve semantically relevant business summaries.
* Support appropriate metadata filtering.
* Return knowledge metadata and source references with retrieval results.
* Resolve retrieved knowledge back to authoritative entities or business data where detailed evidence is required.
* Expose semantic retrieval through a controlled AI tool/capability.

#### Exact vs Semantic Retrieval

* Preserve the architectural distinction between:
  * Exact retrieval for known business entities.
  * Semantic retrieval for exploratory business questions and contextual discovery.
* Ensure exact retrieval continues to use authoritative platform services rather than vector search.

#### Hybrid Retrieval

* Implement the retrieval flow required to combine semantic discovery with exact authoritative retrieval.
* Allow semantic knowledge to identify relevant Merchants, Shoppers, Campaigns, Journeys, metrics, or historical context.
* Allow subsequent business tools to retrieve authoritative supporting information.
* Preserve source metadata throughout the combined retrieval process.
* Prevent semantic knowledge from being treated as authoritative evidence when underlying business records are required.

#### Retrieval Verification

* Add focused retrieval tests.
* Validate metadata filtering.
* Validate source resolution.
* Validate representative semantic queries against generated knowledge.
* Evaluate whether retrieved knowledge is sufficiently relevant for representative MVP investigation scenarios.

### Definition of Done

* Exploratory business questions can retrieve semantically relevant knowledge from Qdrant.
* Known entities can be retrieved directly through exact business tools.
* Semantic retrieval results maintain source metadata and lineage.
* Semantic results can guide subsequent exact business retrieval.
* Hybrid retrieval can combine contextual discovery with authoritative evidence.
* Retrieval respects merchant and authorization boundaries.
* Representative MVP investigation questions return useful retrieval candidates.
* The retrieval layer is independently testable before being orchestrated by the Investigation Agent.

---

## Milestone 8 - Basic Investigation Agent & Evidence Persistence

### Goal

Implement the MVP AI-assisted investigation workflow using LangGraph so business questions can be investigated through controlled retrieval and business tools before grounded findings are generated.

### Scope

#### Investigation Workflow

* Implement the bounded LangGraph Investigation Agent.
* Define the investigation state required by the MVP workflow.
* Interpret the user's business question and investigation objective.
* Identify relevant business entities and context.
* Determine what evidence is required.
* Select appropriate exact, semantic, or hybrid retrieval capabilities.
* Execute controlled business tools.
* Gather supporting evidence.
* Evaluate whether sufficient evidence exists.
* Allow bounded additional evidence gathering when required.
* Prevent uncontrolled or unnecessary investigation loops.
* Generate findings only after evidence collection.
* Communicate insufficient evidence when the available information does not support a reliable conclusion.
* Generate recommendations only when supported by gathered evidence.

#### Evidence Grounding

* Associate generated findings with supporting evidence.
* Preserve source references for retrieved business information.
* Distinguish semantic contextual knowledge from authoritative business evidence where appropriate.
* Ensure final responses do not claim conclusions unsupported by collected evidence.
* Return structured investigation responses suitable for frontend presentation.

#### Investigation Persistence

* Persist investigation metadata.
* Persist user and AI investigation messages.
* Persist tool executions.
* Persist supporting evidence and source references.
* Persist generated findings/responses where required by the established investigation schema.
* Support retrieval of an existing investigation required for basic continuation.
* Maintain sufficient information for auditability and debugging.

#### Investigation APIs

* Implement the MVP Investigation API capabilities required to:
  * Create an investigation.
  * Submit an investigation question.
  * Retrieve investigation details.
  * Continue an active investigation where required by the MVP workflow.
  * Retrieve findings and supporting evidence.
* Keep API handlers thin and delegate investigation behaviour to the appropriate service and AI layers.

### Definition of Done

* A user can submit a natural-language business question through the backend.
* The LangGraph workflow can select and execute appropriate controlled tools.
* Investigations can use exact, semantic, and hybrid retrieval as required.
* Multiple bounded evidence-gathering steps can occur when a question requires them.
* The agent evaluates evidence sufficiency before generating findings.
* Unsupported conclusions are not presented as established findings.
* Insufficient evidence produces an explicit uncertainty/insufficient-information response.
* Findings maintain references to supporting evidence.
* Investigation metadata, messages, tool executions, and evidence are persisted.
* Existing investigations can be retrieved for the continuation required by the MVP.
* The MVP investigation workflow remains intentionally bounded, leaving richer reflection, working memory, and advanced multi-step behaviour for Version 1.

---

## Milestone 9 - Investigation UX, Integration & MVP Hardening

### Goal

Integrate deterministic business intelligence and AI-assisted investigation into one coherent internal-user MVP and harden the complete platform through realistic end-to-end validation.

### Investigation Frontend

* Implement the AI Investigation interface.
* Allow users to submit natural-language business questions.
* Display investigation progress and appropriate loading states.
* Display AI findings.
* Display supporting evidence.
* Display business observations and recommendations where present.
* Clearly distinguish user messages, AI responses, and supporting investigation information.
* Support the basic continuation behaviour included in the MVP.
* Retrieve authoritative investigation state from the backend rather than relying only on frontend state.

### Dashboard-to-Investigation Workflows

* Add **Investigate with AI** entry points to relevant dashboard and drill-down contexts.
* Allow investigations to start with relevant context already attached, such as:
  * Merchant.
  * Shopper.
  * Campaign.
  * Business metric.
  * Observed trend.
  * Selected time range.
* Avoid requiring users to repeat business context already available in the dashboard.
* Allow users to move naturally from business monitoring to AI-assisted investigation.
* Preserve dashboard usefulness independently of the AI experience.

### End-to-End Integration

Validate representative MVP workflows such as:

* Investigating a conversion decline.
* Investigating declining Merchant Health.
* Investigating feature adoption or usage changes.
* Investigating shopper behaviour or Customer Journeys.
* Investigating campaign performance and attribution.
* Retrieving known merchant, shopper, campaign, or order information through exact AI-assisted lookup.

Each representative workflow should validate the complete path where applicable:

```text
Business Activity
      │
      ▼
Kafka Processing
      │
      ▼
Operational Business Data
      │
      ▼
Derived Intelligence
      │
      ▼
Analytics / Dashboard
      │
      ▼
AI Investigation
      │
      ├── Exact Business Tools
      └── Semantic Knowledge
      │
      ▼
Evidence-Grounded Response
```

### Redis Caching

* Measure or inspect MVP access patterns before introducing application-level caching.
* Introduce Redis caching only where repeated or computationally expensive access patterns justify it.
* Appropriate candidates may include frequently accessed dashboard aggregates, Profile summaries, or repeated investigation context.
* Keep PostgreSQL and the relevant derived data products as the source of truth.
* Define predictable cache invalidation or refresh behaviour.
* Do not introduce caching solely because Redis is available.

### MVP Hardening

* Add integration tests across major backend layers.
* Add representative end-to-end tests across data, API, retrieval, AI, and frontend workflows where practical.
* Verify authorization boundaries across REST and AI paths.
* Verify merchant isolation.
* Verify investigation evidence persistence.
* Verify AI failure and insufficient-evidence behaviour.
* Verify knowledge-generation and retrieval failure handling.
* Verify scheduled-processing recovery.
* Validate that Phase 1 event processing and analytics continue to operate correctly.
* Review query and retrieval performance for major MVP workflows.
* Address measured performance problems without introducing premature optimization.
* Ensure meaningful operational failures are logged and diagnosable.
* Remove temporary implementation shortcuts or obsolete Prototype-specific assumptions discovered during MVP integration.

### Definition of Done

* Internal users can monitor meaningful platform-wide business intelligence.
* Users can drill into Merchants, Shoppers, Campaigns, Profiles, Journeys, Segments, Health, and relevant analytics.
* Users can initiate an AI investigation directly from relevant business context.
* Dashboard context is transferred into the investigation where appropriate.
* The Investigation Agent can gather structured and semantic evidence through controlled platform capabilities.
* Findings are presented together with supporting evidence.
* Authorization boundaries are preserved throughout dashboard, API, retrieval, tool, and investigation workflows.
* Representative end-to-end MVP scenarios operate successfully.
* Redis caching is introduced only for access patterns where it provides demonstrated value.
* Major MVP integration and failure scenarios are covered by automated verification.
* Phase 1 functionality continues to operate without architectural replacement or regression.

---

# Phase 2 Completion Criteria

Phase 2 is complete when the Customer Intelligence Platform operates as the first usable internal-team MVP.

The MVP must demonstrate that:

* The Phase 1 event-driven operational data platform continues to operate reliably.
* Derived business data is generated incrementally without unnecessary full recomputation.
* Merchant Profiles are generated and maintained.
* Shopper Profiles are generated and maintained.
* Shopper Journeys are generated from shopper activity, including both converting and non-converting behaviour.
* Merchant Journeys are generated from merchant lifecycle activity.
* Shopper Segment Membership is generated deterministically.
* Merchant Health is generated from explainable business signals.
* Required MVP merchant, shopper, campaign, revenue, conversion, platform, and feature analytics are available.
* Campaign analytics support the attribution required by MVP workflows.
* Internal users can navigate platform-level intelligence and drill into relevant merchants, shoppers, campaigns, journeys, segments, and analytical data.
* Lightweight identity and authorization boundaries distinguish internal and merchant-scoped access.
* Merchant-scoped access cannot retrieve another merchant's business information.
* Retrieval-oriented business summaries are generated from deterministic platform data.
* BGE embeddings are generated and semantic knowledge is stored in Qdrant with source metadata.
* Exact entity retrieval accesses authoritative business data through controlled business tools.
* Semantic retrieval can identify relevant business knowledge for exploratory questions.
* Hybrid retrieval can use semantic discovery to guide authoritative business-data retrieval.
* The AI Gateway controls model interaction, tool execution, data minimization, masking, and authorization context.
* The LangGraph Investigation Agent can perform bounded evidence-gathering workflows.
* AI-generated findings are grounded in identifiable supporting evidence.
* The platform communicates insufficient evidence rather than generating unsupported conclusions.
* Investigation metadata, messages, tool executions, findings, and supporting evidence are persisted as required by the MVP.
* Users can initiate investigations directly from relevant dashboard context.
* Representative dashboard-to-investigation workflows operate end to end.
* Integration tests validate the major deterministic, retrieval, authorization, AI, and user-facing workflows.
* Redis caching is introduced only where justified by measured or clearly demonstrated access patterns.
* The implementation remains aligned with the finalized architecture and continues directly into Version 1 without requiring architectural replacement.

At the completion of Phase 2, the platform should demonstrate the complete MVP workflow:

```text
Merchant & Shopper Activity
        │
        ▼
Event-Driven Data Platform
        │
        ▼
Authoritative Business State
        │
        ▼
Profiles • Journeys • Segments • Health
        │
        ▼
Business Metrics & Analytics
        │
        ▼
Internal Business Intelligence
        │
        ▼
Business Question
        │
        ▼
Controlled AI Investigation
        │
        ├── Exact Business Retrieval
        ├── Semantic Knowledge Retrieval
        └── Hybrid Evidence Gathering
        │
        ▼
Evidence Evaluation
        │
        ▼
Grounded Findings & Supporting Evidence
        │
        ▼
User Makes an Informed Business Decision
```

The MVP therefore validates the complete Customer Intelligence Platform concept: reliable business data and deterministic intelligence remain the foundation, while AI assists users in investigating that information through controlled, explainable, and evidence-grounded workflows.

---

# Phase 3 - Version 1

Phase 3 focuses on expanding business value and improving the overall product experience.

Expected areas include:

* Enhanced multi-step investigation workflows.
* Investigation context and follow-up experience.
* Evidence validation and improved grounding.
* Investigation history.
* Improved recommendations.
* Enhanced shopper segmentation.
* Campaign recommendations.
* Merchant churn insights.
* Product and feature usage recommendations.
* Merchant-facing dashboards.
* Merchant AI assistant.
* Store-specific intelligence.
* Improved dashboard and investigation UX.
* Expanded testing and observability.
* Performance optimization based on measured behaviour.
* Overall product polish.

Detailed Version 1 planning will occur after the MVP is complete.

---

# Implementation Rules

Throughout implementation:

* Existing design documents remain the source of truth for architecture and technology decisions.
* Implementation from completed phases should continue into subsequent phases rather than being replaced by phase-specific or disposable code.
* Business logic belongs within the Business Service Layer.
* APIs, Kafka consumers, scheduled jobs, and AI tools should reuse the same business services.
* Database access should remain within the Data Access Layer.
* Operational data and event history remain authoritative business data.
* Derived data must remain reproducible and traceable to its underlying sources.
* AI should not be introduced into deterministic business processing.
* New technologies or architectural components should not be introduced unless an existing design genuinely cannot satisfy an implementation requirement.
* When implementation exposes a flaw in an existing design decision, the tradeoff should be discussed and the appropriate design document updated before introducing a conflicting implementation.
* Prefer working vertical slices and measurable progress over expanding documentation.

---

# Current Progress

```text
Product Design                 COMPLETE
Architecture Design            COMPLETE
Technology Decisions           COMPLETE
Backend Design                 COMPLETE
Database Design                COMPLETE
Frontend Design                COMPLETE

Implementation
└── Phase 1 - End-to-End Prototype                          COMPLETE
    ├── Milestone 1 - Project & Infrastructure Foundation   COMPLETE
    ├── Milestone 2 - Database Foundation                   COMPLETE
    ├── Milestone 3 - Event Generation & Ingestion          COMPLETE
    ├── Milestone 4 - Basic Business Processing & Analytics COMPLETE
    └── Milestone 5 - API & Dashboard Vertical Slice        COMPLETE

Phase 2 - MVP                  PLANNED
Phase 3 - Version 1            PLANNED
```
