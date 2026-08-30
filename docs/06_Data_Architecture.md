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

### Order

An Order represents a completed purchase made by a shopper from a merchant.

Orders capture the commercial transaction resulting from a shopper's purchasing journey and provide the foundation for revenue analysis, conversion measurement, customer lifetime value, and purchase history.

An Order is created from shopper purchase events and continues to evolve as its lifecycle progresses through states such as payment, fulfilment, delivery, cancellation, or return.

Order information supports merchant analytics, shopper analytics, business metrics, customer journeys, and AI-assisted investigations.

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
   ├── Serves Shoppers
   │
   └── Receives Orders

Shopper
   │
   ├── Interacts with Products
   │
   ├── Responds to Campaigns
   │
   ├── Places Orders
   │
   └── Generates Business Events

Order
   │
   ├── Belongs to Merchant
   │
   ├── Belongs to Shopper
   │
   └── Contains Products

Business Events
   │
   └── Capture interactions involving Merchants, 
       Shoppers, Products, Orders, 
       Campaigns, and Platform Features
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
* Orders
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

---

# 4. Business Data Products

The Customer Intelligence Platform continuously transforms operational business data into higher-level business data products that support analytics, dashboards, AI investigations, and business decision-making.

Unlike the operational data stored within the platform's source-of-truth layers, business data products are derived by combining, aggregating, and analysing business events and operational entities. They provide a business-oriented view of the platform that is easier to consume than raw transactional data.

These data products are generated continuously as new merchant and shopper activity enters the platform. Since they are derived from the platform's source-of-truth data, they can always be regenerated if business logic changes or additional historical data becomes available.

The primary business data products maintained by the platform include:

* Merchant Profiles
* Shopper Profiles
* Customer Journeys
* Shopper Segments
* Merchant Health
* Campaign Analytics
* Business Metrics
* AI Knowledge Products

Each of these data products serves a different business purpose while collectively enabling dashboards, analytics, and AI-assisted investigations.

---

## 4.1 Merchant Profile

The Merchant Profile provides a unified business view of a merchant's relationship with the platform.

Rather than requiring users to inspect multiple operational records, the Merchant Profile consolidates key business information into a single, analytics-ready representation that supports reporting, customer success, product analytics, sales, and AI investigations.

The profile is continuously updated as new merchant events are processed, ensuring that it reflects the merchant's current business state while remaining traceable to the underlying operational data.

A Merchant Profile may include information such as:

* Merchant identity and account information
* Subscription status and subscription history
* Enabled platform features
* Platform adoption and usage metrics
* Campaign activity and performance
* Business growth indicators
* Revenue contribution
* Merchant sales and order trends
* Merchant health indicators
* Recent platform activity
* Important business milestones

The Merchant Profile serves as the primary business representation of a merchant throughout the platform.

It is consumed by multiple platform capabilities, including:

* Internal business dashboards
* Customer Success workflows
* Sales and account management
* Product analytics
* Merchant dashboards
* AI-assisted investigations

Although the Merchant Profile provides a consolidated view of merchant information, it is not the platform's source of truth.

Instead, it is a derived business data product generated from the underlying operational business data and can always be regenerated if the underlying data changes.

---

## 4.2 Shopper Profile

The Shopper Profile provides a unified business view of a shopper's interactions and relationship with a merchant.

Rather than analysing individual behavioural events in isolation, the Shopper Profile consolidates shopper activity into a single, analytics-ready representation that helps the platform understand customer behaviour, engagement, purchasing patterns, and lifecycle.

The profile is continuously updated as new shopper events are processed, ensuring that it reflects the shopper's latest behaviour while remaining traceable to the underlying operational data.

A Shopper Profile may include information such as:

* Shopper identity
* Associated merchant
* Demographic information, where available
* Shopping preferences
* Product interests and browsing behaviour
* Purchase history
* Wishlist and Save for Later activity
* Cart and checkout behaviour
* Campaign engagement
* Customer lifecycle stage
* Behavioural patterns and engagement metrics
* Customer lifetime value and purchase frequency
* Recent shopper activity

The Shopper Profile serves as the primary business representation of a shopper throughout the platform.

It is consumed by multiple platform capabilities, including:

* Shopper analytics
* Customer journey analysis
* Shopper segmentation
* Campaign targeting
* Merchant dashboards
* AI-assisted investigations

Although the Shopper Profile provides a consolidated view of shopper behaviour, it is not the platform's source of truth.

Instead, it is a derived business data product generated from the underlying operational business data and can always be regenerated if the underlying data changes.

