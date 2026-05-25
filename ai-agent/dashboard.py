# ============================================================
# dashboard.py — Contract Health Dashboard (Flask Web App)
# ============================================================
# PURPOSE:
#   A comprehensive web dashboard that visualizes contract testing
#   health in real-time. Integrates all AI Agent modules:
#
#     - Overall health status (HEALTHY / WARNING / CRITICAL)
#     - Contract coverage (endpoint + negative scenario coverage)
#     - Coverage trends over time (line chart)
#     - Per-endpoint coverage breakdown with statuses
#     - Drift detection results (uncovered, orphaned, drifted)
#     - Root cause analysis of recent failures
#     - Backward compatibility status
#     - CI pipeline status
#     - Actionable remediation suggestions
#     - History of health checks over time
#
# USAGE:
#   cd ai-agent
#   python dashboard.py
#   # Open http://localhost:5050 in your browser
#
# PREREQUISITES:
#   - Provider API must be running on http://localhost:8080
#   - Python packages: pip install -r requirements.txt
# ============================================================

import json
import os
import sys
import glob
import subprocess
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

# Add parent directory so we can import agent modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.spec_reader import OpenApiSpecReader
from agent.drift_detector import DriftDetector
from agent.coverage_tracker import CoverageTracker
from agent.root_cause_analyzer import RootCauseAnalyzer

app = Flask(__name__, template_folder="templates")

