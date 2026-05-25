# Contract Testing Automation with AI Agents — Presentation Content
# Comprehensive Slide Deck for Project Pitch

---
**Author:** Druva S Kumar  
**Company:** Bottomline Technologies  
**Role:** DevOps Intern  
**Duration:** January 2026 – June 2026  
**Total Slides:** 12 (Designed to impress)

---


# ═══════════════════════════════════════════════════════════════
# SLIDE 1: TITLE SLIDE
# ═══════════════════════════════════════════════════════════════

## Contract Testing Automation with AI Agents

**Automated Consumer-Provider API Contract Verification**  
*Powered by Spring Cloud Contract, OpenAPI Specifications & AI-Driven Intelligence*

---

**Druva S Kumar**  
DevOps Intern | Bottomline Technologies  
January 2026 – June 2026

---

Tech Badges: `Java 25` • `Spring Boot 3.3.8` • `Spring Cloud Contract 4.1.5` • `Python 3.14` • `GitLab CI` • `Microsoft Teams`


# ═══════════════════════════════════════════════════════════════
# SLIDE 2: THE PROBLEM — Why This Project Exists
# ═══════════════════════════════════════════════════════════════

## "Microservices Break Each Other Silently"

### The Problem

In a microservices architecture, services communicate over APIs.  
When one team changes their API, **other teams' services break — silently, in production.**

### Real-World Scenario

```
┌─────────────────────────────────┐        ┌─────────────────────────────────┐
│ TEAM A: User Service            │        │ TEAM B: Order Service           │
│─────────────────────────────────│        │─────────────────────────────────│
│                                 │        │                                 │
│ Renames "name" → "fullName"     │        │ Expects response with "name"    │
│ Updates their own tests ✅       │        │ Doesn't know about change ❌     │
│ Deploys to production ✅         │        │ Deploys to production ✅         │
│                                 │        │                                 │
│                                 │        │   💥 BREAKS IN PRODUCTION       │
│                                 │        │   Users see errors              │
│                                 │        │   Hours of debugging            │
└─────────────────────────────────┘        └─────────────────────────────────┘
```

### Key Pain Points

| # | Problem | Impact |
|---|---------|--------|
| 1 | No formal API agreement between teams | Services change without coordination |
| 2 | Integration tests are expensive & flaky | Often skipped, failures reach production |
| 3 | API changes invisible to consumers | Silent breakage, no early warning |
| 4 | Manual contract maintenance doesn't scale | 10+ services × 50+ endpoints = impossible |
| 5 | Slow identification of violations | Extended downtime, angry customers |


# ═══════════════════════════════════════════════════════════════
# SLIDE 3: THE SOLUTION — What This Project Does
# ═══════════════════════════════════════════════════════════════

## "Catch Breaking Changes at Build Time, Not in Production"

### The Core Idea

A **contract** = a formal YAML agreement between Provider & Consumer:

> *"When the Consumer sends THIS request, the Provider MUST return THIS response.  
> If the Provider breaks this agreement, the BUILD FAILS and DEPLOYMENT IS BLOCKED."*

```yaml
# Contract: "Order Service expects this from User Service"
request:
  method: GET
  url: /api/users/1
response:
  status: 200
  body:
    id: 1
    name: "Alice Johnson"       ← If Provider removes/renames this field
    email: "alice@example.com"     the contract test FAILS automatically
    role: "ADMIN"                  → deployment BLOCKED before production
```

### Three Layers of Protection

| Layer | What It Does | Technology |
|-------|-------------|-----------|
| **Contract Testing** | Verifies Provider fulfills agreements | Spring Cloud Contract |
| **AI Agent** | Auto-generates, monitors, and fixes contracts | Python (12 modules) |
| **CI/CD Pipeline** | Runs everything automatically on every push | GitLab CI (13 jobs) |

### Result

**Integration failure detection shifts from:**  
🔴 **Production** (expensive, painful, user-impacting)  
→ 🟢 **Build Time** (cheap, fast, developer-friendly)


# ═══════════════════════════════════════════════════════════════
# SLIDE 4: COMPLETE SYSTEM ARCHITECTURE DIAGRAM
# (The impressive, complicated workflow diagram)
# ═══════════════════════════════════════════════════════════════

