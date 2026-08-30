## 1. Architecture Goals

The system architecture should support the product workflows defined in the previous documents while keeping the platform simple, secure, and easy to extend.

The architecture should:

* accept merchant and shopper events from upstream sources
* store business data in well defined source of truth layers
* generate merchant and shopper profiles, metrics, and business views
* support dashboards for both internal teams and merchants
* allow users to ask business questions in natural language
* investigate those questions using relevant platform data
* return grounded answers supported by evidence
* protect sensitive information through access control and masking
* scale as the amount of merchant and shopper data grows
* remain maintainable so that new workflows can be added later without redesigning the entire system

The main design principle is that the platform should first be a reliable business system, and only then an intelligent one. AI should improve the product, not replace the product itself.

---

## 2. End-to-End System Overview

The platform is built around two continuous flows:

1. data flowing into the system from merchants and shoppers
2. questions flowing into the system from users who want to understand that data

At a high level, the system works like this:

```text
Merchant events and shopper events
                ↓
         Ingestion layer
                ↓
     Validation and processing
                ↓
       Source-of-truth storage
                ↓
 Profiles, metrics, and analytics views
                ↓
     Dashboards and AI interface
                ↓
   User asks a business question
                ↓
  AI investigates using platform data
                ↓
   Platform returns grounded answer
```

### Data flow

Merchant and shopper activity enters the platform continuously.

The ingestion layer validates and processes the incoming data before storing it in the appropriate data layers. From there, the platform builds profiles, metrics, and analytics views that represent the current state of the business.

These views are then used by dashboards and by the AI investigation layer.

---

### Investigation flow

When a user notices something unusual, they can ask the platform a question directly from the dashboard or AI interface.

The platform then investigates the question by gathering relevant business information, reviewing supporting evidence, and determining whether enough context exists to provide a reliable answer.

If the answer is clear, the platform explains the findings.

If the evidence is incomplete, the platform should say so rather than guessing.

---

### Why this structure matters

This architecture keeps the platform organized into two clear directions:

* data moves inward from merchants and shoppers
* questions move inward from users

The platform converts both into useful business decisions through storage, analytics, and AI-assisted investigation.

This design keeps the system easy to understand, easier to extend, and easier to debug later.

---

## 3. Core Components

The platform is organized into logical layers, where each layer has a clearly defined responsibility. This separation keeps the system modular, easier to maintain, and easier to extend as new business capabilities are added.

---

### 3.1 External Systems

The External Systems layer represents all upstream systems that generate business events consumed by the platform.

#### Responsibilities

* Generate merchant events
* Generate shopper events
* Continuously send business events into the platform

#### Key Components

**Merchant Event Sources**

Merchant event sources generate events representing how merchants interact with our SaaS platform.

Examples include:

* Application installation
* Subscription creation
* Subscription renewal
* Subscription cancellation
* Feature enablement
* Campaign management
* Merchant configuration updates

---

**Shopper Event Sources**

Shopper event sources generate behavioural events representing how shoppers interact with merchant storefronts.

Examples include:

* Product views
* Wishlist actions
* Save for Later actions
* Add to Cart
* Checkout
* Purchases
* Campaign interactions
* Feature usage

---

**Why this layer exists**

The platform should remain independent of how upstream systems generate data. As long as merchant and shopper events are produced in the expected format, the platform should be able to process them regardless of where they originate.

---

### 3.2 Data Platform

The Data Platform is responsible for transforming incoming business events into reliable, structured business data that can be used throughout the platform.

#### Responsibilities

* Receive merchant and shopper events
* Validate incoming data
* Verify schema correctness
* Perform data quality checks
* Normalize and enrich data
* Store data in appropriate business data layers
* Build merchant and shopper profiles
* Maintain business metrics

#### Key Components

**Ingestion Layer**

Receives events generated by merchant and shopper event sources.

---

**Data Processing Layer**

Validates, cleans, transforms, and enriches incoming business events before storing them.

---

**Primary Data Storage**

Stores the platform's source-of-truth business data, including merchant information, shopper information, business events, profiles, journeys, and analytics-ready datasets.

---

**Profile Generation**

Maintains up-to-date merchant and shopper profiles using processed business data.

---

**Business Metrics**

Continuously updates business metrics that are consumed by dashboards, analytics, and AI investigations.

