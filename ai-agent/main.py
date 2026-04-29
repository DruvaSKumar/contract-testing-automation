# ============================================================
# main.py — AI Agent CLI Entry Point
# ============================================================
# PURPOSE:
#   Command-line interface for the Contract Testing AI Agent.
#   This is the file you run to use the agent's capabilities.
#
# USAGE:
#   python main.py generate              Generate contracts from OpenAPI spec
#   python main.py generate --overwrite  Regenerate all contracts (overwrite existing)
#   python main.py drift                 Detect drift between spec and contracts
#   python main.py drift --notify         Detect drift + auto-send notifications
#   python main.py report                Full report (drift + coverage)
#   python main.py report --notify        Full report + email summary to team
#   python main.py validate              Validate existing contracts against spec
#   python main.py ci                    Generate .gitlab-ci.yml pipeline
#   python main.py fix                   Auto-fix drifted/missing contracts (local)
#   python main.py fix --create-mr       Auto-fix + create GitLab Merge Request
#   python main.py notify                Send Slack/email notification on drift
#   python main.py dashboard             Start the Contract Health Dashboard
#
# PREREQUISITES:
#   - Provider API must be running on http://localhost:8080
#   - Python packages installed: pip install -r requirements.txt
#
# HOW IT WORKS:
#   The CLI uses Python's argparse module to parse commands.
#   Each command maps to one or more agent modules:
#     generate → spec_reader + contract_generator
#     drift    → spec_reader + drift_detector
#     report   → spec_reader + drift_detector + report_generator
#     validate → spec_reader + drift_detector (focused on schema checks)
#     ci       → ci_config_generator (generates .gitlab-ci.yml)
#     fix      → spec_reader + drift_detector + contract_generator + mr_creator
#     notify   → spec_reader + drift_detector + notifier (Slack/email)
#     dashboard → Flask web UI (spec_reader + drift_detector)
# ============================================================

import argparse
import os
import sys

import yaml

from agent.spec_reader import OpenApiSpecReader
from agent.contract_generator import ContractGenerator
from agent.drift_detector import DriftDetector
from agent.report_generator import ReportGenerator
from agent.ci_config_generator import CIConfigGenerator
from agent.mr_creator import MRCreator
from agent.notifier import Notifier


def get_default_contracts_dir():
    """Returns the default contracts directory path relative to this script."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(
        os.path.join(base, "..", "provider-api", "src", "test", "resources", "contracts")
    )


def cmd_generate(args):
    """
    GENERATE command — Generates contract YAML files from the OpenAPI spec.

    Steps:
      1. Fetch the OpenAPI spec from the running Provider
      2. Parse all endpoints
      3. Generate SCC YAML contracts for each endpoint
      4. Save to the contracts directory
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Contract Generation")
    print("=" * 65)

    # Step 1: Read the OpenAPI spec
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    # Step 2: Extract endpoints
    endpoints = reader.extract_endpoints()

    if not endpoints:
        print("\n[WARNING] No endpoints found in the OpenAPI spec.")
        print("  Make sure the Provider has REST endpoints annotated with @RestController.")
        sys.exit(1)

    # Step 3: Generate contracts
    generator = ContractGenerator(output_dir=args.output_dir)
    results = generator.generate_all(endpoints, overwrite=args.overwrite)

    # Step 4: Generate and print report
    reporter = ReportGenerator()
    report = reporter.generate_generation_report(results)
    print(report)

    # Save report if requested
    if args.save_report:
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports", "generation_report.txt"
        )
        reporter.save_report(report, report_path)

    return results