## End-to-End System Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        GITLAB CI/CD PIPELINE (13 Jobs, 5 Stages)                                │
│                                                                                                                 │
│  ┌─── STAGE 1: BUILD ───────────────────┐  ┌─── STAGE 2: TEST ──────────────────────────────────────────────┐  │
│  │                                       │  │                                                                │  │
│  │  ┌────────────────┐                   │  │  ┌──────────────────────┐   ┌──────────────────────────────┐   │  │
│  │  │ provider-build │─── mvn compile ──►│  │  │ ai-agent-drift-check │   │ backward-compat-check (MR)   │   │  │
│  │  └────────────────┘                   │  │  │ Python drift detect  │   │ Blocks breaking API changes  │   │  │
│  │  ┌────────────────┐                   │  │  └──────────┬───────────┘   └──────────────────────────────┘   │  │
│  │  │ consumer-build │─── mvn compile ──►│  │             │                                                  │  │
│  │  └────────────────┘                   │  │  ┌──────────▼───────────┐   ┌──────────────────────────────┐   │  │
│  │  ┌────────────────────────────────┐   │  │  │provider-contract-test│   │ consumer-contract-test       │   │  │
│  │  │ generate-contracts             │   │  │  │ mvn install (SCC)    │──►│ mvn test (WireMock stubs)    │   │  │
│  │  │ AI reads OpenAPI spec          │   │  │  │ 12 contracts verified│   │ Consumer ↔ Stubs verified    │   │  │
│  │  │ → Generates 12 YAML contracts │───┤  │  │ Stubs JAR generated  │   └──────────────────────────────┘   │  │
│  │  └────────────────────────────────┘   │  │  └──────────────────────┘                                      │  │
│  └───────────────────────────────────────┘  └────────────────────────────────────────────────────────────────┘  │
│                                                                                                                 │
│  ┌─── STAGE 3: REPORT ──────────────────────────────────────────────────────┐  ┌─── STAGE 4 ─┐  ┌─ STAGE 5 ─┐ │
│  │                                                                           │  │             │  │            │ │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────┐   │  │ auto-fix-   │  │  deploy    │ │
│  │  │ contract-report │  │ notify-team      │  │ root-cause-analysis   │   │  │ contracts   │  │  GATED by  │ │
│  │  │ JUnit XML agg.  │  │ Teams/Slack/SMTP │  │ AI: WHAT/WHY/HOW     │   │  │ (manual)    │  │  ALL tests │ │
│  │  └─────────────────┘  └──────────────────┘  └───────────────────────┘   │  │ → MR        │  │  main only │ │
│  │  ┌───────────────────────────┐                                           │  └─────────────┘  └────────────┘ │
│  │  │ mr-validation-comment     │                                           │                                   │
│  │  │ Posts summary on MR       │                                           │                                   │
│  │  └───────────────────────────┘                                           │                                   │
│  └───────────────────────────────────────────────────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │                              │                              │
                              ▼                              ▼                              ▼
              ┌───────────────────────────┐  ┌───────────────────────────┐  ┌───────────────────────────┐
              │     PROVIDER API          │  │     CONSUMER API          │  │     AI AGENT (Python)     │
              │     User Service          │  │     Order Service         │  │     12 Modules            │
              │     Spring Boot :8080     │  │     Spring Boot :8081     │  │                           │
              │                           │  │                           │  │  ┌─────────────────────┐  │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │  │  │ spec_reader         │  │
              │  │ GET  /api/users     │  │  │  │ GET  /api/orders    │  │  │  │ contract_generator  │  │
              │  │ GET  /api/users/:id │  │  │  │ GET  /api/orders/:id│  │  │  │ negative_gen        │  │
              │  │ POST /api/users     │  │  │  │ POST /api/orders    │  │  │  │ drift_detector      │  │
              │  │ PUT  /api/users/:id │  │  │  │ DEL  /api/orders/:id│  │  │  │ coverage_tracker    │  │
              │  │ DEL  /api/users/:id │  │  │  └─────────┬───────────┘  │  │  │ report_generator    │  │
              │  └─────────────────────┘  │  │            │              │  │  │ root_cause_analyzer │  │
              │            │              │  │  Calls Provider API via   │  │  │ backward_compat     │  │
              │            ▼              │  │  RestTemplate for user    │  │  │ ci_config_generator │  │
              │  ┌─────────────────────┐  │  │  enrichment              │  │  │ notifier (4 ch.)    │  │
              │  │ OpenAPI Spec        │  │  │                           │  │  │ mr_creator          │  │
              │  │ /v3/api-docs        │──┼──┼───────────────────────────┼──┼─►│ mr_validator        │  │
              │  │ (auto-generated)    │  │  │                           │  │  └─────────────────────┘  │
              │  └─────────────────────┘  │  │                           │  │            │              │
              └───────────────────────────┘  └───────────────────────────┘  │            ▼              │
                              ▲                              ▲              │  ┌─────────────────────┐  │
                              │                              │              │  │ Flask Dashboard     │  │
                              │         Contract YAML        │              │  │ Port 5050           │  │
                              │         Files (12)           │              │  │ Live Metrics & RCA  │  │
                              │              │               │              │  └─────────────────────┘  │
                              │              ▼               │              └───────────────────────────┘
                              │  ┌───────────────────────┐   │
                              │  │  12 Contract YAMLs    │   │
                              │  │                       │   │
                              │  │  5 Positive (200/201) │   │
                              │  │  7 Negative (400/404) │   │
                              │  │                       │   │
                              │  │  ┌───────────────┐    │   │
                              ├──│  │ SCC Verifier  │────┘   │
                              │  │  │ → JUnit Tests │        │
                              │  │  └───────┬───────┘        │
                              │  │          │                │
                              │  │          ▼                │
                              │  │  ┌───────────────┐        │
                              │  │  │ Stubs JAR     │────────┘
                              │  │  │ (WireMock)    │  Consumer tests
                              │  │  └───────────────┘  against stubs
                              │  └───────────────────────┘
                              │
              ┌───────────────┴───────────────────────────────────────────────────┐
              │                        NOTIFICATION FLOW                          │
              │                                                                   │
              │  Pipeline Result ─┬─► Microsoft Teams (Adaptive Card)             │
              │                   ├─► GitLab Issue Notes (@mentions → auto-email) │
              │                   ├─► Slack (Block Kit message)                   │
              │                   ├─► SMTP Email (HTML, corp network)             │
              │                   └─► Local File (reports/ directory)             │
              └───────────────────────────────────────────────────────────────────┘
