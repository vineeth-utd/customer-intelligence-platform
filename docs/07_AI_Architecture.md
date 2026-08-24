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

---

# 3. Core AI Components

The AI investigation system is composed of a small set of core architectural components that work together to understand business questions, gather evidence, reason over available information, and generate grounded responses.

Each component has a clearly defined responsibility, allowing the platform to remain modular, secure, and extensible while ensuring that AI-generated insights remain consistent with the platform's authoritative business data.

---

## 3.1 Investigation Engine

The Investigation Engine is the central reasoning component of the AI architecture.

Rather than generating immediate responses, it coordinates the complete investigation process by understanding business questions, determining what information is required, gathering evidence, and evaluating whether sufficient information exists before producing findings.

Its responsibilities include:

* Understanding user intent
* Planning investigations
* Determining the required business information
* Coordinating evidence gathering
* Evaluating investigation completeness
* Producing grounded findings
* Recommending appropriate business actions

The Investigation Engine focuses on business reasoning rather than data retrieval, relying on the platform's other AI components to access business information.

---

## 3.2 AI Gateway

The AI Gateway acts as the controlled entry point between the AI model and the rest of the Customer Intelligence Platform.

Rather than allowing the AI to directly access business data or platform services, every investigation request passes through the AI Gateway.

Its responsibilities include:

* Receiving investigation requests
* Orchestrating business tool execution
* Building investigation context
* Applying authorization and data masking
* Enforcing AI guardrails and business policies
* Constructing prompts for the AI model
* Coordinating interactions with the AI model
* Validating and returning grounded responses

By centralizing these responsibilities, the AI Gateway ensures that every investigation follows the platform's security, privacy, and explainability requirements.

---

## 3.3 Tool Layer

The Tool Layer provides controlled access to the platform's business capabilities.

Rather than exposing databases directly to the AI model, each tool encapsulates a well-defined business capability that retrieves or performs a specific business operation.

Examples include:

* Merchant Profile Retrieval
* Shopper Profile Retrieval
* Order Retrieval
* Customer Journey Retrieval
* Campaign Analytics Retrieval
* Business Metrics Retrieval
* Business Documentation Search
* AI Knowledge Search

Each tool is responsible for applying the platform's business rules while returning only the information required for the current investigation.

This separation keeps business logic within the platform while allowing the AI to focus on investigation and reasoning.

---

## 3.4 AI Knowledge Layer

The AI Knowledge Layer provides retrieval-oriented business knowledge that supports semantic search and intelligent investigations.

Rather than storing operational business records, it maintains summaries and business knowledge that help the AI quickly identify relevant context before retrieving authoritative business data when necessary.

Examples include:

* Merchant summaries
* Shopper behaviour summaries
* Customer journey summaries
* Campaign summaries
* Business metric explanations
* Investigation summaries
* Business documentation

Every knowledge item maintains traceability to the platform's source-of-truth data, ensuring that AI investigations remain grounded in verifiable business information.

---

## 3.5 Investigation Context

The Investigation Context maintains the state of an active business investigation across multiple interactions.

Rather than treating every user request as an independent question, the platform preserves investigation context so that follow-up questions can build upon previously gathered evidence without repeating the entire investigation.

The investigation context may include information such as:

* Current investigation objective
* Business entities involved
* Retrieved evidence
* Business tools already executed
* Intermediate findings
* Previous AI observations
* Follow-up questions

Maintaining investigation context enables the AI to support natural, multi-step investigations while improving efficiency, reducing unnecessary data retrieval, and providing a more coherent user experience.

---

# 4. Information Retrieval Strategy

Business questions vary significantly in complexity and therefore require different approaches for retrieving information.

Some questions reference known business entities and can be answered by retrieving authoritative business records directly from the platform's source-of-truth data.

Other questions require the AI to investigate business behaviour, correlate information across multiple business domains, and retrieve historical knowledge before sufficient evidence can be gathered.

For this reason, the Customer Intelligence Platform supports multiple retrieval strategies, allowing the AI to select the most appropriate approach based on the user's business question.

---

## 4.1 Exact Entity Retrieval

Exact Entity Retrieval is used when users reference specific business entities that are already known.

Examples include:

* Show Merchant ABC.
* Retrieve Order ORD-10234.
* Display Shopper John Smith.
* Show Campaign CAMP-205 performance.

For these requests, the AI retrieves authoritative business information directly through the platform's business tools without requiring semantic search.

Characteristics of Exact Entity Retrieval include:

* Deterministic retrieval of known business entities.
* Direct access to source-of-truth business data.
* Tool-based retrieval using controlled platform capabilities.
* Minimal reasoning before data retrieval.

This strategy provides fast, accurate access to operational business information while preserving the platform's security and access control policies.

---

## 4.2 Semantic Retrieval

Semantic Retrieval is used when users ask exploratory or investigative business questions that cannot be answered through a single business record.

Examples include:

* Why did conversion decrease yesterday?
* Explain recent merchant churn.
* Which shopper segments are becoming inactive?
* Have we encountered similar situations before?

Rather than retrieving specific entities, the AI searches the AI Knowledge Layer to identify relevant business knowledge, historical investigations, behavioural summaries, and supporting context.

Characteristics of Semantic Retrieval include:

* Retrieval based on business meaning rather than exact identifiers.
* Discovery of related business knowledge and historical context.
* Support for exploratory investigations.
* Retrieval of summarized business information before accessing detailed operational data.

Semantic Retrieval enables the AI to rapidly identify relevant business context while avoiding unnecessary access to large volumes of operational data.

---

## 4.3 Hybrid Investigation

Many business investigations require a combination of Exact Entity Retrieval and Semantic Retrieval.

For example, when investigating a question such as:

> Why did Merchant ABC's revenue decrease this month?

the AI may perform an investigation similar to the following:

```text
Retrieve Merchant Profile
          │
          ▼
Retrieve Business Metrics
          │
          ▼
Search Historical Business Knowledge
          │
          ▼
Retrieve Campaign Analytics
          │
          ▼
Retrieve Order Information
          │
          ▼
Correlate Evidence
          │
          ▼
Generate Findings
```

During a single investigation, the AI may alternate between structured business retrieval and semantic knowledge retrieval multiple times until sufficient evidence has been collected.

This hybrid approach enables the platform to answer complex business questions while remaining grounded in authoritative business data.

---

## 4.4 Selecting the Appropriate Retrieval Strategy

The AI determines the appropriate retrieval strategy based on the user's intent rather than following a single retrieval approach for every request.

| User Request | Retrieval Strategy |
|--------------|-------------------|
| Show Merchant ABC | Exact Entity Retrieval |
| Retrieve Order ORD-10234 | Exact Entity Retrieval |
| Show Shopper John Smith | Exact Entity Retrieval |
| Why did conversion decrease yesterday? | Semantic Retrieval followed by Exact Entity Retrieval |
| Why is Merchant ABC at risk of churn? | Hybrid Investigation |
| Have we seen similar issues before? | Semantic Retrieval |

Selecting the appropriate retrieval strategy allows the platform to efficiently answer both operational business queries and complex investigative questions without compromising accuracy or explainability.

---

## 4.5 Why Multiple Retrieval Strategies Matter

Using a single retrieval strategy for every business question would either limit the AI's investigative capabilities or result in unnecessary retrieval of business information.

By combining Exact Entity Retrieval, Semantic Retrieval, and Hybrid Investigations, the platform can:

* Retrieve authoritative business data when exact information is required.
* Discover relevant business knowledge during exploratory investigations.
* Correlate evidence across multiple business domains.
* Minimize unnecessary data retrieval.
* Produce grounded and explainable business insights.

This flexible retrieval strategy allows the AI to investigate business questions in a manner that closely resembles how experienced business analysts gather and evaluate evidence before reaching conclusions.

---

# 5. Responsible AI and Security

The Customer Intelligence Platform is designed to ensure that AI-assisted investigations remain secure, explainable, and aligned with the platform's business and privacy requirements.

Rather than allowing unrestricted access to business information, the AI operates within clearly defined architectural boundaries that protect sensitive data, enforce business policies, and ensure that every investigation remains grounded in authoritative business information.

These safeguards help maintain user trust while allowing the AI to provide meaningful business insights.

---

## 5.1 Controlled Access

The AI does not communicate directly with the platform's operational data stores.

All access to business information occurs through controlled platform capabilities exposed by the Tool Layer and coordinated by the AI Gateway.

This ensures that every investigation follows the platform's security, authorization, and business policies before any information is retrieved.

Controlled access practices include:

* Tool-based access to business capabilities
* Authorization checks before data retrieval
* Role-based access to business information
* Enforcement of business rules
* Controlled interaction with platform services

This approach protects sensitive business information while maintaining consistent access to authoritative data.

---

## 5.2 AI Guardrails

The AI Gateway enforces the operational guardrails that govern every AI investigation.

These guardrails ensure that the AI behaves consistently with the platform's business policies and remains within its intended responsibilities.

Examples include:

* Restricting access to approved business tools
* Preventing direct access to operational databases
* Enforcing business and security policies
* Applying data masking where required
* Limiting access to only the information required for an investigation
* Ensuring investigations remain within authorized business boundaries

By centralizing these responsibilities within the AI Gateway, the platform maintains consistent AI behaviour regardless of the underlying AI model.

---

## 5.3 Data Minimization

The AI follows the principle of data minimization throughout every investigation.

Rather than retrieving complete business records or large datasets, the platform provides only the information necessary to answer the user's business question.

Data minimization practices include:

* Retrieving only relevant business entities
* Limiting unnecessary business data exposure
* Masking sensitive information where appropriate
* Providing summarized business knowledge whenever sufficient
* Retrieving detailed operational data only when required

This approach reduces unnecessary exposure of sensitive information while improving investigation efficiency.

---

## 5.4 Grounded Responses

Every AI-generated response should be supported by evidence retrieved from the platform's business capabilities.

The AI should never generate conclusions based on assumptions or information that cannot be verified using authoritative business data.

Grounded responses require the AI to:

* Base findings on retrieved business evidence
* Correlate information across multiple business domains
* Distinguish observations from recommendations
* Clearly communicate when available evidence is insufficient
* Avoid unsupported conclusions or speculation

Maintaining grounded responses ensures that AI-generated insights remain trustworthy and consistent with the platform's source-of-truth data.

---

## 5.5 Explainability

Business users should understand how the AI reached its conclusions.

Rather than presenting recommendations without context, the platform explains the evidence and business reasoning that contributed to each investigation.

Explainability includes:

* Presenting supporting business evidence
* Explaining relationships between business observations
* Describing why recommendations were generated
* Maintaining traceability to underlying business data
* Supporting transparent business decision-making

This enables users to validate AI-assisted investigations and make informed business decisions with confidence.

---

## 5.6 Safe Tool Usage

The AI interacts with the Customer Intelligence Platform exclusively through approved business tools.

Rather than generating direct database queries or bypassing platform services, every business operation is performed through controlled tool invocations.

Safe tool usage ensures that:

* Business logic remains within platform services
* Security policies are consistently enforced
* Business permissions are respected
* Operational data remains protected
* Tool execution remains auditable

This separation of responsibilities allows the AI to focus on investigation and reasoning while the platform retains full control over business operations and data access.