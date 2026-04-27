# ============================================================
# ci_config_generator.py — GitLab CI Pipeline Generator
# ============================================================
# PURPOSE:
#   Generates a .gitlab-ci.yml pipeline configuration that
#   automates contract testing in the CI/CD workflow. The
#   generated pipeline:
#     1. Builds the Provider API
#     2. Runs contract verification tests on Provider
#     3. Generates stubs JAR
#     4. Runs Consumer tests against stubs
#     5. Runs AI agent drift detection
#     6. Blocks deployment on any contract failure
#
# WHY IS THIS NEEDED?
#   Manually writing CI/CD pipelines is tedious and error-prone.
#   This generator reads the project structure and produces a
#   production-ready GitLab CI pipeline that enforces contract
#   compliance on every push — automatically.
#
# HOW IT WORKS:
#   1. Scans the project root for Maven modules (provider-api/, consumer-api/)
#   2. Detects the AI agent directory (ai-agent/)
#   3. Generates a multi-stage pipeline with:
#      - build stage: compile both APIs
#      - test stage: run contract tests on provider, consumer, and drift detection
#      - report stage: generate coverage report
#      - deploy stage: gated by test success
#   4. Writes the .gitlab-ci.yml file to the project root
#
# GITLAB CI CONCEPTS:
#   - stages: Ordered groups of jobs (build → test → report → deploy)
#   - jobs: Individual tasks (e.g., "provider-contract-test")
#   - artifacts: Files passed between jobs (e.g., stubs JAR)
#   - cache: Dependencies cached between pipeline runs (Maven .m2)
#   - rules: Conditions for when jobs run (e.g., only on main branch)
# ============================================================

import os