---

**Why this layer exists**

The Data Platform ensures that every downstream component works with clean, reliable, and consistent business data.

---

### 3.3 Business Intelligence Layer

The Business Intelligence Layer converts processed business data into meaningful insights that help users understand business performance.

#### Responsibilities

* Generate merchant analytics
* Generate shopper analytics
* Generate campaign analytics
* Generate business metrics
* Generate customer journey analytics
* Support dashboard visualizations

#### Key Components

**Merchant Analytics**

Provides insights into merchant lifecycle, subscriptions, feature adoption, revenue contribution, and business health.

---

**Shopper Analytics**

Provides insights into shopper behaviour, customer journeys, conversion funnels, engagement, and purchasing patterns.

---

**Campaign Analytics**

Measures campaign effectiveness, shopper engagement, and segment performance.

---

**Business Metrics**

Maintains platform-wide metrics such as revenue, conversion, growth, churn, and feature usage.

---

**Dashboard Views**

Organizes business metrics into role-specific dashboards for internal teams and merchants.

---

**Why this layer exists**

Users should be able to understand business performance without manually querying raw data.

---

### 3.4 AI Layer

The AI Layer enables intelligent investigation of business questions while ensuring that business data remains secure and controlled.

#### Responsibilities

* Understand business questions
* Investigate available evidence
* Retrieve relevant business knowledge
* Access business data through controlled platform services
* Generate explainable answers
* Recommend actions when appropriate

#### Key Components

**AI Gateway**

Acts as the controlled entry point between the AI model and the rest of the platform.

---

**Investigation Engine**

Coordinates the investigation process by gathering relevant information, evaluating available evidence, and determining whether sufficient information exists to answer a business question.

---

**Tool Layer**

Provides controlled access to business capabilities such as profile retrieval, analytics retrieval, business documentation, and other platform services.

---

**AI Knowledge Layer**

Maintains retrieval-oriented business knowledge derived from platform data, allowing the AI to quickly locate relevant context during investigations.

---

**Conversation Context**

Maintains investigation context throughout a conversation, enabling users to ask follow-up questions without restarting the investigation.

---

**Why this layer exists**

The AI should investigate business questions using controlled platform capabilities rather than directly accessing underlying business data.

---

### 3.5 Presentation Layer

The Presentation Layer provides interfaces through which users interact with the platform.

#### Responsibilities

* Display business metrics
* Visualize business performance
* Enable AI investigations
* Present investigation results
* Support role-based experiences

#### Key Components

**Internal Dashboard**

Provides dashboards for Product, Marketing, Customer Success, Support, Sales, and Leadership teams.

---

**Merchant Dashboard**

Provides merchants with insights into store performance, shopper behaviour, feature adoption, campaign performance, and business growth.

---

**AI Investigation Interface**

Allows users to ask business questions using natural language and receive explainable, evidence-based answers.

---

**Why this layer exists**

The Presentation Layer transforms business intelligence into actionable information that users can easily understand and use for decision making.

---

## 4. End-to-End System Flows

The Customer Intelligence Platform continuously performs two primary workflows.

1. Data continuously enters the platform from merchant and shopper activities.
2. Business questions are investigated using the information available within the platform.

These two workflows together form the complete lifecycle of the system.

---

# 4.1 Data Ingestion Flow

The platform continuously receives business events generated by merchants and shoppers.

The high-level flow is shown below.

```text
Merchant Event Generator      Shopper Event Generator      Campaign Event Generator
            │                          │                            │
            ▼                          ▼                            ▼
   Merchant Events Topic      Shopper Events Topic      Campaign Events Topic
            │                          │                            │
            ▼                          ▼                            ▼
    Merchant Consumer         Shopper Consumer         Campaign Consumer
            │                          │                            │
            ▼                          ▼                            ▼
        Event Tables              Event Tables              Event Tables
                      │
                      ▼
             Business Service Layer
                      │
                      ▼
           Operational Business Data
                      │
                      ▼
      Profiles, Metrics & Analytics
                      │
                      ▼
              Business Dashboards
```

### Workflow

1. Merchant, shopper, and campaign activities generate business events.

2. Event generators publish these events to their respective Kafka topics.

3. Dedicated consumers receive the events, validate them, and persist them to the corresponding event tables.

