# Contract Testing Automation with AI Agents — Presentation Content
# 3 Slides / Pages

---

# ═══════════════════════════════════════════════════════════════
# SLIDE 1: THE PROBLEM & SOLUTION
# Title: "Contract Testing Automation with AI Agents"
# ═══════════════════════════════════════════════════════════════

## Slide Title
**Contract Testing Automation with AI Agents**
Automated Consumer-Provider API Contract Verification

---

### THE PROBLEM (Left Section)

**"Microservices Break Each Other Silently"**

In microservices architecture, services communicate over APIs.
When one team changes their API, other teams' services break — silently, in production.

**Real-World Scenario:**
```
Team A (User Service)           Team B (Order Service)
─────────────────────           ──────────────────────
Renames "name" → "fullName"     Expects response with "name"
Updates their own tests ✅       Doesn't know about change ❌
Deploys to production ✅         Deploys to production ✅
                                 💥 BREAKS IN PRODUCTION
```

**Key Pain Points:**
• Manual contract testing is error-prone → Integration failures reach production
• APIs updated frequently without contract updates → Consumer apps break silently
• No automated CI/CD verification → Breaking changes deployed unknowingly
• Contract file maintenance is labor-intensive → Developers skip updates
• Slow identification of violations → Extended downtime & debugging

---

### THE SOLUTION (Right Section)

**"Catch Breaking Changes at Build Time, Not in Production"**

A **contract** = formal YAML agreement between Provider & Consumer:
_"When the Consumer sends THIS request, the Provider MUST return THIS response."_

```yaml
request:
  method: GET
  url: /api/users/1
response:
  status: 200
  body:
    id: 1
    name: "Alice Johnson"       ← If removed/renamed,
    email: "alice@example.com"     contract test FAILS
    role: "ADMIN"                  → deployment BLOCKED
```

**Result:** Integration failure detection shifts from
**Production** (expensive, painful) → **Build Time** (cheap, fast)

---

### ARCHITECTURE DIAGRAM (Bottom Section — Full Width)

```
┌────────────────────────────────────────────────────────────────────┐
│                      GITLAB CI/CD PIPELINE                         │
│   Build → Contract Verify → Drift Check → Report → Deploy (gated) │
└──────────┬──────────────────────┬──────────────────┬───────────────┘
           │                      │                  │
  ┌────────▼─────────┐  ┌────────▼────────┐  ┌──────▼──────────────┐
  │ PROVIDER API     │  │ CONTRACT FILES  │  │ AI AGENT (Python)   │
  │ User Service     │  │ (YAML)          │  │                     │
  │ Spring Boot:8080 │  │                 │  │ • Reads OpenAPI spec│
  │                  │  │ 5 Contracts     │  │ • Generates contracts│
  │ GET  /api/users  │  │ covering all    │  │ • Detects API drift │
  │ POST /api/users  │  │ 5 endpoints     │  │ • Health reports    │
  │ PUT  /api/users  │  │                 │  │ • CI/CD pipeline gen│
  │ DEL  /api/users  │  │ Auto-generated  │  │                     │
  └────────┬─────────┘  │ by AI Agent ▲   │  └─────────────────────┘
           │            └─────────────┘   │
  ┌────────▼─────────┐                    │
  │ CONSUMER API     │      OpenAPI Spec  │
  │ Order Service    │◄───────────────────┘
  │ Spring Boot:8081 │    /v3/api-docs
  │                  │
  │ Tests via WireMock│
  │ stubs from       │
  │ contracts        │
  └──────────────────┘
```

---

### SUGGESTED VISUAL LAYOUT FOR SLIDE 1:
- **Top Banner:** Title + subtitle + tech logo badges (Java, Spring Boot, Python, GitLab)
- **Left Column (40%):** The Problem — scenario diagram + pain points as icons with short text
- **Right Column (40%):** The Solution — contract YAML snippet + key benefit callout
- **Bottom Strip (20%):** Simplified architecture diagram showing the 4 components connected


