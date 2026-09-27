# Customer Intelligence Platform

A production-inspired, event-driven platform that transforms merchant and shopper activity into structured business data, analytics, and actionable insights.

Modern SaaS and eCommerce businesses generate data across merchant lifecycle events, shopper behaviour, products, campaigns, subscriptions, and feature usage. Understanding business performance often requires teams to combine information manually across multiple systems.

The Customer Intelligence Platform brings this information together through an event-driven data pipeline that maintains operational business state, generates reproducible analytics, and exposes business intelligence through APIs and dashboards.

The long-term platform extends this foundation with AI-assisted investigations for questions such as:

- Why did conversion decrease?
- Which merchants are showing declining engagement?
- How are merchants adopting and using platform features?
- Which shopper behaviours are affecting revenue?
- How are campaigns contributing to business performance?

AI is intentionally layered on top of authoritative business data and deterministic processing rather than replacing them.

## Current Status

**Phase 1 — End-to-End Prototype: Complete**

The working Prototype validates the complete core platform flow:

`Synthetic Business Activity → Kafka → Event Processing → PostgreSQL → Analytics → FastAPI → React Dashboard`

Phase 2 will expand this foundation into the MVP with richer business views, profiles, journeys, retrieval infrastructure, and AI-assisted investigations.

---

## What the Platform Does

The platform combines merchant, shopper, product, campaign, subscription, and feature activity into a consistent view of business behaviour and performance.

It currently supports:

- **Merchant intelligence** — lifecycle activity, subscriptions, feature adoption, product/catalog activity, and campaign behaviour.
- **Shopper intelligence** — sessions, product views, Wishlist and Save for Later activity, carts, checkouts, purchases, recommendations, and campaign engagement.
- **Operational business state** — authoritative records for merchants, subscriptions, features, products, variants, shoppers, orders, and campaigns alongside preserved event history.
- **Business analytics** — revenue, orders, conversion, shopper activity, platform growth, feature adoption and usage, and campaign performance.
- **Business intelligence APIs and dashboards** — platform KPIs and trends, merchant performance, subscription information, campaign analytics, shoppers, and orders.
- **Future business investigations** — the same business services and analytics will support evidence-grounded AI investigations in later phases.

---

## Phase 1 — End-to-End Prototype

Phase 1 was built using the real application architecture rather than as a throwaway prototype. It demonstrates that realistic business activity can flow through the complete platform and become visible business intelligence.

### Implemented

- Coherent Merchant, Product, Shopper, and Campaign event generators
- Domain-specific Kafka producers, topics, and asynchronous consumers
- Versioned Pydantic event contracts and UUID-based event identity
- Event validation, duplicate protection, and controlled offset commits
- Dead Letter Queue isolation for deterministic business failures
- PostgreSQL event history and operational business state
- Merchant, Platform, Feature, and Campaign daily analytics
- Historical subscription and feature-state reconstruction
- Idempotent analytical recomputation and materialized summaries
- APScheduler-based background analytics processing
- Typed FastAPI operational and analytics endpoints
- React dashboard using TanStack Query and Apache ECharts
- Loading, error, empty, pagination, and responsive UI states
- End-to-end validation from generated activity to dashboard visualization

### End-to-End Flow

```text
Synthetic Business Activity
          │
          ▼
    Event Generators
          │
          ▼
    Kafka Producers
          │
          ▼
     Apache Kafka
          │
          ▼
    Domain Consumers
          │
          ▼
Event + Operational Data
      (PostgreSQL)
          │
          ▼
  Scheduled Analytics
          │
          ▼
Daily Metrics + Materialized Views
          │
          ▼
       FastAPI
          │
          ▼
 React + TanStack Query
          │
          ▼
Business Intelligence Dashboard
```

The Phase 1 implementation continues directly into the MVP rather than being replaced by a separate architecture.

---

## Architecture

