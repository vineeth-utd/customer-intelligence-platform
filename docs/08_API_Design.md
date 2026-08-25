# 1. API Design Goals

The API Design defines how different components of the Customer Intelligence Platform communicate with one another and how the platform exposes its business capabilities to user interfaces and AI-powered investigations.

Its purpose is to provide a consistent, secure, and maintainable interface between the Presentation Layer, AI Layer, Business Services, and the underlying data platform.

Rather than focusing on implementation-specific endpoint definitions, this document describes the business capabilities exposed through APIs, the responsibilities of each API group, and how they support the workflows defined in the previous design documents.

The API design should support the product workflows, system architecture, data architecture, and AI architecture while remaining simple, extensible, and aligned with the platform's business-first philosophy.

Specifically, the API design should:

* Expose business capabilities through well-defined APIs.
* Provide a clear separation between API responsibilities and business logic.
* Support dashboard experiences for internal teams and merchants.
* Enable AI-assisted investigations through controlled API interactions.
* Protect business data through authentication, authorization, and validation.
* Maintain consistent request and response patterns across the platform.
* Support future platform enhancements without requiring major API redesign.

The API layer serves as the communication boundary between clients and the platform.

It is responsible for receiving requests, validating them, enforcing security policies, and delegating business operations to the appropriate business services. Business logic remains within the service layer, allowing the same capabilities to be reused by REST APIs, AI tools, scheduled jobs, and future integration mechanisms.

Throughout this document, every API should answer one fundamental question:

> **What business capability does this API expose?**

The APIs should represent meaningful business operations rather than exposing underlying databases or implementation details.

Maintaining this principle keeps the platform modular, easier to evolve, and ensures that the API layer remains a stable contract between the platform and its consumers.

---

# 2. API Architecture Overview

The API layer acts as the communication boundary between clients and the Customer Intelligence Platform.

It provides a consistent interface through which user interfaces, AI-assisted investigations, and future external integrations interact with the platform's business capabilities. Rather than containing business logic, the API layer is responsible for validating incoming requests, enforcing security policies, and routing requests to the appropriate business services.

This separation ensures that business logic remains centralized and reusable across multiple consumers, including REST APIs, AI tools, scheduled jobs, and future integration interfaces.

The high-level API architecture is illustrated below.

```text
                    Clients
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
 Internal & Merchant UI        AI Investigation
        │                             │
        └──────────────┬──────────────┘
                       ▼
                   API Layer
                       │
                       ▼
               Business Services
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
 Business Data   Analytics Layer   AI Gateway
                       │              │
                       └──────┬───────┘
                              ▼
                     Platform Data Stores
```

## Responsibilities of the API Layer

The API layer is responsible for:

* Receiving requests from platform clients.
* Validating request structure and input parameters.
* Authenticating and authorizing users.
* Delegating business operations to the appropriate business services.
* Returning consistent responses to clients.
* Handling request-level errors and validation failures.

The API layer does not implement business rules or interact directly with the underlying data stores. Those responsibilities belong to the business service layer and the platform's data architecture.

## Why This Separation Matters

Separating the API layer from the business services provides several architectural benefits.

It allows business logic to be implemented once and reused across multiple consumers, keeps the API layer lightweight and focused on communication concerns, and makes the platform easier to maintain as new clients and integration points are introduced.

This approach also aligns with the AI architecture, where AI tools invoke the same business services used by the REST APIs, ensuring consistent business behaviour regardless of how a capability is accessed.

---

# 3. API Capabilities

The Customer Intelligence Platform exposes APIs based on business capabilities rather than underlying data stores or implementation details.

Each API group represents a logical business domain and provides the operations required to support dashboards, business workflows, and AI-assisted investigations. This organization keeps the API layer aligned with the platform's architecture while making it easier to evolve individual capabilities independently.

---

## 3.1 Merchant APIs

Merchant APIs provide access to merchant-related information and business operations.

These APIs support internal teams such as Customer Success, Sales, and Product, as well as merchant-facing experiences.

Key capabilities include:

* Retrieve merchant profile
* Retrieve merchant health
* Retrieve subscription information
* Retrieve feature adoption
* Retrieve merchant campaigns

---

## 3.2 Shopper APIs

Shopper APIs provide access to shopper-related information and behavioural insights.

These APIs support customer journey analysis, shopper investigations, segmentation, and merchant dashboards.

Key capabilities include:

* Retrieve shopper profile
* Retrieve customer journey
* Retrieve purchase history
* Retrieve shopper segments
* Retrieve shopper activity

---

## 3.3 Campaign APIs

Campaign APIs expose campaign information and performance analytics.

These APIs enable users to evaluate campaign effectiveness and understand shopper engagement.

Key capabilities include:

* Retrieve campaign details
* Retrieve campaign performance
* Retrieve campaign engagement metrics
* Retrieve campaign audience information

---

## 3.4 Analytics APIs

Analytics APIs provide access to business metrics and analytical data products generated by the platform.

These APIs primarily power dashboards and business reporting.

Key capabilities include:

* Retrieve business metrics
* Retrieve revenue metrics
* Retrieve conversion metrics
* Retrieve merchant analytics
* Retrieve shopper analytics
* Retrieve campaign analytics
* Retrieve feature adoption metrics

---

## 3.5 Dashboard APIs