# ═══════════════════════════════════════════════════════════════
# SLIDE 2: WHAT WAS BUILT — TECHNICAL DEEP DIVE
# Title: "How It Works — End to End"
# ═══════════════════════════════════════════════════════════════

## Slide Title
**How It Works — From Code to CI/CD Pipeline**

---

### SECTION A: TWO REAL MICROSERVICES (Top Left)

**Provider: User Service (Port 8080)**
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/users | GET | List all users |
| /api/users/{id} | GET | Get user by ID |
| /api/users | POST | Create new user |
| /api/users/{id} | PUT | Update user |
| /api/users/{id} | DELETE | Delete user |

Built with: Spring Boot 3.3.8 • Java 25 • REST • OpenAPI/Swagger
Features: Jakarta Validation, Global Exception Handling, In-Memory Store

**Consumer: Order Service (Port 8081)**
• Calls Provider via RestTemplate to enrich orders with user data
• Tests against WireMock stubs (no real Provider needed during test)
• Demonstrates real inter-service dependency

---

### SECTION B: CONTRACT TESTING FLOW (Top Right)

**Spring Cloud Contract — The Verification Engine**

```
   Contract YAML Files (shared agreement)
            │
   ┌────────┴────────┐
   ▼                 ▼
PROVIDER SIDE     CONSUMER SIDE
SCC Verifier      Stub Runner
   │                 │
   ▼                 ▼
Auto-generates    Starts WireMock
JUnit tests       (fake Provider)
   │                 │
   ▼                 ▼
Tests REAL API    Consumer tests
   │              against stubs
   ▼                 │
✅ Pass → Stubs JAR → ▼
❌ Fail → BUILD BLOCKED  ✅ Pass / ❌ Fail
```

**5 Contract YAML Files covering 100% of API endpoints:**
1. should_return_user_by_id.yml (GET by ID)
2. should_return_all_users.yml (GET all)
3. should_create_a_new_user.yml (POST)
4. should_update_user_by_id.yml (PUT) ← AI-Generated
5. should_delete_user_by_id.yml (DELETE) ← AI-Generated

---

### SECTION C: AI AGENT — THE AUTOMATION ENGINE (Bottom Left)

**Python AI Agent — 5 CLI Commands, 7 Internal Tools**

| Command | What It Does |
|---------|-------------|
| `python main.py generate` | Reads OpenAPI spec → generates contract YAMLs |
| `python main.py drift` | Compares contracts vs live API → finds mismatches |
| `python main.py report` | Full health report with coverage % & remediation |
| `python main.py validate` | CI-friendly check → exit code 0 (pass) / 2 (fail) |
| `python main.py ci` | Generates complete .gitlab-ci.yml pipeline |

**Under the Hood (7 Modules):**
• **spec_reader.py** — Fetches & parses OpenAPI spec, resolves $ref references
• **contract_generator.py** — Converts endpoints to SCC YAML with smart sample values
• **drift_detector.py** — Detects uncovered, orphaned, and schema-drifted contracts
• **report_generator.py** — Coverage bars, health status, remediation steps
• **ci_config_generator.py** — Multi-stage pipeline with caching & artifact passing
• **notifier.py** — Team notifications via Slack webhooks + GitLab Issue Notes
• **mr_creator.py** — Auto-creates GitLab Merge Requests with fixed contracts

---

### SECTION D: CI/CD PIPELINE (Bottom Right)

**AI-Generated GitLab CI Pipeline — 9 Jobs, 5 Stages**