# ---- Configuration ----
PROVIDER_URL = os.environ.get("PROVIDER_URL", "http://localhost:8080")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "dashboard_history.json")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def load_history():
    """Load health check history from disk."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    """Persist health check history to disk."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    # Keep only the last 50 entries
    history = history[-50:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def load_coverage_history():
    """Load coverage trend history."""
    coverage_file = os.path.join(REPORTS_DIR, "coverage_history.json")
    if os.path.exists(coverage_file):
        with open(coverage_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_compat_report():
    """Load the latest backward compatibility report."""
    compat_file = os.path.join(REPORTS_DIR, "compatibility_report.txt")
    if os.path.exists(compat_file):
        with open(compat_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "BREAKING CHANGES DETECTED" in content:
            return {"status": "breaking", "report": content}
        elif "COMPATIBLE (with warnings)" in content:
            return {"status": "warning", "report": content}
        elif "FULLY COMPATIBLE" in content:
            return {"status": "compatible", "report": content}
        return {"status": "unknown", "report": content}
    return None


def load_rca_report():
    """Load the latest root cause analysis."""
    rca_file = os.path.join(REPORTS_DIR, "root_cause_analysis.txt")
    if os.path.exists(rca_file):
        with open(rca_file, "r", encoding="utf-8") as f:
            return f.read()
    return None


def run_live_rca(drift_results):
    """
    Run Root Cause Analysis live based on fresh surefire reports
    and drift detection results.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    provider_reports = os.path.join(base, "..", "provider-api", "target", "surefire-reports")
    consumer_reports = os.path.join(base, "..", "consumer-api", "target", "surefire-reports")

    analyzer = RootCauseAnalyzer()
    rca = analyzer.analyze_failures(
        provider_report_dir=provider_reports if os.path.isdir(provider_reports) else None,
        consumer_report_dir=consumer_reports if os.path.isdir(consumer_reports) else None,
        drift_results=drift_results,
    )

    # Also add drift-based analysis if there are drifts but no test failures
    if drift_results and not rca["has_failures"]:
        drifted = drift_results.get("drifted", [])
        if drifted:
            lines = []
            lines.append(f"⚠️ {len(drifted)} contract drift(s) detected — these WILL cause test failures:")
            lines.append("")
            for d in drifted:
                lines.append(f"  • {d['method']} {d['url']} ({d['file']})")
                for issue in d.get("issues", []):
                    lines.append(f"    └─ {issue}")
                suggestion = _get_drift_suggestion(d)
                if suggestion:
                    lines.append(f"    💡 Fix: {suggestion}")
                lines.append("")
            rca["summary"] = "\n".join(lines)
            rca["has_failures"] = True
            rca["total_failures"] = len(drifted)

    return rca


def _get_drift_suggestion(drift_entry):
    """Generate actionable fix suggestion for a specific drift."""
    issues = drift_entry.get("issues", [])
    if not issues:
        return None

    suggestions = []
    for issue in issues:
        issue_lower = issue.lower()
        if "request field" in issue_lower and "not in api spec" in issue_lower:
            field = issue.split("'")[1] if "'" in issue else "unknown"
            suggestions.append(
                f"Remove field '{field}' from contract request body, or revert the field name in the Provider model"
            )
        elif "required request field" in issue_lower and "missing from contract" in issue_lower:
            field = issue.split("'")[1] if "'" in issue else "unknown"
            suggestions.append(
                f"Add required field '{field}' to contract request body"
            )
        elif "in api spec but missing from contract" in issue_lower:
            field = issue.split("'")[1] if "'" in issue else "unknown"
            suggestions.append(
                f"Add field '{field}' to the contract response body, or run: python main.py generate --overwrite"
            )
        elif "in contract but not in api spec" in issue_lower:
            field = issue.split("'")[1] if "'" in issue else "unknown"
            suggestions.append(
                f"Field '{field}' was removed from the API. Remove it from the contract or restore it in the Provider"
            )
        else:
            suggestions.append("Run: python main.py generate --overwrite to regenerate the contract")

    return suggestions[0] if len(suggestions) == 1 else "; ".join(suggestions)


def get_recent_test_results():
    """
    Run Maven tests LIVE and parse fresh surefire reports.
    This ensures the dashboard always reflects the current state of
    contracts — no stale data from previous manual runs.

    In CI (CI env var set), skips running Maven since tests already ran
    in prior pipeline jobs and surefire reports are available as artifacts.
    """
    import xml.etree.ElementTree as ET

    base = os.path.dirname(os.path.abspath(__file__))
    results = {"provider": None, "consumer": None}
    is_ci = os.environ.get("CI") or os.environ.get("GITLAB_CI")

    for name, subdir in [("provider", "provider-api"), ("consumer", "consumer-api")]:
        project_dir = os.path.join(base, "..", subdir)
        if not os.path.isdir(project_dir):
            continue

        # In CI, surefire reports already exist from earlier pipeline jobs.
        # Locally, run mvn clean test LIVE so results reflect current contract state.
        if not is_ci:
            try:
                subprocess.run(
                    "mvn clean test -q",
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    shell=True,
                )
            except subprocess.TimeoutExpired:
                pass  # Even on timeout, partial surefire reports may exist

        # Parse surefire reports
        report_dir = os.path.join(project_dir, "target", "surefire-reports")
        if os.path.isdir(report_dir):
            xml_files = glob.glob(os.path.join(report_dir, "TEST-*.xml"))
            total_tests = 0
            total_failures = 0
            total_errors = 0
            for xml_file in xml_files:
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    total_tests += int(root.get("tests", 0))
                    total_failures += int(root.get("failures", 0))
                    total_errors += int(root.get("errors", 0))
                except Exception:
                    continue
            if total_tests > 0:
                results[name] = {
                    "tests": total_tests,
                    "passed": total_tests - total_failures - total_errors,
                    "failures": total_failures + total_errors,
                    "pass_rate": round((total_tests - total_failures - total_errors) / total_tests * 100, 1),
                }
    return results


def run_health_check():
    """
    Runs a full health check by fetching the OpenAPI spec,
    extracting endpoints, and detecting drift.

    Returns:
        dict with keys: drift_results, endpoints, timestamp, error, coverage, etc.
    """
    try:
        reader = OpenApiSpecReader(PROVIDER_URL)
        reader.fetch_spec()
        endpoints = reader.extract_endpoints()

        detector = DriftDetector()
        drift = detector.detect_drift(endpoints)

        # Coverage metrics
        tracker = CoverageTracker()
        coverage = tracker.calculate_coverage(endpoints)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Append to history
        history = load_history()
        history.append({
            "timestamp": timestamp,
            "health": drift["summary"]["health"],
            "coverage_percent": drift["summary"]["coverage_percent"],
            "covered": drift["summary"]["covered_count"],
            "uncovered": drift["summary"]["uncovered_count"],
            "orphaned": drift["summary"]["orphaned_count"],
            "drifted": drift["summary"]["drifted_count"],
            "total_endpoints": drift["summary"]["total_spec_endpoints"],
            "total_contracts": drift["summary"]["total_contracts"],
        })
        save_history(history)

        return {
            "drift": drift,
            "endpoints": endpoints,
            "coverage": coverage,
            "timestamp": timestamp,
            "error": None,
        }
    except ConnectionError:
        return {
            "drift": None,
            "endpoints": [],
            "coverage": None,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": f"Cannot connect to Provider API at {PROVIDER_URL}. Is it running?",
        }
    except Exception as e:
        return {
            "drift": None,
            "endpoints": [],
            "coverage": None,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": str(e),
        }


# ---- Routes ----

@app.route("/")
def dashboard():
    """Main dashboard page — runs a live health check and renders the UI."""
    result = run_health_check()
    history = load_history()
    coverage_history = load_coverage_history()
    compat_report = load_compat_report()
    test_results = get_recent_test_results()

    # Run live RCA based on fresh test results and drift
    live_rca = run_live_rca(result.get("drift"))
    rca_report = live_rca["summary"] if live_rca and live_rca.get("has_failures") else None

    return render_template(
        "dashboard.html",
        result=result,
        history=history,
        coverage_history=coverage_history,
        compat_report=compat_report,
        rca_report=rca_report,
        test_results=test_results,
    )


@app.route("/api/health")
def api_health():
    """JSON API endpoint — returns health check data for programmatic access."""
    result = run_health_check()
    return jsonify({
        "timestamp": result["timestamp"],
        "error": result["error"],
        "summary": result["drift"]["summary"] if result["drift"] else None,
        "covered": result["drift"]["covered"] if result["drift"] else [],
        "uncovered": result["drift"]["uncovered"] if result["drift"] else [],
        "orphaned": result["drift"]["orphaned"] if result["drift"] else [],
        "drifted": result["drift"]["drifted"] if result["drift"] else [],
        "coverage": result["coverage"],
    })


@app.route("/api/history")
def api_history():
    """JSON API endpoint — returns health check history."""
    return jsonify(load_history())


@app.route("/api/coverage-history")
def api_coverage_history():
    """JSON API endpoint — returns coverage trend history."""
    return jsonify(load_coverage_history())


@app.route("/api/test-results")
def api_test_results():
    """JSON API endpoint — returns recent test results."""
    return jsonify(get_recent_test_results())


def export_static_html(output_path=None):
    """
    Generates a static HTML snapshot of the dashboard.
    Used in CI to produce a browsable artifact without a running server.
    """
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "reports", "dashboard.html",
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with app.app_context():
        result = run_health_check()
        history = load_history()
        coverage_history = load_coverage_history()
        compat_report = load_compat_report()
        test_results = get_recent_test_results()

        # Run live RCA
        live_rca = run_live_rca(result.get("drift"))
        rca_report = live_rca["summary"] if live_rca and live_rca.get("has_failures") else None

        html = render_template(
            "dashboard.html",
            result=result,
            history=history,
            coverage_history=coverage_history,
            compat_report=compat_report,
            rca_report=rca_report,
            test_results=test_results,
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  [DASHBOARD] Static snapshot saved to: {output_path}")
    return output_path


# ---- Entry Point ----

if __name__ == "__main__":
    # Check for --export flag to generate static HTML
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        export_static_html(path)
        sys.exit(0)

    port = int(os.environ.get("DASHBOARD_PORT", 5050))
    print(f"\n{'=' * 60}")
    print(f"  Contract Health Dashboard")
    print(f"  Running on http://localhost:{port}")
    print(f"  Provider URL: {PROVIDER_URL}")
    print(f"{'=' * 60}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