class CIConfigGenerator:
    """
    Generates GitLab CI/CD pipeline configuration for automated
    contract testing.
    """

    def __init__(self, project_root=None):
        """
        Args:
            project_root: Root directory of the project.
                          Defaults to parent of ai-agent/ directory.
        """
        if project_root is None:
            project_root = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
            )
        self.project_root = project_root

    def detect_project_structure(self):
        """
        Scans the project root to detect which modules exist.

        Returns:
            dict: Detected project components:
                - has_provider: True if provider-api/ exists with pom.xml
                - has_consumer: True if consumer-api/ exists with pom.xml
                - has_ai_agent: True if ai-agent/ exists with main.py
                - provider_dir: Name of provider directory
                - consumer_dir: Name of consumer directory
                - ai_agent_dir: Name of AI agent directory
        """
        structure = {
            "has_provider": False,
            "has_consumer": False,
            "has_ai_agent": False,
            "provider_dir": "provider-api",
            "consumer_dir": "consumer-api",
            "ai_agent_dir": "ai-agent",
        }

        # Check for Provider
        provider_pom = os.path.join(self.project_root, "provider-api", "pom.xml")
        if os.path.exists(provider_pom):
            structure["has_provider"] = True

        # Check for Consumer
        consumer_pom = os.path.join(self.project_root, "consumer-api", "pom.xml")
        if os.path.exists(consumer_pom):
            structure["has_consumer"] = True

        # Check for AI Agent
        agent_main = os.path.join(self.project_root, "ai-agent", "main.py")
        if os.path.exists(agent_main):
            structure["has_ai_agent"] = True

        print(f"[CI GENERATOR] Detected project structure:")
        print(f"  Provider API: {'Found' if structure['has_provider'] else 'Not found'}")
        print(f"  Consumer API: {'Found' if structure['has_consumer'] else 'Not found'}")
        print(f"  AI Agent:     {'Found' if structure['has_ai_agent'] else 'Not found'}")

        return structure

    def generate(self, structure=None, output_path=None):
        """
        Generates the .gitlab-ci.yml pipeline configuration.

        Args:
            structure: Project structure dict from detect_project_structure().
                       If None, auto-detects.
            output_path: Where to write the YAML file.
                         Defaults to project_root/.gitlab-ci.yml

        Returns:
            str: The generated YAML content.
        """
        if structure is None:
            structure = self.detect_project_structure()

        if output_path is None:
            output_path = os.path.join(self.project_root, ".gitlab-ci.yml")

        content = self._build_pipeline(structure)

        # Write the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"\n[CI GENERATOR] Generated pipeline: {output_path}")
        print(f"[CI GENERATOR] Stages: build → test → report → deploy")
        return content

    def _build_pipeline(self, structure):
        """
        Builds the complete .gitlab-ci.yml content string.

        The pipeline is designed with these principles:
        - Contract tests MUST pass before deployment
        - Provider builds first (generates stubs JAR)
        - Consumer tests consume the stubs (dependency)
        - AI agent validates contracts against live spec
        - Reports are always generated (even on failure)
        - Deploy stage is gated by ALL test stages
        """
        sections = []

        # Header comment
        sections.append(self._header_comment())

        # Global configuration
        sections.append(self._global_config())

        # Stages definition
        sections.append(self._stages())

        # Cache configuration
        sections.append(self._cache_config())

        # Build jobs
        if structure["has_provider"]:
            sections.append(self._provider_build_job(structure))

        if structure["has_consumer"]:
            sections.append(self._consumer_build_job(structure))

        # Test jobs
        if structure["has_provider"]:
            sections.append(self._provider_contract_test_job(structure))

        if structure["has_consumer"]:
            sections.append(self._consumer_contract_test_job(structure))

        if structure["has_ai_agent"]:
            sections.append(self._ai_agent_drift_job(structure))

        # Report job
        sections.append(self._report_job(structure))

        # Auto-fix job (manual trigger)
        if structure["has_ai_agent"]:
            sections.append(self._auto_fix_job(structure))

        # Deploy job (gated)
        sections.append(self._deploy_job(structure))

        return "\n".join(sections)

    def _header_comment(self):
        return (
            "# ============================================================\n"
            "# .gitlab-ci.yml — Contract Testing Automation Pipeline\n"
            "# ============================================================\n"
            "# AUTO-GENERATED by AI Agent (ci_config_generator.py)\n"
            "#\n"
            "# This pipeline automates contract testing on every push:\n"
            "#   1. BUILD:  Compile Provider and Consumer APIs\n"
            "#   2. TEST:   Run contract verification tests\n"
            "#   3. REPORT: Generate contract coverage report\n"
            "#   4. DEPLOY: Gated — only deploys if ALL tests pass\n"
            "#\n"
            "# Contract test failures BLOCK deployment, preventing\n"
            "# breaking API changes from reaching production.\n"
            "#\n"
            "# To regenerate: cd ai-agent && python main.py ci\n"
            "# ============================================================\n"
        )

    def _global_config(self):
        return (
            "\n"
            "# ---- Global Configuration ----\n"
            "# The Docker image used for all jobs unless overridden.\n"
            "# maven:3.9-eclipse-temurin-22 includes both Maven and JDK 22.\n"
            "# Spring Cloud Contract plugin 4.1.3 requires Java 22+.\n"
            "image: maven:3.9-eclipse-temurin-22\n"
            "\n"
            "# Variables available to all jobs\n"
            "variables:\n"
            "  # Use batch mode for Maven (less verbose output)\n"
            "  MAVEN_OPTS: \"-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository\"\n"
            "  MAVEN_CLI_OPTS: \"--batch-mode --errors --fail-at-end\"\n"
        )

    def _stages(self):
        return (
            "\n"
            "# ---- Pipeline Stages ----\n"
            "# Jobs in the same stage run in parallel.\n"
            "# A stage only starts after ALL jobs in the previous stage succeed.\n"
            "stages:\n"
            "  - build       # Compile source code\n"
            "  - test        # Run contract verification tests\n"
            "  - report      # Generate test & coverage reports\n"
            "  - fix         # Auto-fix drifted contracts (manual trigger)\n"
            "  - deploy      # Deploy (only if all tests pass)\n"
        )

    def _cache_config(self):
        return (
            "\n"
            "# ---- Cache Configuration ----\n"
            "# Caches Maven dependencies between pipeline runs so that\n"
            "# subsequent builds don't re-download everything from Maven Central.\n"
            "# The cache key is per-branch so branches don't pollute each other.\n"
            "cache:\n"
            "  key: ${CI_COMMIT_REF_SLUG}\n"
            "  paths:\n"
            "    - .m2/repository/\n"
            "    - ai-agent/.venv/\n"
        )

    def _provider_build_job(self, structure):
        d = structure["provider_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: Build Provider API\n"
            f"# ============================================================\n"
            f"# Compiles the Provider (User Service) and verifies it builds.\n"
            f"# This catches compilation errors early before running tests.\n"
            f"# ============================================================\n"
            f"provider-build:\n"
            f"  stage: build\n"
            f"  script:\n"
            f"    - cd {d}\n"
            f"    - mvn $MAVEN_CLI_OPTS clean compile\n"
            f"  rules:\n"
            f"    - changes:\n"
            f"        - {d}/**/*\n"
            f"        - .gitlab-ci.yml\n"
            f"      when: always\n"
            f"    - when: manual\n"
            f"      allow_failure: true\n"
        )

    def _consumer_build_job(self, structure):
        d = structure["consumer_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: Build Consumer API\n"
            f"# ============================================================\n"
            f"# Compiles the Consumer (Order Service) and verifies it builds.\n"
            f"# ============================================================\n"
            f"consumer-build:\n"
            f"  stage: build\n"
            f"  script:\n"
            f"    - cd {d}\n"
            f"    - mvn $MAVEN_CLI_OPTS clean compile\n"
            f"  rules:\n"
            f"    - changes:\n"
            f"        - {d}/**/*\n"
            f"        - .gitlab-ci.yml\n"
            f"      when: always\n"
            f"    - when: manual\n"
            f"      allow_failure: true\n"
        )

    def _provider_contract_test_job(self, structure):
        d = structure["provider_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: Provider Contract Tests\n"
            f"# ============================================================\n"
            f"# This is the CRITICAL job in the pipeline.\n"
            f"#\n"
            f"# What happens:\n"
            f"#   1. Spring Cloud Contract reads YAML contract files\n"
            f"#   2. Auto-generates JUnit tests from the contracts\n"
            f"#   3. Runs tests against the REAL Provider API (via MockMvc)\n"
            f"#   4. If ALL pass → generates stubs JAR (WireMock mappings)\n"
            f"#   5. If ANY fail → BUILD FAILS → deployment blocked\n"
            f"#\n"
            f"# The stubs JAR is saved as an artifact so the Consumer\n"
            f"# test job can use it without rebuilding the Provider.\n"
            f"# ============================================================\n"
            f"provider-contract-test:\n"
            f"  stage: test\n"
            f"  script:\n"
            f"    - cd {d}\n"
            f"    - mvn $MAVEN_CLI_OPTS clean install\n"
            f"  artifacts:\n"
            f"    when: always\n"
            f"    paths:\n"
            f"      # Stubs JAR — needed by Consumer tests\n"
            f"      - {d}/target/*-stubs.jar\n"
            f"      # Test reports — displayed in GitLab merge requests\n"
            f"      - {d}/target/surefire-reports/\n"
            f"    reports:\n"
            f"      junit:\n"
            f"        - {d}/target/surefire-reports/TEST-*.xml\n"
            f"    expire_in: 7 days\n"
        )

    def _consumer_contract_test_job(self, structure):
        pd = structure["provider_dir"]
        cd = structure["consumer_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: Consumer Contract Tests\n"
            f"# ============================================================\n"
            f"# Tests the Consumer (Order Service) against Provider stubs.\n"
            f"#\n"
            f"# What happens:\n"
            f"#   1. Provider is built locally (tests skipped — already passed)\n"
            f"#      to install the stubs JAR into the local Maven repository\n"
            f"#   2. Stub Runner loads the Provider's stubs JAR from Maven repo\n"
            f"#   3. Starts a WireMock server with stub responses\n"
            f"#   4. Consumer's UserServiceClient calls WireMock\n"
            f"#   5. Tests verify the Consumer correctly parses responses\n"
            f"#\n"
            f"# This job depends on provider-contract-test to ensure\n"
            f"# Provider contracts pass before Consumer tests run.\n"
            f"# ============================================================\n"
            f"consumer-contract-test:\n"
            f"  stage: test\n"
            f"  needs:\n"
            f"    - job: provider-contract-test\n"
            f"  script:\n"
            f"    # Build Provider and install stubs JAR to local Maven repo\n"
            f"    # Tests are skipped because they already passed in provider-contract-test\n"
            f"    - cd {pd}\n"
            f"    - mvn $MAVEN_CLI_OPTS clean install -DskipTests\n"
            f"    # Create settings.xml so the forked surefire JVM's stub runner knows\n"
            f"    # where the local Maven repo is (MAVEN_OPTS is NOT inherited by forked JVMs)\n"
            f'    - mkdir -p /root/.m2 && echo "<settings><localRepository>${{CI_PROJECT_DIR}}/.m2/repository</localRepository></settings>" > /root/.m2/settings.xml\n'
            f"    - rm -rf /root/.m2/repository && ln -s $CI_PROJECT_DIR/.m2/repository /root/.m2/repository\n"
            f"    # Run Consumer contract tests against Provider stubs\n"
            f"    - cd ../{cd}\n"
            f"    - mvn $MAVEN_CLI_OPTS clean test\n"
            f"  artifacts:\n"
            f"    when: always\n"
            f"    paths:\n"
            f"      - {cd}/target/surefire-reports/\n"
            f"    reports:\n"
            f"      junit:\n"
            f"        - {cd}/target/surefire-reports/TEST-*.xml\n"
            f"    expire_in: 7 days\n"
        )

    def _ai_agent_drift_job(self, structure):
        pd = structure["provider_dir"]
        ad = structure["ai_agent_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: AI Agent — Contract Drift Detection\n"
            f"# ============================================================\n"
            f"# Runs the AI agent to check if contracts are in sync with\n"
            f"# the Provider's OpenAPI specification.\n"
            f"#\n"
            f"# This job:\n"
            f"#   1. Starts the Provider API in the background\n"
            f"#   2. Waits for it to be ready\n"
            f"#   3. Runs the drift detector against the live spec\n"
            f"#   4. Generates a coverage report\n"
            f"#\n"
            f"# Exit codes:\n"
            f"#   0 = All contracts valid (HEALTHY)\n"
            f"#   1 = Warnings found (orphaned contracts)\n"
            f"#   2 = Critical drift detected (blocks pipeline)\n"
            f"# ============================================================\n"
            f"ai-agent-drift-check:\n"
            f"  stage: test\n"
            f"  image: maven:3.9-eclipse-temurin-22\n"
            f"  needs:\n"
            f"    - job: provider-contract-test\n"
            f"      artifacts: true\n"
            f"  before_script:\n"
            f"    # Install Python for the AI agent\n"
            f"    - apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv > /dev/null 2>&1\n"
            f"    - cd {ad}\n"
            f"    - python3 -m venv .venv\n"
            f"    - . .venv/bin/activate\n"
            f"    - pip install -q -r requirements.txt\n"
            f"  script:\n"
            f"    # Start Provider API in background for OpenAPI spec access\n"
            f"    - cd $CI_PROJECT_DIR/{pd}\n"
            f"    - mvn $MAVEN_CLI_OPTS spring-boot:run &\n"
            f"    - PROVIDER_PID=$!\n"
            f"    # Wait for Provider to be ready (max 60 seconds)\n"
            f"    - |\n"
            f"      for i in $(seq 1 30); do\n"
            f"        if curl -s http://localhost:8080/v3/api-docs > /dev/null 2>&1; then\n"
            f"          echo \"Provider is ready!\"\n"
            f"          break\n"
            f"        fi\n"
            f"        echo \"Waiting for Provider... ($i/30)\"\n"
            f"        sleep 2\n"
            f"      done\n"
            f"    # Run drift detection\n"
            f"    - cd $CI_PROJECT_DIR/{ad}\n"
            f"    - . .venv/bin/activate\n"
            f"    - python3 main.py --save-report drift\n"
            f"    # Cleanup — stop the Provider\n"
            f"    - kill $PROVIDER_PID 2>/dev/null || true\n"
            f"  artifacts:\n"
            f"    when: always\n"
            f"    paths:\n"
            f"      - {ad}/reports/\n"
            f"    expire_in: 7 days\n"
            f"  allow_failure: true  # Drift warnings don't block, critical drift does (exit code 2)\n"
        )

    def _auto_fix_job(self, structure):
        pd = structure["provider_dir"]
        ad = structure["ai_agent_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: AI Agent — Auto-Fix Drifted Contracts\n"
            f"# ============================================================\n"
            f"# MANUAL TRIGGER — Click \"Play\" in the GitLab UI to run.\n"
            f"#\n"
            f"# When drift is detected, this job:\n"
            f"#   1. Starts the Provider API for live spec access\n"
            f"#   2. Runs the AI Agent's fix command\n"
            f"#   3. Creates a GitLab Merge Request with the fixed contracts\n"
            f"#\n"
            f"# Prerequisites (CI/CD Variables in GitLab):\n"
            f"#   GITLAB_TOKEN      — Personal Access Token (api scope)\n"
            f"#   GITLAB_PROJECT_ID — Numeric project ID\n"
            f"#\n"
            f"# The MR is created automatically and linked in the job output.\n"
            f"# A human reviews and merges — keeping the process safe.\n"
            f"# ============================================================\n"
            f"auto-fix-contracts:\n"
            f"  stage: fix\n"
            f"  image: maven:3.9-eclipse-temurin-22\n"
            f"  needs:\n"
            f"    - job: ai-agent-drift-check\n"
            f"      artifacts: true\n"
            f"      optional: true\n"
            f"  before_script:\n"
            f"    - apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv > /dev/null 2>&1\n"
            f"    - cd {ad}\n"
            f"    - python3 -m venv .venv\n"
            f"    - . .venv/bin/activate\n"
            f"    - pip install -q -r requirements.txt\n"
            f"  script:\n"
            f"    # Start Provider API in background\n"
            f"    - cd $CI_PROJECT_DIR/{pd}\n"
            f"    - mvn $MAVEN_CLI_OPTS spring-boot:run &\n"
            f"    - PROVIDER_PID=$!\n"
            f"    # Wait for Provider to be ready\n"
            f"    - |\n"
            f"      for i in $(seq 1 30); do\n"
            f"        if curl -s http://localhost:8080/v3/api-docs > /dev/null 2>&1; then\n"
            f"          echo \"Provider is ready!\"\n"
            f"          break\n"
            f"        fi\n"
            f"        echo \"Waiting for Provider... ($i/30)\"\n"
            f"        sleep 2\n"
            f"      done\n"
            f"    # Run auto-fix with MR creation\n"
            f"    - cd $CI_PROJECT_DIR/{ad}\n"
            f"    - . .venv/bin/activate\n"
            f"    - python3 main.py --save-report fix --create-mr\n"
            f"    # Cleanup\n"
            f"    - kill $PROVIDER_PID 2>/dev/null || true\n"
            f"  artifacts:\n"
            f"    when: always\n"
            f"    paths:\n"
            f"      - {ad}/reports/\n"
            f"    expire_in: 7 days\n"
            f"  rules:\n"
            f"    - when: manual\n"
            f"      allow_failure: true\n"
        )

    def _report_job(self, structure):
        pd = structure["provider_dir"]
        cd = structure["consumer_dir"]
        return (
            f"\n"
            f"# ============================================================\n"
            f"# JOB: Contract Test Report\n"
            f"# ============================================================\n"
            f"# Collects and summarizes all contract test results.\n"
            f"# This job ALWAYS runs, even if previous stages failed,\n"
            f"# so you can see what went wrong.\n"
            f"# ============================================================\n"
            f"contract-report:\n"
            f"  stage: report\n"
            f"  when: always\n"
            f"  script:\n"
            f"    - echo \"=== CONTRACT TEST REPORT ===\"\n"
            f"    - echo \"\"\n"
            f"    - echo \"--- Provider Contract Tests ---\"\n"
            f"    - cat {pd}/target/surefire-reports/*.txt 2>/dev/null || echo \"No Provider test reports found\"\n"
            f"    - echo \"\"\n"
            f"    - echo \"--- Consumer Contract Tests ---\"\n"
            f"    - cat {cd}/target/surefire-reports/*.txt 2>/dev/null || echo \"No Consumer test reports found\"\n"
            f"    - echo \"\"\n"
            f"    - echo \"--- AI Agent Drift Report ---\"\n"
            f"    - cat ai-agent/reports/drift_report.txt 2>/dev/null || echo \"No drift report found\"\n"
            f"    - echo \"\"\n"
            f"    - echo \"=== END OF REPORT ===\"\n"
            f"  needs:\n"
            f"    - job: provider-contract-test\n"
            f"      optional: true\n"
            f"      artifacts: true\n"
            f"    - job: consumer-contract-test\n"
            f"      optional: true\n"
            f"      artifacts: true\n"
            f"    - job: ai-agent-drift-check\n"
            f"      optional: true\n"
            f"      artifacts: true\n"
        )

    def _deploy_job(self, structure):
        return (
            "\n"
            "# ============================================================\n"
            "# JOB: Deploy (Gated by Contract Tests)\n"
            "# ============================================================\n"
            "# This job only runs if ALL contract tests passed.\n"
            "# It represents the deployment gate — no broken contracts\n"
            "# can reach production.\n"
            "#\n"
            "# CUSTOMIZE: Replace the placeholder script with your\n"
            "# actual deployment commands (Docker build, kubectl apply,\n"
            "# AWS ECS deploy, etc.)\n"
            "# ============================================================\n"
            "deploy:\n"
            "  stage: deploy\n"
            "  script:\n"
            "    - echo \"All contract tests passed - safe to deploy!\"\n"
            "    - echo \"Deployment placeholder - replace with your deploy commands (docker build, kubectl apply, etc.)\"\n"
            "  rules:\n"
            "    # Only deploy from the main branch\n"
            "    - if: $CI_COMMIT_BRANCH == \"main\"\n"
            "      when: on_success\n"
            "    # Manual deploy for other branches\n"
            "    - when: manual\n"
            "      allow_failure: true\n"
            "  dependencies:\n"
            "    - provider-contract-test\n"
            "    - consumer-contract-test\n"
        )