```
 STAGE 1: BUILD     STAGE 2: TEST           STAGE 3: REPORT    STAGE 4: FIX     STAGE 5: DEPLOY
┌──────────────┐ ┌──────────────────────┐ ┌─────────────────┐ ┌────────────┐ ┌──────────────┐
│provider-build│ │provider-contract-test│ │ contract-report │ │auto-fix-   │ │              │
│  mvn compile │▶│  mvn install (SCC)  │ │  JUnit XMLs     │ │contracts   │ │   deploy     │
└──────────────┘ │  → stubs JAR ───────┤▶│  Summary        │ │(manual)    │ │  GATED by    │
┌──────────────┐ │                     │ └─────────────────┘ │ → MR       │ │  test success│
│consumer-build│ │consumer-contract-test│ ┌─────────────────┐ └────────────┘ │  main only   │
│  mvn compile │▶│  mvn test (stubs)   │ │ notify-team     │                └──────────────┘
└──────────────┘ │                     │ │ Slack + Email   │
                 │ai-agent-drift-check │▶│ via Issue Notes │
                 │  python validate    │ └─────────────────┘
                 └─────────────────────┘
```

**Key Features:**
• Maven dependency caching between runs
• Provider stubs JAR passed as artifact to Consumer test job
• JUnit reports integrated with GitLab MR UI
• Team notifications — Slack + GitLab Issue Notes (auto-email subscribers)
• Auto-fix job — one-click MR creation with regenerated contracts
• Deployment blocked if ANY contract test fails

---

### SUGGESTED VISUAL LAYOUT FOR SLIDE 2:
- **Quadrant layout** — 4 equal boxes, each covering one section (A, B, C, D)
- Use **icons/emojis** for visual appeal: ☕ Java, 🐍 Python, 🔄 CI/CD, 📋 Contracts
- Color code: Provider = Blue, Consumer = Green, AI Agent = Purple, CI/CD = Orange
- Each section should have a **bold header** and **compact content** (tables/diagrams preferred over paragraphs)


# ═══════════════════════════════════════════════════════════════
# SLIDE 3: RESULTS, DEMO & NEXT STEPS
# Title: "Results & What's Next"
# ═══════════════════════════════════════════════════════════════

## Slide Title
**Results, Live Demo Proof & Roadmap**

---

### SECTION A: KEY METRICS & RESULTS (Top — Full Width Banner)

| Metric | Value |
|--------|-------|
| **API Coverage** | 100% — all 5 endpoints have contracts |
| **Provider Tests** | 6/6 passing (5 contract + 1 smoke) |
| **Consumer Tests** | 2/2 passing (1 contract + 1 smoke) |
| **AI-Generated Contracts** | 2 of 5 (PUT update + DELETE) |
| **CI/CD Pipeline** | 9 jobs across 5 stages — fully automated |
| **Health Status** | ✅ HEALTHY — no drift, no orphans |
| **Breaking Change Detection** | Instant — caught at build time, not production |
| **Notification Channels** | 2 (Slack + GitLab Issue Notes with auto-email) |
| **Auto-Fix Capability** | One-click MR creation with regenerated contracts |

---

### SECTION B: LIVE PROOF — BREAKING CHANGE CAUGHT (Middle Left)

**Demo: Rename `name` → `fullName` in contract YAML**

```
BEFORE                              AFTER
───────                             ─────
response:                           response:
  body:                               body:
    name: "Alice Johnson" ✅            fullName: "Alice Johnson" ❌

$ mvn clean test                    $ mvn clean test
BUILD SUCCESS ✅                     BUILD FAILURE ❌

                                    ContractVerifierTest FAILED
                                    JSON path [$.fullName] → null
                                    Expected: "Alice Johnson"
                                    
                                    → DEPLOYMENT BLOCKED 🚫
```

**What This Proves:**

| Without Contract Testing | With Contract Testing |
|---|---|
| Breaking change reaches production 💥 | Build fails immediately ❌ |
| Consumers break silently | Both sides catch drift instantly |
| Hours/days of debugging | Instant feedback on what broke |
| Manual team coordination | Fully automated verification |

---

### SECTION C: TECH STACK SUMMARY (Middle Right)

