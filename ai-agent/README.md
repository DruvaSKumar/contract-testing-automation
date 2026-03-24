# AI Agent — Contract Generator

> Part of the [Contract Testing Automation](../README.md) project.

For **complete documentation** — setup, usage, CLI options, how each tool works, exit codes, and examples — see the main project's **[Phase 7: AI Agent](../README.md#phase-7-ai-agent--contract-generator-python)** section.

---

## Quick Start

```bash
# 1. Setup (one-time)
cd ai-agent
python -m venv .venv
.venv\Scripts\activate      # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Start the Provider API (in a separate terminal)
cd ../provider-api
mvn spring-boot:run

# 3. Run agent commands
python main.py generate     # Generate contracts from OpenAPI spec
python main.py drift        # Check for contract drift
python main.py report       # Full health report
python main.py validate     # CI-friendly check (exit codes)
python main.py ci           # Generate .gitlab-ci.yml pipeline
```

---

## Tools

| Tool | File | Purpose |
|------|------|---------|
| Spec Reader | `agent/spec_reader.py` | Fetches & parses OpenAPI 3.0 spec from Provider |
| Contract Generator | `agent/contract_generator.py` | Generates SCC YAML contract files |
| Drift Detector | `agent/drift_detector.py` | Compares contracts vs spec for mismatches |
| Report Generator | `agent/report_generator.py` | Health reports with remediation suggestions |
| CI Config Generator | `agent/ci_config_generator.py` | Generates GitLab CI pipeline YAML |

---

## CLI Options

Run `python main.py --help` or `python main.py <command> --help` for all options.

Key options: `--provider-url`, `--spec-file`, `--contracts-dir`, `--overwrite`, `--save-report`, `--output-dir`

---

## Example Output

### Contract Generation

```
=================================================================
  AI AGENT: Contract Generation
=================================================================
[SPEC READER] Fetching OpenAPI spec from: http://localhost:8080/v3/api-docs
[SPEC READER] Successfully loaded: User Management API (OpenAPI 3.0.1)
[SPEC READER] Extracted 5 endpoints from spec
  GET    /api/users
  GET    /api/users/{id}
  POST   /api/users
  PUT    /api/users/{id}
  DELETE /api/users/{id}

[CONTRACT GENERATOR] Generation complete:
  Generated: 2 contracts
  Skipped:   3 (already exist)
  Errors:    0

  New contract files:
    + should_update_user_by_id.yml
    + should_delete_user_by_id.yml
```

### Drift Detection

```
=================================================================
  Health Status: [OK] HEALTHY

  API Endpoints (from spec):   5
  Existing Contracts:          5
  Covered (matching):          5
  Uncovered (no contract):     0
  Coverage:                    100%

  Coverage: [####################] 100%
=================================================================
```

---

## Extending the Agent

To add support for new features:

1. **New contract patterns**: Edit `contract_generator.py` — modify `_generate_sample_value()` for new field types
2. **New drift checks**: Edit `drift_detector.py` — add checks in `_check_schema_drift()`
3. **New report formats**: Edit `report_generator.py` — add methods for JSON/HTML output
4. **Support for other frameworks**: The contract YAML format is specific to Spring Cloud Contract; to support Pact or other frameworks, create a new generator module
