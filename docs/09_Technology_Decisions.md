# 1. Technology Selection Principles

The Technology Decisions document defines the technologies chosen to implement the Customer Intelligence Platform and explains the reasoning behind each decision.

The previous design documents intentionally focused on business problems, user workflows, system architecture, data architecture, AI architecture, and API design without committing to specific technologies. This ensured that the architecture remained driven by business requirements rather than implementation preferences.

With the overall architecture now established, this document maps each architectural component to an appropriate technology stack while preserving the principles that guided the project's design.

The selected technologies should support the platform's architecture while remaining practical, maintainable, and appropriate for a production-inspired portfolio project.

Technology decisions should satisfy the following principles:

* Every technology should solve a clearly identified architectural or business problem.
* Simplicity should be preferred over unnecessary complexity.
* Technologies should integrate naturally with the overall system architecture.
* The stack should support incremental development from prototype to Version 1.
* Components should be selected based on their suitability for the problem rather than popularity or industry trends.
* The technology stack should provide opportunities to demonstrate strong Software Engineering, Data Engineering, and AI Engineering practices.

Throughout this document, every technology selection should answer one fundamental question:

> **Why is this technology the right choice for this part of the system?**

Rather than documenting every available option, this document focuses on the technologies that best support the platform's architecture and the tradeoffs behind those decisions.

Maintaining this principle ensures that every component of the technology stack has a clear purpose and contributes meaningfully to the overall design of the Customer Intelligence Platform.

---

# 2. Backend & API Layer

The Backend & API Layer is responsible for exposing the platform's business capabilities, processing business requests, coordinating AI-assisted investigations, and communicating with the underlying data platform.

The selected technologies should provide a simple, maintainable, and scalable foundation while supporting the platform's Software Engineering, Data Engineering, and AI Engineering requirements.

---

## Programming Language

**Selected Technology:** Python

Python is selected as the primary backend programming language for the Customer Intelligence Platform.

The platform combines backend APIs, business services, data processing workflows, and AI-powered investigations within a single application. Python provides a mature ecosystem across all of these domains, allowing the platform to be implemented using one consistent technology stack.

Compared to alternatives such as Go, Java, or Clojure, Python offers the strongest ecosystem for AI integration while also providing excellent support for backend development and data engineering.

Using a single programming language simplifies development, reduces operational complexity, and enables all major platform components to share the same ecosystem and tooling.

---

## API Style

**Selected Technology:** REST APIs

The platform exposes its business capabilities through REST APIs.

REST provides a simple, well-understood communication model that naturally supports the platform's business resources such as merchants, shoppers, campaigns, analytics, and investigations.

REST APIs are also well suited for frontend applications, AI integrations, and future external clients while keeping the platform architecture straightforward and easy to maintain.

---

## Backend Framework

**Selected Technology:** FastAPI

FastAPI is selected as the backend framework for implementing the platform's REST APIs.

FastAPI provides native asynchronous request handling, automatic request validation, OpenAPI specification generation, interactive API documentation, and excellent performance. These capabilities align well with the platform's architecture, which coordinates multiple database operations, AI services, and external integrations during business investigations.

Its modern Python ecosystem and developer experience also support rapid development while maintaining clean and maintainable application code.

---

## Application Architecture

**Selected Architecture:** Layered Architecture

The backend follows a layered architecture that separates request handling, business logic, and infrastructure concerns.

The logical architecture consists of:

```text
API Layer
      │
      ▼
Business Service Layer
      │
      ▼
Infrastructure Layer
```

Each layer has a clearly defined responsibility.

The API Layer receives requests, performs request validation, authentication, and authorization, and delegates business operations to the appropriate services.

The Business Service Layer contains the platform's business logic and orchestrates workflows across multiple business domains.

The Infrastructure Layer communicates with external systems such as databases, caches, message queues, AI services, vector databases, and other third-party integrations.

This separation promotes code reuse, improves maintainability, and ensures that business logic remains independent of infrastructure and communication concerns.

---

## Middleware

The backend uses middleware to enforce cross-cutting concerns consistently across all APIs.

Middleware responsibilities include:

* Authentication
* Authorization
* CORS handling
* Request logging
* Global exception handling

Request validation is performed automatically by FastAPI using Pydantic models before requests reach the business service layer.

---

## Dependency Management

**Selected Technology:** uv

