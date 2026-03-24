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
#   python main.py report                Full report (drift + coverage)
#   python main.py validate              Validate existing contracts against spec
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
# ============================================================

import argparse
import os
import sys

from agent.spec_reader import OpenApiSpecReader
from agent.contract_generator import ContractGenerator
from agent.drift_detector import DriftDetector
from agent.report_generator import ReportGenerator
from agent.ci_config_generator import CIConfigGenerator


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
            "  python main.py report                     Full contract health report\n"
            "  python main.py validate                   Validate contracts (for CI/CD)\n"
            "  python main.py ci                          Generate .gitlab-ci.yml pipeline\n"
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
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
