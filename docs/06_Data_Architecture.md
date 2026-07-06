# 1. Data Architecture Goals

The Data Architecture defines how business data is organized, transformed, and maintained throughout the Customer Intelligence Platform.

Its purpose is to ensure that merchant activity, shopper behaviour, business metrics, customer intelligence, and AI knowledge are built upon a consistent and reliable data foundation.

Rather than focusing on specific storage technologies or database implementations, this document describes how business information moves through the platform, how different types of data relate to one another, and which components are responsible for maintaining them.

The data architecture should support the business workflows and system architecture defined in the previous documents while remaining simple, scalable, and easy to extend.

Specifically, the architecture should:

* Represent the core business entities of the platform, including merchants, shoppers, campaigns, products, and business events.
* Organize business data into well-defined layers with clear ownership and responsibilities.
* Maintain the primary data stores as the authoritative source of truth.
* Support efficient generation of merchant profiles, shopper profiles, customer journeys, business metrics, and analytics datasets.
* Enable downstream business intelligence and dashboard reporting.
* Provide reliable data products that support AI-assisted investigations.
* Preserve data lineage so that derived insights can always be traced back to their originating business records.
* Support secure handling of sensitive business and customer information.
* Remain extensible as new event sources, business capabilities, and analytics requirements are introduced.

The data architecture also establishes a clear separation between operational business data and AI-oriented knowledge.

Operational business data represents the current state of the business and remains the platform's source of truth. AI-oriented knowledge, such as business summaries and semantic representations, is derived from that data to improve information retrieval and investigations, but never replaces the underlying business records.

Throughout this document, every layer of the data architecture should answer one of two fundamental questions:

> **What happened?**

or

> **What have we learned from what happened?**

Raw events, processed records, merchant profiles, shopper profiles, customer journeys, and business metrics describe **what happened** within the platform.

Analytics datasets, behavioural summaries, investigation summaries, and semantic knowledge represent **what the platform has learned** from those events.

Maintaining this distinction keeps the platform explainable, prevents duplication of business truth, and ensures that every insight can always be traced back to verifiable business data.

---

# 2. Core Business Entities and Event Categories

The Customer Intelligence Platform organizes business information around a small set of core business entities. These entities represent the primary objects that exist within the platform and form the foundation for all analytics, business intelligence, and AI investigations.

While entities describe the current state of the business, business events capture how that state changes over time. Together, they provide both a snapshot of the business and the historical context needed to understand customer behaviour and business performance.

---

## 2.1 Core Business Entities

The platform is built around the following primary business entities.

### Merchant

A Merchant represents a business that uses our SaaS platform.

Merchants install applications, manage subscriptions, configure platform features, create marketing campaigns, and monitor their business performance through the platform.

Merchant-related information forms the basis for merchant health analysis, subscription analytics, feature adoption, revenue attribution, and customer success workflows.

---

### Shopper

A Shopper represents a customer interacting with a merchant's online store.

Shoppers generate behavioural signals as they browse products, interact with platform features, engage with campaigns, and complete purchases.

These interactions drive customer journey analysis, shopper segmentation, behavioural analytics, and conversion insights.

---

### Product

A Product represents an item offered by a merchant for sale.

Products are central to shopper interactions and campaign performance. They provide context for analysing browsing behaviour, purchase patterns, product popularity, and merchandising effectiveness.

---

### Campaign

A Campaign represents a merchant-initiated marketing activity designed to engage shoppers.

Campaigns target specific shopper segments and influence customer behaviour throughout the shopping journey. Campaign data enables analysis of engagement, conversion, and overall marketing effectiveness.

---

### Platform Feature

A Platform Feature represents a capability provided by our SaaS platform.

Examples include Wishlist, Save for Later, Back in Stock, product recommendations, and marketing automation features.

Tracking feature usage enables the platform to measure feature adoption, merchant engagement, and business impact.

---

### Business Event