**Technologies Used:**

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Java + Spring Boot | 25 / 3.3.8 |
| **Contract Testing** | Spring Cloud Contract | 4.1.5 |
| **API Spec** | OpenAPI / Swagger | 3.0 |
| **Build Tool** | Apache Maven | 3.9.12 |
| **Mock Server** | WireMock | (managed) |
| **HTTP Testing** | REST Assured | (managed) |
| **AI Agent** | Python + requests + PyYAML + Flask | 3.14 |
| **CI/CD** | GitLab CI | 9 jobs, 5 stages |
| **Notifications** | Slack + GitLab Issue Notes | Auto-email |
| **Version Control** | Git (GitHub + GitLab) | — |

---

### SECTION D: PROJECT PHASES & ROADMAP (Bottom — Full Width)

**Completed Phases (9/9 = 100%):**

```
Phase 1 ✅  Phase 2 ✅  Phase 3 ✅  Phase 4 ✅  Phase 5 ✅  Phase 6 ✅  Phase 7 ✅  Phase 8 ✅  Phase 9 ✅
Problem     OpenAPI &   Provider    Consumer    Contract    Breaking    AI Agent    CI/CD       Reporting &
Statement   SCC Study   API Built   API Built   Testing     Change      Complete    Pipeline    Notifications
                                                Working     Demo                   (Live)      Complete
```

**What's Done:**
✅ Provider API (User Service) — full CRUD with validation & OpenAPI
✅ Consumer API (Order Service) — calls Provider, enriches orders
✅ 5 contract YAML files — 100% endpoint coverage
✅ Spring Cloud Contract — auto-generated tests, WireMock stubs
✅ Breaking change detection — proven with live demo
✅ AI Agent — generates contracts, detects drift, health reports, CI pipeline
✅ GitLab CI pipeline — 9 jobs, 5 stages, gated deployment
✅ Team notifications — Slack + GitLab Issue Notes (auto-email subscribers)
✅ Auto-fix with MR creation — one-click contract regeneration
✅ Flask web dashboard — visual contract health at a glance

**Future Enhancements (Optional Roadmap):**
🔮 Multi-provider support (multiple APIs monitored by single agent)
🔮 Historical trend tracking (coverage over time)
🔮 LLM-powered contract generation (smarter sample values)
🔮 Kubernetes deployment with Helm charts

---

### SUGGESTED VISUAL LAYOUT FOR SLIDE 3:
- **Top Banner (25%):** Metrics in large, bold numbers with colored cards/badges
- **Middle Left (35%):** Before/After comparison with red/green highlighting
- **Middle Right (15%):** Tech stack as a compact icon grid or vertical list with logos
- **Bottom Strip (25%):** Phase timeline as a horizontal progress bar (green filled for completed, blue for in-progress, gray for remaining)
- End with a **"Questions?"** or **"Thank You"** callout in the corner


# ═══════════════════════════════════════════════════════════════
# DESIGN TIPS FOR THE PPT
# ═══════════════════════════════════════════════════════════════

## Color Palette Suggestion
- **Primary:** #1E3A5F (Dark Blue — Professional)
- **Accent 1:** #2ECC71 (Green — Success/Passing)
- **Accent 2:** #E74C3C (Red — Failure/Breaking)
- **Accent 3:** #9B59B6 (Purple — AI Agent)
- **Accent 4:** #F39C12 (Orange — CI/CD Pipeline)
- **Background:** #FFFFFF or #F8F9FA (Clean White/Light Gray)
- **Text:** #2C3E50 (Dark Gray)

## Font Suggestions
- **Headings:** Montserrat Bold or Poppins Bold
- **Body:** Inter, Roboto, or Open Sans
- **Code snippets:** JetBrains Mono or Fira Code

## General Tips
- Keep text minimal — use diagrams, tables, and icons instead of paragraphs
- Use the architecture diagram as a centerpiece on Slide 1
- Use before/after comparison on Slide 3 with red/green color coding
- Add your name and date on Slide 1 (subtitle area)
- Add tech logos (Spring Boot, Java, Python, GitLab) as small icons
- Keep animations minimal — just simple fade-ins if any