```


# ═══════════════════════════════════════════════════════════════
# SLIDE 5: HOW CONTRACT TESTING WORKS
# ═══════════════════════════════════════════════════════════════

## Spring Cloud Contract — The Verification Engine

### The Two-Sided Test

```
                    12 Contract YAML Files
                    (formal API agreement)
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
    ╔═══════════════╗            ╔═══════════════╗
    ║   PROVIDER    ║            ║   CONSUMER    ║
    ║───────────────║            ║───────────────║
    ║ SCC Verifier  ║            ║ Stub Runner   ║
    ║ reads YAMLs   ║            ║ loads stubs   ║
    ║       │       ║            ║       │       ║
    ║       ▼       ║            ║       ▼       ║
    ║ Auto-generates║            ║ Starts        ║
    ║ JUnit tests   ║            ║ WireMock      ║
    ║       │       ║            ║ (fake server) ║
    ║       ▼       ║            ║       │       ║
    ║ Tests real API║            ║       ▼       ║
    ║       │       ║            ║ Consumer tests║
    ║       ▼       ║            ║ against stubs ║
    ║ ✅ or ❌      ║  ─────►   ║       │       ║
    ║               ║  stubs    ║       ▼       ║
    ║ Generates     ║  JAR      ║ ✅ or ❌      ║
    ║ stubs JAR     ║            ╚═══════════════╝
    ╚═══════════════╝
