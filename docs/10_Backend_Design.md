# 1. Backend Design Goals

The Backend Design defines how the Customer Intelligence Platform will be implemented, translating the previously established product, architecture, data, AI, and API designs into a clean, maintainable backend application.

Rather than introducing new architectural concepts, this document describes how the backend application is organized, how responsibilities are separated across different layers, and how the various platform components collaborate to implement the business capabilities defined in the earlier design documents.

The backend should remain aligned with the architecture established throughout the project while providing a practical foundation for implementation.

Specifically, the backend should:

* Implement business capabilities through a well-defined layered architecture.
* Keep business logic independent of APIs, databases, AI providers, and infrastructure technologies.
* Reuse business services across REST APIs, AI investigations, background jobs, and event processing.
* Maintain a clear separation between business logic and data access.
* Support asynchronous processing for event ingestion and scheduled background tasks.
* Integrate AI capabilities without allowing AI components to bypass business rules or access data directly.
* Remain modular, testable, and easy to extend as new business capabilities are introduced.

Throughout this document, every implementation decision should answer one fundamental question:

> **Where does this responsibility belong within the backend application?**

Maintaining clear ownership of responsibilities keeps the backend easy to understand, reduces coupling between components, and ensures that new features can be implemented without affecting unrelated parts of the system.

---

# 2. Backend Architecture

The backend follows a layered architecture that separates request handling, business logic, data access, and infrastructure concerns into well-defined implementation layers.

Each layer has a single responsibility and communicates only with the layers directly beneath it. This separation keeps the backend modular, easier to test, and easier to maintain while ensuring that business logic remains independent of implementation details such as databases, messaging systems, or AI providers.

The backend serves as the central coordinator of the platform. Whether a request originates from a REST API, an AI investigation, a Kafka consumer, or a scheduled background job, the same business services are reused to ensure consistent behaviour throughout the platform.

The high-level backend architecture is illustrated below.

```text
                    Clients
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     REST APIs     AI Gateway    Background Jobs
                       │
                       ▼
                 Business Services
                  │             │
                  ▼             ▼
          Data Access Layer  Infrastructure Layer
                  │             │
                  ▼             ▼
            PostgreSQL   Kafka • Redis • Qdrant • LLM
```

## 2.1 API Layer

The API Layer provides the entry point for client applications to interact with the platform.

Its responsibilities include:

* Receiving HTTP requests.
* Validating request payloads.
* Authenticating and authorizing users.
* Delegating requests to the appropriate business services.
* Returning consistent API responses.

The API Layer remains intentionally thin and does not contain business logic.

---

## 2.2 Business Service Layer

The Business Service Layer implements the platform's business capabilities.

It coordinates workflows across multiple business domains while enforcing business rules and ensuring consistent behaviour regardless of how a request enters the system.

Its responsibilities include:

* Implementing business logic.
* Coordinating workflows across multiple services.
* Validating business rules.
* Managing transactions where required.
* Invoking the Data Access Layer and Infrastructure Layer.
* Providing reusable business capabilities for APIs, AI investigations, and background processing.

This layer forms the core of the backend application.

---

## 2.3 Data Access Layer

The Data Access Layer encapsulates all interactions with the platform's primary data stores.

Rather than allowing business services to communicate directly with databases, this layer provides a consistent abstraction for retrieving and persisting business data.

Its responsibilities include:

* Reading and writing business data.
* Encapsulating database queries.
* Managing database transactions.
* Mapping database models to application objects.
* Isolating persistence logic from business logic.

Keeping data access separate from business services improves maintainability and allows persistence implementations to evolve independently.

---

## 2.4 Infrastructure Layer

The Infrastructure Layer integrates the backend with external systems and supporting platform services.

Unlike the Business Service Layer, which focuses on business behaviour, the Infrastructure Layer handles communication with technologies that support the platform's operation.

Examples include:

* PostgreSQL
* Apache Kafka
* Redis
* Qdrant
* LLM providers
* External APIs

This separation allows infrastructure technologies to be replaced or modified without affecting the platform's business logic.

---

## 2.5 Request Flow

Most backend requests follow the same execution pattern regardless of where they originate.

```text
Client Request
      │
      ▼
 API Layer
      │
      ▼
Business Service Layer
      │
      ├──────────────► Infrastructure Layer
      │
      ▼
Data Access Layer
      │
      ▼
PostgreSQL
```

