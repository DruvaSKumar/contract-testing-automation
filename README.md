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
- [Phase 9: Reporting & Maintenance](#phase-9-reporting--maintenance)
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
4. **AI-powered contract generation** _(upcoming)_ — a Python agent reads the OpenAPI spec and automatically generates/updates contract files

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
│   │               └── should_create_a_new_user.yml
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
└── ai-agent/                          ← Python AI Agent (Phase 7 — upcoming)
    ├── requirements.txt
    ├── agent/
    │   ├── spec_reader.py
    │   ├── contract_generator.py
    │   ├── drift_detector.py
    │   ├── remediation_reporter.py
    │   └── ci_config_generator.py
    └── tests/
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
| **Python** | 3.x | Language for the AI Agent _(upcoming)_ |
| **GitLab CI** | — | CI/CD pipeline automation _(upcoming)_ |
| **OpenAPI/Swagger** | 3.0 | API specification standard |

---

## Prerequisites

Before running this project, ensure you have:

- [x] **Java JDK 17+** → [Download](https://www.oracle.com/java/technologies/downloads/)
- [x] **Apache Maven 3.8+** → [Download](https://maven.apache.org/download.cgi)
- [x] **Git** → [Download](https://git-scm.com/downloads)
- [ ] **Python 3.10+** _(needed for Phase 7)_ → [Download](https://www.python.org/downloads/)
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

> **Status: 🔜 UPCOMING**

A Python-based AI agent that reads the Provider's OpenAPI specification (`/v3/api-docs`) and **automatically generates** contract YAML files.

### Planned capabilities:
- Read and parse OpenAPI 3.0 spec from the running Provider
- Generate Spring Cloud Contract YAML files for all endpoints
- Detect API drift (when the spec changes vs existing contracts)
- Suggest contract updates and fixes
- Generate CI/CD configuration

---

## Phase 8: CI/CD Pipeline (GitLab CI)

> **Status: 🔜 UPCOMING**

A `.gitlab-ci.yml` pipeline that automates:
1. **Build** — Compile Provider and Consumer
2. **Contract Verify** — Run contract tests automatically
3. **Report** — Generate contract violation reports
4. **Deploy Gate** — Block deployment if contracts fail

---

## Phase 9: Reporting & Maintenance

> **Status: 🔜 UPCOMING**

- Contract violation reports and dashboards
- AI-powered fix suggestions for contract drift
- Auto-update contracts via merge requests

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

# 6. Open Swagger UI
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