The project uses **uv** for Python dependency and environment management.

uv provides fast dependency installation, virtual environment management, and reproducible project environments through a single tool while remaining fully compatible with the broader Python ecosystem.

---

## Testing Framework

**Selected Technology:** pytest

The backend uses **pytest** as the primary testing framework.

pytest provides a simple and flexible approach for writing unit tests, integration tests, and API tests while integrating naturally with the selected Python technology stack.

---

# 3. Data Platform

The Data Platform is responsible for ingesting, processing, storing, and transforming business data generated by merchants and shoppers into reliable data products that support analytics, dashboards, and AI-assisted investigations.

The selected technologies should support an event-driven architecture while maintaining data consistency, scalability, and clear separation between operational business data, derived analytical data, and AI-oriented knowledge.

---

## Primary Database

**Selected Technology:** PostgreSQL

PostgreSQL is selected as the primary database for the Customer Intelligence Platform.

The platform manages highly related business entities such as merchants, shoppers, products, orders, campaigns, investigations, and business events. These entities require strong relational modeling and efficient querying across multiple domains to support dashboards, analytics, and AI investigations.

PostgreSQL provides excellent support for relational data modeling, transactional consistency, analytical SQL queries, indexing, partitioning, and materialized views, making it well suited for both operational data storage and business intelligence workloads.

Alternative technologies such as MongoDB, CockroachDB, or columnar databases were evaluated but are not required for the current architecture since they do not solve a business problem that PostgreSQL cannot address effectively.

---

## Event Streaming Platform

**Selected Technology:** Apache Kafka

The platform follows an event-driven architecture where merchant activities and shopper interactions continuously generate business events.

Apache Kafka is selected as the event streaming platform because it provides durable event storage, consumer groups, partitioning, replay capability, fault tolerance, and reliable event processing.

Kafka also enables multiple consumers to process the same event stream independently, allowing the platform to evolve without changing upstream producers.

---

## Event Generation

Business events are generated through dedicated event generators that simulate realistic merchant and shopper behaviour.

Rather than generating random records, the event generators simulate realistic business scenarios such as:

* Merchant onboarding
* Subscription lifecycle changes
* Feature adoption
* Campaign creation
* Shopper browsing behaviour
* Wishlist activity
* Save for Later usage
* Cart interactions
* Purchases
* Campaign engagement

This approach produces realistic business data that supports meaningful analytics, dashboards, customer journeys, and AI-assisted investigations.

---

### Future Enhancement

Future versions of the platform may incorporate LLM-assisted synthetic data generation to improve the realism and diversity of generated business scenarios.

Rather than generating every business event directly, the language model would generate realistic merchant and shopper behaviour templates that capture business patterns such as merchant growth, feature adoption, shopper journeys, campaign interactions, and churn scenarios.

These behaviour templates would then be consumed by the deterministic event generators to produce large volumes of realistic business events while maintaining consistency, scalability, and low generation cost.

This approach combines AI-generated behavioural realism with deterministic event generation, allowing the platform to simulate complex business scenarios without requiring the language model to generate every individual event.

---

## Event Processing Pipeline

Incoming events are processed through a structured ingestion pipeline before becoming part of the platform's operational business data.

The high-level processing flow is illustrated below.

```text
Event Generator
        │
        ▼
Kafka
        │
        ▼
Consumer
        │
        ▼
Validation
        │
        ▼
Normalization
        │
        ▼
Optional Enrichment
        │
        ▼
Raw Event Storage
        │
        ▼
Operational Business Data
```

The processing pipeline performs:

* Schema validation
* Required field validation
* Data normalization
* Optional data enrichment
* Idempotent writes to operational business data

Kafka offsets are committed only after successful processing, allowing failed messages to be safely retried without data loss.

---

## Incremental Derived Data Generation

Profiles, customer journeys, business metrics, and other derived business data products are generated incrementally rather than after every incoming event.

The platform maintains processing state for each business entity type, allowing downstream processing jobs to determine whether new events have arrived since the previous processing cycle.

Examples include:

* Merchant
* Shopper
* Campaign

Each processing state maintains information such as:

* Last Event At
* Last Profile Generated At
* Last Knowledge Generated At

At scheduled intervals, processing jobs compare these timestamps to determine whether new business activity requires profile or knowledge regeneration.