Background jobs, Kafka consumers, and AI investigations follow the same flow by invoking the Business Service Layer directly instead of entering through the API Layer. This ensures that business rules are implemented only once and reused consistently throughout the platform.

---

## 2.6 Why This Structure Matters

Organizing the backend into well-defined implementation layers provides a clear separation of responsibilities while keeping the application modular and maintainable.

This architecture promotes code reuse by ensuring that business logic is implemented once within the Business Service Layer and shared across REST APIs, AI investigations, event processing, and scheduled background jobs. It also isolates database interactions and infrastructure concerns from core business logic, making the platform easier to test, extend, and evolve as new business capabilities are introduced.

---

# 3. Project Structure

The backend is organized using a layered project structure that mirrors the implementation architecture described in the previous section.

Each top-level package represents a specific implementation responsibility, making it easy to locate business logic, data access code, infrastructure integrations, and shared utilities. This organization promotes separation of concerns while keeping the project simple to navigate and maintain.

The proposed project structure is shown below.

```text
backend/
│
├── app/
│   ├── api/
│   ├── services/
│   ├── data_access/
│   ├── models/
│   ├── schemas/
│   ├── ai/
│   ├── kafka/
│   ├── scheduler/
│   ├── middleware/
│   ├── dependencies/
│   ├── db/
│   ├── config/
│   ├── utils/
│   └── main.py
│
├── tests/
├── migrations/
├── scripts/
├── docker/
├── docs/
├── pyproject.toml
└── README.md
```

## 3.1 Package Responsibilities

| Package | Responsibility |
|----------|----------------|
| `api/` | Defines REST API endpoints and request routing. |
| `services/` | Implements business logic and coordinates platform workflows. |
| `data_access/` | Encapsulates database interactions and persistence logic. |
| `models/` | Defines database models and entity mappings. |
| `schemas/` | Defines request and response models used for validation and serialization. |
| `ai/` | Implements the AI Gateway, investigation workflow, tool registry, and AI-related integrations. |
| `kafka/` | Contains Kafka producers, consumers, and event processing components. |
| `scheduler/` | Implements scheduled background jobs such as profile generation, business metrics, and AI knowledge generation. |
| `middleware/` | Implements cross-cutting request processing such as authentication, authorization, logging, and exception handling. |
| `dependencies/` | Defines shared application dependencies used by FastAPI endpoints. |
| `db/` | Manages database configuration, sessions, and migration support. |
| `config/` | Stores application configuration and environment-specific settings. |
| `utils/` | Provides reusable helper functions and common utilities shared across the backend. |
| `main.py` | Application entry point responsible for initializing and starting the FastAPI application. |

## 3.2 Business Domain Organization

Within the primary implementation layers, components are organized by business domain rather than by individual operations.

For example:

```text
services/
    merchant.py
    shopper.py
    campaign.py
    analytics.py
    investigation.py

data_access/
    merchant.py
    shopper.py
    campaign.py
    analytics.py
    investigation.py

api/
    merchant.py
    shopper.py
    campaign.py
    analytics.py
    investigation.py

models/
    merchant.py
    shopper.py
    campaign.py

schemas/
    merchant.py
    shopper.py
    campaign.py
```

Organizing components by business domain keeps related functionality easy to locate while preserving the layered architecture of the backend. As individual domains grow, they can later be refactored into dedicated subpackages without changing the overall project structure.

## 3.3 Why This Structure Matters

The project structure reflects the architectural principle of separating communication, business logic, data access, and infrastructure into distinct implementation layers.

This organization makes the codebase easier to understand, encourages reuse of business services across multiple entry points, and provides a scalable foundation that can grow naturally as additional business capabilities are introduced.

---

# 4. Backend Components

The backend consists of a small set of core components that work together to implement the platform's business capabilities. Each component has a clearly defined responsibility and collaborates with the others through well-defined interfaces.

---

## 4.1 API Layer

The API Layer exposes the platform's business capabilities through REST endpoints.

It is responsible for:

* Receiving client requests.
* Validating request payloads.
* Authenticating and authorizing users.
* Delegating requests to the appropriate business services.
* Returning standardized API responses.

The API Layer remains lightweight and contains no business logic.

---

## 4.2 Business Service Layer

The Business Service Layer contains the platform's core business logic.

