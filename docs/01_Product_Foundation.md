# Customer Intelligence Platform

## Vision

Modern B2B SaaS companies collect enormous amounts of data from merchants, shopper interactions, campaigns, product usage, and business operations. Although this data exists, extracting meaningful insights still requires analysts and engineers to manually query databases, compare dashboards, inspect customer journeys, and collaborate across multiple teams.

The goal of this project is to build an AI-powered Customer Intelligence Platform that enables internal business teams and merchants to understand customer behavior, investigate business metrics, and make data-driven decisions using both structured data and semantic knowledge.

Rather than functioning as a chatbot, the platform acts as an intelligent business analyst that gathers evidence from multiple data sources, reasons over available information, and provides explainable insights and recommendations.

---

# Domain Overview

The platform operates in a B2B SaaS ecosystem consisting of three primary entities.

## Platform

Our SaaS platform provides products and features that merchants integrate into their online stores.

Internal teams use the platform to understand business performance, merchant adoption, shopper behavior, and product usage.

---

## Merchant

Merchants are the direct customers of our SaaS platform.

They install and subscribe to our applications, configure platform features, create campaigns, and use the platform to improve shopper engagement and business growth.

Examples of merchant activities include:

* Installing applications
* Managing subscriptions
* Enabling platform features
* Configuring campaigns
* Viewing business dashboards
* Investigating shopper behavior

---

## Shopper

Shoppers are the customers of the merchants.

They interact with the merchant's storefront and generate behavioral events by browsing products, adding items to wishlists, saving products for later, adding products to carts, completing purchases, and engaging with campaigns.

These interactions generate the behavioral data that powers analytics and AI investigations.

---

## Customer Intelligence

Throughout this project, **Customer Intelligence** refers to generating meaningful insights across both merchant and shopper data.

This includes understanding:

* Merchant health and adoption
* Shopper behavior
* Campaign performance
* Product usage
* Feature adoption
* Revenue trends
* Customer journeys
* Business performance

---

# Problem Statement

Internal business teams frequently need answers to questions such as:

* Why did merchant retention decrease this month?
* Which merchants are at risk of churning?
* Which platform features contribute most to merchant revenue?
* Why did conversion decrease for a specific merchant?
* Which shopper segments are responding well to campaigns?
* Which merchants should Customer Success engage with?
* Which product features should the Product team prioritize?
* Which marketing campaigns are producing the highest ROI?

Merchants have a different set of questions, including:

* Why has my store's conversion rate decreased?
* Which shoppers are most likely to purchase?
* Which campaigns performed best?
* Which shopper segments should I target?
* Which features are contributing most to my revenue?
* How can I improve shopper engagement?

Although the required data exists, answering these questions typically requires navigating multiple dashboards, writing SQL queries, manually analyzing reports, and collaborating across different teams.

The objective of this platform is to significantly reduce the effort required to investigate business questions by combining analytics, data engineering, retrieval-augmented generation (RAG), and agentic AI into a single investigation workflow.

---

# Project Goals

The platform aims to:

* Build a complete customer intelligence platform instead of an isolated AI application.
* Simulate realistic shopper event generation similar to production systems.
* Build an end-to-end data ingestion pipeline.
* Organize data using well-defined storage layers.
* Generate analytics-ready merchant and shopper profiles.
* Generate business metrics and customer intelligence.
* Enable semantic retrieval over business knowledge and derived insights.
* Allow users to investigate business questions using natural language.
* Use an intelligent AI agent capable of planning investigations, selecting tools, gathering evidence, reasoning over multiple data sources, and generating explainable answers.
* Provide dashboards and visual analytics alongside AI-generated insights.
* Demonstrate production-inspired software engineering, backend architecture, data engineering, and AI system design.

---

# Scope

## In Scope

### Merchant Event Sources

The platform receives merchant-related events that represent how merchants interact with and use our SaaS platform.

For this project, these production systems will be simulated through merchant event generators that continuously produce realistic merchant events.

Example merchant events include:

* Merchant onboarding
* Application installation
* Application uninstallation
* Subscription creation
* Subscription renewal
* Subscription upgrade or downgrade
* Subscription cancellation
* Merchant profile updates
* Platform feature enablement or disablement
* Campaign creation, update, and deletion
* Merchant configuration changes
* Merchant login and platform usage

These events provide insights into merchant lifecycle, platform adoption, feature usage, subscription health, and overall business performance.

---

### Shopper Event Sources

The platform also receives shopper-related events generated by customers interacting with merchant storefronts.

For this project, these production systems will be simulated through shopper event generators that continuously produce realistic shopper events.

Example shopper events include:

* Product views
* Search activity
* Wishlist actions
* Save for Later actions
* Add to Cart
* Checkout
* Purchases
* Campaign interactions
* Feature usage
* Session activity

These events capture shopper behavior throughout the customer journey and form the primary source for behavioral analytics, customer segmentation, campaign analysis, and AI-driven business insights.


---

### Data Ingestion Pipeline

The platform will ingest shopper events through a dedicated ingestion layer.

The pipeline will perform:

* Validation
* Schema verification
* Data quality checks
* Normalization
* Transformation
* Enrichment

before persisting processed data into appropriate storage layers.

---

### Data Platform

The platform will organize information into multiple logical data layers.

Examples include:

* Raw merchant events
* Raw shopper events
* Processed merchant events
* Processed shopper events
* Merchant profiles
* Shopper profiles
* Analytics-ready datasets
* Segment definitions
* Campaign metrics
* Business metrics

The platform correlates merchant events and shopper events to generate business intelligence and customer insights.

The primary databases remain the source of truth for all business data.

---

### Business Intelligence & Analytics

Business intelligence is generated by combining merchant activity, shopper behavior, campaign performance, and product usage to provide a holistic view of platform performance and customer engagement.

The platform will generate analytics across multiple domains.

#### Merchant Analytics

* Merchant health
* Subscription analytics
* Churn analysis
* Feature adoption
* Revenue contribution
* Product usage

#### Shopper Analytics

* Customer journeys
* Behavioral analysis
* Conversion funnels
* Purchase patterns
* Cohort analysis
* Segmentation

#### Campaign Analytics

* Campaign performance
* Shopper engagement
* Segment effectiveness

#### Business Analytics

* Revenue trends
* Platform adoption
* Business growth
* Feature impact

---

### AI Knowledge Layer

The AI Knowledge Layer supports semantic retrieval and intelligent reasoning.

It is not the primary source of truth.

Instead, it stores retrieval-oriented knowledge derived from platform data.

Examples include:

* Merchant summaries
* Shopper behavior summaries
* Campaign summaries
* Business metric explanations
* Product documentation
* Investigation summaries
* Frequently accessed business knowledge

Each knowledge item is embedded for semantic retrieval and contains metadata referencing the original source of truth.

Metadata includes information such as:

* Source system
* Entity type
* Entity identifier
* Source table or collection
* Document or row reference
* Time window
* Additional retrieval attributes

This enables the platform to retrieve exact business records whenever detailed investigation is required.

---

### Retrieval Strategy

The platform supports two complementary retrieval strategies.

#### Semantic Retrieval

Semantic retrieval is used when users ask exploratory or analytical questions.

Examples include:

* Why did conversion decrease yesterday?
* Which merchants are showing unusual behavior?
* Explain recent retention changes.
* Which shopper segments are becoming inactive?

Semantic retrieval identifies relevant knowledge and supporting context to guide further investigation.

---

#### Exact Entity Retrieval

Exact retrieval is used when users reference known entities.

Examples include:

* Show orders for shopper [john@example.com](mailto:john@example.com).
* Display merchant ABC's subscription details.
* Show campaign CAMP-102 performance.

The AI agent invokes backend tools to retrieve authoritative business data directly from the primary data stores.

Semantic retrieval may provide supporting context, but the source of truth always remains the primary databases.

---

### Agentic AI Investigation Engine

Rather than generating immediate responses, the AI follows a structured investigation workflow similar to how an experienced business analyst investigates problems.

The investigation process includes:

* Understanding user intent
* Planning an investigation
* Selecting appropriate tools dynamically
* Retrieving semantic and structured evidence
* Maintaining working memory throughout the investigation
* Evaluating whether sufficient evidence has been collected
* Performing additional investigation when required
* Producing explainable conclusions
* Recommending follow-up actions

The objective is to gather sufficient evidence before generating conclusions.

---

### Tool Layer

The AI agent interacts with the platform exclusively through well-defined backend tools.

Example capabilities include:

* Schema inspection
* Data dictionary lookup
* Merchant profile retrieval
* Shopper profile retrieval
* Analytics retrieval
* Revenue metrics
* Campaign retrieval
* Customer journey retrieval
* Vector search
* Business documentation search

Each tool exposes business capabilities rather than direct database operations.

---

### AI Gateway

The AI Gateway coordinates every interaction between the AI model and platform services.

Responsibilities include:

* Tool orchestration
* Semantic retrieval
* Exact entity retrieval
* Metadata resolution
* Context assembly
* Prompt construction
* Data minimization
* Sensitive data masking
* Authorization
* Response generation

The AI model never communicates directly with the underlying databases.

All platform interactions occur through controlled backend services.

---

### Dashboards

The platform provides role-based dashboards for both internal teams and merchants.

Internal dashboards provide platform-wide visibility into merchant health, shopper behavior, business growth, campaign performance, and feature adoption.

Merchant dashboards provide visibility into their own store's performance, shopper engagement, campaign analytics, revenue attribution, feature usage, and AI-powered recommendations.

---

# Out of Scope

The following capabilities are intentionally excluded from Version 1.

* Production authentication providers
* Multi-tenant deployment
* Real merchant datasets
* Large-scale distributed infrastructure
* Production cloud deployment
* Billing and subscription management
* Fine-tuning custom language models
* Multi-agent collaboration
* Engineering observability and log investigation (planned as a future project)

---

# Success Criteria

The project will be considered successful if it demonstrates:

* Strong backend engineering practices
* Production-inspired data engineering workflows
* Well-defined system architecture
* Thoughtful AI integration rather than AI-first design
* Explainable agentic investigation workflows
* Clear separation between storage, retrieval, analytics, and AI reasoning
* A realistic end-to-end platform solving meaningful business problems

---

# Project Philosophy

Every architectural decision in this project should satisfy two questions.

1. Would a real company build the system this way?

2. Can every technology and component be justified based on the problem being solved?

Technologies are introduced only when they naturally solve a problem within the system rather than to showcase a particular framework or trend.

The platform should remain valuable even if the AI component is temporarily unavailable. AI enhances the platform rather than defining it.