This incremental approach avoids unnecessary recomputation while ensuring that derived business data remains up to date.

---

## AI Knowledge Pipeline

The AI Knowledge Pipeline transforms structured business information into retrieval-oriented knowledge for semantic search.

Rather than sending raw business events directly to the language model, the platform first generates business profiles, journeys, metrics, and analytics using deterministic business logic.

The pipeline then follows the flow below.

```text
Derived Business Data
        │
        ▼
Summary Builder
        │
        ▼
LLM
        │
        ▼
Natural Language Summary
        │
        ▼
Embedding Generation
        │
        ▼
Vector Database
```

The Summary Builder prepares structured business facts that are provided to the language model.

The language model generates concise business summaries that capture important trends, behavioural patterns, and business observations suitable for semantic retrieval.

This approach minimizes AI cost, preserves deterministic business logic, and produces high-quality knowledge optimized for retrieval.

---

## Caching

**Selected Technology:** Redis

Redis is selected as the platform's caching technology.

Caching is applied selectively to frequently accessed or computationally expensive data such as dashboard aggregates, merchant profile summaries, and repeated investigation context.

The platform first attempts to retrieve cached information before accessing the primary database. Cache entries are refreshed whenever underlying business data changes.

Caching remains an optimization layer and never replaces PostgreSQL as the platform's source of truth.

---

## Database Migrations

**Selected Technology:** Alembic

Alembic is selected for managing PostgreSQL database schema migrations.

All schema changes are version-controlled through incremental migration scripts, ensuring that database evolution remains consistent, reproducible, and traceable throughout the project's lifecycle.

---

## Data Platform Summary

| Component | Selected Technology |
|-----------|---------------------|
| Primary Database | PostgreSQL |
| Event Streaming | Apache Kafka |
| Event Generation | Synthetic Behavioural Event Generators |
| Caching | Redis |
| AI Knowledge Storage | Vector Database |
| Database Migrations | Alembic |

---

# 4. AI Platform

The AI Platform enables the Customer Intelligence Platform to investigate business questions, generate business knowledge, and provide grounded, explainable insights while maintaining strict separation between AI reasoning and business logic.

The selected technologies should support structured investigations, controlled tool execution, semantic retrieval, and incremental knowledge generation while keeping the platform provider-agnostic and easy to extend.

---

## Large Language Model

**Development Provider:** Groq

**Production Provider:** OpenAI

The platform is designed to remain independent of any single LLM provider through the AI Gateway.

Groq is selected as the default development provider because it offers fast inference, supports modern open-weight models, provides native tool calling, and enables cost-effective development.

The architecture also supports alternative providers such as OpenAI without requiring changes to the investigation workflow or business services.

---

## Agent Framework

**Selected Technology:** LangGraph

The Investigation Agent is implemented using LangGraph.

The platform follows a structured investigation workflow consisting of multiple stages including understanding user intent, planning investigations, gathering evidence, evaluating findings, and generating grounded responses.

LangGraph provides an explicit state-based workflow that closely matches the platform's investigation architecture while allowing the investigation process to remain transparent and easily extensible.

Rather than relying on multiple collaborating agents, Version 1 uses a single Investigation Agent with a well-defined investigation workflow.

---

## Tool Calling

**Selected Technology:** Native Provider Tool Calling

The Investigation Agent interacts with the platform using native tool calling supported by the selected LLM provider.

Rather than generating database queries directly, the language model selects the appropriate business tool together with the required parameters.

The AI Gateway validates every tool request before invoking the corresponding backend capability.

This approach keeps business logic within the platform while allowing the language model to focus on investigation and reasoning.

---

## AI Gateway

**Selected Implementation:** Custom AI Gateway

The AI Gateway acts as the controlled entry point between the Investigation Agent and the rest of the platform.

It is responsible for enforcing platform policies, executing business tools, protecting sensitive information, and ensuring that every AI response remains grounded in authoritative business data.

The AI Gateway is responsible for:

* User request validation
* Guardrails and policy enforcement
* Authentication and authorization
* Tool registry and tool call validation
* Tool execution
* Tool response processing
* Data minimization
* Sensitive data masking
* Investigation context construction
* Prompt construction
* Response grounding and validation
* Audit logging

Separating these responsibilities from the language model ensures that the AI remains secure, explainable, and consistent with the platform's business rules.

---

## AI Agents