Dashboard APIs provide consolidated data required to render role-based dashboards.

Rather than requiring clients to make multiple API calls, these APIs aggregate the information needed for a specific dashboard experience.

Key capabilities include:

* Retrieve internal dashboard data
* Retrieve merchant dashboard data
* Retrieve dashboard summaries
* Retrieve dashboard KPIs

---

## 3.6 Investigation APIs

Investigation APIs enable users to investigate business questions through a structured investigation workflow.

An investigation is treated as a first-class business entity that captures the complete lifecycle of analyzing a business problem, from the initial question through evidence gathering, findings, and recommendations.

These APIs coordinate AI-assisted investigations while relying on the AI Gateway and business services to gather evidence, execute business capabilities, and generate grounded responses.

Key capabilities include:

* Create a new investigation
* Continue an existing investigation
* Retrieve investigation details
* Retrieve investigation history
* Retrieve investigation findings
* Retrieve supporting evidence
* Search previous investigations

---

## API Design Philosophy

Each API group exposes business capabilities rather than direct access to underlying databases or implementation details.

This approach keeps the API layer aligned with the platform's business domains, encourages reuse of business services across multiple consumers, and provides a stable foundation for future implementation.

---

# 4. API Interaction Flows

Although the platform exposes multiple API groups, most requests follow one of two interaction patterns.

The first supports dashboards and business data retrieval through direct access to business services.

The second supports AI-assisted investigations, where the platform gathers evidence across multiple business domains before returning a response.

These interaction patterns demonstrate how the API layer coordinates requests while keeping business logic within the service layer.

---

## 4.1 Business Data Retrieval

Business data retrieval APIs power dashboards, merchant views, shopper views, and analytics.

A typical request follows the flow below.

```text
Client
   │
   ▼
API Layer
   │
   ▼
Business Service
   │
   ▼
Business Data
   │
   ▼
Response
```

### Workflow

1. A client sends a request for business information.
2. The API layer authenticates the request and validates the input.
3. The request is routed to the appropriate business service.
4. The business service retrieves the required business data.
5. The API layer returns a consistent response to the client.

This interaction pattern is used by most dashboard and analytics APIs.

---

## 4.2 AI-Assisted Investigation

Investigation APIs coordinate AI-assisted business investigations while ensuring that all business data is accessed through controlled platform capabilities.

A typical investigation follows the flow below.

```text
Client
   │
   ▼
Investigation API
   │
   ▼
AI Gateway
   │
   ▼
Business Services & AI Tools
   │
   ▼
Business Data & AI Knowledge
   │
   ▼
Grounded Investigation Response
```

### Workflow

1. A user creates or continues an investigation.
2. The Investigation API forwards the request to the AI Gateway.
3. The AI Gateway plans the investigation and determines which business capabilities are required.
4. Business services and AI tools retrieve the necessary business data and semantic knowledge.
5. The AI Gateway evaluates the available evidence and generates grounded findings.
6. The Investigation API returns the investigation response to the client.

This interaction pattern supports multi-step investigations while ensuring that business logic, security, and data access remain within the platform.

---

# 5. API Design Principles

The API layer follows a small set of design principles that ensure the platform remains consistent, maintainable, and aligned with the overall system architecture.

---

## Business-First APIs

APIs expose meaningful business capabilities rather than underlying databases or implementation details.

For example, APIs provide capabilities such as retrieving merchant profiles, campaign analytics, or investigation findings instead of exposing direct data access.

---

## Thin API Layer

The API layer is responsible for request handling, validation, authentication, authorization, and response generation.

Business logic remains within the business service layer, allowing the same capabilities to be reused by REST APIs, AI investigations, scheduled jobs, and future integration mechanisms.

---

## Consistent API Contracts

All APIs should follow consistent request and response patterns to simplify client development and improve maintainability.

This includes consistent naming, response structures, validation behaviour, and error handling across all API groups.

---

## Stateless Communication

Each API request should contain all the information required to process it.

Business state is maintained within platform resources such as merchants, campaigns, and investigations rather than within the API layer itself.

---

## Secure by Default

Every API request is authenticated and authorized before business data is accessed.

The platform follows the principle of least privilege, ensuring users can access only the data and capabilities permitted by their role.

---

## Extensible Design

The API layer should evolve by introducing new business capabilities without breaking existing clients whenever possible.

This allows the platform to expand while maintaining stable interfaces for user applications and future integrations.

---

# 6. Cross-Cutting Concerns

Certain responsibilities apply consistently across all API groups regardless of the business capability being exposed.

---

## Authentication

All API requests require authenticated users before accessing platform resources.

---

## Authorization

Every request is evaluated against the user's role and permissions to ensure access is limited to authorized business data and operations.

---

## Request Validation

Incoming requests are validated before reaching the business service layer.

Validation includes request structure, required fields, parameter formats, and supported values.

---

## Error Handling

The platform returns clear and consistent error responses that help clients understand why a request failed without exposing internal implementation details.

---

## Audit Logging

Important business operations and investigation activities are recorded to support auditing, troubleshooting, and compliance requirements.

Examples include:

* Investigation creation
* Business data access
* AI-assisted investigations
* Significant business operations

---

## Observability

The platform records operational metrics, logs, and traces that help monitor API health, diagnose failures, and understand system behaviour.

These capabilities support reliable platform operations without affecting business functionality.