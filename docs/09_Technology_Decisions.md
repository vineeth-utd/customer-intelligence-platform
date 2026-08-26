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