---

## 4.3 Customer Journey

A Customer Journey represents the sequence of interactions a shopper performs while engaging with a merchant's store.

Rather than analysing individual events independently, the Customer Journey organizes related shopper activities into a chronological view that explains how a shopper progresses through different stages of the purchasing lifecycle.

By connecting behavioural events across multiple sessions and interactions, the platform can identify how shoppers discover products, engage with platform features, respond to campaigns, and ultimately complete or abandon purchases.

A Customer Journey may include interactions such as:

* Product discovery and browsing
* Product searches
* Wishlist activity
* Save for Later activity
* Campaign interactions
* Add to Cart
* Checkout initiation
* Order placement and purchase completion
* Repeat purchases
* Post-purchase engagement

Customer Journeys provide important context that individual events cannot capture. They help explain how shopper behaviour evolves over time and where opportunities or points of friction exist within the shopping experience.

These journeys support multiple business capabilities, including:

* Conversion funnel analysis
* Behavioural analytics
* Campaign effectiveness analysis
* Shopper segmentation
* Merchant dashboards
* AI-assisted investigations

Customer Journeys are continuously updated as new shopper events are processed, ensuring that they accurately represent the shopper's latest interactions while preserving the complete sequence of behavioural activity.

Although Customer Journeys provide a consolidated representation of shopper behaviour, they are not the platform's source of truth.

Instead, they are a derived business data product generated by correlating chronological shopper events and can always be reconstructed from the underlying event history.

---

## 4.4 Shopper Segment Definitions

Shopper Segment Definitions represent the logical business segments available within a merchant's store.

Unlike segment memberships, which are generated from shopper behaviour, segment definitions are stable business entities that describe how shoppers should be grouped.

Examples include:

* High Value Customers
* Frequent Buyers
* Cart Abandoners
* Inactive Shoppers
* Campaign Responsive Shoppers

Segment Definitions support multiple business capabilities, including:

* Campaign targeting
* Merchant dashboards
* Customer behaviour analysis
* AI-assisted investigations

Campaigns reference Shopper Segment Definitions directly, allowing business relationships to remain stable even as shopper memberships change over time.

Although Segment Definitions are maintained operationally, the shoppers belonging to each segment are generated separately as derived analytical data.

---

## 4.5 Shopper Segment Membership

Shopper Segment Membership stores the shoppers that currently belong to each Shopper Segment Definition.

Unlike Segment Definitions, memberships are generated by analysing shopper profiles, customer journeys, purchasing behaviour, and other behavioural signals.

Since shopper behaviour changes continuously, memberships are periodically regenerated to reflect the latest business activity.

A Shopper Segment Membership associates:

* Shopper
* Segment Definition
* Membership generation timestamp

This separation allows analytical processing to evolve independently while preserving stable business relationships between campaigns and segment definitions.

Segment Membership is a derived business data product and can always be regenerated from operational business data.

---

## 4.6 Merchant Health

Merchant Health provides an overall assessment of a merchant's engagement, adoption, and business performance within the platform.

Rather than relying on a single metric, Merchant Health combines multiple business signals to provide a holistic view of how effectively a merchant is using the platform and whether they are demonstrating healthy growth or exhibiting signs of declining engagement.

Merchant Health is continuously evaluated as new merchant activity, shopper behaviour, and business metrics become available, ensuring that it reflects the merchant's latest business state.

A Merchant Health assessment may consider information such as:

* Subscription status and lifecycle
* Platform feature adoption
* Merchant activity and platform usage
* Campaign creation and engagement
* Shopper engagement trends
* Revenue and business growth
* Conversion performance
* Recent business activity
* Historical business trends

Merchant Health enables the platform to proactively identify merchants that may require additional support or present opportunities for growth.

It supports multiple platform capabilities, including:

* Customer Success workflows
* Merchant retention analysis
* Churn risk identification
* Sales and account management
* Internal business dashboards
* AI-assisted investigations

Merchant Health represents a continuously evolving business assessment rather than a static business record.

Although it provides an overall view of a merchant's business condition, it is not the platform's source of truth.

Instead, it is a derived business data product generated by analysing operational business data, merchant profiles, shopper behaviour, campaign performance, and other business metrics, and can always be recalculated as business rules or evaluation models evolve.

---

## 4.7 Campaign Analytics

Campaign Analytics provides a comprehensive view of how marketing campaigns perform across different merchants, shopper segments, and business objectives.