```

### 12 Contract Files — Full Coverage (Positive + Negative)

| # | Contract File | Scenario | Type |
|---|--------------|----------|------|
| 1 | should_return_user_by_id.yml | GET /api/users/1 → 200 | ✅ Happy path |
| 2 | should_return_all_users.yml | GET /api/users → 200 | ✅ Happy path |
| 3 | should_create_a_new_user.yml | POST /api/users → 201 | ✅ Happy path |
| 4 | should_update_user_by_id.yml | PUT /api/users/1 → 200 | ✅ Happy path (AI-gen) |
| 5 | should_delete_user_by_id.yml | DELETE /api/users/1 → 204 | ✅ Happy path (AI-gen) |
| 6 | should_return_404_when_getting_user_not_found.yml | GET /api/users/999 → 404 | ❌ Error case |
| 7 | should_return_404_when_updating_user_not_found.yml | PUT /api/users/999 → 404 | ❌ Error case |
| 8 | should_return_404_when_deleting_user_not_found.yml | DELETE /api/users/999 → 404 | ❌ Error case |
| 9 | should_return_400_when_creating_with_missing_fields.yml | POST {} → 400 | ❌ Validation |
| 10 | should_return_400_when_creating_with_invalid_email.yml | POST {bad email} → 400 | ❌ Validation |
| 11 | should_return_400_when_updating_with_missing_fields.yml | PUT {} → 400 | ❌ Validation |
| 12 | should_return_400_when_updating_with_invalid_email.yml | PUT {bad email} → 400 | ❌ Validation |

### Strict Assertion Mode

Provider tests use **by_command** matchers with `assertFieldErrorsStrict()` — validates exact error response structure including field-level error messages, not just status codes.


# ═══════════════════════════════════════════════════════════════
# SLIDE 6: AI AGENT — The Intelligent Automation Engine
# ═══════════════════════════════════════════════════════════════

## Python AI Agent — 12 Modules, Infinite Scale

### Internal Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         AI AGENT (Python 3.14)                            │
│                                                                          │
│  ┌─ GENERATION ─────────────────┐   ┌─ DETECTION ──────────────────────┐ │
│  │                              │   │                                  │ │
│  │  [1] spec_reader.py          │   │  [4] drift_detector.py           │ │
│  │      Fetches OpenAPI spec    │   │      Compares contracts vs spec  │ │
│  │      Resolves $ref refs      │   │      Coverage % calculation      │ │
│  │                              │   │                                  │ │
│  │  [2] contract_generator.py   │   │  [5] coverage_tracker.py         │ │
│  │      Happy path YAMLs       │   │      Historical trend tracking   │ │
│  │      Smart sample values     │   │      Snapshots over time         │ │
│  │                              │   │                                  │ │
│  │  [3] negative_contract_gen.  │   │  [8] backward_compatibility.py   │ │
│  │      Error cases (400/404)   │   │      Breaking change detection   │ │
│  │      Validation scenarios    │   │      MR gate for safety          │ │
│  └──────────────────────────────┘   └──────────────────────────────────┘ │
│                                                                          │
│  ┌─ REPORTING ──────────────────┐   ┌─ AUTOMATION ─────────────────────┐ │
│  │                              │   │                                  │ │
│  │  [6] report_generator.py     │   │  [9]  ci_config_generator.py     │ │
│  │      Coverage bars, status   │   │       Full .gitlab-ci.yml gen    │ │
│  │      Remediation steps       │   │                                  │ │
│  │                              │   │  [10] notifier.py                │ │
│  │  [7] root_cause_analyzer.py  │   │       Teams/Slack/GitLab/SMTP   │ │
│  │      Parses failure XML      │   │       4-channel delivery         │ │
│  │      WHAT / WHY / HOW        │   │                                  │ │
│  │      Category classification │   │  [11] mr_creator.py              │ │
│  │                              │   │       Auto-creates fix MRs       │ │
│  │                              │   │                                  │ │
│  │                              │   │  [12] mr_validator.py            │ │
│  │                              │   │       Posts MR summary comment   │ │
│  └──────────────────────────────┘   └──────────────────────────────────┘ │
│                                                                          │
│  ┌─ WEB INTERFACE ──────────────────────────────────────────────────────┐ │
│  │  dashboard.py — Flask (port 5050)                                    │ │
│  │  • Live test execution (runs Maven, shows real results)              │ │
│  │  • Coverage metrics cards (contracts, endpoints, health status)       │ │
│  │  • Drift detection table with AI-suggested fixes                     │ │
│  │  • Root Cause Analysis display (formatted)                           │ │
│  │  • Static HTML export for CI artifacts                               │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### CLI Commands

| Command | What It Does | CI Exit Code |
|---------|-------------|-------------|
| `python main.py generate` | Reads OpenAPI → generates happy-path YAMLs | — |
| `python main.py generate --negative` | Generates error scenario contracts | — |
| `python main.py drift` | Detects drift (uncovered/orphaned/schema) | 0/1/2 |
| `python main.py report` | Full health report + remediation steps | — |
| `python main.py validate` | CI check → exit 0 (pass) / 2 (fail) | 0/1/2 |
| `python main.py analyze` | AI root cause analysis on failures | — |
| `python main.py compat` | Backward compatibility vs main branch | 0/1/2 |
| `python main.py fix --create-mr` | Auto-fix + create GitLab MR | — |
| `python main.py ci` | Generate .gitlab-ci.yml pipeline | — |
| `python main.py dashboard` | Start Flask web dashboard (port 5050) | — |


# ═══════════════════════════════════════════════════════════════
# SLIDE 7: CI/CD PIPELINE — Full Automation
# ═══════════════════════════════════════════════════════════════

## GitLab CI Pipeline — 13 Jobs, 5 Stages, Zero Manual Effort

### Pipeline Flow

```
 ┌─ PUSH / MR ─┐
 │  Developer   │
 │  pushes code │
 └──────┬───────┘
        │
        ▼
 ════════════════════════════════════════════════════════════════════════
 STAGE 1: BUILD (Parallel)
 ────────────────────────────────────────────────────────────────────────
  provider-build ──► mvn compile (Java 25 + Spring Boot)
  consumer-build ──► mvn compile
  generate-contracts ──► AI reads /v3/api-docs → 12 YAMLs (needs provider-build)
 ════════════════════════════════════════════════════════════════════════
        │
        ▼
 ════════════════════════════════════════════════════════════════════════
 STAGE 2: TEST (Sequential + Parallel)
 ────────────────────────────────────────────────────────────────────────
  ai-agent-drift-check ──► Python: compare contracts vs live spec
  backward-compat-check ──► Python: detect breaking changes (MR only)
                │
                ▼
  provider-contract-test ──► mvn install: 12 contracts → 15 JUnit tests
                │
                ▼ (stubs JAR artifact)
  consumer-contract-test ──► mvn test: WireMock stubs → Consumer verified
 ════════════════════════════════════════════════════════════════════════
        │
        ▼
 ════════════════════════════════════════════════════════════════════════
 STAGE 3: REPORT (Always runs — even on failure)
 ────────────────────────────────────────────────────────────────────────
  contract-report ──► Aggregate JUnit XML results
  notify-team ──► Teams + Slack + GitLab Notes + SMTP
  root-cause-analysis ──► AI WHAT/WHY/HOW (only on failure)
  mr-validation-comment ──► Post summary on MR (MR pipelines only)
 ════════════════════════════════════════════════════════════════════════
        │                                              │
        ▼                                              ▼
 ═══════════════════════                ════════════════════════════
 STAGE 4: FIX (Manual)                 STAGE 5: DEPLOY (Gated)
 ───────────────────────                ────────────────────────────
  auto-fix-contracts                     deploy
  → Regenerate YAMLs                     → ONLY if ALL tests pass
  → Create GitLab MR                     → ONLY on main branch
  → Human reviews & merges               → Blocked on ANY failure
 ═══════════════════════                ════════════════════════════