The Customer Intelligence Platform uses a modular, event-driven architecture that separates event ingestion, operational business processing, analytics, APIs, presentation, and future AI capabilities.

The architecture is designed around a core principle: authoritative business data and deterministic processing remain independent of the AI layer.

### High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                  Synthetic Business Activity                 │
│                                                              │
│   Merchant     Product      Shopper       Campaign           │
│   Generators   Generators   Generators    Generators         │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       Apache Kafka                           │
│                                                              │
│   Domain Topics  •  Event Ordering  •  DLQ Failure Isolation │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend Processing                        │
│                                                              │
│   Kafka Consumers                                            │
│         │                                                    │
│         ▼                                                    │
│   Event Validation                                           │
│         │                                                    │
│         ▼                                                    │
│   Business Service Layer                                     │
│         │                                                    │
│         ▼                                                    │
│   Data Access Layer                                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                        PostgreSQL                            │
│                                                              │
│   Event History  •  Operational State  •  Derived Metrics    │
│   Reference Data •  Materialized Analytical Views            │
└──────────────────────┬───────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
┌───────────────────────┐  ┌──────────────────────────────────┐
│ Scheduled Analytics   │  │            FastAPI               │
│                       │  │                                  │
│ APScheduler           │  │ Operational APIs                 │
│ Daily Aggregations    │  │ Analytics APIs                   │
│ View Refreshes        │  │ Typed Pydantic Contracts         │
└───────────┬───────────┘  └────────────────┬─────────────────┘
            │                               │
            └──────────► PostgreSQL         ▼
                                  ┌────────────────────────────┐
                                  │       React Frontend       │
                                  │                            │
                                  │ TanStack Query             │
                                  │ ECharts                    │
                                  │ Platform Dashboard         │
                                  │ Merchant Views             │
                                  └────────────────────────────┘


                         Phase 2+
                             │
                             ▼
                  ┌─────────────────────┐
                  │ AI Investigation    │
                  │                     │
                  │ AI Gateway          │
                  │ Retrieval           │
                  │ Business Tools      │
                  │ Investigation Agent │
                  └─────────────────────┘
```

### Architecture Principles

- **Event-driven ingestion** — Kafka decouples synthetic business activity from domain processing and allows Merchant, Product, Shopper, and Campaign events to be processed asynchronously.
- **Layered backend** — APIs, Kafka consumers, scheduled jobs, and future AI tools reuse the Business Service and Data Access layers instead of duplicating business logic.
- **Authoritative business data** — PostgreSQL preserves immutable event history alongside current operational state for merchants, subscriptions, features, products, shoppers, orders, and campaigns.
- **Decoupled analytics** — scheduled, idempotent processing generates daily metrics and materialized summaries outside the synchronous Kafka path.
- **Typed boundaries** — Pydantic, SQLAlchemy, TypeScript, and TanStack Query keep contracts explicit across events, persistence, APIs, and the frontend.
- **AI above deterministic systems** — future AI investigations consume controlled business capabilities rather than participating in deterministic processing.

---

## Key Engineering Highlights

Phase 1 focuses on data correctness, recoverability, reproducibility, and realistic end-to-end behaviour rather than simply connecting technologies.

### Reliable Event Processing

Domain events use unique identifiers and persisted processing state to prevent duplicate business mutations when Kafka redelivers an event.

Offsets advance only after an event reaches the appropriate terminal processing state.

For deterministic business failures, the consumer framework:

1. Rolls back the failed business transaction.
2. Preserves the original event in a structured Dead Letter Queue record.
3. Publishes it to the domain DLQ.
4. Commits the original offset only after DLQ publication succeeds.

Unexpected infrastructure failures halt processing without advancing the offset.

### Coherent Synthetic Business Data

Synthetic generators use existing business context rather than producing independent random records.

Generated behaviour respects relationships such as:

- Merchant subscriptions and plan entitlements
- Enabled platform features
- Product catalogs and variants
- Inventory availability
- Existing merchant identities

For example, shopper feature-usage events are generated only when the feature is both entitled through the merchant's plan and enabled for that merchant.

### Historical State Reconstruction

Analytics sometimes need the business state that existed when an event occurred rather than today's operational state.

Feature analytics reconstruct historical:

- App installation state
- Subscription plan state
- Feature enablement state

This allows usage to count only when a merchant was actually eligible for and using the feature at that point in time.

### Reproducible Analytics

Daily metrics are generated using set-based PostgreSQL aggregation and idempotent upserts, allowing the same period to be safely recomputed.

This supports:

- Historical recomputation
- Late-arriving events
- Recovery from interrupted runs
- Repeatable analytical results

Calculated metrics such as conversion rate, average order value, adoption rate, and usage rate are recomputed from their underlying totals rather than averaging previously calculated percentages.

### Operational and Analytical Isolation

Kafka consumers maintain event history and operational business state without synchronously updating analytical summaries.

APScheduler separately orchestrates daily metric generation and materialized-view refreshes, keeping ingestion responsive while preserving traceability from derived metrics back to authoritative source data.

### Reusable Business Capabilities

The backend follows a consistent execution path:

```text
API / Kafka / Scheduler
          │
          ▼
   Business Services
          │
          ▼
    Data Access Layer
          │
          ▼
      PostgreSQL