Rather than evaluating individual campaign interactions in isolation, Campaign Analytics consolidates campaign performance into meaningful business insights that help merchants and internal teams understand which campaigns drive shopper engagement, conversions, and revenue.

Campaign Analytics is continuously updated as shoppers interact with campaigns and complete subsequent actions throughout their customer journeys.

A Campaign Analytics data product may include information such as:

* Campaign details and lifecycle
* Target shopper segments
* Campaign reach and delivery
* Shopper engagement metrics
* Click-through and interaction metrics
* Conversion performance
* Order and revenue attribution
* Campaign effectiveness trends
* Comparative campaign performance
* Historical campaign analysis

Campaign Analytics enables merchants and internal business teams to evaluate marketing effectiveness, identify successful engagement strategies, and optimize future campaigns.

It supports multiple platform capabilities, including:

* Marketing performance analysis
* Campaign optimization
* Shopper engagement analysis
* Merchant dashboards
* Business intelligence dashboards
* AI-assisted investigations

Campaign Analytics represents a continuously evolving analytical view of campaign performance rather than a collection of operational campaign records.

Although it provides valuable business insights, it is not the platform's source of truth.

Instead, it is a derived business data product generated from campaign events, shopper behaviour, customer journeys, and operational business data, and can always be regenerated as additional business activity becomes available.

---

## 4.8 Business Metrics

Business Metrics provide a consolidated view of the overall performance and health of the platform.

Rather than focusing on individual merchants, shoppers, or campaigns, Business Metrics aggregate information across multiple business domains to provide a high-level understanding of platform performance, customer engagement, product adoption, and business growth.

Business Metrics are continuously updated as new merchant and shopper activity is processed, ensuring that dashboards and analytical workflows always reflect the latest state of the business.

A Business Metrics data product may include information such as:

* Revenue trends
* Order volume
* Merchant growth
* Shopper growth
* Conversion rates
* Shopper engagement metrics
* Platform feature adoption
* Campaign performance summaries
* Subscription trends
* Merchant retention and churn
* Customer acquisition metrics
* Business growth indicators

Business Metrics enable both internal teams and merchants to monitor business performance, identify trends, measure the impact of business initiatives, and make informed decisions based on reliable, data-driven insights.

It supports multiple platform capabilities, including:

* Executive dashboards
* Product analytics
* Marketing analytics
* Customer Success reporting
* Merchant dashboards
* AI-assisted investigations

Business Metrics represent continuously evolving analytical views generated from operational business data and other business data products.

Although they provide valuable insights into business performance, they are not the platform's source of truth.

Instead, they are derived business data products generated from merchant activity, shopper behaviour, campaign analytics, operational business data, and other analytical datasets, and can always be recalculated as business logic, reporting requirements, or analytical models evolve.

---

## 4.9 AI Knowledge Products

AI Knowledge Products organize business information into retrieval-oriented knowledge that supports AI-assisted investigations.

Unlike operational business data and analytical data products, AI Knowledge Products are designed specifically to help the AI layer efficiently locate relevant business context, correlate related information, and generate grounded explanations during investigations.

Rather than storing raw business records, these data products summarize and organize information in a form that is easier for semantic retrieval while maintaining references to the underlying source-of-truth data.

AI Knowledge Products may include information such as:

* Merchant summaries
* Shopper behaviour summaries
* Customer journey summaries
* Campaign summaries
* Business metric explanations
* Investigation summaries
* Business documentation
* Frequently accessed business knowledge

These knowledge products enable the AI to quickly identify relevant business context before retrieving authoritative operational data when detailed investigation is required.

They support multiple platform capabilities, including:

* Semantic search
* AI-assisted investigations
* Context retrieval
* Business question answering
* Investigation history
* Explainable AI workflows

AI Knowledge Products are continuously generated and refreshed as operational business data and analytical data products evolve, ensuring that AI investigations remain aligned with the latest state of the business.

Although AI Knowledge Products improve retrieval efficiency and investigation quality, they are not the platform's source of truth.

Instead, they are derived business data products generated from operational business data, business data products, and business documentation. Every knowledge product maintains traceability to the underlying business records, allowing the platform to validate AI-generated insights against authoritative data whenever detailed investigation is required.

---

# 5. Data Lineage and Traceability

Data Lineage describes how business information flows through the Customer Intelligence Platform, from its original source to the derived business data products consumed by dashboards, analytics, and AI investigations.

As data moves through the platform, it is validated, transformed, aggregated, and summarized to support different business use cases. Maintaining clear lineage ensures that every derived insight can be traced back to the underlying business records from which it was generated.