A Business Event represents a business action or interaction that occurred within the platform.

Unlike the other entities, which describe business objects, business events describe changes to those objects over time.

Every meaningful activity within the platform is captured as a business event and linked to one or more business entities, such as merchants, shoppers, products, campaigns, or platform features.

Business events provide the historical foundation from which profiles, customer journeys, business metrics, analytics, and AI-generated insights are derived.

---

## 2.2 Event Categories

Business events are grouped into logical categories based on the business activity they represent.

### Merchant Events

Merchant events capture how merchants interact with our SaaS platform.

Examples include:

* Merchant onboarding
* Application installation and uninstallation
* Subscription creation, renewal, upgrade, downgrade, and cancellation
* Campaign creation and management
* Platform feature enablement or disablement
* Merchant configuration changes
* Merchant login and platform usage

These events help the platform understand merchant lifecycle, platform adoption, and overall business health.

---

### Shopper Events

Shopper events capture customer behaviour throughout the shopping journey.

Examples include:

* Product views
* Product searches
* Wishlist activity
* Save for Later activity
* Add to Cart
* Checkout
* Purchases
* Campaign interactions
* Session activity

These events form the primary source of behavioural analytics and customer intelligence.

---

### Campaign Events

Campaign events capture shopper interactions with merchant marketing campaigns.

Examples include:

* Campaign delivered
* Campaign opened
* Campaign clicked
* Campaign conversion
* Campaign completion

These events enable campaign performance measurement and attribution analysis.

---

### Platform Events

Platform events represent activities generated internally by the platform itself rather than directly by merchants or shoppers.

Examples include:

* Profile generation
* Segment refresh
* Business metric calculation
* Recommendation generation
* Scheduled processing jobs

These events support operational monitoring, data lineage, and downstream business intelligence workflows.

---

## 2.3 Relationships Between Business Entities

The core business entities are closely related and together describe the complete business ecosystem.

```text
Merchant
   │
   ├── Owns Products
   │
   ├── Creates Campaigns
   │
   ├── Enables Platform Features
   │
   └── Serves Shoppers

Shopper
   │
   ├── Interacts with Products
   │
   ├── Responds to Campaigns
   │
   └── Generates Business Events

Business Events
   │
   └── Capture interactions involving Merchants, Shoppers,
       Products, Campaigns, and Platform Features
```

These relationships allow the platform to correlate activity across multiple business domains and generate a unified view of customer behaviour and business performance.

---

## 2.4 Why Business Events Are a Separate Entity

Business entities describe the current state of the business.

Business events explain how that state was reached.

For example, a merchant profile may indicate that a merchant is currently subscribed to the Premium plan. The corresponding merchant events record the complete subscription history that led to that state, including upgrades, renewals, and cancellations.

Similarly, a shopper profile may identify a shopper as a high-value customer, while the underlying shopper events explain why through their browsing history, purchases, campaign interactions, and overall engagement.

Keeping business events as a separate entity preserves the complete history of the platform while allowing current business views, profiles, customer journeys, business metrics, and AI knowledge to be derived from a single, consistent source of historical truth.

---

# 3. Logical Data Layers and Source of Truth Boundaries

Business data serves different purposes throughout its lifecycle.

Incoming events must be preserved for historical accuracy, processed into reliable business records, transformed into analytics-ready datasets, and eventually summarized into AI-oriented knowledge. Attempting to store all of these representations within a single data model would make the platform difficult to maintain, scale, and evolve.

To address this, the Customer Intelligence Platform organizes business information into multiple logical data layers. Each layer has a clearly defined responsibility and represents a different stage in the lifecycle of business data.

These layers describe **how business information evolves**, not **how it is physically stored**. A logical data layer may be implemented using one or more databases, tables, collections, or files depending on implementation requirements.

---

## 3.1 Logical Data Flow

The high-level flow of business data through the platform is illustrated below.

