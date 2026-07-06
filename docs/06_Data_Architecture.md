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