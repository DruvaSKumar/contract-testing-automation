# ============================================================
# dashboard.py — Contract Health Dashboard (Flask Web App)
# ============================================================
# PURPOSE:
#   A lightweight web dashboard that visualizes contract testing
#   health in real-time. Reuses the existing AI Agent modules
#   (spec_reader, drift_detector) to show:
#
#     - Overall health status (HEALTHY / WARNING / CRITICAL)
#     - Contract coverage percentage across all API endpoints
#     - Per-endpoint coverage breakdown with statuses
#     - Drift detection results (uncovered, orphaned, drifted)
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
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template

# Add parent directory so we can import agent modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.spec_reader import OpenApiSpecReader
from agent.drift_detector import DriftDetector

app = Flask(__name__, template_folder="templates")

# ---- Configuration ----
PROVIDER_URL = os.environ.get("PROVIDER_URL", "http://localhost:8080")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "dashboard_history.json")


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


def run_health_check():
    """
    Runs a full health check by fetching the OpenAPI spec,
    extracting endpoints, and detecting drift.

    Returns:
        dict with keys: drift_results, endpoints, timestamp, error
    """
    try:
        reader = OpenApiSpecReader(PROVIDER_URL)
        reader.fetch_spec()
        endpoints = reader.extract_endpoints()

        detector = DriftDetector()
        drift = detector.detect_drift(endpoints)

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
            "timestamp": timestamp,
            "error": None,
        }
    except ConnectionError:
        return {
            "drift": None,
            "endpoints": [],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": f"Cannot connect to Provider API at {PROVIDER_URL}. Is it running?",
        }
    except Exception as e:
        return {
            "drift": None,
            "endpoints": [],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": str(e),
        }


# ---- Routes ----

@app.route("/")
def dashboard():
    """Main dashboard page — runs a live health check and renders the UI."""
    result = run_health_check()
    history = load_history()
    return render_template("dashboard.html", result=result, history=history)


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
    })


@app.route("/api/history")
def api_history():
    """JSON API endpoint — returns health check history."""
    return jsonify(load_history())


# ---- Entry Point ----

if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 5050))
    print(f"\n{'=' * 60}")
    print(f"  Contract Health Dashboard")
    print(f"  Running on http://localhost:{port}")
    print(f"  Provider URL: {PROVIDER_URL}")
    print(f"{'=' * 60}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
