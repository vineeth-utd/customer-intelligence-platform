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

Transform incoming events into meaningful operational business state and basic analytics.

### Scope

Implement the business services and data access required by the Prototype's event flows.

Initial processing should cover enough business activity to demonstrate meaningful end-to-end behaviour, including:

* Merchant lifecycle state.
* Shopper state.
* Product and Product Variant information required by shopper activity.
* Orders and Order Items.
* Basic campaign activity where required.
* Relevant feature activity.
* Basic merchant and shopper analytical data.
* Initial daily business metrics.
* Required materialized view refreshes.
* Analytics Service capabilities required by the Prototype dashboard.

The implementation should use the real Business Service and Data Access layers rather than Prototype-specific shortcuts.

### Definition of Done

* Event processing produces correct operational business records.
* Related entities remain consistent with database constraints.
* Basic derived metrics can be generated from processed business activity.
* Analytical results can be reproduced from underlying source data.
* Business services can retrieve the data required by the Prototype APIs.

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

---

# Phase 2 - Minimum Viable Product

Phase 2 expands the working Prototype into the first usable Customer Intelligence Platform for internal teams.

Expected areas of implementation include:

* Complete merchant, shopper, campaign, product, order, subscription, and feature processing.
* Merchant Profiles.
* Shopper Profiles.
* Customer Journeys.
* Merchant Journeys.
* Shopper Segment Membership.
* Merchant Health.
* Complete daily business metrics.
* Campaign analytics and attribution.
* Platform and feature analytics.
* Richer internal dashboards and drill-down experiences.
* Incremental scheduled processing using APScheduler.
* Redis caching where justified by access patterns.
* AI Knowledge Pipeline.
* Retrieval-oriented business summaries.
* BGE embedding generation.
* Qdrant semantic knowledge storage.
* AI Gateway.
* Controlled business tools.
* Exact entity retrieval.
* Semantic retrieval.
* Hybrid retrieval.
* LangGraph Investigation Agent.
* Evidence-grounded investigation responses.
* Investigation persistence.
* Dashboard-to-investigation workflows.
* Integration testing and MVP hardening.

Detailed Phase 2 milestones will be defined after the Phase 1 vertical slice is working.

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
* Phase 1 code should be designed to continue into the MVP rather than being treated as disposable Prototype code.
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
└── Phase 1 - End-to-End Prototype
    ├── Milestone 1 - Project & Infrastructure Foundation   COMPLETE
    ├── Milestone 2 - Database Foundation                   NEXT
    ├── Milestone 3 - Event Generation & Ingestion
    ├── Milestone 4 - Basic Business Processing & Analytics
    └── Milestone 5 - API & Dashboard Vertical Slice

Phase 2 - MVP                  PLANNED
Phase 3 - Version 1            PLANNED
```