def cmd_drift(args):
    """
    DRIFT command — Detects drift between contracts and the OpenAPI spec.

    Steps:
      1. Fetch the current OpenAPI spec
      2. Load existing contract files
      3. Compare them to find drift
      4. Print a detailed report
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Contract Drift Detection")
    print("=" * 65)

    # Step 1: Read the OpenAPI spec
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    # Step 2: Extract endpoints
    endpoints = reader.extract_endpoints()

    # Step 3: Detect drift
    detector = DriftDetector(contracts_dir=args.contracts_dir)
    drift_results = detector.detect_drift(endpoints)

    # Step 4: Generate and print report
    reporter = ReportGenerator()
    report = reporter.generate_drift_report(drift_results)
    print(report)

    # Save report if requested
    if args.save_report:
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports", "drift_report.txt"
        )
        reporter.save_report(report, report_path)

    # Auto-notify if --notify flag is set
    if args.notify:
        notifier = Notifier()
        result = notifier.auto_notify(drift_results, command_name="drift", pipeline_url=args.pipeline_url)
        _print_notify_result(result)

    # Return non-zero exit code if critical issues found
    health = drift_results.get("summary", {}).get("health", "UNKNOWN")
    if health == "CRITICAL":
        sys.exit(2)
    elif health == "WARNING":
        sys.exit(1)

    return drift_results


def cmd_report(args):
    """
    REPORT command — Full report combining generation status and drift detection.
    This does NOT generate any files — it only analyzes and reports.
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Full Contract Report")
    print("=" * 65)

    # Step 1: Read the OpenAPI spec
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    # Step 2: Extract endpoints
    endpoints = reader.extract_endpoints()

    # Step 3: Run drift detection
    detector = DriftDetector(contracts_dir=args.contracts_dir)
    drift_results = detector.detect_drift(endpoints)

    # Step 4: Print drift report
    reporter = ReportGenerator()
    report = reporter.generate_drift_report(drift_results)
    print(report)

    # Save report if requested
    if args.save_report:
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports", "full_report.txt"
        )
        reporter.save_report(report, report_path)

    # Auto-notify if --notify flag is set
    if args.notify:
        notifier = Notifier()
        result = notifier.auto_notify(drift_results, command_name="report", pipeline_url=args.pipeline_url)
        _print_notify_result(result)

    return drift_results


def cmd_validate(args):
    """
    VALIDATE command — Validates existing contracts against the spec.
    Focused check: are all contracts still valid? Any schema mismatches?
    Returns exit code 0 if valid, non-zero if issues found.
    Useful in CI/CD pipelines as a pre-check before running tests.
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Contract Validation")
    print("=" * 65)

    # Step 1: Read the OpenAPI spec
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    # Step 2: Extract endpoints
    endpoints = reader.extract_endpoints()

    # Step 3: Detect drift (focused on schema validation)
    detector = DriftDetector(contracts_dir=args.contracts_dir)
    drift_results = detector.detect_drift(endpoints)

    # Step 4: Report only the validation-relevant findings
    drifted = drift_results.get("drifted", [])
    orphaned = drift_results.get("orphaned", [])
    summary = drift_results.get("summary", {})

    print(f"\n  Contracts checked: {summary.get('total_contracts', 0)}")
    print(f"  Valid:             {summary.get('covered_count', 0)}")
    print(f"  Schema mismatch:   {summary.get('drifted_count', 0)}")
    print(f"  Orphaned:          {summary.get('orphaned_count', 0)}")

    if drifted:
        print("\n  VALIDATION FAILED — Schema mismatches found:")
        for item in drifted:
            print(f"\n    {item['method']} {item['url']} ({item['file']})")
            for issue in item.get("issues", []):
                print(f"      - {issue}")

    if orphaned:
        print("\n  WARNING — Orphaned contracts found:")
        for item in orphaned:
            print(f"    {item['method']} {item['url']} ({item['file']})")

    if not drifted and not orphaned:
        print("\n  All contracts are valid and in sync with the API spec.")
        print("  No issues found.")

    print("")

    # Auto-notify if --notify flag is set
    if args.notify:
        notifier = Notifier()
        result = notifier.auto_notify(drift_results, command_name="validate", pipeline_url=args.pipeline_url)
        _print_notify_result(result)

    # Exit code for CI/CD integration
    if drifted:
        sys.exit(2)
    elif orphaned:
        sys.exit(1)
    else:
        sys.exit(0)


def cmd_ci(args):
    """
    CI command — Generates a .gitlab-ci.yml pipeline configuration.

    Scans the project structure and generates a GitLab CI pipeline that:
    - Builds Provider and Consumer APIs
    - Runs contract verification tests on both sides
    - Runs AI agent drift detection
    - Generates test reports
    - Gates deployment on contract test success
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: CI/CD Pipeline Generation")
    print("=" * 65)

    generator = CIConfigGenerator(project_root=args.project_root)
    content = generator.generate(output_path=args.output)

    print(f"\n  Pipeline file generated successfully!")
    print(f"  File: {args.output or os.path.join(args.project_root, '.gitlab-ci.yml')}")
    print(f"\n  NEXT STEPS:")
    print(f"  1. Review the generated .gitlab-ci.yml")
    print(f"  2. Commit and push to GitLab")
    print(f"  3. The pipeline will run automatically on the next push")
    print(f"  4. Contract test failures will BLOCK deployment")
    print("")

    return content