```

The same business capabilities can therefore support event consumers, REST APIs, scheduled processing, and future AI tools.

### Failure-Aware Verification

Phase 1 verifies both successful processing and important failure scenarios, including:

- Invalid event payloads
- Duplicate events
- Deterministic business-rule failures
- DLQ publication failures
- Inventory conflicts
- Empty analytical periods
- Feature entitlement inconsistencies
- Historical subscription changes
- Late analytical recomputation

The resulting Prototype validates not only the happy path, but also the recovery and isolation behaviour expected from an event-driven data platform.

---

## Technology Stack

| Area | Technologies |
| --- | --- |
| **Backend** | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| **Event Streaming** | Apache Kafka, aiokafka |
| **Data & Analytics** | PostgreSQL, APScheduler |
| **Caching** | Redis |
| **Search & Logging** | OpenSearch |
| **Vector Storage** | Qdrant |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS |
| **Server State** | TanStack Query |
| **Visualization** | Apache ECharts |
| **Infrastructure** | Docker, Docker Compose |
| **Tooling & Testing** | uv, npm, pytest, pytest-asyncio, ESLint |
| **AI / Agents** | LangGraph *(planned for Phase 2)* |
| **Embeddings** | BGE models *(planned for Phase 2)* |

PostgreSQL serves as the authoritative store for event history, operational state, reference data, derived metrics, and materialized analytical summaries.

Kafka provides the event-streaming backbone, while FastAPI and React expose the resulting business intelligence through typed APIs and dashboards.

Redis, OpenSearch, Qdrant, LangGraph, and embedding infrastructure support capabilities introduced progressively in later phases.

---

## Repository Structure

```text
customer-intelligence-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── config/           # Application configuration
│   │   ├── data_access/      # Persistence and database queries
│   │   ├── generators/       # Synthetic event generators
│   │   ├── kafka/            # Kafka producer/consumer infrastructure
│   │   ├── models/           # SQLAlchemy models
│   │   ├── reference_data/   # Plans, features, and mappings
│   │   ├── scheduler/        # Scheduled analytics
│   │   ├── schemas/          # Pydantic contracts
│   │   ├── services/         # Business Service Layer
│   │   └── main.py           # FastAPI entry point
│   │
│   ├── migrations/           # Alembic migrations
│   ├── scripts/              # Generators, consumers, initialization, jobs
│   └── tests/                # Backend tests
│
├── frontend/
│   └── src/
│       ├── api/              # Typed API client
│       ├── components/       # Shared UI components
│       ├── features/         # Domain-focused features
│       ├── hooks/            # TanStack Query hooks
│       ├── pages/            # Application pages
│       └── types/            # TypeScript API/domain types
│
├── docs/                     # Product and architecture documentation
├── docker-compose.yml        # Local infrastructure
├── Implementation_Plan.md    # Implementation roadmap and status
├── specs.md                  # Design index and implementation guidance
├── AGENTS.md                 # Coding-agent instructions
└── README.md
```

Detailed architectural decisions are documented under [`docs/`](./docs/), while [`Implementation_Plan.md`](./Implementation_Plan.md) tracks implementation progress across project phases.

---

## Getting Started

The Phase 1 Prototype runs locally using Docker for infrastructure, `uv` for the Python backend, and npm for the React frontend.

### Prerequisites

- Docker and Docker Compose
- Python
- [`uv`](https://docs.astral.sh/uv/)
- Node.js and npm
- Git

### 1. Clone and Configure

```bash
git clone <repository-url>
cd customer-intelligence-platform
```

Review the provided environment examples and configure local values as required:

```text
backend/.env.example
frontend/.env.example
```

Docker Compose uses the root environment configuration. Do not commit local `.env` files or credentials.

### 2. Start Infrastructure

```bash
docker compose up -d
docker compose ps
```

This starts the local PostgreSQL, Kafka, Redis, Qdrant, OpenSearch, and supporting services.

### 3. Initialize the Backend

```bash
cd backend
uv sync

