# User Workflows

This document describes how different users interact with the Customer Intelligence Platform to solve real business problems.

The workflows focus on user goals, platform behavior, and business value. Technical implementation details are intentionally excluded and will be covered in the architecture documents.

---

# Workflow 1 - Product Manager investigates a conversion drop

## Goal

Understand why a business metric has changed and identify opportunities to improve the product.

---

## Trigger

The Product Manager notices that the conversion rate has dropped significantly compared to the previous week.

---

## User Actions

* Opens the Product Dashboard.
* Reviews conversion metrics.
* Selects the affected time period.
* Clicks **Investigate with AI**.
* Asks:

> Why did conversion decrease yesterday?

---

## Platform Behaviour

The platform:

- Reviews recent business metrics.
- Investigates shopper behaviour.
- Reviews campaign performance.
- Examines merchant feature adoption.
- Retrieves relevant historical knowledge.
- Correlates the available evidence.
- Identifies possible causes.
- Provides recommendations when the investigation identifies actionable improvement opportunities.

---

## Outcome

The Product Manager receives:

* A summary of the investigation.
* Supporting evidence.
* Impacted merchants or shopper segments.
* Recommendations for further investigation or product improvements, when applicable.

---

## Business Value

Reduces investigation time from hours to minutes while enabling faster, data-driven product decisions.

---

# Workflow 2 - Marketing Manager plans a campaign

## Goal

Identify new campaign opportunities and shopper segments that can help merchants improve shopper engagement and increase revenue.

---

## Trigger

The Marketing team plans to launch a new campaign.

---

## User Actions

- Reviews campaign analytics.
- Explores shopper behaviour across merchants.
- Reviews existing shopper segments.
- Starts an AI investigation.
- Asks:

> Are there any new shopper segments or campaign opportunities we should recommend to merchants?

---

## Platform Behaviour

The platform:

- Reviews historical campaign performance.
- Analyses shopper behaviour across merchants.
- Identifies emerging shopper cohorts.
- Detects merchants with similar business characteristics.
- Identifies merchants who could benefit from similar campaigns.
- Generates evidence-based campaign recommendations.
- Explains the reasoning behind each recommendation.

---

## Outcome

The Marketing Manager receives:

- Recommended shopper cohorts.
- Suggested campaign strategies.
- Merchants likely to benefit from those campaigns.
- Supporting evidence.
- Expected business impact.

---

## Business Value

Helps Marketing identify scalable campaign opportunities and proactively recommend successful strategies to merchants, improving shopper engagement and merchant revenue.

---

# Workflow 3 - Customer Success investigates merchant health

## Goal

Understand why a merchant's health is declining and recommend actions that improve business outcomes.

---

## Trigger

A merchant is identified as having an increased churn risk.

---

## User Actions

* Opens the Merchant Dashboard.
* Reviews merchant health metrics.
* Starts an AI investigation.
* Asks:

> Why is Merchant ABC at risk of churning?

---

## Platform Behaviour

The platform:

* Reviews merchant activity.
* Reviews subscription history.
* Examines feature adoption.
* Reviews shopper engagement.
* Analyses campaign performance.
* Identifies changes in business metrics.
* Identifies possible causes and suggests actions that may improve merchant success when appropriate.

---

## Outcome

Customer Success receives:

* Merchant health summary.
* Possible churn causes.
* Supporting evidence.
* Recommended actions.
* Talking points for the customer meeting.

---

## Business Value

Helps Customer Success proactively engage merchants before churn occurs.

---

# Workflow 4 - Support investigates a merchant issue

## Goal

Investigate customer issues efficiently without manually searching across multiple systems.

---

## Trigger

A merchant reports an unexpected issue.

---

## User Actions

* Opens the Support Dashboard.
* Searches for the merchant.
* Reviews recent activity.
* Asks AI:

> Explain why this merchant is experiencing this issue.

---

## Platform Behaviour

The platform:

- Reviews recent merchant activity and configuration changes.
- Reviews shopper activity related to the reported issue.
- Retrieves relevant business metrics and supporting data.
- Searches historical investigations and similar issues.
- Correlates the available evidence.
- Identifies possible causes.
- Summarises the findings and recommends troubleshooting steps when applicable.

---

## Outcome

Support receives:

* Investigation summary.
* Relevant customer activity.
* Supporting evidence.
* Recommended troubleshooting steps.

---

## Business Value

Reduces investigation time while improving support quality and consistency.

---

# Workflow 5 - Merchant improves store performance

## Goal

Understand store performance and identify opportunities to improve shopper engagement and revenue.

---

## Trigger

A merchant notices reduced revenue or lower shopper engagement.

---

## User Actions

- Reviews overall store performance.
- Reviews shopper journey metrics.
- Reviews feature usage such as Wishlist, Save for Later, and Add to Cart.
- Reviews campaign performance.
- Starts an AI investigation.
- Asks:

> How can I improve my store's conversion rate?

---

## Platform Behaviour

The platform:

- Reviews overall store performance.
- Analyses shopper journeys across the conversion funnel.
- Compares product views, Wishlist actions, Save for Later usage, Add to Cart, Checkout, and Purchases.
- Reviews campaign effectiveness.
- Reviews platform feature adoption and usage.
- Identifies areas of friction or unusual behavioural patterns.
- Correlates historical business knowledge with current trends.
- Provides recommendations when actionable improvement opportunities are identified.

---

## Outcome

The merchant receives:

* Performance summary.
* Shopper behaviour insights.
* Recommended feature usage.
* Campaign suggestions.
* Opportunities to improve conversions.

---

## Business Value

Helps merchants make better business decisions, improve shopper experience, and increase revenue.

---

# Workflow Summary

Although users interact with the platform in different ways, every workflow follows the same high-level pattern.

```text
User identifies a business question
            │
            ▼
Platform gathers relevant business information and supporting evidence
            │
            ▼
Platform investigates the available evidence
            │
            ▼
Platform explains findings
            │
            ▼
Platform recommends possible actions
            │
            ▼
User makes an informed business decision
```

The platform is designed to reduce manual investigation effort by combining business intelligence, analytics, and AI-assisted investigations into a single workflow.