4. Business services process the events based on their event type and update the operational business data.

5. Updated operational data is used to regenerate business data products such as merchant profiles, shopper profiles, customer journeys, and business metrics.

6. The refreshed business data becomes available through dashboards and AI-assisted investigations.

This event-driven architecture preserves the complete history of business activity while ensuring that operational business data always reflects the latest state of the platform.

---

# 4.2 AI Investigation Flow

When users need additional insights beyond dashboards, they can ask business questions using natural language.

The platform investigates the question before producing an answer.

The high-level investigation flow is shown below.

```text
User Question
        │
        ▼
Question Understanding
        ▼
Investigation
        ▼
Evidence Collection
        ▼
Evidence Evaluation
        ▼
Explanation Generation
        ▼
User Response
```

### Workflow

1. A user asks a business question through the AI interface.

2. The platform understands the intent of the question and determines what information is required.

3. The platform gathers relevant business information and supporting evidence.

4. If additional information is required, the investigation continues until sufficient evidence has been collected.

5. The platform evaluates the available evidence before generating an answer.

6. If sufficient evidence exists, the platform returns:

* Findings
* Supporting evidence
* Business observations
* Recommendations when appropriate

7. If sufficient evidence is not available, the platform clearly communicates that it cannot confidently answer the question instead of making assumptions.

8. Users may continue the investigation through follow-up questions.

The objective of this flow is to provide grounded, explainable, and trustworthy business insights instead of immediate AI-generated responses.

---

# Relationship Between Both Flows

Both workflows operate continuously within the platform.

The Data Ingestion Flow ensures that business information remains current and reliable.

The AI Investigation Flow consumes that business information to answer questions, explain business behaviour, and support decision making.

Together, these workflows enable the platform to transform continuous merchant and shopper activity into meaningful business intelligence.

---

## 5. Architecture Principles

The architecture of the Customer Intelligence Platform follows a few core principles that guide all design decisions.

---

### 5.1 Separation of Concerns

Each layer in the system has a clear responsibility.

* External Systems generate events
* The Data Platform stores and prepares business data
* The Business Intelligence Layer turns data into insights
* The AI Layer handles investigations and explanations
* The Presentation Layer shows information to users

This keeps the system modular and easier to maintain.

---

### 5.2 Source of Truth Comes First

The primary data stores are the source of truth for all business data.

Any derived views, summaries, or AI-oriented representations must always trace back to the original data source.

The platform should never treat AI-generated knowledge as the authoritative business record.

---

### 5.3 AI Supports the Product

AI should improve the platform, not define it.

The product must remain useful even if the AI layer is temporarily unavailable.

Dashboards, analytics, and business data should still provide value on their own.

---

### 5.4 Controlled Access

The AI layer should not directly access raw business data without control.

All access should happen through platform services that enforce:

* authentication
* authorization
* masking
* business rules
* safe data access

This keeps the system secure and easier to audit.

---

### 5.5 Evidence Before Explanation

The platform should gather relevant evidence before generating a conclusion.

If the evidence is sufficient, the platform can explain the result.

If the evidence is incomplete, the platform should say so instead of guessing.

This helps keep responses grounded and trustworthy.

---

### 5.6 Data Minimization

Only the minimum required data should be shared with the AI layer.

Sensitive information should be masked or omitted whenever possible.

The system should preserve business meaning while reducing unnecessary exposure of private data.

---

### 5.7 User Role Awareness

Different users should only see the data and capabilities relevant to their role.

Internal teams and merchants have different permissions, dashboards, and AI experiences.

The system should always respect these boundaries.

---

### 5.8 Build for Extension

The architecture should make it easy to add future capabilities without redesigning the entire platform.

Examples include:

* new analytics views
* new investigation workflows
* new dashboards
* new business data sources
* future engineering intelligence features

The system should evolve in a controlled way rather than growing randomly.

---

### 5.9 Keep Explanations Understandable

The platform should be simple to understand from both a user and engineering perspective.

Architecture decisions should be explainable in plain language.

This applies to documentation, internal design discussions, and future implementation work.

---

### 5.10 Prefer Practical Solutions

The platform should use the simplest approach that solves the problem well.

Components should be added because they are needed, not because they are trendy.

This keeps the system practical, maintainable, and easier to reason about.