The AI Platform consists of two independent AI agents.

### Investigation Agent

The Investigation Agent interacts directly with users.

Its responsibilities include:

* Understanding business questions
* Planning investigations
* Selecting business tools
* Gathering evidence
* Evaluating investigation completeness
* Producing grounded explanations
* Recommending business actions

### Knowledge Generation Agent

The Knowledge Generation Agent operates as a background process.

Its responsibilities include:

* Generating business summaries from derived business data
* Producing retrieval-oriented knowledge
* Preparing content for semantic search
* Keeping the AI Knowledge Layer up to date

The two agents operate independently and solve different business problems without introducing unnecessary multi-agent orchestration.

---

## Embedding Model

**Selected Technology:** BGE Embeddings

The platform uses the BGE embedding model to convert business summaries into vector representations suitable for semantic retrieval.

BGE provides high-quality semantic embeddings, integrates well with Python, and avoids unnecessary dependency on proprietary embedding APIs while delivering strong retrieval performance.

---

## Vector Database

**Selected Technology:** Qdrant

Qdrant is selected as the platform's vector database.

It provides efficient semantic similarity search, metadata filtering, incremental updates, and production-ready vector indexing while remaining fully open source.

The platform stores both embeddings and associated business metadata, allowing semantic retrieval to be combined with business-specific filtering during AI investigations.

---

## AI Knowledge Pipeline

The platform generates AI knowledge incrementally from derived business data rather than directly from raw business events.

The high-level pipeline is illustrated below.

```text
Derived Business Data
        │
        ▼
Summary Builder
        │
        ▼
LLM
        │
        ▼
Natural Language Summary
        │
        ▼
Embedding Generation
        │
        ▼
Qdrant
```

The Summary Builder prepares structured business facts that are provided to the language model.

The language model converts those facts into concise business summaries suitable for semantic retrieval.

The resulting summaries are embedded and stored within Qdrant together with their associated business metadata.

This approach keeps business logic deterministic while using AI only to generate business understanding suitable for semantic search.

---

## AI Knowledge

The AI Knowledge Layer stores business understanding rather than operational business data.

Examples of AI knowledge include:

* Merchant summaries
* Merchant journey summaries
* Shopper behaviour summaries
* Shopper journey summaries
* Product summaries
* Category summaries
* Campaign summaries
* Feature adoption summaries
* Business summaries
* Investigation summaries

Different knowledge types follow different refresh strategies depending on the nature of the business information.

Current business understanding is refreshed periodically, while historical business knowledge such as investigation summaries and business summaries is preserved to support future semantic retrieval and business investigations.

---

# 5. Frontend

The Frontend provides the user interface through which internal teams and merchants interact with the Customer Intelligence Platform.

It is responsible for presenting business dashboards, analytics, customer journeys, AI-assisted investigations, and business insights while providing a responsive and intuitive user experience.

The selected technologies should support modern web development, rich data visualization, strong type safety, and efficient interaction with the platform's backend services.

---

## Frontend Framework

**Selected Technology:** React.js

React is selected as the frontend framework for the Customer Intelligence Platform.

The platform primarily consists of dashboard views, analytical reports, AI-assisted investigations, business tables, charts, and timeline-based visualizations. React's component-based architecture naturally supports these user interfaces while enabling reusable and maintainable application development.

Its mature ecosystem, strong community support, and seamless integration with the selected backend technologies make it well suited for the platform.

---

## Frontend Language

**Selected Technology:** TypeScript

TypeScript is selected as the frontend programming language.

The frontend communicates extensively with backend APIs returning complex business entities such as merchants, shoppers, campaigns, investigations, analytics, and business metrics.

Strong typing improves development productivity by detecting integration errors during development rather than at runtime while making the frontend easier to maintain as the platform evolves.

---

## Styling

**Selected Technology:** Tailwind CSS

Tailwind CSS is selected as the primary styling framework.

Its utility-first approach enables rapid UI development while maintaining consistent styling across dashboards, analytical pages, AI interfaces, and administrative views.

The framework also supports responsive design and simplifies long-term UI maintenance.

---

## Data Visualization

**Selected Technology:** Apache ECharts

Apache ECharts is selected as the primary charting library.

The Customer Intelligence Platform relies heavily on business dashboards and analytical visualizations including trend analysis, revenue metrics, conversion funnels, customer journeys, feature adoption, campaign performance, and business growth.