It implements business workflows, coordinates interactions between multiple components, enforces business rules, and provides reusable capabilities that can be invoked by REST APIs, AI investigations, Kafka consumers, and scheduled background jobs.

This layer serves as the central implementation of the platform's business behaviour.

---

## 4.3 Data Access Layer

The Data Access Layer manages all interactions with the platform's primary data stores.

It encapsulates persistence logic, database queries, and transaction handling while exposing simple data access operations to the Business Service Layer.

This separation prevents business logic from becoming tightly coupled to database implementation details.

---

## 4.4 Domain Models

Domain Models represent the platform's core business entities and define how they are persisted within the database.

Examples include:

* Merchant
* Shopper
* Product
* Order
* Campaign
* Investigation

These models form the foundation of the platform's operational data.

---

## 4.5 API Schemas

API Schemas define the request and response models exchanged between clients and the backend.

They provide input validation, response serialization, and a stable contract between the backend and its consumers while remaining independent of the underlying database models.

---

## 4.6 AI Components

The AI components implement the backend functionality required to support AI-assisted investigations.

Responsibilities include:

* AI Gateway integration.
* Investigation orchestration.
* Tool registration and execution.
* Prompt construction.
* Context management.
* Response processing.

The AI components coordinate investigations while relying on the Business Service Layer to retrieve business data.

---

## 4.7 Event Processing

The Event Processing components consume merchant and shopper events from Kafka and transform them into operational business data.

Responsibilities include:

* Event consumption.
* Data validation.
* Data normalization.
* Event processing.
* Delegating business operations to the appropriate services.

This enables the platform to continuously ingest and process business events.

---

## 4.8 Background Processing

Background Processing components execute scheduled platform tasks independently of user requests.

Examples include:

* Profile generation.
* Business metric generation.
* AI knowledge generation.
* Scheduled maintenance tasks.

These jobs reuse the same business services used throughout the rest of the platform to ensure consistent behaviour.

---

## 4.9 Shared Infrastructure

Several shared components support the operation of the backend across all implementation layers.

These include:

* Middleware
* Dependency management
* Database configuration
* Application configuration
* Logging
* Utility functions

These components provide common functionality while allowing the core business logic to remain focused on implementing the platform's business capabilities.

---

## 4.10 Component Collaboration

Although each component has a distinct responsibility, they work together to implement the platform's end-to-end workflows.

Business requests enter through the API Layer or background processing components, are coordinated by the Business Service Layer, retrieve or persist data through the Data Access Layer, and leverage supporting infrastructure such as Kafka, Redis, PostgreSQL, and AI services when required.

This clear separation of responsibilities keeps the backend modular, maintainable, and easy to extend while ensuring that business logic is implemented only once and reused consistently throughout the platform.

---

# 5. Business Service Design

The Business Service Layer implements the platform's core business capabilities and serves as the central coordinator of backend operations.

Rather than interacting directly with databases or external infrastructure, clients, AI investigations, Kafka consumers, and scheduled background jobs delegate business operations to this layer. This ensures that business rules are implemented only once and reused consistently throughout the platform.

The Business Service Layer is responsible for orchestrating workflows across multiple business domains while remaining independent of APIs, persistence mechanisms, and infrastructure technologies.

---

## 5.1 Responsibilities

The Business Service Layer is responsible for:

* Implementing business logic.
* Enforcing business rules and validations.
* Coordinating workflows across multiple business domains.
* Retrieving and persisting business data through the Data Access Layer.
* Invoking infrastructure components when required.
* Managing transactions for business operations.
* Providing reusable business capabilities across the platform.

Business services should focus on business behaviour rather than technical implementation details.

---

## 5.2 Business Domain Services

Business logic is organized around the platform's core business domains.

Examples include:

* Merchant Service
* Shopper Service
* Campaign Service
* Analytics Service
* Investigation Service

Each service owns the business operations related to its domain while collaborating with other services when implementing cross-domain workflows.

This organization keeps the backend closely aligned with the business architecture defined throughout the project.

---

## 5.3 Service Collaboration

Many business operations require information from multiple business domains.

Rather than allowing one service to directly access another service's data, services collaborate through well-defined business operations while delegating persistence to the Data Access Layer.

For example, an AI investigation may require:

```text
Investigation Service
          │
          ├────────► Merchant Service
          │
          ├────────► Shopper Service
          │
          ├────────► Campaign Service
          │
          └────────► Analytics Service
```

