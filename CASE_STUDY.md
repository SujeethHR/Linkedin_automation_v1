# Case Study: LinkedIn AI Post Studio

**Role:** Solo Scrum practitioner (PO / SM / Developer)
**Project:** Local Python Web App for AI Content Automation (2025–2026)
**Release covered:** On-Demand Publishing rebuild → Fact Check → Versioned API → SEO / AEO (current release)

---

## Agile Governance & Product Ownership (The "What")

- **Vision to Backlog Transformation:** Acted as the sole Product Owner to translate high-level personal branding goals into a structured backlog of 35+ category features and 20+ user stories across 7 content domains (AI, cybersecurity, cloud, GRC, pharma, and more).

- **Value-Based Prioritization:** Decomposed a complex multi-phase workflow (trend fetch → draft → review → publish) into independently shippable increments, ensuring a functional "Minimum Viable Product" by the end of Sprint 1 and protecting a predictable delivery cadence thereafter.

- **Decisive Scope Reduction (Descoping as a Feature):** Rather than defending a bloated backlog, exercised hard PO discipline by **formally removing the scheduler and analytics epics** once the underlying OAuth constraint made them low-value and high-maintenance. Re-anchored the product around a leaner "on-demand publishing" vision — cutting technical debt, sharpening the value proposition, and increasing sprint velocity on the features users actually reached for.

- **Strategic Scope Guardrails:** Maintained a documented out-of-scope register (multi-account support, hosted SaaS deployment, autonomous multi-account posting) to prevent scope creep and keep every sprint anchored to the single-user, locally-run product vision.

---

## Scrum Mastery & Process Facilitation (The "Process")

- **End-to-End Sprint Management:** Facilitated the full agile lifecycle across multiple releases, maintaining strict iterative discipline from initial discovery through the on-demand rebuild, the Fact Check release, the versioned-API migration, and the current SEO / AEO release.

- **Impediment Removal & Risk Mitigation:** Proactively identified LinkedIn's `r_member_social` OAuth restriction as a hard blocker for the analytics/insights features. Instead of stalling the sprint on an external dependency outside the team's control, **pivoted transparently** — descoping analytics, documenting the constraint, and redirecting that capacity toward higher-value content-quality features (Fact Check and SEO / AEO).

- **Retrospective-Driven Improvement:** Ran personal retrospectives that converted friction into concrete backlog items — including a "regenerate-without-refetch" flow to cut draft-iteration cycle time, and the simplification decision that retired unused scheduling complexity.

- **Protecting the Increment (Zero-Regression Delivery):** Delivered the SEO / AEO release as a strictly **additive, off-by-default** increment. Existing draft and publishing behavior remained byte-for-byte unchanged for users who left the toggle off, honoring the Scrum value of a "Done," non-breaking increment every sprint and eliminating regression risk on shipped functionality.

---

## Technical Execution & Architecture (The "How")

- **Cross-System Integration:** Executed and maintained integrations across 5 external systems (LinkedIn REST API, Abacus.AI LLM, DuckDuckGo search, 50+ RSS feeds, and Google Trends), establishing robust API contracts, timeouts, and graceful fallback strategies so a single upstream failure never breaks the workflow.

- **Platform Deprecation Management:** Treated LinkedIn's API deprecation timeline as a first-class technical risk and **migrated the entire publishing pipeline to the versioned LinkedIn REST API** (`LinkedIn-Version: 202507`, `/rest/posts` and `/rest/images`), future-proofing the app's core "go-live" capability against legacy-endpoint sunset.

- **Quality Engineering — Content Trust:** Engineered a **Fact Check** capability that extracts 3–5 verifiable claims from a draft, searches live web sources for each, and scores the post against real evidence (verified / uncertain / likely-false) — grounding AI output in current reality rather than model training data.

- **Discoverability Engineering — SEO / AEO:** Shipped an optional SEO / Answer-Engine-Optimization layer that tunes drafts and hashtags for search and AI answer engines (ChatGPT, Perplexity, Google AI Overviews), plus an **AEO Score** that rates any post 0–100 across keyword presence, quotability, claim clarity, and structure with concrete improvement suggestions.

- **Technical Transparency:** Maintained a "living" technical specification — including `.env` guides, API endpoint tables, LLM token budgets, and an architecture overview in the README — to minimize technical debt and keep the codebase maintainable by a solo practitioner.

---

## Operational Resilience

- **Dependency Management:** Managed the recurring 60-day LinkedIn OAuth token expiry cycle as a high-priority operational risk; built a debug validation endpoint to catch expired credentials early and mitigate "go-live" publishing failures.

- **Data Freshness Engineering:** Responded to duplicate-content feedback by implementing a 30-day TTL "seen-articles" cache, eliminating repeat suggestions and guaranteeing users see fresh source material on every fetch.
