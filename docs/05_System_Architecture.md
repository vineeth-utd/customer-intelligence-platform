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