Each service contributes its own business knowledge while remaining responsible only for its own domain.

---

## 5.4 Data Access

Business services never communicate directly with PostgreSQL.

Instead, all persistence operations are delegated to the Data Access Layer.

```text
Business Service
        │
        ▼
Data Access Layer
        │
        ▼
PostgreSQL
```

This separation isolates persistence logic from business logic and simplifies testing, maintenance, and future implementation changes.

---

## 5.5 Infrastructure Integration

Business services may interact with infrastructure components when required by business workflows.

Examples include:

* Publishing events to Kafka.
* Reading or updating Redis caches.
* Invoking the AI Gateway.
* Performing vector searches.
* Calling external platform integrations.

These interactions should remain focused on supporting business operations rather than embedding infrastructure-specific logic throughout the application.

---

## 5.6 Reusability Across the Platform

One of the primary goals of the Business Service Layer is to provide reusable business capabilities.

The same service implementations are used by:

* REST APIs
* AI investigations
* Kafka consumers
* Scheduled background jobs

This approach ensures that business behaviour remains consistent regardless of how a request enters the platform while avoiding duplicated business logic across different components.

---

## 5.7 Why This Design Matters

Centralizing business logic within the Business Service Layer creates a clear separation between business behaviour and technical implementation.

This design improves maintainability, encourages code reuse, simplifies testing, and allows the platform to evolve without duplicating business rules across APIs, AI workflows, background jobs, or event processing components.

---

# 6. Data Access Layer

The Data Access Layer is responsible for all interactions with the platform's primary data stores.

Rather than allowing business services to communicate directly with the database, this layer provides a consistent abstraction for retrieving, creating, updating, and deleting business data. It encapsulates persistence logic while allowing the Business Service Layer to focus entirely on implementing business behaviour.

This separation ensures that database implementation details remain isolated from the rest of the application.

---

## 6.1 Responsibilities

The Data Access Layer is responsible for:

* Retrieving business data from the database.
* Creating, updating, and deleting business entities.
* Encapsulating database queries.
* Managing database transactions.
* Mapping database models to application objects.
* Providing reusable data access operations for business services.

The Data Access Layer should not contain business logic or workflow orchestration.

---

## 6.2 Business Domain Organization

Data access components are organized according to the platform's business domains.

Examples include:

* Merchant Data Access
* Shopper Data Access
* Campaign Data Access
* Analytics Data Access
* Investigation Data Access

Each component is responsible for interacting with the underlying data for its respective business domain while exposing simple, reusable operations to the Business Service Layer.

---

## 6.3 Interaction with Business Services

Business services retrieve and persist data exclusively through the Data Access Layer.

```text
Business Service
        │
        ▼
Data Access Layer
        │
        ▼
PostgreSQL
```

This keeps business logic independent of persistence technologies and ensures that database operations remain centralized and consistent across the platform.

---

## 6.4 Query Responsibility

The Data Access Layer is responsible for implementing efficient database queries while hiding query complexity from the rest of the application.

Typical responsibilities include:

* Entity retrieval.
* Filtered searches.
* Pagination.
* Aggregation queries.
* Bulk operations.
* Relationship loading.

Business services request the required business data without needing to understand how it is retrieved.

---

## 6.5 Transaction Management

Business operations often involve multiple database updates that must succeed or fail as a single unit.

The Data Access Layer is responsible for participating in transaction management to ensure data consistency during these operations.

Transaction boundaries should remain aligned with business operations rather than individual database queries.

---

## 6.6 Why This Design Matters

Separating data access from business logic improves maintainability, readability, and testability.

Business services remain focused on implementing business behaviour, while the Data Access Layer provides a centralized location for persistence logic and database interactions. This separation also allows database implementations and query optimizations to evolve without affecting the rest of the backend.

---

# 7. Background Processing

Not all backend operations are initiated by user requests. The platform also performs continuous event-driven processing and scheduled background tasks to keep business data, analytics, and AI knowledge up to date.

Rather than implementing business logic directly, background processing components delegate work to the Business Service Layer, ensuring that business behaviour remains consistent regardless of how an operation is triggered.

---

## 7.1 Event Processing

Event processing is responsible for handling merchant and shopper events received from the event streaming platform.

Its responsibilities include:

* Receiving incoming events.
* Validating event structure.
* Determining the event type.
* Delegating processing to the appropriate business services based on the event type.
* Recording processing outcomes.
* Supporting retry mechanisms for failed events.

Event processing components remain lightweight and do not implement business logic themselves.

---

## 7.2 Scheduled Processing

Scheduled processing executes recurring backend tasks that maintain the platform's derived business data and AI knowledge.

Examples include:

* Merchant profile generation.
* Shopper profile generation.
* Business metric generation.
* AI knowledge generation.
* Periodic maintenance tasks.

Like event processing, scheduled jobs invoke business services rather than implementing business logic directly.

---

## 7.3 Processing Flow

Regardless of how work is initiated, background processing follows the same implementation flow.

```text
Kafka Event / Scheduler
          │
          ▼
 Background Worker
          │
          ▼
Business Service Layer
          │
          ▼
 Data Access Layer
          │
          ▼
     PostgreSQL
```

This ensures that business rules are implemented once and reused consistently across APIs, AI investigations, event processing, and scheduled jobs.

---

## 7.4 Design Principles

Background processing follows a small set of implementation principles:

* Workers remain lightweight and stateless.
* Business logic resides exclusively within the Business Service Layer.
* Existing business services are reused rather than duplicated.
* Processing failures should support retries and appropriate logging.
* Event-driven and scheduled workflows should behave consistently with user-initiated operations.

This approach keeps background processing simple while ensuring that all platform workflows follow the same business rules and implementation patterns.

---

# 8. AI Backend Integration

The backend integrates AI as an extension of the platform's existing business capabilities rather than as an independent system.

AI-assisted investigations follow the same implementation principles as the rest of the backend. Business logic remains within the Business Service Layer, while AI components focus on investigation, reasoning, and coordinating the retrieval of relevant business information.

This approach ensures that the platform remains fully functional even when AI capabilities are unavailable.

---

## 8.1 AI Request Flow

AI investigations are processed through the backend using the following flow.

```text
User Request
      │
      ▼
Investigation API
      │
      ▼
Investigation Service
      │
      ▼
AI Gateway
      │
      ▼
Investigation Agent
      │
      ▼
Business Tools
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

This flow ensures that every AI investigation remains grounded in the platform's existing business capabilities and source-of-truth data.

---

## 8.2 Business Tool Integration

Business tools provide the interface through which the Investigation Agent interacts with the backend.

Rather than accessing databases directly, each tool delegates work to the appropriate business service.

```text
Business Tool
      │
      ▼
Business Service
      │
      ▼
Data Access Layer
```

This design prevents duplication of business logic while ensuring that AI investigations follow the same business rules as every other backend workflow.

---

## 8.3 Investigation Context

The backend maintains the state of an active investigation throughout a conversation.

The investigation context may include:

* Investigation objective.
* Retrieved business entities.
* Supporting evidence.
* Tool execution history.
* Intermediate findings.

Maintaining this context enables users to ask follow-up questions without repeating the entire investigation.

---

## 8.4 Design Principles

AI integration follows a small set of implementation principles:

* AI components never access business data directly.
* Business services remain the single source of business logic.
* Business tools reuse existing backend capabilities.
* AI responses are grounded using platform data and supporting evidence.
* The backend remains fully functional even without AI capabilities.

This approach keeps AI tightly integrated with the backend while preserving the platform's separation of concerns and ensuring consistent business behaviour across all workflows.

---

# 9. Error Handling

The backend should handle errors consistently across all components while preventing internal implementation details from being exposed to clients.

Errors should be handled as close to their source as possible, while allowing global exception handlers to provide standardized API responses.

Common categories include:

* Request validation errors.
* Authentication and authorization failures.
* Business rule violations.
* Resource not found errors.
* Infrastructure failures.
* Unexpected application errors.

Background workers should log failures and support appropriate retry mechanisms without affecting the overall stability of the platform.

---

# 10. Logging & Observability

The backend should produce structured logs that help developers understand application behaviour, troubleshoot failures, and monitor background processing.

Logging should be implemented consistently across all backend components, including:

* API requests and responses.
* Business service execution.
* Background job execution.
* Event processing.
* AI investigations.
* Application errors.

Logs should provide sufficient operational context while avoiding unnecessary logging of sensitive business or customer information.

Observability should support monitoring the health of the backend without introducing additional business logic into the application.