uv run alembic upgrade head
uv run python -m scripts.init_reference_data
uv run python -m scripts.init_segments
```

### 4. Generate Business Activity

For each domain, run the consumer and generator in separate terminals.

| Domain | Consumer | Generator |
| --- | --- | --- |
| Merchant | `uv run python -m scripts.run_merchant_event_consumer` | `uv run python -m scripts.run_merchant_generator` |
| Product | `uv run python -m scripts.run_product_event_consumer` | `uv run python -m scripts.run_product_generator` |
| Shopper | `uv run python -m scripts.run_shopper_event_consumer` | `uv run python -m scripts.run_shopper_generator` |
| Campaign | `uv run python -m scripts.run_campaign_event_consumer` | `uv run python -m scripts.run_campaign_generator` |

For coherent synthetic data, generate the domains in dependency order:

`Merchant → Product → Shopper → Campaign`

Allow each consumer to process its generated events before moving to dependent activity.

### 5. Generate Analytics

Analytics run automatically through APScheduler while FastAPI is running. They can also be triggered manually:

```bash
uv run python -m scripts.run_analytics_job
```

### 6. Start FastAPI

From `backend/`:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- API: `http://localhost:8000`
- OpenAPI / Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

> APScheduler runs inside the Phase 1 FastAPI process. Do not run the Dockerized backend on port `8000` simultaneously with local Uvicorn.

### 7. Start the Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server typically runs at:

`http://localhost:5173`

The frontend connects to FastAPI through `VITE_API_BASE_URL`.

Once synthetic activity and analytics are available, the dashboard exposes platform KPIs and trends, feature adoption, merchant performance, campaign analytics, shoppers, and orders.

---

## Testing

### Backend

Run the complete backend suite from `backend/`:

```bash
uv run pytest -q -rs
```

The suite covers generators, event contracts, Kafka processing, business services, data access, DLQ behaviour, operational persistence, analytics, scheduling, and FastAPI endpoints.

Focused tests can also be run during development:

```bash
uv run pytest tests/services/test_analytics.py
uv run pytest tests/generators/test_shopper.py
uv run pytest tests/api/
```

### Frontend

From `frontend/`:

```bash
npm run lint
npm run build
```

These commands verify linting, TypeScript compilation, and the production Vite build.

### End-to-End Verification

Phase 1 was also validated through the complete running pipeline:

```text
Generators
    ↓
Kafka
    ↓
Consumers
    ↓
PostgreSQL
    ↓
Scheduled Analytics
    ↓
FastAPI
    ↓
TanStack Query
    ↓
React Dashboard
```