Apache ECharts provides a comprehensive set of interactive visualization capabilities while remaining open source and highly extensible for future analytical requirements.

---

## Server State Management

**Selected Technology:** TanStack Query

The frontend uses TanStack Query to manage server-side state.

Rather than repeatedly requesting the same business information from the backend, TanStack Query manages data fetching, caching, background refresh, request deduplication, and cache invalidation.

This reduces unnecessary API calls while providing a responsive user experience across dashboards, investigations, and analytical views.

---

## Local State Management

**Selected Technology:** React State

Local component state is managed using React's built-in state management capabilities.

Component-specific interactions such as dialog visibility, filters, form inputs, and UI behaviour remain localized to individual components without introducing unnecessary global state management complexity.

---

## Client-side Routing

**Selected Technology:** React Router

React Router is selected for client-side navigation.

It enables seamless navigation between dashboards, merchant views, shopper analytics, investigations, and administrative pages while maintaining a single-page application experience.

---

## Frontend Summary

| Component | Selected Technology |
|-----------|---------------------|
| Frontend Framework | React.js |
| Frontend Language | TypeScript |
| Styling | Tailwind CSS |
| Data Visualization | Apache ECharts |
| Server State Management | TanStack Query |
| Local State Management | React State |
| Client-side Routing | React Router |

---

# 6. Infrastructure & Deployment

The Customer Intelligence Platform is designed to run consistently across different development environments while remaining easy to deploy, test, and maintain.

The selected infrastructure technologies focus on simplifying local development, supporting automated validation, and providing a production-inspired deployment workflow without introducing unnecessary operational complexity.

---

## Containerization

**Selected Technology:** Docker

Each major platform component is packaged as an independent Docker container.

Containerization provides a consistent runtime environment by packaging the application together with its required runtime, dependencies, and configuration.

This eliminates environment-specific issues while ensuring that the platform behaves consistently across different development machines.

The primary platform components include:

* Frontend
* Backend
* PostgreSQL
* Apache Kafka
* Redis
* Qdrant
* OpenSearch

---

## Local Environment Orchestration

**Selected Technology:** Docker Compose

Docker Compose is used to orchestrate the complete local development environment.

It starts all platform services, configures networking between containers, manages service dependencies, and provides a reproducible local development environment through a single command.

This allows the complete Customer Intelligence Platform to be started without manually installing or configuring individual infrastructure components.

---

## Scheduled Processing

**Selected Technology:** APScheduler

The platform uses APScheduler to execute periodic background jobs.

Examples include:

* Profile generation
* Business metric generation
* AI Knowledge Pipeline execution

These scheduled jobs operate independently of the event ingestion pipeline and process only the incremental business data identified through the platform's processing state.

---

## Observability

**Selected Technology:** OpenSearch

OpenSearch is used for centralized application logging.

The platform records structured logs across backend services, event processing, AI investigations, and infrastructure components to simplify debugging, troubleshooting, and operational visibility.

Examples include:

* API requests
* Kafka consumer activity
* Investigation execution
* Tool invocation
* Processing failures
* Dead letter events

OpenSearch Dashboards provides searchable log visualization for development and operational analysis.

Future platform versions may introduce Prometheus and Grafana for infrastructure metrics, monitoring, and alerting.

---

## Continuous Integration

**Selected Technology:** GitHub Actions

GitHub Actions is used to automate Continuous Integration workflows.

Each code change is automatically validated by executing development workflows such as:

* Dependency installation
* Static analysis
* Automated testing
* Docker image builds

This helps ensure that code quality is continuously validated before deployment.

---

## Frontend Deployment

**Selected Technology:** Vercel

The frontend is deployed using Vercel.

Vercel integrates directly with GitHub and automatically builds and deploys the frontend whenever new changes are pushed to the repository.

This provides a simple deployment workflow while allowing rapid iteration during development.

Backend deployment remains outside the scope of the current implementation and may be introduced as part of future production deployment.

---

## Infrastructure Summary

| Component | Selected Technology |
|-----------|---------------------|
| Containerization | Docker |
| Local Environment | Docker Compose |
| Scheduled Processing | APScheduler |
| Logging & Observability | OpenSearch |
| Continuous Integration | GitHub Actions |
| Frontend Deployment | Vercel |