This traceability improves transparency, simplifies debugging, supports auditing, and ensures that business users and AI-generated insights remain grounded in authoritative data.

---

## 5.1 End-to-End Data Lineage

The platform maintains a continuous lineage from business events to the final business insights presented to users.

```text
Business Events
        │
        ▼
Processed Business Data
        │
        ▼
Business Data Products
        │
        ├──────────────► Dashboards & Analytics
        │
        └──────────────► AI Knowledge Products
                             │
                             ▼
                    AI-Assisted Investigations
```

Every stage in this flow builds upon information generated by the previous stage without creating a new source of business truth.

---

## 5.2 Traceability Across Business Data Products

Every business data product maintained by the platform preserves traceability to the operational business data from which it was derived.

For example:

* Merchant Profiles are generated from merchant events and operational merchant data.
* Shopper Profiles are generated from shopper events and operational shopper data.
* Customer Journeys are reconstructed from chronological shopper events.
* Shopper Segments are generated using shopper profiles, customer journeys, and behavioural data.
* Merchant Health combines multiple business signals derived from merchant activity, shopper behaviour, and business metrics.
* Campaign Analytics aggregate campaign events and shopper interactions.
* Business Metrics consolidate information across multiple business domains.
* AI Knowledge Products summarize business information while maintaining references to the underlying operational data.

This traceability ensures that every business insight can always be validated against authoritative business records.

---

## 5.3 Why Data Lineage Matters

Maintaining end-to-end data lineage provides several important benefits throughout the platform.

It enables:

* Explainable business intelligence
* Transparent AI-assisted investigations
* Simplified debugging and root cause analysis
* Reliable audit trails
* Reproducible business data products
* Consistent business reporting
* Confidence that every analytical insight can be traced back to verifiable business data

By preserving clear lineage throughout the data lifecycle, the platform ensures that business intelligence and AI-generated insights remain trustworthy, explainable, and fully grounded in the platform's source-of-truth data.

---

# 6. Data Governance

Data Governance defines the policies and practices that ensure business data remains accurate, secure, consistent, and trustworthy throughout its lifecycle.

As data flows through the Customer Intelligence Platform, it passes through multiple stages including ingestion, processing, analytics, and AI-assisted investigations. Data Governance ensures that every stage maintains the quality and integrity required to support reliable business decisions.

Rather than introducing additional business capabilities, Data Governance establishes the standards that guide how data is validated, protected, maintained, and audited across the platform.

---

## 6.1 Data Quality

Reliable business intelligence depends on the quality of the underlying data.

As merchant and shopper events enter the platform, they are validated and standardized before becoming part of the platform's operational data.

Data quality practices include:

* Schema validation
* Data type verification
* Required field validation
* Data normalization
* Duplicate detection
* Data consistency checks
* Data enrichment where appropriate

Maintaining high-quality operational data ensures that downstream business data products, dashboards, and AI investigations remain accurate and reliable.

---

## 6.2 Data Privacy

The platform is designed to protect sensitive business and customer information throughout the data lifecycle.

Access to business data is governed by user roles and business responsibilities, ensuring that users only access information relevant to their responsibilities.

When business information is used by the AI layer, the platform follows the principle of data minimization by providing only the information required to complete an investigation.

Data privacy practices include:

* Role-based access to business data
* Protection of sensitive customer information
* Data masking where appropriate
* Data minimization for AI investigations
* Controlled access through platform services

These practices help ensure that sensitive information remains protected while still enabling meaningful business analysis.

---

## 6.3 Data Retention

Different categories of business data serve different purposes and therefore have different lifecycle requirements.

Operational business data preserves the platform's business history, while derived business data products and AI knowledge can be regenerated from the underlying source-of-truth data whenever necessary.

The platform therefore distinguishes between data that must be retained as part of the business record and data that can be refreshed or regenerated as business logic evolves.

This approach reduces unnecessary duplication while ensuring that historical business information remains available for analytics, auditing, and future investigations.

---

## 6.4 Auditability

The platform maintains sufficient information to understand how business insights and AI-assisted investigations were produced.

Business data products preserve traceability to the operational data from which they were derived, while AI investigations maintain references to the business information used during each investigation.

Examples of auditable information include:

* Business data transformations
* Business data product generation
* AI investigation history
* Data sources referenced during investigations
* Business metrics used to support conclusions

Maintaining comprehensive auditability improves transparency, simplifies troubleshooting, and increases confidence in both business intelligence and AI-generated insights.