### Clean Regression Runs

Synthetic E2E sessions intentionally leave Kafka and database state behind. Before a clean integration/regression run, reset the local infrastructure:

```bash
docker compose down -v
docker compose up -d

cd backend
uv run alembic upgrade head
uv run python -m scripts.init_reference_data
uv run pytest -q -rs
```

This keeps automated regression testing isolated from state accumulated during manual E2E demonstrations.

---

## Roadmap

The platform is being developed incrementally, with each phase building directly on the previous architecture.

### Phase 1 — End-to-End Prototype ✅

**Complete**

Phase 1 established and validated the complete platform foundation:

- Event generation and Kafka-based ingestion
- Deterministic operational business processing
- PostgreSQL event and operational data
- Reproducible scheduled analytics
- FastAPI operational and analytics APIs
- React platform and merchant dashboards
- End-to-end event-to-dashboard verification

### Phase 2 — Minimum Viable Product

Phase 2 expands the Prototype into the first usable Customer Intelligence Platform for internal teams.

Major areas include:

- Merchant and Shopper Profiles
- Customer and Merchant Journeys
- Shopper segmentation and Merchant Health
- Richer business intelligence and dashboards
- AI Knowledge Pipeline and retrieval-oriented summaries
- Embeddings and Qdrant semantic storage
- AI Gateway and controlled business tools
- Exact, semantic, and hybrid retrieval
- LangGraph investigation workflows
- Evidence-grounded responses and investigation persistence

Detailed Phase 2 milestones will be defined before MVP implementation begins.

### Phase 3 — Version 1

Version 1 will expand the investigation and intelligence experience with capabilities such as:

- Enhanced multi-step investigations
- Investigation history and improved evidence validation
- Campaign, churn, product, and feature recommendations
- Enhanced segmentation
- Merchant-facing dashboards and AI assistant
- Performance, observability, and UX improvements

See [`Implementation_Plan.md`](./Implementation_Plan.md) for the full implementation roadmap and current project status.

---

## Documentation

Detailed product and engineering decisions are maintained under [`docs/`](./docs/).

| Document | Focus |
| --- | --- |
| [`00_Project_Design_Journal.md`](./docs/00_Project_Design_Journal.md) | Design discussions and decision context |
| [`01_Product_Foundation.md`](./docs/01_Product_Foundation.md) | Product vision and platform principles |
| [`02_Product_Requirements.md`](./docs/02_Product_Requirements.md) | Requirements and product roadmap |
| [`03_User_Workflows.md`](./docs/03_User_Workflows.md) | User goals and workflows |
| [`04_Product_Workflows.md`](./docs/04_Product_Workflows.md) | End-to-end product behaviour |
| [`05_System_Architecture.md`](./docs/05_System_Architecture.md) | System components and interactions |
| [`06_Data_Architecture.md`](./docs/06_Data_Architecture.md) | Operational, analytical, and retrieval data |
| [`07_AI_Architecture.md`](./docs/07_AI_Architecture.md) | AI, retrieval, tools, and investigation design |
| [`08_API_Design.md`](./docs/08_API_Design.md) | REST API design |
| [`09_Technology_Decisions.md`](./docs/09_Technology_Decisions.md) | Technology selections and rationale |
| [`10_Backend_Design.md`](./docs/10_Backend_Design.md) | Backend architecture and processing |
| [`11_Database_Design.md`](./docs/11_Database_Design.md) | PostgreSQL schema and analytical views |
| [`12_Frontend_Design.md`](./docs/12_Frontend_Design.md) | Frontend architecture and UX |

Additional project guidance:

- [`Implementation_Plan.md`](./Implementation_Plan.md) — implementation phases, milestones, and status
- [`specs.md`](./specs.md) — design-document index and task-based implementation guide
- [`AGENTS.md`](./AGENTS.md) — repository instructions for coding agents

The numbered design documents remain the architectural source of truth as implementation progresses into the MVP.