```

### Key Pipeline Features

| Feature | How It Works |
|---------|-------------|
| **Deployment Gate** | If ANY contract test fails → deploy job is blocked |
| **Backward Compat** | MR pipelines compare API vs main branch → blocks breaking changes |
| **Root Cause Analysis** | On failure, AI parses XML reports → explains exactly what broke |
| **MR Validation Comment** | Formatted table posted on every MR with pass/fail summary |
| **Multi-channel Notify** | Teams (primary) → GitLab Notes → Slack → SMTP → local file |
| **Auto-Fix** | One-click: regenerate contracts + open MR for review |
| **Maven Caching** | Dependencies cached per-branch between pipeline runs |
| **Artifact Passing** | Stubs JAR flows from provider-test → consumer-test |


# ═══════════════════════════════════════════════════════════════
# SLIDE 8: NOTIFICATION SYSTEM — Multi-Channel Alerting
# ═══════════════════════════════════════════════════════════════

## 4-Channel Team Notifications

### Delivery Architecture

```
┌────────────────────────┐
│ Pipeline Completes     │
│ (Pass or Fail)         │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Notification Engine    │
│ (notifier.py)          │
│                        │
│ Builds message with:   │
│ • Health status        │
│ • Endpoints covered    │
│ • Total contracts (12) │
│ • Test results (15/15) │
│ • Drift details        │
│ • RCA suggestions      │
│ • Pipeline link        │
└────┬───┬───┬───┬───────┘
     │   │   │   │
     ▼   │   │   │
