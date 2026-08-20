# 1. AI Architecture Goals

The AI Architecture defines how artificial intelligence is integrated into the Customer Intelligence Platform to support business investigations, decision-making, and customer intelligence.

Its purpose is to enable users to investigate complex business questions using natural language while ensuring that every response remains grounded in authoritative business data and supported by relevant evidence.

Rather than functioning as an isolated chatbot, the AI operates as an intelligent investigation layer built on top of the platform's business intelligence capabilities. It enhances existing workflows by gathering relevant information, correlating evidence, and explaining business behaviour, while the platform's operational data remains the authoritative source of truth.

The AI architecture should support the business workflows, system architecture, and data architecture defined in the previous documents while remaining secure, explainable, and easy to extend.

Specifically, the AI architecture should:

* Understand business questions expressed in natural language.
* Plan investigations based on the user's intent.
* Retrieve relevant business information using controlled platform capabilities.
* Combine structured business data with retrieval-oriented business knowledge.
* Correlate evidence across multiple business domains.
* Generate explainable insights supported by verifiable evidence.
* Recommend appropriate business actions when meaningful opportunities are identified.
* Preserve investigation context across multi-step conversations.
* Protect sensitive business information through controlled data access and masking.
* Remain extensible as new AI capabilities and investigation workflows are introduced.

The AI architecture establishes a clear separation between business intelligence and AI reasoning.

The platform remains responsible for maintaining business truth through its operational data, business data products, and analytics.

The AI is responsible for understanding business intent, planning investigations, gathering relevant evidence, reasoning over the available information, and communicating findings in a clear and explainable manner.

Throughout this document, every AI interaction should answer two fundamental questions:

> **What information is needed to answer this business question?**

and

> **What evidence supports the final conclusion?**

The AI should never generate conclusions without first gathering sufficient evidence from the platform's business capabilities.

Maintaining this principle ensures that AI-assisted investigations remain trustworthy, explainable, and fully grounded in the platform's authoritative business data.

---

# 2. End-to-End AI Investigation Flow

The Customer Intelligence Platform treats every AI interaction as an investigation rather than a simple question-and-answer session.

Instead of generating immediate responses, the AI follows a structured investigation process that resembles how an experienced business analyst approaches a business problem. It gathers relevant information, evaluates available evidence, determines whether sufficient context exists, and only then produces an explanation or recommendation.

This investigation-centric approach helps ensure that AI-generated insights remain grounded in business data and supported by verifiable evidence.

---

## 2.1 High-Level Investigation Flow

The overall AI investigation process is illustrated below.

```text
User Business Question
           │
           ▼
Understand User Intent
           │
           ▼
Plan Investigation
           │
           ▼
Retrieve Business Evidence
           │
           ▼
Evaluate Available Evidence
           │
           ▼
Need More Evidence?
      │             │
     Yes            No
      │             │
      ▼             ▼
Continue      Generate Findings
Investigation        │
                     ▼
          Explain Supporting Evidence
                     │
                     ▼
        Recommend Business Actions
                     │
                     ▼
              Return Response
```

Rather than assuming that the first available information is sufficient, the AI continuously evaluates whether additional investigation is required before generating conclusions.

---

## 2.2 Investigation Workflow

The investigation process consists of the following stages.

### Understand User Intent

The AI begins by interpreting the user's business question and identifying the underlying investigation objective.

This includes determining:

* The business problem being investigated.
* The business entities involved.
* The type of information required.
* Whether the request is exploratory or an exact lookup.

Understanding user intent allows the platform to select an appropriate investigation strategy before retrieving any business information.

---

### Plan the Investigation

Once the business objective has been identified, the AI determines what information is required to answer the question.

Depending on the investigation, the AI may need to review multiple business domains such as:

* Merchant information
* Shopper behaviour
* Orders
* Customer journeys
* Campaign performance
* Business metrics
* Historical business knowledge

Rather than following a fixed sequence, the investigation plan adapts to the business question being asked.

---

### Retrieve Business Evidence

The AI gathers relevant evidence from the platform using controlled business capabilities.

Evidence may include:

* Operational business data
* Business data products
* Historical business knowledge
* Previous investigation summaries
* Business documentation

The objective is to collect sufficient information to explain the observed business behaviour rather than retrieving unnecessary data.

---

### Evaluate Available Evidence

After gathering information, the AI evaluates whether the available evidence is sufficient to answer the business question with confidence.

If important information is missing or additional investigation is required, the AI continues gathering evidence before attempting to generate conclusions.

This iterative approach helps prevent incomplete or unsupported responses.

---

### Generate Findings

Once sufficient evidence has been collected, the AI correlates the available information to identify meaningful business observations.

The generated findings remain grounded in the evidence collected throughout the investigation and should accurately reflect the current state of the business.

---

### Explain Supporting Evidence

Every conclusion presented by the AI should be accompanied by the business evidence that supports it.

Rather than presenting unexplained recommendations, the platform explains how the available business information contributed to the final findings.

This improves transparency, builds user confidence, and allows users to validate the investigation results.

---

### Recommend Business Actions

When appropriate, the AI may recommend possible business actions based on the investigation findings.

Recommendations should always be evidence-based and directly related to the identified business problem.

If sufficient evidence does not exist to support a recommendation, the AI should clearly communicate its uncertainty instead of making assumptions.

---

## 2.3 Why This Investigation Approach Matters

Treating AI interactions as structured investigations rather than immediate question answering provides several important benefits.

It enables the platform to:

* Gather evidence before generating conclusions.
* Produce grounded and explainable business insights.
* Combine information from multiple business domains.
* Adapt investigations based on the user's business question.
* Maintain consistency with the platform's source-of-truth data.
* Improve user confidence through transparent reasoning.

By following a structured investigation workflow, the AI acts as an intelligent business analyst that assists users in understanding business behaviour rather than functioning as a generic conversational chatbot.