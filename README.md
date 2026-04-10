# Contract Testing Automation with AI Agents

> Automated consumer-provider API contract verification powered by Spring Cloud Contract, OpenAPI specifications, and AI-driven contract generation.

[![Java](https://img.shields.io/badge/Java-25-orange)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.5-brightgreen)](https://spring.io/projects/spring-boot)
[![Spring Cloud Contract](https://img.shields.io/badge/Spring%20Cloud%20Contract-4.1.3-blue)](https://spring.io/projects/spring-cloud-contract)
[![Maven](https://img.shields.io/badge/Maven-3.9.12-red)](https://maven.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Solution Architecture](#solution-architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Phase 1: Understanding the Problem Statement](#phase-1-understanding-the-problem-statement)
- [Phase 2: Understanding OpenAPI/Swagger & Spring Cloud Contract](#phase-2-understanding-openapiswagger--spring-cloud-contract)
- [Phase 3: Provider API — User Service (Spring Boot)](#phase-3-provider-api--user-service-spring-boot)
- [Phase 4: Consumer API — Order Service (Spring Boot)](#phase-4-consumer-api--order-service-spring-boot)
- [Phase 5: Contract Testing with Spring Cloud Contract](#phase-5-contract-testing-with-spring-cloud-contract)
- [Phase 6: Breaking the Contract — Proving It Works](#phase-6-breaking-the-contract--proving-it-works)
- [Phase 7: AI Agent — Contract Generator (Python)](#phase-7-ai-agent--contract-generator-python)
- [Phase 8: CI/CD Pipeline (GitLab CI)](#phase-8-cicd-pipeline-gitlab-ci)
- [Phase 9: Reporting & Dashboard](#phase-9-reporting--dashboard)
- [Quick Start Guide](#quick-start-guide)
- [API Documentation](#api-documentation)
- [Glossary](#glossary)
- [License](#license)

---

## Project Overview

This project implements **automated contract testing** for REST APIs. It ensures that when an API provider changes its endpoints, any breaking changes are caught **before deployment** — automatically.

### What is Contract Testing?

A "contract" is a formal agreement between an API **provider** (the server) and a **consumer** (the client). It specifies:
- What requests the consumer will send
- What responses the provider must return

Contract testing verifies that the provider **actually fulfills** these contracts, preventing integration failures in production.

### What makes this project special?

1. **Two real microservices** — a Provider (User Service) and a Consumer (Order Service) that communicate over HTTP, demonstrating real-world inter-service dependencies
2. **Spring Cloud Contract** — auto-generates tests from YAML contract files on the Provider side, and creates WireMock stubs for the Consumer side
3. **Breaking change detection** — when someone modifies the API in a way that violates contracts, tests fail immediately, blocking bad deployments
4. **AI-powered contract generation** — a Python agent reads the OpenAPI spec and automatically generates/updates contract files

---

## Problem Statement

In a microservices architecture, services communicate over APIs. When one team changes their API, **other teams' services can break silently**. This project exists to solve that problem.

| Problem | Impact |
|---------|--------|
| Manual contract testing is difficult and error-prone | Integration failures reach production |
| APIs are updated frequently without contract updates | Consumer applications break silently |
| No automated verification in CI/CD pipeline | Breaking changes deployed unknowingly |
| Contract file maintenance is labor-intensive | Developers skip contract updates |
| Slow identification of contract violations | Extended downtime and debugging time |

### Real-World Example

Imagine this scenario:
1. **Team A** runs the User Service (Provider) with a field called `name`
2. **Team B** runs the Order Service (Consumer) that calls the User Service and expects `name`
3. Team A renames `name` → `fullName` in a "harmless refactor"
4. Team A's own tests pass (they updated their tests)
5. **Team B's Order Service breaks in production** — it expects `name` but gets `fullName`

**Contract testing catches this at build time**, before anyone deploys anything.

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GITLAB CI/CD PIPELINE                     │
│  Build → Contract Verify → Report → Deploy (blocked on fail)│
└────────────────────┬────────────────────┬───────────────────┘
                     │                    │
    ┌────────────────▼────────┐  ┌───────▼────────────────┐
    │  PROVIDER (User Service)│  │   CONTRACT FILES       │
    │  Spring Boot :8080      │  │   (YAML definitions)   │
    │                         │  │                        │
    │  GET  /api/users        │  │  Requests + Responses  │
    │  POST /api/users        │  │  Verified by SCC       │
    │  PUT  /api/users/{id}   │  │                        │
    │  DELETE /api/users/{id} │  │  Auto-generated by     │
    └────────────┬────────────┘  │  AI Agent              │
                 │               └────────▲───────────────┘
    ┌────────────▼────────────┐          │
    │  CONSUMER (Order Service)│  ┌──────┴────────────────┐
    │  Spring Boot :8081      │  │  AI AGENT (Python)     │
    │                         │  │                        │
    │  Calls Provider API     │  │  • Reads OpenAPI spec  │
    │  via RestTemplate       │  │  • Generates contracts │
    │  Tests via WireMock     │  │  • Detects API drift   │
    │  stubs from contracts   │  │  • Suggests fixes      │
    └─────────────────────────┘  └────────────────────────┘
                 ▲
    ┌────────────┴────────────┐
    │   OPENAPI SPEC          │
    │   (Auto-generated)      │
    │   /v3/api-docs          │
    └─────────────────────────┘
```

### How the pieces fit together

```
Provider contracts (YAML)
    │
    ├──► [mvn install on Provider] ──► Auto-generated JUnit tests ──► Verifies Provider API
    │                                                                    │
    │                                                              Stubs JAR (WireMock)
    │                                                                    │
    └──► [mvn test on Consumer] ──► StubRunner loads stubs ──► Consumer tests pass
                                     (no real Provider needed)
```

---

## Project Structure

```
contract-testing-automation/
│
├── README.md                          ← You are here
├── .gitignore                         ← Files Git should ignore
├── DEMO_SCRIPT.txt                    ← Demo script for presenting this project
│
├── provider-api/                      ← Provider: User Service (Spring Boot, port 8080)
│   ├── pom.xml                        ← Maven config + SCC Verifier plugin
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/contracttest/provider/
│   │   │   │   ├── ProviderApplication.java       ← App entry point
│   │   │   │   ├── config/
│   │   │   │   │   └── OpenApiConfig.java          ← OpenAPI/Swagger config
│   │   │   │   ├── controller/
│   │   │   │   │   └── UserController.java         ← REST endpoints (CRUD)
│   │   │   │   ├── model/
│   │   │   │   │   ├── User.java                   ← User data model
│   │   │   │   │   └── ErrorResponse.java          ← Error response model
│   │   │   │   ├── service/
│   │   │   │   │   └── UserService.java            ← Business logic
│   │   │   │   └── exception/
│   │   │   │       └── GlobalExceptionHandler.java ← Centralized error handling
│   │   │   └── resources/
│   │   │       └── application.yml                 ← App config (port 8080)
│   │   └── test/
│   │       ├── java/com/contracttest/provider/
│   │       │   ├── ProviderApplicationTests.java   ← Smoke test
│   │       │   └── BaseContractTest.java           ← Base class for SCC tests
│   │       └── resources/
│   │           └── contracts/user/                 ← Contract YAML files
│   │               ├── should_return_user_by_id.yml
│   │               ├── should_return_all_users.yml
│   │               ├── should_create_a_new_user.yml
│               ├── should_update_user_by_id.yml  ← AI-generated
│               └── should_delete_user_by_id.yml  ← AI-generated
│   └── target/                        ← Build output (git-ignored)
│
├── consumer-api/                      ← Consumer: Order Service (Spring Boot, port 8081)
│   ├── pom.xml                        ← Maven config + SCC Stub Runner
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/contracttest/consumer/
│   │   │   │   ├── ConsumerApplication.java        ← App entry point
│   │   │   │   ├── config/
│   │   │   │   │   ├── OpenApiConfig.java          ← OpenAPI/Swagger config
│   │   │   │   │   └── RestTemplateConfig.java     ← HTTP client bean
│   │   │   │   ├── controller/
│   │   │   │   │   └── OrderController.java        ← REST endpoints (CRUD)
│   │   │   │   ├── model/
│   │   │   │   │   ├── Order.java                  ← Order data model
│   │   │   │   │   ├── OrderResponse.java          ← Order + User enriched
│   │   │   │   │   ├── UserDTO.java                ← DTO for Provider's User
│   │   │   │   │   └── ErrorResponse.java          ← Error response model
│   │   │   │   ├── service/
│   │   │   │   │   └── OrderService.java           ← Business logic
│   │   │   │   ├── client/
│   │   │   │   │   └── UserServiceClient.java      ← Calls Provider API
│   │   │   │   └── exception/
│   │   │   │       └── GlobalExceptionHandler.java ← Error handling
│   │   │   └── resources/
│   │   │       └── application.yml                 ← App config (port 8081)
│   │   └── test/
│   │       └── java/com/contracttest/consumer/
│   │           ├── ConsumerApplicationTests.java   ← Smoke test
│   │           └── UserServiceClientContractTest.java ← Consumer contract test
│   └── target/                        ← Build output (git-ignored)
│
├── ai-agent/                          ← Python AI Agent (Phase 7-9)
│   ├── main.py                        ← CLI entry point (generate/drift/report/validate/ci/dashboard)
│   ├── dashboard.py                   ← Flask Contract Health Dashboard (Phase 9)
│   ├── requirements.txt               ← Python dependencies (requests, pyyaml, flask)
│   ├── README.md                      ← AI Agent documentation
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── spec_reader.py             ← Fetches & parses OpenAPI specs
│   │   ├── contract_generator.py      ← Generates SCC YAML contracts
│   │   ├── drift_detector.py          ← Detects contract drift
│   │   ├── report_generator.py        ← Generates reports & remediation
│   │   └── ci_config_generator.py     ← Generates GitLab CI pipeline
│   ├── templates/
│   │   └── dashboard.html             ← Dashboard UI template (Jinja2)
│   ├── reports/                       ← Generated reports & dashboard history
│   └── tests/
│       └── __init__.py
│
└── .gitlab-ci.yml                     ← CI/CD pipeline (AI-generated)
```

---

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| **Java** | 25 | Programming language for Provider & Consumer APIs |
| **Spring Boot** | 3.2.5 | Framework for building REST APIs |
| **Spring Cloud Contract** | 4.1.3 | Contract testing framework (Verifier + Stub Runner) |
| **Spring Cloud BOM** | 2023.0.3 | Dependency version management |
| **REST Assured** | (managed) | HTTP assertions for contract test verification |
| **WireMock** | (managed) | Mock server for Consumer-side contract stubs |
| **Maven** | 3.9.12 | Build tool and dependency manager |
| **springdoc-openapi** | 2.5.0 | Auto-generates OpenAPI 3.0 specs from code |
| **Jakarta Validation** | (managed) | Request body validation annotations |
| **RestTemplate** | (managed) | HTTP client for inter-service communication |
| **Python** | 3.14 | Language for the AI Agent |
| **requests** | 2.32 | HTTP client (Python, for fetching OpenAPI spec) |
| **PyYAML** | 6.0 | YAML parsing/generation (Python) |
| **Flask** | 3.1 | Contract Health Dashboard web framework (Python) |
| **GitLab CI** | — | CI/CD pipeline automation |
| **OpenAPI/Swagger** | 3.0 | API specification standard |

---

## Prerequisites

Before running this project, ensure you have:

- [x] **Java JDK 17+** → [Download](https://www.oracle.com/java/technologies/downloads/)
- [x] **Apache Maven 3.8+** → [Download](https://maven.apache.org/download.cgi)
- [x] **Git** → [Download](https://git-scm.com/downloads)
- [x] **Python 3.10+** → [Download](https://www.python.org/downloads/)
- [ ] **GitHub Account** → [Sign Up](https://github.com/join)
- [ ] **GitLab Account** → [Sign Up](https://gitlab.com/users/sign_up)

Verify your setup:

```bash
java -version       # Should show 17+ (e.g., 25.0.2)
mvn -version        # Should show 3.8+ (e.g., 3.9.12)
git --version       # Should show any recent version
```

---

## Phase 1: Understanding the Problem Statement

> **Status: ✅ COMPLETED**

Before writing any code, I studied the core problem that contract testing solves.

### The Problem: Microservices Break Each Other Silently

In modern software, applications are split into **microservices** — small, independent services that talk to each other over HTTP APIs. For example:

- A **User Service** manages user data (create, read, update, delete users)
- An **Order Service** manages orders and needs user information — so it **calls** the User Service's API

This creates a **dependency**: the Order Service depends on the User Service's API to work correctly.

### What Goes Wrong Without Contract Testing?

```
  Team A (User Service)              Team B (Order Service)
  ─────────────────────              ────────────────────────
  Renames "name" → "fullName"       Expects response with "name"
  Updates their own tests ✅         Doesn't know about the change ❌
  Deploys to production ✅           Deploys to production ✅
                                     💥 BREAKS — gets "fullName"
                                        but expects "name"
```

The core issues identified:

| # | Issue | Why It Matters |
|---|-------|----------------|
| 1 | **No formal agreement** between services about API shape | Either team can change anything without coordination |
| 2 | **Integration tests are expensive** and often skipped | They require both services running simultaneously |
| 3 | **API changes are invisible** to consumers | No notification system when APIs change |
| 4 | **Manual testing doesn't scale** | With 10+ services, manually checking every combination is impossible |
| 5 | **Breaking changes reach production** | By the time anyone notices, users are already affected |

### The Solution: Contract Testing

A **contract** is a YAML file that says:

> _"When the Consumer sends THIS request, the Provider MUST return THIS response."_

```yaml
# Example: "The Order Service expects this from the User Service"
request:
  method: GET
  url: /api/users/1
response:
  status: 200
  body:
    id: 1
    name: "Alice Johnson"       # ← If Provider removes/renames this field,
    email: "alice@example.com"  #   the contract test FAILS, and the build
    role: "ADMIN"               #   is BLOCKED before deployment
```

- The **Provider** runs these contracts as tests during every build
- If the Provider's actual response doesn't match → **BUILD FAILS** → deployment blocked
- The **Consumer** gets auto-generated WireMock stubs from these contracts to test against
- Both sides are always in sync because they share the same contract files

### Key Takeaway

**Contract testing shifts integration failure detection from production (expensive, painful) to build time (cheap, fast).**

---

## Phase 2: Understanding OpenAPI/Swagger & Spring Cloud Contract

> **Status: ✅ COMPLETED**

Before implementing, I researched the two key technologies that power this project.

### OpenAPI / Swagger — The API Specification Standard

**OpenAPI** (formerly Swagger) is a specification format for describing REST APIs. Instead of reading source code to understand an API, you get a machine-readable JSON/YAML document that describes every endpoint.

#### What OpenAPI provides:
- Every endpoint URL, HTTP method, and description
- Request parameters, headers, and body schemas
- Response formats for every status code (200, 400, 404, etc.)
- Data types and validation rules

#### How we use it in this project:
- **springdoc-openapi** library auto-generates the OpenAPI spec from Java annotations
- Available at `http://localhost:8080/v3/api-docs` when the Provider runs
- The **Swagger UI** at `/swagger-ui.html` lets you interactively test the API
- The AI Agent _(Phase 7)_ will read this spec to auto-generate contracts

#### Example: What the auto-generated OpenAPI spec looks like

```json
{
  "openapi": "3.0.1",
  "paths": {
    "/api/users/{id}": {
      "get": {
        "summary": "Get user by ID",
        "parameters": [
          { "name": "id", "in": "path", "required": true, "schema": { "type": "integer" } }
        ],
        "responses": {
          "200": {
            "description": "User found",
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/User" }
              }
            }
          },
          "404": { "description": "User not found" }
        }
      }
    }
  }
}
```

### Spring Cloud Contract (SCC) — The Testing Framework

**Spring Cloud Contract** is a framework by Spring (Pivotal/VMware) that makes contract testing work in the Java/Spring ecosystem.

#### The Two Sides of SCC:

| Side | Component | What It Does |
|------|-----------|--------------|
| **Provider** | SCC Verifier | Reads contract YAML files → auto-generates JUnit tests → runs them against the real API |
| **Consumer** | SCC Stub Runner | Downloads Provider's stubs JAR → starts WireMock (fake server) → Consumer tests against stubs |

#### How the Flow Works:

```
                    Contract YAML Files
                    (shared agreement)
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

#### Key Concepts Learned:

| Concept | Description |
|---------|-------------|
| **Contract YAML** | Defines expected request/response pairs in `src/test/resources/contracts/` |
| **Base Test Class** | Sets up the test environment (e.g., `RestAssuredMockMvc.standaloneSetup(controller)`) |
| **Stubs JAR** | Generated during `mvn install`, contains WireMock-compatible JSON mappings |
| **Matchers** | Allow flexible assertions (e.g., `by_regex` for dynamic values like IDs) |
| **Stub Runner** | Auto-downloads and starts WireMock with stubs, configured via `@AutoConfigureStubRunner` |

---

## Phase 3: Provider API — User Service (Spring Boot)

> **Status: ✅ COMPLETED**

The Provider API is a **User Management REST API** — the service that other microservices depend on.

### What was built

| Component | File | Purpose |
|-----------|------|---------|
| Entry Point | `ProviderApplication.java` | Spring Boot main class, runs on port **8080** |
| REST Controller | `UserController.java` | CRUD endpoints at `/api/users` with OpenAPI annotations |
| Data Model | `User.java` | User entity with Jakarta validation (`@NotBlank`, `@Email`, `@Size`) |
| Error Model | `ErrorResponse.java` | Standardized error format with `status`, `message`, `timestamp`, `fieldErrors` |
| Business Logic | `UserService.java` | In-memory store (ConcurrentHashMap) with 3 sample users |
| Error Handler | `GlobalExceptionHandler.java` | `@RestControllerAdvice` for validation errors (400) and server errors (500) |
| OpenAPI Config | `OpenApiConfig.java` | Custom API metadata for Swagger UI |
| App Config | `application.yml` | Server port, springdoc settings, logging level |

### API Endpoints

| Endpoint | Method | Description | Success | Error |
|---|---|---|---|---|
| `/api/users` | GET | List all users | 200 + User[] | — |
| `/api/users/{id}` | GET | Get user by ID | 200 + User | 404 |
| `/api/users` | POST | Create new user | 201 + User | 400 (validation) |
| `/api/users/{id}` | PUT | Update existing user | 200 + User | 400, 404 |
| `/api/users/{id}` | DELETE | Delete user | 204 (no content) | 404 |

### Sample Data (pre-loaded)

| ID | Name | Email | Role |
|----|------|-------|------|
| 1 | Alice Johnson | alice@example.com | ADMIN |
| 2 | Bob Smith | bob@example.com | USER |
| 3 | Charlie Brown | charlie@example.com | MANAGER |

### How to run the Provider

```bash
cd provider-api
mvn clean compile
mvn spring-boot:run
```

### Verify it works

| URL | What you'll see |
|---|---|
| http://localhost:8080/api/users | JSON array of all users |
| http://localhost:8080/api/users/1 | Single user (Alice) |
| http://localhost:8080/v3/api-docs | OpenAPI spec (JSON) |
| http://localhost:8080/swagger-ui.html | Interactive Swagger UI |

### Sample requests

```bash
# Get all users
curl http://localhost:8080/api/users

# Get user by ID
curl http://localhost:8080/api/users/1

# Create a new user (note the validation rules: name 2-100 chars, valid email, role required)
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Diana Prince", "email": "diana@example.com", "role": "USER"}'

# Update a user
curl -X PUT http://localhost:8080/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Updated", "email": "alice.new@example.com", "role": "ADMIN"}'

# Delete a user
curl -X DELETE http://localhost:8080/api/users/1
```

**PowerShell users** (Windows):
```powershell
# Get all users
Invoke-RestMethod -Uri http://localhost:8080/api/users | ConvertTo-Json

# Create a new user
Invoke-RestMethod -Uri http://localhost:8080/api/users -Method POST `
  -ContentType "application/json" `
  -Body '{"name": "Diana Prince", "email": "diana@example.com", "role": "USER"}' | ConvertTo-Json
```

---

## Phase 4: Consumer API — Order Service (Spring Boot)

> **Status: ✅ COMPLETED**

To demonstrate contract testing, we need **two services** that talk to each other. The Consumer (Order Service) calls the Provider (User Service) to enrich order data with user information.

### Why do we need a Consumer?

Contract testing verifies the agreement **between** services. Without a Consumer, there's nothing to test against. The Order Service represents a real-world scenario — it creates orders for users and needs to fetch user details from the Provider.

### What was built

| Component | File | Purpose |
|-----------|------|---------|
| Entry Point | `ConsumerApplication.java` | Spring Boot main class, runs on port **8081** |
| REST Controller | `OrderController.java` | CRUD endpoints at `/api/orders` |
| HTTP Client | `UserServiceClient.java` | Calls Provider's `GET /api/users/{id}` via RestTemplate |
| Order Model | `Order.java` | Order entity with validation (`@NotBlank`, `@Min`, `@DecimalMin`) |
| User DTO | `UserDTO.java` | Mirrors Provider's User model — **this IS the contract dependency** |
| Enriched Response | `OrderResponse.java` | Combines Order + User data in API responses |
| Error Model | `ErrorResponse.java` | Same format as Provider |
| Business Logic | `OrderService.java` | In-memory store, enriches orders with user data |
| Config | `RestTemplateConfig.java` | Creates `RestTemplate` bean for HTTP calls |
| Config | `application.yml` | Port 8081, `provider.api.base-url=http://localhost:8080` |

### The Key Dependency

```
Order Service (Consumer)                    User Service (Provider)
        │                                          │
        │       GET /api/users/{userId}            │
        ├─────────────────────────────────────────►│
        │                                          │
        │       { id, name, email, role }          │
        │◄─────────────────────────────────────────┤
        │                                          │
   OrderResponse = Order + UserDTO
   (enriched with user's name)
```

The `UserDTO.java` in Consumer must match the Provider's `User.java` response format. If the Provider changes its response shape, the Consumer breaks. **This is exactly what contract testing protects against.**

### API Endpoints

| Endpoint | Method | Description | Success | Error |
|---|---|---|---|---|
| `/api/orders` | GET | List all orders (enriched with user data) | 200 + OrderResponse[] | — |
| `/api/orders/{id}` | GET | Get order by ID (enriched) | 200 + OrderResponse | 404 |
| `/api/orders` | POST | Create new order | 201 + Order | 400 (validation) |
| `/api/orders/{id}` | DELETE | Delete order | 204 | 404 |

### Sample Data (pre-loaded)

| ID | Product | Qty | Price | User ID | Status |
|----|---------|-----|-------|---------|--------|
| 1 | Laptop Pro | 1 | $1299.99 | 1 (Alice) | CONFIRMED |
| 2 | Wireless Mouse | 3 | $29.99 | 2 (Bob) | PENDING |
| 3 | USB-C Monitor | 2 | $449.99 | 1 (Alice) | CONFIRMED |
| 4 | Mechanical Keyboard | 1 | $159.99 | 3 (Charlie) | PENDING |

### How to run (both services)

```bash
# Terminal 1: Start Provider (must be running first)
cd provider-api
mvn spring-boot:run

# Terminal 2: Start Consumer
cd consumer-api
mvn spring-boot:run
```

### Verify inter-service communication

```bash
# This calls the Consumer, which internally calls the Provider for user data
curl http://localhost:8081/api/orders/1
```

Expected response (notice the `userName` comes from the Provider):
```json
{
  "id": 1,
  "productName": "Laptop Pro",
  "quantity": 1,
  "price": 1299.99,
  "userId": 1,
  "status": "CONFIRMED",
  "userName": "Alice Johnson",
  "userEmail": "alice@example.com"
}
```

---

## Phase 5: Contract Testing with Spring Cloud Contract

> **Status: ✅ COMPLETED**

With both services built, we implemented **contract testing** using Spring Cloud Contract (SCC).

### What was added

#### Provider Side (SCC Verifier)

| Item | Description |
|------|-------------|
| **Dependencies** | `spring-cloud-contract-verifier`, `spring-mock-mvc` (REST Assured) added to `pom.xml` |
| **SCC Maven Plugin** | Configured in `pom.xml` with `baseClassForTests` pointing to `BaseContractTest` |
| **BaseContractTest.java** | Abstract base class that sets up `RestAssuredMockMvc.standaloneSetup(userController)` |
| **3 Contract YAML files** | Define the expected request/response pairs (see below) |

#### Consumer Side (SCC Stub Runner)

| Item | Description |
|------|-------------|
| **Dependency** | `spring-cloud-contract-stub-runner` added to `pom.xml` |
| **UserServiceClientContractTest.java** | Tests `UserServiceClient` against WireMock stubs from Provider |
| **@AutoConfigureStubRunner** | Auto-starts WireMock with Provider's stubs on port 8080 |

### The 3 Contract Files

Located in `provider-api/src/test/resources/contracts/user/`:

**1. `should_return_user_by_id.yml`** — GET /api/users/1
```yaml
request:
  method: GET
  url: /api/users/1
response:
  status: 200
  body:
    id: 1
    name: "Alice Johnson"
    email: "alice@example.com"
    role: "ADMIN"
  matchers:
    body:
      - path: $.id
        type: by_regex
        value: "[0-9]+"
      - path: $.name
        type: by_regex
        value: "[A-Za-z ]+"
      - path: $.email
        type: by_regex
        value: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      - path: $.role
        type: by_regex
        value: "(ADMIN|USER|MANAGER)"
```

**2. `should_return_all_users.yml`** — GET /api/users
```yaml
request:
  method: GET
  url: /api/users
response:
  status: 200
  body:
    - id: 1
      name: "Alice Johnson"
      email: "alice@example.com"
      role: "ADMIN"
    - id: 2
      name: "Bob Smith"
      email: "bob@example.com"
      role: "USER"
    - id: 3
      name: "Charlie Brown"
      email: "charlie@example.com"
      role: "MANAGER"
```

**3. `should_create_a_new_user.yml`** — POST /api/users
```yaml
request:
  method: POST
  url: /api/users
  headers:
    Content-Type: application/json
  body:
    name: "Dave Wilson"
    email: "dave@example.com"
    role: "USER"
response:
  status: 201
  body:
    id: 4
    name: "Dave Wilson"
    email: "dave@example.com"
    role: "USER"
  matchers:
    body:
      - path: $.id
        type: by_regex
        value: "[0-9]+"
```

### How to run contract tests

```bash
# Step 1: Build Provider and generate stubs (run from provider-api/)
cd provider-api
mvn clean install
# Result: 4 tests pass (3 auto-generated contract tests + 1 smoke test)
# Output: Stubs JAR installed to local Maven repo (~/.m2/repository)

# Step 2: Run Consumer tests against stubs (run from consumer-api/)
cd ../consumer-api
mvn clean test
# Result: 2 tests pass (1 contract test via WireMock + 1 smoke test)
# The Stub Runner auto-starts WireMock with Provider's stubs on port 8080
```

### What happens during `mvn install` on Provider

1. SCC Maven plugin reads YAML contracts from `src/test/resources/contracts/`
2. Auto-generates JUnit test classes (one test method per contract)
3. Each test calls the **real** Controller using REST Assured MockMvc
4. Asserts the actual response matches the contract
5. If all pass → generates a **stubs JAR** containing WireMock mappings
6. Installs the stubs JAR to local Maven repository (`~/.m2/`)

### What happens during `mvn test` on Consumer

1. `@AutoConfigureStubRunner` finds Provider's stubs JAR in local Maven repo
2. Starts a **WireMock** server on port 8080
3. WireMock serves responses matching the contracts
4. Consumer's `UserServiceClient` calls WireMock (thinks it's the real Provider)
5. Test verifies the client correctly parses the response into `UserDTO`

---

## Phase 6: Breaking the Contract — Proving It Works

> **Status: ✅ COMPLETED (demonstrated)**

The entire point of contract testing is to **catch breaking changes**. Here's how to prove it works by intentionally breaking a contract.

### Demo: Simulate a Breaking Change

**Scenario**: The Provider team renames the `name` field to `fullName` in the User response.

#### Step 1: Edit the contract to simulate what the Consumer expects

Open `provider-api/src/test/resources/contracts/user/should_return_user_by_id.yml` and change `name` to `fullName`:

```yaml
# BEFORE (original — what the Consumer expects)
response:
  body:
    id: 1
    name: "Alice Johnson"         # ← Consumer expects "name"

# AFTER (simulating the Provider changed the field name)
response:
  body:
    id: 1
    fullName: "Alice Johnson"     # ← Provider now returns "fullName"
```

#### Step 2: Run the Provider's contract tests

```bash
cd provider-api
mvn clean test
```

#### Step 3: Watch it FAIL ❌

```
ContractVerifierTest > should_return_user_by_id FAILED
  java.lang.AssertionError: 1 expectation failed.
  JSON path [$.fullName] doesn't match.
  Expected: Alice Johnson
  Actual: null
```

The build fails because the **actual Provider API** still returns `name`, but the contract now expects `fullName`. This mismatch is EXACTLY what would break the Consumer in production — and SCC caught it at build time.

#### Step 4: Revert the change

Change `fullName` back to `name` in the YAML file and run `mvn clean test` again — tests pass ✅.

### What This Proves

| Without Contract Testing | With Contract Testing |
|---|---|
| Breaking change reaches production | ❌ Build fails immediately |
| Consumers break silently | ✅ Both Provider and Consumer tests catch drift |
| Hours/days of debugging | ✅ Instant feedback on which contract broke |
| Manual coordination between teams | ✅ Automated verification on every build |

---

## Phase 7: AI Agent — Contract Generator (Python)

> **Status: ✅ COMPLETE**

Everything up to Phase 6 was **manual** — we wrote contract YAML files by hand, looking at the API and figuring out what the request/response should be. That works for 3 contracts, but what happens when you have 50 endpoints? Or when the API changes every sprint? Manual maintenance doesn't scale.

The AI Agent solves this by **reading the Provider's OpenAPI specification** (`/v3/api-docs`) and automatically generating contract YAML files, detecting drift when the API changes, producing health reports, and even generating CI/CD pipeline configuration.

### Why we need an AI Agent

| Manual Approach (Phase 1–6) | AI Agent Approach (Phase 7) |
|---|---|
| Write each contract YAML by hand | Agent reads OpenAPI spec and generates all contracts |
| Manually check if contracts match the API | Agent compares contracts vs spec automatically |
| No way to know if API changed without checking | Agent detects drift and tells you exactly what changed |
| Hope the CI pipeline is configured correctly | Agent generates the entire pipeline YAML |
| Takes hours for large APIs | Takes seconds for any API size |

### What was built

The AI Agent lives in `ai-agent/` and consists of **5 tools** orchestrated through a **single CLI entry point** (`main.py`). Each tool does one job well, and the CLI combines them into useful commands.

#### The 5 CLI Commands

| Command | What it does | When to use it |
|---------|-------------|----------------|
| `python main.py generate` | Fetches OpenAPI spec → generates SCC YAML contracts for all endpoints | When the API has new endpoints that need contracts |
| `python main.py drift` | Compares existing contracts vs current spec → finds mismatches | After API changes, to check if contracts are stale |
| `python main.py report` | Full health report with coverage %, recommendations, remediation steps | Regular health checks or before releases |
| `python main.py validate` | CI-friendly validation → returns exit code 0 (pass) or 1 (fail) | In CI/CD pipelines to gate deployments |
| `python main.py ci` | Generates `.gitlab-ci.yml` pipeline with build/test/report/deploy stages | One-time setup or when project structure changes |

### How to set up the AI Agent

```bash
# 1. Navigate to the ai-agent directory
cd ai-agent

# 2. Create a virtual environment (isolates Python packages from your system)
python -m venv .venv

# 3. Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# 4. Install dependencies (requests for HTTP calls, pyyaml for YAML parsing)
pip install -r requirements.txt
```

### How to use the AI Agent

**Important:** The Provider API must be running for the agent to fetch the OpenAPI spec.

```bash
# Start the Provider first (in a separate terminal)
cd provider-api
mvn spring-boot:run
# Wait for "Started ProviderApplication" message

# Then in the ai-agent directory:
cd ai-agent
.venv\Scripts\activate

# Generate contracts from the running Provider's OpenAPI spec
python main.py generate

# Generate and overwrite existing contracts
python main.py generate --overwrite

# Detect drift between contracts and spec
python main.py drift

# Full health report
python main.py report

# Save report to a file (in ai-agent/reports/)
python main.py report --save-report

# Validate contracts (CI/CD friendly — uses exit codes)
python main.py validate

# Generate GitLab CI pipeline configuration
python main.py ci

# Use a saved spec file instead of fetching from Provider
python main.py generate --spec-file path/to/openapi.json

# Use a custom Provider URL (if not running on default port)
python main.py generate --provider-url http://localhost:9090
```

### CLI Options Reference

#### Global Options (all commands)

| Option | Description | Default |
|--------|-------------|---------|
| `--provider-url` | Base URL of the running Provider API | `http://localhost:8080` |
| `--spec-file` | Path to a saved OpenAPI JSON file (skip fetching) | None |
| `--contracts-dir` | Directory containing existing contract YAML files | Auto-detected |
| `--save-report` | Save report to `ai-agent/reports/` directory | Off |

#### Generate Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--overwrite` | Overwrite existing contract files | Off (skip existing) |
| `--output-dir` | Output directory for generated contracts | Auto-detected |

#### CI Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-root` | Root directory of the project | Parent of ai-agent/ |
| `--output` | Output path for `.gitlab-ci.yml` | `project_root/.gitlab-ci.yml` |

### The 5 Tools — How Each One Works

#### Tool 1: Spec Reader (`spec_reader.py`)

**Purpose:** Fetches and parses the Provider's OpenAPI specification so other tools can work with structured data.

**How it works:**
1. Sends an HTTP GET request to `http://localhost:8080/v3/api-docs`
2. Parses the OpenAPI 3.0 JSON response
3. **Resolves `$ref` references** — OpenAPI specs use references like `"$ref": "#/components/schemas/User"` to avoid repeating schemas. The spec reader follows these references and replaces them with the actual schema definitions.
4. Extracts every endpoint with its:
   - HTTP method (GET, POST, PUT, DELETE)
   - URL path (`/api/users/{id}`)
   - Path and query parameters
   - Request body schema (for POST/PUT)
   - Response body schemas for each status code (200, 201, 400, 404, etc.)
5. Returns a structured Python list of endpoint objects that other tools consume

**Why this matters:** The OpenAPI spec is the single source of truth for the API. By reading it programmatically, we ensure contracts always reflect the real API structure — not what someone remembered to write down.

#### Tool 2: Contract Generator (`contract_generator.py`)

**Purpose:** Converts parsed OpenAPI endpoints into Spring Cloud Contract YAML files.

**How it works:**
1. Takes the parsed endpoint list from the Spec Reader
2. For each endpoint, builds a contract YAML file containing:
   - **Request block:** method, URL (with sample path parameters), headers, body (for POST/PUT)
   - **Response block:** status code, content-type header, response body with sample data
   - **Matchers block:** Regex-based validators for flexible field checking
3. **Smart sample value generation** — instead of using random values, it generates realistic samples based on field names:
   - `id` (integer) → `1`, with matcher `[0-9]+`
   - `email` (string with email format) → `"sample@example.com"`, with email regex matcher
   - `name` (string) → `"Sample User"`, with matcher `.+`
   - `role` (string) → `"Sample Role"`, with matcher `.+`
   - `price` (number) → `99.99`, with matcher `[0-9]+\\.?[0-9]*`
4. **Directory organization** — contracts are placed in subdirectories based on URL path segments:
   - `/api/users/{id}` → `contracts/user/` directory
   - `/api/orders/{id}` → `contracts/order/` directory
5. **Descriptive file names** — `should_return_user_by_id.yml`, `should_create_a_new_user.yml`

**What it generated for this project:**
- `should_update_user_by_id.yml` — PUT /api/users/1 → 200 + updated User with matchers
- `should_delete_user_by_id.yml` — DELETE /api/users/1 → 204 (no content)

These were the two endpoints that didn't have contracts yet. The generator detected what was missing and filled the gaps.

**AI-Generated Contract #4: `should_update_user_by_id.yml`** — PUT /api/users/1
```yaml
description: Update an existing user
name: should_update_user_by_id
request:
  method: PUT
  url: /api/users/1
  headers:
    Content-Type: application/json
  body:
    name: Sample User
    email: sample@example.com
    role: USER
response:
  status: 200
  headers:
    Content-Type: application/json
  body:
    id: 1
    name: Sample User
    email: sample@example.com
    role: USER
  matchers:
    body:
    - path: $.id
      type: by_regex
      value: '[0-9]+'
    - path: $.name
      type: by_regex
      value: .+
    - path: $.email
      type: by_regex
      value: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    - path: $.role
      type: by_regex
      value: .+
```

**AI-Generated Contract #5: `should_delete_user_by_id.yml`** — DELETE /api/users/1
```yaml
description: Delete a user
name: should_delete_user_by_id
request:
  method: DELETE
  url: /api/users/1
response:
  status: 204
```

Notice how the DELETE contract is minimal — no request body, no response body, just `status: 204` (No Content). The generator is smart enough to know that DELETE endpoints typically don't return data.

#### Tool 3: Drift Detector (`drift_detector.py`)

**Purpose:** Compares existing contract files against the current API spec to find mismatches.

**How it works:**
1. Loads all existing contract YAML files from the contracts directory
2. Fetches the current OpenAPI spec from the running Provider
3. Maps each contract to its corresponding spec endpoint using HTTP method + URL path
4. Checks for three types of drift:

| Drift Type | What it means | Example |
|---|---|---|
| **Uncovered** | API endpoint exists but has no contract | New endpoint added, no one wrote a contract |
| **Orphaned** | Contract exists but endpoint was removed | Endpoint was deleted, but old contract remains |
| **Schema Drift** | Contract exists but fields don't match spec | Spec added `createdAt` field, contract doesn't have it |

5. Calculates:
   - **Coverage percentage** — what fraction of API endpoints have contracts
   - **Health status** — HEALTHY (100% coverage, no drift), WARNING (minor issues), CRITICAL (major drift)

#### Tool 4: Report Generator (`report_generator.py`)

**Purpose:** Produces human-readable reports with actionable recommendations.

**How it works:**
1. Takes findings from the Drift Detector
2. Formats them into a structured report with:
   - **Coverage bar** — visual representation like `[████████████████████] 100%`
   - **Health status icon** — ✅ HEALTHY, ⚠️ WARNING, or 🚨 CRITICAL
   - **Detailed breakdown** — lists every endpoint with its coverage status
   - **Remediation steps** — specific actions to fix each issue (e.g., "Run `python main.py generate` to create missing contracts for PUT /api/users/{id}")
3. Can save reports to `ai-agent/reports/` directory with timestamps

#### Tool 5: CI Config Generator (`ci_config_generator.py`)

**Purpose:** Generates a complete `.gitlab-ci.yml` pipeline configuration.

**How it works:**
1. **Project detection** — scans the project root to find:
   - Maven modules (looks for `pom.xml` in `provider-api/` and `consumer-api/`)
   - AI Agent directory (looks for `ai-agent/main.py`)
2. **Generates a multi-stage pipeline** with 7 jobs across 4 stages:

| Stage | Job | What it does |
|-------|-----|-------------|
| **build** | `provider-build` | `mvn clean compile` on Provider |
| **build** | `consumer-build` | `mvn clean compile` on Consumer |
| **test** | `provider-contract-test` | `mvn clean install` → runs contracts, generates stubs |
| **test** | `consumer-contract-test` | `mvn clean test` → tests against stubs from Provider |
| **test** | `ai-agent-drift-check` | `python main.py validate` → drift detection |
| **report** | `contract-report` | Collects JUnit XML reports, generates summary |
| **deploy** | `deploy` | Gated deployment — only runs if all tests pass, only on `main` branch |

3. **Smart configuration:**
   - Maven dependency caching (`.m2/repository`) — speeds up repeated builds
   - Artifact passing — Provider's stubs JAR is passed to the Consumer test job
   - JUnit test report integration — test results appear in GitLab merge request UI
   - Docker image: `maven:3.9-eclipse-temurin-17` (Java 17 for Spring Boot)

### AI Agent Project Structure

```
ai-agent/
├── main.py                    ← CLI entry point (run this)
├── requirements.txt           ← Python dependencies (requests, pyyaml)
├── README.md                  ← Quick-start guide (points here for full docs)
├── agent/
│   ├── __init__.py            ← Package marker listing all 5 modules
│   ├── spec_reader.py         ← Tool 1: Fetches & parses OpenAPI specs
│   ├── contract_generator.py  ← Tool 2: Generates SCC YAML contracts
│   ├── drift_detector.py      ← Tool 3: Detects contract drift
│   ├── report_generator.py    ← Tool 4: Generates reports & remediation
│   └── ci_config_generator.py ← Tool 5: Generates GitLab CI pipeline
├── reports/                   ← Saved reports (when using --save-report)
└── tests/
    └── __init__.py
```

### Exit Codes (for CI/CD integration)

When running `python main.py validate` in a CI pipeline, the exit code tells the pipeline whether to proceed:

| Exit Code | Meaning | Pipeline Action |
|-----------|---------|-----------------|
| `0` | All contracts are valid and in sync with spec | ✅ Continue to deploy |
| `1` | Warnings found (orphaned contracts, minor issues) | ⚠️ Continue but review |
| `2` | Critical issues (schema drift, missing contracts for key endpoints) | ❌ Block deployment |

### Test Isolation Fix

During development, a subtle issue arose: the DELETE contract test was removing user ID 1 from the in-memory store, which broke subsequent GET tests that expected user 1 to exist. This is a classic **test isolation** problem.

**The fix:**
1. Added a `resetData()` method to `UserService.java` that clears the user store, resets the ID counter to 1, and re-initializes the 3 sample users
2. Updated `BaseContractTest.java` to call `userService.resetData()` in `@BeforeEach`, ensuring every contract test starts with a clean, predictable state

This is important because it means **contract tests can run in any order** and always produce the same result.

### Results

| Metric | Value |
|--------|-------|
| Contracts generated by AI Agent | **2** (PUT update, DELETE) |
| Total contracts (manual + AI) | **5** covering all 5 API endpoints |
| API coverage | **100%** — every endpoint has a contract |
| Health status | **HEALTHY** — no drift, no orphans |
| Provider tests | **6/6 pass** (5 contract + 1 smoke) |
| Consumer tests | **2/2 pass** (1 contract + 1 smoke) |
| CI pipeline generated | **7 jobs** across **4 stages** |

---

## Phase 8: CI/CD Pipeline (GitLab CI)

> **Status: � IN PROGRESS** — Pipeline YAML generated, pending GitLab push & live testing

The `.gitlab-ci.yml` file (generated by the AI Agent's `ci` command) automates the full workflow:

| Stage | Jobs | Purpose |
|-------|------|---------|
| **build** | `provider-build`, `consumer-build` | Compile & package both APIs |
| **test** | `provider-contract-test`, `consumer-contract-test`, `ai-agent-drift-check` | Run SCC verification, Consumer stub tests, drift detection |
| **report** | `contract-report` | Collect and summarize all test results |
| **deploy** | `deploy` | Gated by test success, auto-deploys from `main` branch only |

### Key features
- Maven dependency caching between pipeline runs
- Provider stubs JAR passed as artifact to Consumer test job
- JUnit test reports integrated with GitLab merge request UI
- Deployment blocked if any contract test fails

### Remaining work
- Push code to GitLab (currently blocked by permission — needs Maintainer role)
- Run and verify the pipeline end-to-end
- Demonstrate a failing contract blocking deployment

---

## Phase 9: Reporting & Dashboard

> **Status: ✅ COMPLETE**

A full **Contract Health Dashboard** provides real-time visibility into contract coverage and drift.

### What was built

- ✅ **Flask web dashboard** — live contract health UI at `http://localhost:5050`
- ✅ **JSON health API** — `GET /api/health` returns machine-readable health data
- ✅ **Health history API** — `GET /api/history` returns timestamped check history (last 50 entries)
- ✅ **CLI integration** — `python main.py dashboard` launches the dashboard from the CLI
- ✅ Contract health reports with coverage % and status (via `python main.py report`)
- ✅ Drift detection with specific remediation suggestions
- ✅ Validation with CI-friendly exit codes (via `python main.py validate`)

### Dashboard Features

| Feature | Description |
|---|---|
| **Health status** | Overall status: HEALTHY (100%), WARNING (>50%), or CRITICAL (≤50%) |
| **Coverage metrics** | Coverage %, covered/uncovered/orphaned/drifted endpoint counts |
| **Endpoint tables** | Per-endpoint breakdown with method badges and status pills |
| **Drift detection** | Schema mismatches highlighted with details |
| **Health history** | Bar chart showing coverage trend over time |
| **Auto-refresh** | One-click refresh fetches live data from the running Provider API |

### Running the Dashboard

```bash
cd ai-agent

# Option 1: Via CLI (recommended)
python main.py dashboard                    # Default port 5050
python main.py dashboard --port 8888        # Custom port
python main.py dashboard --debug            # Flask debug mode with auto-reload

# Option 2: Directly
python dashboard.py                          # Runs on port 5050
```

### Dashboard Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | HTML dashboard UI with live health data |
| `/api/health` | GET | JSON health check (coverage, drift, endpoint details) |
| `/api/history` | GET | JSON array of historical health checks |

### Sample `/api/health` Response

```json
{
  "summary": {
    "health": "HEALTHY",
    "coverage_percent": 100.0,
    "covered_count": 5,
    "uncovered_count": 0,
    "orphaned_count": 0,
    "drifted_count": 0,
    "total_spec_endpoints": 5,
    "total_contracts": 5
  },
  "covered": ["..."],
  "uncovered": [],
  "orphaned": [],
  "drifted": [],
  "timestamp": "2026-04-09T09:36:00Z"
}
```

### Future enhancements
- Automated merge request creation for contract updates
- Team notification integration (Slack/email on contract failure)

---

## Quick Start Guide

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd contract-testing-automation

# 2. Build and run the Provider API (Terminal 1)
cd provider-api
mvn clean compile
mvn spring-boot:run
# Runs on http://localhost:8080

# 3. Build and run the Consumer API (Terminal 2)
cd consumer-api
mvn clean compile
mvn spring-boot:run
# Runs on http://localhost:8081

# 4. Test the APIs
curl http://localhost:8080/api/users       # Provider: all users
curl http://localhost:8081/api/orders       # Consumer: all orders (enriched with user data)

# 5. Run contract tests
cd provider-api
mvn clean install    # Builds + runs contract tests + generates stubs

cd ../consumer-api
mvn clean test       # Tests Consumer against Provider's stubs

# 6. Run AI Agent (optional — generates contracts from spec)
cd ../ai-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py generate   # Generate contracts
python main.py drift      # Check for drift
python main.py report     # Health report
python main.py ci         # Generate CI pipeline
python main.py dashboard  # Start health dashboard on http://localhost:5050

# 7. Open Swagger UI
# Provider: http://localhost:8080/swagger-ui.html
# Consumer: http://localhost:8081/swagger-ui.html
```

---

## API Documentation

API documentation is auto-generated using **springdoc-openapi**:

### Provider (User Service) — Port 8080
| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8080/swagger-ui.html |
| OpenAPI JSON | http://localhost:8080/v3/api-docs |
| OpenAPI YAML | http://localhost:8080/v3/api-docs.yaml |

### Consumer (Order Service) — Port 8081
| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8081/swagger-ui.html |
| OpenAPI JSON | http://localhost:8081/v3/api-docs |
| OpenAPI YAML | http://localhost:8081/v3/api-docs.yaml |

---

## Glossary

| Term | Definition |
|---|---|
| **Contract** | A formal YAML file defining expected request/response behavior between API consumer and provider |
| **Provider** | The service that PROVIDES the API (our User Service on port 8080) |
| **Consumer** | The service that CONSUMES/CALLS the API (our Order Service on port 8081) |
| **Spring Cloud Contract (SCC)** | Java framework that auto-generates tests from contract files and creates WireMock stubs |
| **SCC Verifier** | Provider-side component — reads contracts, generates JUnit tests, verifies the API |
| **SCC Stub Runner** | Consumer-side component — loads stubs JAR and starts WireMock for testing |
| **WireMock** | A mock HTTP server that serves pre-defined responses (from stubs) for testing |
| **REST Assured** | Java library for testing REST APIs with a fluent assertion syntax |
| **Stubs JAR** | A generated artifact containing WireMock mappings, created by the Provider during `mvn install` |
| **OpenAPI/Swagger** | Standard specification format for documenting REST APIs (auto-generated from code) |
| **Contract Drift** | When the API's actual behavior diverges from what contracts specify |
| **DTO** | Data Transfer Object — a class that carries data between services (e.g., `UserDTO.java`) |
| **CI/CD** | Continuous Integration / Continuous Deployment — automated build + deploy pipeline |
| **Maven** | Java build tool that manages dependencies, compilation, testing, and packaging |
| **YAML** | Human-readable data format used for contract definitions and CI/CD configs |
| **RestTemplate** | Spring's HTTP client for making API calls between services |
| **Matchers** | Flexible contract assertions (e.g., `by_regex`) that validate response structure instead of exact values |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