```text
Business Events
        │
        ▼
Raw Event Layer
        │
        ▼
Processed Business Data Layer
        │
        ▼
Derived Data Layer
        │
        ├──────────────► Dashboards & Analytics
        │
        └──────────────► AI Knowledge Layer
```

As business events move through the platform, they are progressively transformed into increasingly valuable business information while preserving clear ownership of the platform's source of truth.

---

## 3.2 Raw Event Layer

The Raw Event Layer stores business events exactly as they are received from upstream systems.

Its primary responsibility is to preserve an immutable history of business activity before any validation, transformation, or enrichment occurs.

Examples of data stored within this layer include:

* Merchant events
* Shopper events
* Campaign events
* Platform events

This layer serves as the historical record of everything that occurred within the platform and supports auditing, replay, debugging, and future reprocessing if business logic changes.

Although this is a single logical layer, it may be implemented using multiple physical tables or collections based on the type of business event being stored.

**Source of Truth:** Yes, for original business events.

---

## 3.3 Processed Business Data Layer

The Processed Business Data Layer contains validated, standardized, and enriched business data derived from the raw event layer.

At this stage, incoming events have been cleaned, normalized, and transformed into reliable business records that accurately represent the operational state of the platform.

Examples include:

* Merchants
* Shoppers
* Products
* Campaigns
* Platform Features

This layer provides the authoritative operational view of the business and serves as the foundation for downstream analytics, reporting, and AI investigations.

**Source of Truth:** Yes, for operational business entities.

---

## 3.4 Derived Data Layer

The Derived Data Layer contains business information generated from the operational business data.

Unlike the previous layers, this layer does not introduce new business facts. Instead, it organizes existing business data into forms that are easier to analyze and consume.

Examples include:

* Merchant Profiles
* Shopper Profiles
* Customer Journeys
* Shopper Segments
* Business Metrics
* Campaign Metrics
* Conversion Funnels
* Revenue Aggregates

These datasets improve analytical performance and simplify business intelligence workflows while remaining fully reproducible from the underlying business data.

**Source of Truth:** No. These datasets can always be regenerated from the underlying operational data.

---

## 3.5 AI Knowledge Layer

The AI Knowledge Layer stores retrieval-oriented knowledge generated from business data.

Its purpose is not to store operational business records, but to organize business knowledge in a form that enables efficient semantic retrieval and AI-assisted investigations.

Examples include:

* Merchant summaries
* Shopper behaviour summaries
* Campaign summaries
* Investigation summaries
* Business metric explanations
* Semantic embeddings

Every knowledge item maintains references to the underlying business records from which it was derived.

This ensures that AI-generated explanations remain grounded in verifiable business data.

**Source of Truth:** No. The AI Knowledge Layer is a retrieval optimization layer built on top of the platform's business data.

---

## 3.6 Source of Truth Boundaries

Different layers serve different purposes within the platform.

Only layers that represent original or operational business data are considered authoritative. All other layers contain information derived from those primary sources.

| Logical Data Layer | Source of Truth | Purpose |
|--------------------|-----------------|---------|
| Raw Event Layer | Yes | Preserves the complete history of business events. |
| Processed Business Data Layer | Yes | Represents the authoritative operational state of the business. |
| Derived Data Layer | No | Provides analytics-ready datasets generated from business data. |
| AI Knowledge Layer | No | Provides retrieval-oriented knowledge for AI investigations. |

Maintaining these boundaries ensures that business truth exists in only one place, while analytics and AI capabilities remain reproducible and fully traceable to the underlying business records.

---

## 3.7 Why This Separation Matters

Separating business data into logical layers provides several important architectural benefits.

It enables the platform to preserve historical business events, maintain a reliable operational view of the business, generate analytics without duplicating business truth, and support AI investigations using derived knowledge rather than raw operational data.

This separation also improves maintainability by allowing each layer to evolve independently while preserving clear ownership of business data and ensuring that every insight can be traced back to its original source.