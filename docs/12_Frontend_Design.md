# 1. Frontend Design Goals

The Frontend Design defines how users interact with the Customer Intelligence Platform through dashboards, analytics, and AI-assisted investigations.

Building upon the previously established product workflows, API design, and technology decisions, this document translates the platform's user-facing capabilities into a practical React application structure.

The frontend is responsible for presenting business information clearly and enabling users to explore platform data without containing business logic or directly interacting with underlying data stores.

Specifically, the frontend should:

* Provide intuitive dashboard experiences for internal teams and merchants.
* Present business metrics, trends, customer journeys, and analytics through clear visualizations.
* Enable users to navigate between merchant, shopper, campaign, and analytical views.
* Provide a natural interface for creating and continuing AI-assisted investigations.
* Present AI findings together with supporting business evidence.
* Retrieve and manage backend data efficiently through well-defined APIs.
* Maintain clear separation between presentation logic, server state, and backend business logic.
* Provide consistent loading, error, and empty states across the application.
* Remain modular and reusable as additional dashboards and business capabilities are introduced.

The frontend remains a presentation and interaction layer. Business rules, analytics calculations, data processing, and AI reasoning remain within the backend and platform services.

Throughout this document, every frontend design decision should answer one fundamental question:

> **How should this business capability be presented and interacted with by the user?**

Maintaining this separation keeps the frontend simple, responsive, and focused on helping users understand business information and make informed decisions.

---

# 2. Frontend Architecture & Project Structure

The frontend follows a simple component-based architecture that separates route-level pages, business-specific features, reusable UI components, and backend communication.

The high-level interaction flow is:

```text
Route
  │
  ▼
Page
  │
  ▼
Feature & Shared Components
  │
  ▼
TanStack Query Hooks
  │
  ▼
API Client
  │
  ▼
Backend REST APIs
```

Pages compose the user experience, while feature components implement domain-specific interactions. Backend data is accessed through dedicated API clients and managed through TanStack Query rather than being fetched directly within UI components.

Business logic, analytical calculations, and data processing remain within the backend.

---

## 2.1 Project Structure

The proposed frontend structure is:

```text
frontend/
│
├── src/
│   ├── pages/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── api/
│   ├── types/
│   ├── routes/
│   ├── utils/
│   ├── config/
│   ├── App.tsx
│   └── main.tsx
│
├── public/
├── tests/
├── package.json
└── tsconfig.json
```

| Directory | Responsibility |
|---|---|
| `pages/` | Route-level application screens. |
| `components/` | Reusable UI components shared across the application. |
| `features/` | Business-specific functionality organized around merchants, shoppers, campaigns, analytics, and investigations. |
| `hooks/` | Shared React and TanStack Query hooks. |
| `api/` | Backend API client and domain-specific API functions. |
| `types/` | Shared TypeScript types and API contracts. |
| `routes/` | Application routing configuration. |
| `utils/` | Reusable frontend utilities. |
| `config/` | Frontend configuration and environment settings. |

---

## 2.2 Feature Organization

Business-specific frontend functionality is organized by domain.

```text
features/
    merchants/
    shoppers/
    campaigns/
    analytics/
    investigations/
```

Shared UI elements such as KPI cards, tables, chart containers, loading states, and error states remain within `components/`.

This keeps reusable presentation components separate from business-specific frontend behaviour.

---

## 2.3 Routing

React Router manages navigation between major platform experiences such as dashboards, merchant views, shopper views, campaign analytics, and investigations.

Route-level pages compose the required feature components while keeping navigation concerns separate from business functionality.

The frontend does not introduce a separate global state management library. Server state is managed through TanStack Query, while component-specific UI state remains within React.

---

# 3. Dashboard & Visualization Design

The frontend provides dashboard experiences that allow users to monitor business performance, explore analytical data, and drill down into specific merchants, shoppers, campaigns, and customer journeys.

Dashboards consume business data and metrics provided by backend APIs. Business calculations remain within the backend, while the frontend focuses on presenting and interacting with the resulting information.

---

## 3.1 Dashboard Experiences

The platform provides different dashboard scopes for internal users and merchants.

### Internal Experience

Internal teams require visibility across the entire SaaS platform while also being able to investigate individual merchants and their underlying business activity.

The internal experience supports:

* Platform-wide business performance.
* Merchant growth, retention, and subscription trends.
* Cross-merchant analytics.
* Platform feature adoption.
* Campaign performance.
* Merchant health monitoring.
* Merchant-level drill-down.
* Shopper, campaign, and customer journey drill-down.

This enables users to move naturally from platform-level trends into the specific merchants or business activity contributing to those trends.

### Merchant Experience

Merchant-facing dashboards are scoped to the authenticated merchant's own business.

The merchant experience supports:

* Store performance.
* Revenue and conversion trends.
* Shopper behaviour.
* Customer journeys.
* Campaign performance.
* Feature adoption and usage.

Merchants cannot access platform-wide information or information belonging to other merchants.

---

## 3.2 Visualization Components

The frontend uses a small set of reusable visualization components across dashboard experiences.

Common components include:

* KPI cards for important business metrics.
* Line charts for time-series trends.
* Bar charts for comparisons.
* Funnel charts for conversion analysis.
* Tables for merchants, shoppers, campaigns, and other business records.
* Timelines for customer and merchant journeys.
* Status indicators for merchant health and other business states.
* Context-specific filters and date-range selectors.

Apache ECharts provides the underlying charting capabilities while React components provide consistent presentation and interaction patterns.

---

## 3.3 Dashboard Data

Dashboard pages retrieve consolidated business information through the platform's Dashboard and Analytics APIs.

```text
Dashboard
    │
    ▼
TanStack Query
    │
    ▼
Dashboard / Analytics API
    │
    ▼
Business Data
```

The frontend does not calculate authoritative business metrics. It presents metrics and analytical results generated by the backend and allows users to filter, explore, and visualize them.

Filters such as date range, merchant, campaign, feature, or shopper segment are introduced only where relevant to the current dashboard context.

---

## 3.4 AI Investigation Entry Points

Users can initiate AI-assisted investigations directly from relevant dashboard context.

For example, a user viewing a conversion decline, merchant health change, or campaign performance issue can select **Investigate with AI** to begin an investigation with the relevant business entity, metric, and time range already available as context.

```text
Dashboard Insight
       │
       ▼
Investigate with AI
       │
       ▼
AI Investigation
```

This connects business monitoring with investigation while allowing dashboards to remain independently useful without AI.

---