┌────────┐│   │   │         ┌─────────────────────────────┐
│ Teams  ││   │   │         │ Teams Adaptive Card:        │
│ (1st)  ││   │   │         │ ┌─────────────────────────┐ │
└────────┘│   │   │         │ │ 🔴 CONTRACT DRIFT       │ │
     ▼────┘   │   │         │ │                         │ │
┌────────┐    │   │         │ │ Status: ⚠️ DRIFTED      │ │
│ GitLab │    │   │         │ │ Endpoints: 5            │ │
│ Notes  │    │   │         │ │ Contracts: 12           │ │
│ (2nd)  │    │   │         │ │ Covered: 5/5 endpoints  │ │
└────────┘    │   │         │ │                         │ │
     ▼────────┘   │         │ │ Drifted:                │ │
┌────────┐        │         │ │  • GET /api/users/:id   │ │
│ Slack  │        │         │ │    Missing: createdAt   │ │
│ (3rd)  │        │         │ │                         │ │
└────────┘        │         │ │ 💡 Suggestion:          │ │
     ▼────────────┘         │ │ Run: python main.py fix │ │
┌────────┐                  │ └─────────────────────────┘ │
│ SMTP   │                  └─────────────────────────────┘
│ (4th)  │
└────────┘
```

### Why Multi-Channel?

| Channel | Strength | Use Case |
|---------|----------|----------|
| **Microsoft Teams** | Immediate visibility, adaptive cards | Primary — real-time team awareness |
| **GitLab Notes** | @mentions guarantee email delivery | Accountability — specific owner notified |
| **Slack** | Familiar for dev teams, threaded | Secondary — quick team chat integration |
| **SMTP** | Corporate compliance, audit trail | Fallback — works without external services |


# ═══════════════════════════════════════════════════════════════
# SLIDE 9: AI ROOT CAUSE ANALYSIS
# ═══════════════════════════════════════════════════════════════

## When Tests Fail — AI Explains Why

### Root Cause Categories

| Category | What It Means | Example |
|----------|-------------|---------|
| SCHEMA_MISMATCH | Response body doesn't match contract | `name` renamed to `fullName` |
| STATUS_CODE_MISMATCH | Wrong HTTP status returned | Expected 200, got 500 |
| MISSING_ENDPOINT | Endpoint removed from Provider | `DELETE /api/users` removed |
| NEW_REQUIRED_FIELD | Consumer missing a required field | New `phone` field required |
| VALIDATION_ERROR | Request validation rules changed | Email regex changed |
| SERIALIZATION_ERROR | JSON parsing/format issues | Date format changed |

### RCA Output Example

```
═══════════════════════════════════════════════════════════
 ROOT CAUSE ANALYSIS — Contract Test Failures
═══════════════════════════════════════════════════════════

 WHAT FAILED:
   • UserTest > should_return_user_by_id (PROVIDER)
   • 1 contract test failed out of 15

 WHY IT FAILED:
   Category: SCHEMA_MISMATCH
   The Provider's response no longer matches the contract.
   Field 'name' expected in response but not present.
   Instead, field 'fullName' was found.

 HOW TO FIX:
   Option A: Revert the Provider change (if unintentional)
     → git revert <commit-hash>
   Option B: Update the contract (if change is intentional)
     → Edit should_return_user_by_id.yml
     → Change "name" to "fullName"
     → Run: cd provider-api && mvn clean test
   Option C: Auto-fix via AI Agent
     → Run: python main.py fix --create-mr
═══════════════════════════════════════════════════════════
```


# ═══════════════════════════════════════════════════════════════
# SLIDE 10: LIVE DEMO — Breaking Change Detection
# ═══════════════════════════════════════════════════════════════

## Proof It Works — Breaking Change Caught Instantly

### Before (Tests Passing ✅)

```
$ cd provider-api && mvn clean test