def cmd_fix(args):
    """
    FIX command — Detects drift, regenerates affected contracts, and
    optionally creates a GitLab Merge Request with the fixes.

    Steps:
      1. Fetch the current OpenAPI spec
      2. Detect drift (drifted + uncovered contracts)
      3. Regenerate contracts for all drifted/uncovered endpoints
      4. If --create-mr flag is set, push changes and create a GitLab MR
      5. Otherwise, just write the fixed files locally
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Auto-Fix Drifted Contracts")
    print("=" * 65)

    # Step 1: Read the OpenAPI spec
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    # Step 2: Extract endpoints and detect drift
    endpoints = reader.extract_endpoints()
    detector = DriftDetector(contracts_dir=args.contracts_dir)
    drift_results = detector.detect_drift(endpoints)

    drifted = drift_results.get("drifted", [])
    uncovered = drift_results.get("uncovered", [])

    if not drifted and not uncovered:
        print("\n  No drift detected — all contracts are in sync!")
        print("  Nothing to fix.\n")
        sys.exit(0)

    print(f"\n  Found {len(drifted)} drifted and {len(uncovered)} uncovered endpoint(s).")

    # Step 3: Regenerate contracts for affected endpoints
    # Build a lookup from spec endpoints
    spec_by_path = {}
    for ep in endpoints:
        key = (ep["method"].upper(), ep["path"])
        spec_by_path[key] = ep

    generator = ContractGenerator(output_dir=args.contracts_dir)
    regenerated_files = {}  # {relative_path: yaml_content}

    # Fix drifted contracts (schema mismatch → regenerate)
    for item in drifted:
        method = item["method"]
        url = item["url"]
        # Find the matching spec endpoint
        matched_ep = _find_matching_endpoint(method, url, spec_by_path)
        if matched_ep:
            file_path = generator._build_file_path(matched_ep)
            contract = generator._build_contract(matched_ep)
            header = generator._build_header_comment(matched_ep)
            yaml_content = header + yaml.dump(
                contract, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
            # Write locally
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            # Track for MR (use relative path from project root)
            rel_path = _to_relative_path(file_path)
            regenerated_files[rel_path] = yaml_content
            print(f"    Fixed: {method} {url} → {os.path.basename(file_path)}")

    # Generate contracts for uncovered endpoints
    for item in uncovered:
        method = item["method"].upper()
        path = item["path"]
        key = (method, path)
        ep = spec_by_path.get(key)
        if ep:
            file_path = generator._build_file_path(ep)
            contract = generator._build_contract(ep)
            header = generator._build_header_comment(ep)
            yaml_content = header + yaml.dump(
                contract, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            rel_path = _to_relative_path(file_path)
            regenerated_files[rel_path] = yaml_content
            print(f"    Generated: {method} {path} → {os.path.basename(file_path)}")

    print(f"\n  Total: {len(regenerated_files)} contract file(s) written locally.")

    # Step 4: Create GitLab MR if requested
    if args.create_mr:
        print("\n  Creating GitLab Merge Request...")
        try:
            mr_creator = MRCreator()
            result = mr_creator.create_fix_mr(
                drift_results=drift_results,
                regenerated_files=regenerated_files,
                target_branch=args.target_branch,
            )
            if result["success"]:
                print(f"\n  SUCCESS: {result['message']}")
                print(f"  MR URL: {result['mr_url']}")
            else:
                print(f"\n  {result['message']}")
        except ValueError as e:
            print(f"\n  [ERROR] {e}")
            print("  Files were written locally. Fix the configuration and retry with --create-mr.")
            sys.exit(1)
        except RuntimeError as e:
            print(f"\n  [ERROR] GitLab API error: {e}")
            print("  Files were written locally. You can commit and push them manually.")
            sys.exit(1)
    else:
        print("\n  Files written locally only.")
        print("  To also create a GitLab MR, rerun with --create-mr flag:")
        print("    python main.py fix --create-mr")
        print("\n  Required env vars for MR creation:")
        print("    GITLAB_TOKEN=<your-personal-access-token>")
        print("    CI_PROJECT_ID=<numeric-project-id>  (auto-set in GitLab CI)")

    print("")

    # Save report if requested
    if args.save_report:
        reporter = ReportGenerator()
        report = reporter.generate_drift_report(drift_results)
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports", "fix_report.txt"
        )
        reporter.save_report(report, report_path)

    # Auto-notify if --notify flag is set
    if args.notify:
        notifier = Notifier()
        result = notifier.auto_notify(drift_results, command_name="fix", pipeline_url=args.pipeline_url)
        _print_notify_result(result)

    return regenerated_files


def _find_matching_endpoint(method, contract_url, spec_by_path):
    """
    Finds the spec endpoint that matches a contract's method + URL.
    Handles the mapping from concrete URLs (/api/users/1) to spec paths (/api/users/{id}).
    """
    import re

    method = method.upper()

    # Direct match first
    for (m, path), ep in spec_by_path.items():
        if m == method and path == contract_url:
            return ep

    # Pattern match: replace concrete values with path params
    for (m, path), ep in spec_by_path.items():
        if m != method:
            continue
        # Build regex from spec path: /api/users/{id} → /api/users/[^/]+
        pattern = re.sub(r"\{[^}]+\}", "[^/]+", path)
        if re.fullmatch(pattern, contract_url):
            return ep

    return None


def _to_relative_path(abs_path):
    """
    Converts an absolute file path to a project-relative path.
    e.g., C:\\Projects\\...\\provider-api\\src\\...\\file.yml → provider-api/src/.../file.yml
    """
    abs_path = os.path.normpath(abs_path)
    # Walk up to find the project root marker (look for provider-api or consumer-api)
    parts = abs_path.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part in ("provider-api", "consumer-api", "ai-agent"):
            return "/".join(parts[i:])
    # Fallback: just the filename
    return os.path.basename(abs_path)


def cmd_dashboard(args):
    """
    DASHBOARD command — Starts the Contract Health Dashboard web UI.

    Launches a Flask web server that shows:
    - Overall health status (HEALTHY / WARNING / CRITICAL)
    - Contract coverage percentage
    - Per-endpoint coverage breakdown
    - Drift detection results
    - Health check history over time

    The dashboard fetches live data from the running Provider API.
    """
    from dashboard import app

    port = args.port
    print("\n" + "=" * 65)
    print("  AI AGENT: Contract Health Dashboard")
    print("=" * 65)
    print(f"\n  Starting dashboard on http://localhost:{port}")
    print(f"  Provider URL: {args.provider_url}")
    print(f"\n  Open your browser to http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")

    os.environ["PROVIDER_URL"] = args.provider_url
    app.run(host="0.0.0.0", port=port, debug=args.debug)


def cmd_notify(args):
    """
    NOTIFY command — Runs drift detection and sends notifications
    to Slack and/or email if issues are found.

    Steps:
      1. Fetch the current OpenAPI spec
      2. Run drift detection
      3. If drift found (WARNING or CRITICAL), send notification
      4. Optionally notify about a specific test failure
    """
    print("\n" + "=" * 65)
    print("  AI AGENT: Team Notification")
    print("=" * 65)

    # If notifying about a specific test failure
    if args.job_name:
        notifier = Notifier()
        result = notifier.notify_test_failure(
            job_name=args.job_name,
            exit_code=args.exit_code,
            log_snippet=args.log_snippet,
            pipeline_url=args.pipeline_url,
        )
        _print_notify_result(result)
        return

    # Otherwise, run drift detection and notify
    reader = OpenApiSpecReader(args.provider_url)
    try:
        if args.spec_file:
            reader.load_spec_from_file(args.spec_file)
        else:
            reader.fetch_spec()
    except (ConnectionError, ValueError) as e:
        print(str(e))
        sys.exit(1)

    endpoints = reader.extract_endpoints()
    detector = DriftDetector(contracts_dir=args.contracts_dir)
    drift_results = detector.detect_drift(endpoints)

    summary = drift_results.get("summary", {})
    health = summary.get("health", "UNKNOWN")
    print(f"\n  Health: {health}")
    print(f"  Coverage: {summary.get('coverage_percent', '?')}%")

    notifier = Notifier()
    result = notifier.notify_drift(
        drift_results=drift_results,
        pipeline_url=args.pipeline_url,
    )
    _print_notify_result(result)


def _print_notify_result(result):
    """Prints a summary of notification results."""
    sent_any = False
    if result.get("slack"):
        print("  Slack: Sent")
        sent_any = True
    if result.get("email"):
        print("  Email: Sent")
        sent_any = True
    if not sent_any:
        print("\n  No notifications sent.")
        print("  Configure SLACK_WEBHOOK_URL and/or SMTP_HOST to enable.")
    print("")


def main():
    """
    Main entry point — parses CLI arguments and dispatches to the
    appropriate command handler.
    """
    parser = argparse.ArgumentParser(
        prog="contract-agent",
        description=(
            "AI Agent for Contract Testing Automation\n"
            "Reads OpenAPI specs and generates/validates Spring Cloud Contract YAML files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py generate                  Generate contracts from running Provider\n"
            "  python main.py generate --overwrite       Regenerate all contracts\n"
            "  python main.py generate --spec-file spec.json    Generate from saved spec file\n"
            "  python main.py drift                      Detect contract drift\n"
            "  python main.py drift --notify             Drift detection + auto-notify\n"
            "  python main.py report                     Full contract health report\n"
            "  python main.py report --notify            Report + email summary to team\n"
            "  python main.py validate                   Validate contracts (for CI/CD)\n"
            "  python main.py ci                         Generate .gitlab-ci.yml pipeline\n"
            "  python main.py fix                        Auto-fix drifted contracts (local)\n"
            "  python main.py fix --create-mr            Auto-fix + create GitLab MR\n"
            "  python main.py notify                     Send notifications on drift\n"
            "  python main.py dashboard                  Start the health dashboard\n"
        ),
    )

    # Global options (shared by all commands)
    parser.add_argument(
        "--provider-url",
        default="http://localhost:8080",
        help="Base URL of the running Provider API (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--spec-file",
        default=None,
        help="Path to a saved OpenAPI spec JSON file (instead of fetching from Provider)",
    )
    parser.add_argument(
        "--contracts-dir",
        default=get_default_contracts_dir(),
        help="Directory containing contract YAML files",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save the report to a file in ai-agent/reports/",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Auto-send Slack/email notifications when issues are detected",
    )
    parser.add_argument(
        "--pipeline-url",
        default=os.environ.get("CI_PIPELINE_URL"),
        help="GitLab pipeline URL to include in notifications (auto-set in CI)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- generate ---
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate contract YAML files from the OpenAPI spec",
    )
    gen_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing contract files (default: skip existing)",
    )
    gen_parser.add_argument(
        "--output-dir",
        default=get_default_contracts_dir(),
        help="Directory to output generated contract files",
    )

    # --- drift ---
    subparsers.add_parser(
        "drift",
        help="Detect drift between existing contracts and the OpenAPI spec",
    )

    # --- report ---
    subparsers.add_parser(
        "report",
        help="Generate a full contract health report",
    )

    # --- validate ---
    subparsers.add_parser(
        "validate",
        help="Validate existing contracts against the spec (CI/CD friendly)",
    )

    # --- ci ---
    ci_parser = subparsers.add_parser(
        "ci",
        help="Generate .gitlab-ci.yml pipeline configuration",
    )
    ci_parser.add_argument(
        "--project-root",
        default=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
        help="Root directory of the project (default: parent of ai-agent/)",
    )
    ci_parser.add_argument(
        "--output",
        default=None,
        help="Output path for .gitlab-ci.yml (default: project_root/.gitlab-ci.yml)",
    )

    # --- dashboard ---
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Start the Contract Health Dashboard web UI",
    )
    dashboard_parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="Port to run the dashboard on (default: 5050)",
    )
    dashboard_parser.add_argument(
        "--debug",
        action="store_true",
        help="Run Flask in debug mode with auto-reload",
    )

    # --- fix ---
    fix_parser = subparsers.add_parser(
        "fix",
        help="Auto-fix drifted/missing contracts and optionally create a GitLab MR",
    )
    fix_parser.add_argument(
        "--create-mr",
        action="store_true",
        help="Create a GitLab Merge Request with the fixed contracts",
    )
    fix_parser.add_argument(
        "--target-branch",
        default="main",
        help="Target branch for the MR (default: main)",
    )

    # --- notify ---
    notify_parser = subparsers.add_parser(
        "notify",
        help="Send Slack/email notification on contract drift or test failure",
    )
    notify_parser.add_argument(
        "--job-name",
        default=None,
        help="CI job name (for test failure notifications)",
    )
    notify_parser.add_argument(
        "--exit-code",
        type=int,
        default=1,
        help="Exit code of the failed job (default: 1)",
    )
    notify_parser.add_argument(
        "--log-snippet",
        default=None,
        help="Last lines of log output from the failed job",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Dispatch to the appropriate command handler
    commands = {
        "generate": cmd_generate,
        "drift": cmd_drift,
        "report": cmd_report,
        "validate": cmd_validate,
        "ci": cmd_ci,
        "fix": cmd_fix,
        "notify": cmd_notify,
        "dashboard": cmd_dashboard,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
