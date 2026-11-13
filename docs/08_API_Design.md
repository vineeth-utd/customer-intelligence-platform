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

Merchant APIs provide access to merchant-related information, configuration, and business operations.

Mounted at `/api/v1/merchants`, these endpoints support internal platform users and merchant-specific experiences:

* `GET /api/v1/merchants`: Paginated merchant listing (`PaginatedResponse[MerchantSummaryResponse]`).
* `GET /api/v1/merchants/{merchant_id}`: Detailed merchant profile and configuration (`MerchantDetailResponse`).
* `GET /api/v1/merchants/{merchant_id}/profile`: Snapshot operational profile and catalog metrics (`MerchantProfileResponse`).
* `GET /api/v1/merchants/{merchant_id}/health`: Normalized health score (0–100), churn risk, and factor breakdown (`MerchantHealthResponse`).
* `GET /api/v1/merchants/{merchant_id}/journeys`: Merchant lifecycle journeys (`List[MerchantJourneyResponse]`).
* `GET /api/v1/merchants/{merchant_id}/journeys/{merchant_journey_id}`: Detailed merchant journey timeline (`MerchantJourneyDetailResponse`).
* `GET /api/v1/merchants/{merchant_id}/features`: Feature entitlement and enablement statuses (`List[MerchantFeatureResponse]`).
* `GET /api/v1/merchants/{merchant_id}/subscription`: Active subscription plan and status (`SubscriptionResponse`).
* `GET /api/v1/merchants/{merchant_id}/shoppers`: Merchant customer directory (`PaginatedResponse[ShopperResponse]`).
* `GET /api/v1/merchants/{merchant_id}/orders`: Merchant orders with pagination (`PaginatedResponse[OrderResponse]`).
* `GET /api/v1/merchants/{merchant_id}/analytics/summary`: Aggregate revenue, conversion, and shopper metrics (`MerchantMetricsSummaryResult`).
* `GET /api/v1/merchants/{merchant_id}/analytics/trend`: Time-series merchant performance metrics (`List[MerchantMetricsTrendResult]`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/analytics`: Campaign performance summary for the merchant (`List[CampaignAnalyticsResult]`).
* `GET /api/v1/merchants/{merchant_id}/analytics/funnel`: Conversion funnel analysis (`ConversionFunnelResult`).
* `GET /api/v1/merchants/{merchant_id}/analytics/journeys`: Aggregated shopper journey conversion statistics (`ShopperJourneyAnalyticsResult`).
* `GET /api/v1/merchants/{merchant_id}/analytics/behavior`: Shopper behavioral analytics (`ShopperBehaviorAnalyticsResult`).
* `GET /api/v1/merchants/{merchant_id}/analytics/revenue`: Granular revenue breakdown (`RevenueAnalyticsResult`).

---

## 3.2 Shopper APIs

Shopper APIs provide access to shopper profiles, journeys, purchasing history, and behavioral activity.

Mounted at `/api/v1/merchants/{merchant_id}/shoppers`:

* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}`: Shopper identity and summary (`ShopperResponse`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/profile`: Operational shopper profile (`ShopperProfileResponse`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/journeys`: Shopper journey list (`List[ShopperJourneyResponse]`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/journeys/{journey_id}`: Detailed 7-day journey timeline events (`ShopperJourneyDetailResponse`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/orders`: Purchase history (`PaginatedResponse[OrderResponse]`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/segments`: Active segment memberships (`List[ShopperSegmentMembershipResponse]`).
* `GET /api/v1/merchants/{merchant_id}/shoppers/{shopper_id}/activity`: Chronological shopper event stream (`PaginatedResponse[ShopperActivityEventResponse]`).

---

## 3.3 Campaign APIs

Campaign APIs expose marketing campaign configurations, delivery performance, multi-perspective attribution, and audience response.

Mounted at `/api/v1/merchants/{merchant_id}/campaigns`:

* `GET /api/v1/merchants/{merchant_id}/campaigns`: Paginated campaign listing (`PaginatedResponse[CampaignSummaryResponse]`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/{campaign_id}`: Campaign configuration details (`CampaignDetailResponse`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/{campaign_id}/performance`: Aggregated send, open, click, and conversion metrics (`CampaignPerformanceDetailResult`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/{campaign_id}/attribution`: Multi-perspective attribution breakdown (direct session match, first-touch, last-touch, and assisted touches) (`CampaignAttributionResult`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/{campaign_id}/journey-correlation`: Correlation with converting and non-converting shopper journeys (`CampaignJourneyCorrelationResult`).
* `GET /api/v1/merchants/{merchant_id}/campaigns/{campaign_id}/audience`: Segment-level audience response and engagement (`CampaignAudienceAnalysisResult`).

---

## 3.4 Analytics APIs

Analytics APIs provide platform-level aggregations and feature adoption metrics.

Mounted at `/api/v1/analytics`:

* `GET /api/v1/analytics/platform/summary`: Platform-wide KPI totals and period-over-period growth (`PlatformSummaryResult`).
* `GET /api/v1/analytics/platform/trend`: Time-series daily platform growth trends (`List[PlatformTrendResult]`).
* `GET /api/v1/analytics/features`: Feature adoption, active merchants, and usage rates (`List[FeatureMetricsResult]`).

---

## 3.5 Dashboard APIs

Dashboard APIs provide consolidated payloads designed specifically for internal and merchant-level dashboard screens, composing multiple underlying business services into a single round trip without raw DAL or database access.

Mounted at `/api/v1/dashboard`:

* `GET /api/v1/dashboard/platform`: Platform overview KPIs, revenue trends, conversion funnel, and feature adoption (`PlatformDashboardResponse`).
* `GET /api/v1/dashboard/merchants/{merchant_id}`: Consolidated merchant intelligence dashboard composing summary metrics, trends, health score, profile, and recent activity (`MerchantDashboardResponse`).

---

## 3.6 Authentication & Development Identity APIs

Development identity endpoints support local development and manual/automated testing of role-based access.

Mounted at `/api/v1/auth`:

* `POST /api/v1/auth/dev-token`: Issue a signed development JWT for an `INTERNAL` or `MERCHANT` principal (`DevTokenResponse`).
* `GET /api/v1/auth/dev-principals`: List preconfigured development principals (`DevPrincipalsResponse`).

---

## 3.7 Investigation APIs

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

## 6.1 Authentication

All API endpoints (except development auth endpoints and `/health`) require an authenticated caller:

- **Bearer Token Scheme**: Transmitted via HTTP `Authorization: Bearer <token>` header.
- **Token Decoding & Verification**: Managed by `app.auth.token.decode_access_token` and injected via the FastAPI dependency `app.dependencies.auth.get_current_principal`.
- **Principal Model**: Decoded into `app.schemas.auth.Principal`, carrying `user_id`, `role`, `scope` (`INTERNAL` | `MERCHANT`), and `permitted_merchant_id` (when `scope == MERCHANT`).
- **Failure Behavior**: Missing, invalid, or expired tokens return HTTP 401 Unauthorized with a standard `WWW-Authenticate: Bearer` header.

---

## 6.2 Authorization & Tenant Isolation

Every request is evaluated against the authenticated `Principal` before reaching the Business Service Layer:

- **Platform-Wide Access (`require_internal_principal`)**: Restricts platform-level routes (such as `/api/v1/dashboard/platform` and `/api/v1/analytics/*`) to users with `scope == INTERNAL`.
- **Tenant-Scoped Access (`require_merchant_access`)**: Restricts merchant-specific routes (`/api/v1/merchants/{merchant_id}/*`, `/shoppers/*`, `/campaigns/*`) to:
  - Any caller with `scope == INTERNAL`.
  - Callers with `scope == MERCHANT` where `principal.permitted_merchant_id == merchant_id`.
- **Tenant Isolation Enforcement**: If a merchant principal attempts to access a different merchant's resources, `app.auth.enforcer.enforce_merchant_access` immediately raises HTTP 403 Forbidden before any resource retrieval occurs.

---

## 6.3 Request Validation

Incoming requests are validated at the FastAPI router boundary using Pydantic request models and path/query parameter constraints:

- Request schemas enforce field types, required fields, and value constraints.
- Date ranges are validated to ensure `start_date <= end_date`.
- Pagination parameters (`page >= 1`, `page_size >= 1`) are validated and capped.
- Schema violations return standard HTTP 422 Unprocessable Entity responses.

---

## 6.4 Error Handling

The platform returns structured error responses using consistent HTTP status codes:

- `400 Bad Request`: Invalid parameter logic (such as inverted date ranges).
- `401 Unauthorized`: Missing or invalid Bearer authentication token.
- `403 Forbidden`: Authenticated caller lacks permission for the requested resource or merchant tenant.
- `404 Not Found`: Requested business entity does not exist. Empty valid result sets return HTTP 200 with empty collections rather than 404 errors.
- `422 Unprocessable Entity`: Request body or query parameter failed Pydantic schema validation.
- `500 Internal Server Error`: Unexpected runtime exceptions (internal details masked from clients).

---

## 6.5 Audit Logging

Important business operations and investigation activities are recorded to support auditing, troubleshooting, and compliance requirements.

Examples include:

* Investigation creation
* Business data access
* AI-assisted investigations
* Significant business operations

---

## 6.6 Observability

The platform records operational metrics, logs, and traces that help monitor API health, diagnose failures, and understand system behaviour.

These capabilities support reliable platform operations without affecting business functionality.