[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS ✅
```

### The Breaking Change

```yaml
# Edit contract: should_return_user_by_id.yml
response:
  body:
    name: "Alice Johnson"       ← RENAME to "fullName"
```

### After (Tests Failing ❌ — Deployment BLOCKED 🚫)

```
$ mvn clean test

ContractVerifierTest > should_return_user_by_id FAILED
  java.lang.AssertionError:
  JSON path [$.fullName] doesn't match.
  Expected: "Alice Johnson"
  Actual: null

Tests run: 15, Failures: 1, Errors: 0
BUILD FAILURE ❌ → DEPLOYMENT BLOCKED 🚫
```

### What Happens Automatically After Failure

```
Pipeline Fails at Test Stage
        │
        ├─► Root Cause Analysis runs → AI generates WHAT/WHY/HOW report
        │
        ├─► Teams notification sent → Adaptive card with RCA + fix steps
        │
        ├─► GitLab MR comment posted → Formatted validation summary
        │
        └─► Auto-fix available → One-click button to regenerate + MR
```

### The Impact

| Without Contract Testing | With This System |
|---|---|
| Breaking change reaches production 💥 | Build fails immediately ❌ |
| Consumers break silently | Team notified in seconds 📢 |
| Hours/days of debugging | AI explains WHAT/WHY/HOW 🤖 |
| Manual coordination between teams | Fully automated verification ⚡ |
| No visibility into API health | Live dashboard + trend tracking 📊 |


# ═══════════════════════════════════════════════════════════════
# SLIDE 11: RESULTS & METRICS
# ═══════════════════════════════════════════════════════════════

## Project Metrics & Impact

### Key Numbers (Big Bold Cards)

| Metric | Value |
|--------|-------|
| **API Coverage** | 100% — all 5 endpoints, positive + negative |
| **Total Contracts** | 12 (5 happy path + 7 error scenarios) |
| **Provider Tests** | 15/15 passing |
| **Consumer Tests** | 2/2 passing |
| **CI/CD Jobs** | 13 across 5 stages |
| **AI Agent Modules** | 12 specialized tools |
| **Notification Channels** | 4 (Teams, Slack, GitLab Notes, SMTP) |
| **Breaking Change Detection** | Instant — at build time |
| **Auto-Fix Capability** | One-click MR creation |
| **Dashboard** | Live Flask web UI (port 5050) |
| **Pipeline Time** | ~3-4 minutes (with Maven caching) |

### All Phases Complete (9/9 = 100%)

```
Phase 1 ✅  Phase 2 ✅  Phase 3 ✅  Phase 4 ✅  Phase 5 ✅  Phase 6 ✅  Phase 7 ✅  Phase 8 ✅  Phase 9 ✅
Problem     OpenAPI &   Provider    Consumer    Contract    Breaking    AI Agent    CI/CD       Reporting &
Statement   SCC Study   API Built   API Built   Testing     Change      (12 mod)   Pipeline    Monitoring
                                                Working     Detected               (13 jobs)   Complete
```

### Technical Achievements

✅ Provider API — Full CRUD with OpenAPI spec, Jakarta validation, error handling  
✅ Consumer API — Inter-service communication, enriched responses  
✅ 12 Contract YAMLs — Both positive and negative scenarios with strict assertions  
✅ Spring Cloud Contract — Auto-generated tests, WireMock stubs, by_command matchers  
✅ AI Agent (12 modules) — Generate, detect, analyze, fix, notify, validate  
✅ Negative contract testing — Validates error handling (400/404 responses)  
✅ Backward compatibility gate — Blocks breaking MR changes automatically  
✅ Root cause analysis — AI-powered WHAT/WHY/HOW for every failure  
✅ Multi-channel notifications — Teams/Slack/GitLab/SMTP with adaptive cards  
✅ MR validation comments — Formatted summary posted on every merge request  
✅ Flask dashboard — Live metrics, coverage charts, RCA display  
✅ GitLab CI/CD — 13 jobs, 5 stages, gated deployment, caching  
✅ Auto-fix with MR — One-click contract regeneration  

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Java + Spring Boot | 25 / 3.3.8 |
| Contract Testing | Spring Cloud Contract | 4.1.5 |
| API Spec | OpenAPI / Swagger | 3.0 |
| Build Tool | Apache Maven | 3.9.12 |
| Mock Server | WireMock | (managed) |
| HTTP Testing | REST Assured | (managed) |
| AI Agent | Python + Flask + requests + PyYAML | 3.14 |
| CI/CD | GitLab CI | 13 jobs, 5 stages |
| Notifications | Teams + Slack + GitLab + SMTP | Multi-channel |
| Version Control | Git (GitHub + GitLab) | — |


# ═══════════════════════════════════════════════════════════════
# SLIDE 12: FUTURE ENHANCEMENTS & THANK YOU
# ═══════════════════════════════════════════════════════════════

## Roadmap & Future Enhancements

### Potential Next Steps

| # | Enhancement | Business Value |
|---|------------|----------------|
| 1 | **Multi-provider support** | Monitor 10+ APIs from a single agent instance |
| 2 | **Performance contracts** | SLAs in contracts (e.g., response < 200ms) |
| 3 | **LLM-powered generation** | Smarter sample values using AI models |
| 4 | **Historical trending dashboard** | Track coverage changes over weeks/months |
| 5 | **Kubernetes deployment** | Helm charts for cloud-native containerized deployment |
| 6 | **Contract versioning** | Major/minor versions for gradual consumer migration |

### Key Takeaway

> **This system shifts integration failure detection from production (expensive, painful, user-impacting) to build time (cheap, fast, developer-friendly).**
>
> For a team running 10+ microservices with 50+ endpoints, this approach prevents the majority of production integration failures — fully automated, zero manual effort.

---

## Thank You

**Druva S Kumar**  
DevOps Intern | Bottomline Technologies  
January 2026 – June 2026

**Repository:** GitHub + GitLab (Mirrored)  
**Dashboard:** http://localhost:5050  
**Questions?**


# ═══════════════════════════════════════════════════════════════
# DESIGN GUIDELINES FOR THE PPT
# ═══════════════════════════════════════════════════════════════

## Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Dark Blue | #1E3A5F | Primary, headings, borders |
| Green | #2ECC71 | Success, passing tests, healthy |
| Red | #E74C3C | Failure, breaking changes, blocked |
| Purple | #9B59B6 | AI Agent, Python, intelligence |
| Orange | #F39C12 | CI/CD, pipeline, automation |
| Light Blue | #3498DB | Provider API, Java, Spring |
| Dark Teal | #16A085 | Consumer API |
| White/Gray | #F8F9FA | Background |
| Dark Text | #2C3E50 | Body text |

## Font Suggestions
- **Headings:** Montserrat Bold or Poppins Bold (24-36pt)
- **Body:** Inter, Roboto, or Open Sans (14-18pt)
- **Code:** JetBrains Mono or Fira Code (12-14pt)

## Layout Tips per Slide

| Slide | Layout Tip |
|-------|-----------|
| 1 (Title) | Clean, professional. Tech badge icons across bottom. |
| 2 (Problem) | Left: scenario diagram. Right: pain points as icon list. |
| 3 (Solution) | YAML snippet prominently displayed. Three-layer table below. |
| 4 (Architecture) | FULL SLIDE — this is the centerpiece. Use landscape orientation. |
| 5 (SCC) | Split: Provider flow left, Consumer flow right. Contract table below. |
| 6 (AI Agent) | Module grid diagram (4 quadrants). CLI table below. |
| 7 (CI/CD) | Pipeline flow diagram (horizontal stages). Features table. |
| 8 (Notifications) | Cascade diagram (4 channels). Teams card mockup. |
| 9 (RCA) | Category table top. RCA output as code block bottom. |
| 10 (Demo) | Before/After with red/green highlighting. Impact table. |
| 11 (Results) | Large metric cards (bold numbers). Phase timeline bar. |
| 12 (Future) | Roadmap table. Key takeaway quote. Thank you. |

## General Design Rules
- ONE key message per slide
- Tables > paragraphs (always)
- Diagrams > bullet points
- Before/After with red/green color coding
- Metrics as large bold numbers in colored cards
- Keep animations minimal — simple fade-ins only
- Add tech logos as small badges where relevant
- Use monospace font for code/YAML snippets
