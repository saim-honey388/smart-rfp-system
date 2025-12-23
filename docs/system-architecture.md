# RFP AI Review System Blueprint

This document describes the proposed web app, the end‑to‑end pipeline, and the planned file structure (what lives where and why). It is implementation-agnostic enough to adapt to different stacks, but concrete on responsibilities.

## Goals
- Let requestors upload/create RFPs and deadlines.
- Let contractors submit proposals (files + structured fields).
- Run AI-assisted review: extraction, price comparison, scope alignment, clarity checks, dates, and overall assessment.
- Summarize proposals side by side for decisions (approve, reject with email, or auto-expire).
- After a proposal is selected, enable a lightweight chat for the requestor to ask questions about that proposal using the AI context.
- Keep outputs auditable: store prompts, model outputs, extracted facts, and decisions.

## High-level workflow
1) Requestor creates or uploads an RFP, sets an expiry window.
2) Contractors submit proposals.
3) Background pipeline:
   - Ingest files → extract text/OCR → normalize numbers/dates.
   - AI analyses per proposal (price, scope match, clarity, dates, overall).
   - Store findings + structured fields.
4) Cross-proposal compare table is generated for the RFP.
5) Requestor decides:
   - Approve → hand off to negotiation workflow.
   - Reject → contractor notified by email with reasons.
   - Let expire → auto-expire at deadline, send notices.

## Planned repository layout (simple stack: Python + SQLite + server-rendered HTML)
```
/apps
  /web                 # Frontend (server-rendered templates + minimal JS)
    templates/         # HTML templates (Jinja2)
    static/            # CSS/JS assets (vanilla JS; no React)
    forms.py|ts        # Server-side form handling/helpers
  /api                 # Backend HTTP API (FastAPI + SQLite)
    main.py            # API entrypoint
    routers/           # Route modules (rfps, proposals, reviews, auth, chat)
    schemas/           # Pydantic/DTOs for requests & responses
    services/          # Business logic layer (RFP, proposal, review)
    models/            # ORM models and migrations
    workers/           # Background job consumers
    config/            # Settings, env loading
    tests/             # API unit/integration tests
/services
  /ingest              # File ingest & text extraction
    extractor.py|ts    # PDF/OCR, mime handling, chunking
    parser.py|ts       # Price/date/unit parsing & normalization
    tests/
  /review              # AI prompts, model calls, scoring logic
    prompts/           # Prompt templates (price, scope, clarity, dates, summary)
    llm_client.py|ts   # Model wrapper with retries, safety
    scorer.py|ts       # Coverage %, risk scoring, aggregation
    comparator.py|ts   # Cross-proposal table builder
    tests/
/jobs                  # Scheduled jobs (expiry sweeps, reminders)
  expire.py|ts         # Auto-expire proposals/RFPs and notify
  reminders.py|ts      # Reminder emails pre-deadline
/infra
  scripts/             # Local dev tooling (format, lint, db reset); no Docker
/docs
  system-architecture.md  # (this doc) overview, pipeline, layout
  api-contracts.md        # REST/GraphQL/OpenAPI stubs & payloads
  prompts.md              # Prompt shapes, guardrails, schema expectations
  data-model.md           # ERD, tables, field definitions
/tests
  e2e/                   # End-to-end tests across web/api/workers
  fixtures/              # Sample RFPs & proposals for tests
```

## What goes in key files
- `apps/web/pages/`: RFP list/detail, proposal detail/review pages, decision panel routes.
- `apps/web/components/`: `RfpForm`, `ProposalUpload`, `ComparisonTable`, `FindingCard`, `DecisionPanel`, `StatusBadge`.
- `apps/web/lib/`: API SDK, SWR/react-query hooks, currency/date formatters, feature flags.
- `apps/api/routers/`: CRUD for RFPs/proposals, trigger review, fetch comparison results, decisions, auth.
- `apps/api/services/`: Orchestrate ingest + review jobs, enforce status transitions, send notifications.
- `apps/api/workers/`: Queue consumers that call `/services/ingest` and `/services/review`, persist outputs.
- `services/ingest/extractor.*`: Read PDFs, OCR if needed, chunk text, extract raw text.
- `services/ingest/parser.*`: Structured extraction (prices, dates, milestones), currency normalization.
- `services/review/prompts/`: Prompt templates per check (price, scope, clarity, dates, overall summary) with JSON schema outputs.
- `services/review/llm_client.*`: Model invocation, retries, rate limits, safety filters.
- `services/review/scorer.*`: Requirement coverage %, risk scoring, aggregation of findings.
- `services/review/comparator.*`: Build cross-proposal comparison rows and deltas vs RFP targets.
- `jobs/expire.*`: Sweep expired RFPs/proposals; update status, send emails.
- `jobs/reminders.*`: Pre-deadline reminders to contractors/requestor.
- `docs/api-contracts.md`: Endpoint list, payloads, status codes, webhooks if any.
- `docs/prompts.md`: Canonical prompts, expected JSON schema, fallback/guardrail rules.
- `docs/data-model.md`: Tables/entities (RFP, Proposal, Contractor, ReviewRun, Finding, Decision, Notification).

## End-to-end pipeline (data flow)
1) **RFP creation**: Store RFP, requirements list, budget, deadlines; schedule expiry job.
2) **Proposal submission**: Accept file(s) + metadata; enqueue ingest job.
3) **Ingest** (worker):
   - Fetch file from storage.
   - Extract text (PDF/OCR), chunk for context.
   - Parse key fields: price (normalize currency/unit), dates, milestones.
   - Persist extracted text + structured fields.
   - Enqueue review job.
4) **AI review** (worker):
   - Load RFP requirements and proposal extracted text.
   - Run prompt set:
     - Price check: compare to budget/peers.
     - Scope alignment: per-requirement coverage with gaps/overreach.
     - Definition clarity: ambiguous/undefined terms, contradictions.
     - Dates: start date viability vs RFP constraints.
     - Overall assessment: summary + scorecard (fit, risk, value).
   - Validate outputs against schemas; persist findings and scores.
   - Trigger comparison build.
5) **Comparison build**:
   - Aggregate proposals for the RFP.
   - Compute deltas (price vs target/median), coverage %, risk flags, earliest viable start date.
   - Store comparison snapshot for the UI.
6) **Decision**:
   - Requestor approves/rejects/lets expire.
   - Approve → mark status, hand off to negotiation (e.g., export package/webhook).
   - Reject → send email with summarized reasons.
   - Expire → scheduled job sets status, sends emails.
7) **Chat on selected proposal**:
   - After approval/selection, provide a chat interface.
   - Ground responses on the selected proposal, its AI findings, and the RFP context (retrieval-augmented).
   - No external cloud dependencies; run the model via local or hosted API as available.
8) **Auditability**:
   - Store prompts, model outputs, normalized fields, and decisions with timestamps and actors.

## Non-functional notes
- Keep stack simple: FastAPI (or Flask) + SQLite + minimal React/Vite or server-rendered templates.
- No Docker/cloud: run locally with venv/poetry/pip and a local SQLite db; file storage on disk.
- Use a lightweight task runner (thread/async queue) for ingest/review to keep uploads snappy.
- Keep prompt+schema versions to make outputs reproducible.
- Add PII safety filters and rate limiting on model calls.
- Include fixtures for deterministic e2e and worker tests.

## Quick start (future)
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `uvicorn apps.api.main:app --reload` (API) and `npm install && npm run dev` (web) if using React; or serve templates directly from FastAPI for simpler setup.

