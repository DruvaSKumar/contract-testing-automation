# ============================================================
# coverage_tracker.py — Contract Coverage Metrics & Trends
# ============================================================
# PURPOSE:
#   Tracks contract coverage metrics over time and provides
#   trend analysis for the dashboard. Calculates:
#
#     - Endpoint coverage (% of API endpoints with contracts)
#     - Positive scenario coverage (happy path)
#     - Negative scenario coverage (error cases: 400, 404, etc.)
#     - Coverage trend direction (improving/declining/stable)
#     - Historical coverage data for charts
#
# USAGE:
#   from agent.coverage_tracker import CoverageTracker
#   tracker = CoverageTracker()
#   metrics = tracker.calculate_coverage(endpoints, contracts_dir)
#   tracker.record_snapshot(metrics)
#   trends = tracker.get_trends()
# ============================================================

import json
import os
import glob
from datetime import datetime, timezone

import yaml


class CoverageTracker:
    """
    Calculates and tracks contract coverage metrics over time.
    """

    HISTORY_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "coverage_history.json"
    )

    # Error status codes that negative contracts cover
    NEGATIVE_STATUS_CODES = {400, 401, 403, 404, 405, 409, 422, 500}

    def __init__(self, history_file=None):
        self.history_file = history_file or self.HISTORY_FILE

    # ================================================================
    # Coverage Calculation
    # ================================================================

    def calculate_coverage(self, endpoints, contracts_dir=None):
        """
        Calculates detailed coverage metrics.

        Args:
            endpoints: List of endpoint dicts from OpenApiSpecReader
            contracts_dir: Path to the contracts directory

        Returns:
            dict with comprehensive coverage metrics
        """
        if contracts_dir is None:
            contracts_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "..", "provider-api", "src", "test", "resources", "contracts", "user"
            )

        # Load all contract files
        contracts = self._load_contracts(contracts_dir)

        # Classify contracts
        positive_contracts = []
        negative_contracts = []

        for contract in contracts:
            status = self._get_contract_status(contract)
            if status in self.NEGATIVE_STATUS_CODES:
                negative_contracts.append(contract)
            else:
                positive_contracts.append(contract)

        # Calculate endpoint coverage
        total_endpoints = len(endpoints)
        covered_endpoints = self._count_covered_endpoints(endpoints, contracts)

        # Calculate negative scenario coverage
        # For each endpoint, what error scenarios are covered?
        negative_coverage = self._calculate_negative_coverage(endpoints, negative_contracts)

        # Overall metrics
        endpoint_coverage_pct = (covered_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        positive_count = len(positive_contracts)
        negative_count = len(negative_contracts)
        total_contracts = len(contracts)

        # Potential negative scenarios (each endpoint could have multiple error cases)
        potential_negatives = self._count_potential_negatives(endpoints)
        negative_coverage_pct = (negative_count / potential_negatives * 100) if potential_negatives > 0 else 0

        # Combined score (weighted: 60% endpoint coverage + 40% negative coverage)
        combined_score = (endpoint_coverage_pct * 0.6) + (negative_coverage_pct * 0.4)

        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "endpoint_coverage": {
                "total_endpoints": total_endpoints,
                "covered_endpoints": covered_endpoints,
                "percentage": round(endpoint_coverage_pct, 1),
            },
            "positive_contracts": {
                "count": positive_count,
                "endpoints_covered": covered_endpoints,
            },
            "negative_contracts": {
                "count": negative_count,
                "potential_scenarios": potential_negatives,
                "percentage": round(negative_coverage_pct, 1),
                "by_status": self._group_by_status(negative_contracts),
            },
            "total_contracts": total_contracts,
            "combined_score": round(combined_score, 1),
            "contracts_per_endpoint": round(total_contracts / total_endpoints, 1) if total_endpoints > 0 else 0,
            "negative_details": negative_coverage,
        }

    # ================================================================
    # Trend Analysis
    # ================================================================

    def record_snapshot(self, metrics):
        """Records a coverage snapshot to the history file."""
        history = self._load_history()
        history.append({
            "timestamp": metrics["timestamp"],
            "endpoint_coverage_pct": metrics["endpoint_coverage"]["percentage"],
            "negative_coverage_pct": metrics["negative_contracts"]["percentage"],
            "combined_score": metrics["combined_score"],
            "total_contracts": metrics["total_contracts"],
            "positive_count": metrics["positive_contracts"]["count"],
            "negative_count": metrics["negative_contracts"]["count"],
            "total_endpoints": metrics["endpoint_coverage"]["total_endpoints"],
        })
        # Keep last 100 entries
        history = history[-100:]
        self._save_history(history)

    def get_trends(self, window=5):
        """
        Analyzes coverage trends over the last N snapshots.

        Args:
            window: Number of recent snapshots to consider

        Returns:
            dict with trend analysis
        """
        history = self._load_history()

        if len(history) < 2:
            return {
                "direction": "insufficient_data",
                "message": "Not enough data points for trend analysis. Need at least 2 snapshots.",
                "data_points": len(history),
                "history": history,
            }

        recent = history[-window:] if len(history) >= window else history
        oldest = recent[0]
        newest = recent[-1]

        # Calculate deltas
        coverage_delta = newest["endpoint_coverage_pct"] - oldest["endpoint_coverage_pct"]
        negative_delta = newest["negative_coverage_pct"] - oldest["negative_coverage_pct"]
        score_delta = newest["combined_score"] - oldest["combined_score"]
        contract_delta = newest["total_contracts"] - oldest["total_contracts"]

        # Determine direction
        if score_delta > 2:
            direction = "improving"
            icon = "📈"
        elif score_delta < -2:
            direction = "declining"
            icon = "📉"
        else:
            direction = "stable"
            icon = "➡️"

        # Build message
        parts = []
        if coverage_delta != 0:
            parts.append(f"Endpoint coverage: {'+' if coverage_delta > 0 else ''}{coverage_delta:.1f}%")
        if negative_delta != 0:
            parts.append(f"Error coverage: {'+' if negative_delta > 0 else ''}{negative_delta:.1f}%")
        if contract_delta != 0:
            parts.append(f"Contracts: {'+' if contract_delta > 0 else ''}{contract_delta}")

        message = f"{icon} Coverage is {direction}"
        if parts:
            message += f" ({', '.join(parts)})"

        return {
            "direction": direction,
            "icon": icon,
            "message": message,
            "coverage_delta": round(coverage_delta, 1),
            "negative_delta": round(negative_delta, 1),
            "score_delta": round(score_delta, 1),
            "contract_delta": contract_delta,
            "data_points": len(history),
            "history": history,
            "period": {
                "from": oldest["timestamp"],
                "to": newest["timestamp"],
            },
        }

    def get_summary_text(self, metrics, trends):
        """Returns a formatted summary for CLI output."""
        lines = []
        lines.append("=" * 65)
        lines.append("  📊 CONTRACT COVERAGE METRICS & TRENDS")
        lines.append("=" * 65)
        lines.append("")

        # Current metrics
        ep = metrics["endpoint_coverage"]
        lines.append(f"  Endpoint Coverage:   {ep['percentage']}% ({ep['covered_endpoints']}/{ep['total_endpoints']})")
        lines.append(f"  Positive Contracts:  {metrics['positive_contracts']['count']}")
        lines.append(f"  Negative Contracts:  {metrics['negative_contracts']['count']} "
                     f"({metrics['negative_contracts']['percentage']}% of potential scenarios)")
        lines.append(f"  Total Contracts:     {metrics['total_contracts']}")
        lines.append(f"  Contracts/Endpoint:  {metrics['contracts_per_endpoint']}")
        lines.append(f"  Combined Score:      {metrics['combined_score']}%")
        lines.append("")

        # Negative coverage breakdown
        by_status = metrics["negative_contracts"]["by_status"]
        if by_status:
            lines.append("  Error Scenario Breakdown:")
            for status, count in sorted(by_status.items()):
                label = {400: "Bad Request", 404: "Not Found", 401: "Unauthorized",
                         403: "Forbidden", 500: "Server Error"}.get(int(status), f"HTTP {status}")
                lines.append(f"    HTTP {status} ({label}): {count} contract(s)")
            lines.append("")

        # Trend
        if trends["direction"] != "insufficient_data":
            lines.append(f"  Trend: {trends['message']}")
            lines.append(f"  Period: {trends['period']['from']} → {trends['period']['to']}")
        else:
            lines.append(f"  Trend: {trends['message']}")
        lines.append("")
        lines.append("=" * 65)

        return "\n".join(lines)

    # ================================================================
    # Internal Helpers
    # ================================================================

    def _load_contracts(self, contracts_dir):
        """Loads all YAML contract files from the directory."""
        contracts = []
        pattern = os.path.join(contracts_dir, "**", "*.yml")
        for filepath in glob.glob(pattern, recursive=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    # Skip comment lines at the top
                    content = f.read()
                    # Find first non-comment line
                    yaml_start = 0
                    for i, line in enumerate(content.split("\n")):
                        if line.strip() and not line.strip().startswith("#"):
                            yaml_start = content.index(line)
                            break
                    data = yaml.safe_load(content[yaml_start:])
                    if data:
                        data["_file"] = os.path.basename(filepath)
                        data["_path"] = filepath
                        contracts.append(data)
            except (yaml.YAMLError, OSError):
                continue
        return contracts

    def _get_contract_status(self, contract):
        """Extracts the HTTP status code from a contract."""
        response = contract.get("response", {})
        return response.get("status", 200)

    def _count_covered_endpoints(self, endpoints, contracts):
        """Counts how many spec endpoints have at least one positive contract."""
        covered = set()
        for contract in contracts:
            request = contract.get("request", {})
            method = request.get("method", "").upper()
            url = request.get("url", "")
            # Normalize URL patterns
            for ep in endpoints:
                if ep["method"].upper() == method and self._url_matches(url, ep["path"]):
                    covered.add((ep["method"].upper(), ep["path"]))
                    break
        return len(covered)

    def _url_matches(self, contract_url, spec_path):
        """Checks if a contract URL matches a spec path (with path params)."""
        import re
        # Convert spec path params to regex: /users/{id} → /users/[^/]+
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", spec_path)
        pattern = f"^{pattern}$"
        return bool(re.match(pattern, contract_url))

    def _calculate_negative_coverage(self, endpoints, negative_contracts):
        """Calculates which endpoints have negative scenario coverage."""
        coverage = {}
        for ep in endpoints:
            key = f"{ep['method'].upper()} {ep['path']}"
            coverage[key] = {
                "endpoint": key,
                "scenarios_covered": [],
            }
            for contract in negative_contracts:
                request = contract.get("request", {})
                method = request.get("method", "").upper()
                url = request.get("url", "")
                status = self._get_contract_status(contract)
                if method == ep["method"].upper() and self._url_matches(url, ep["path"]):
                    coverage[key]["scenarios_covered"].append(status)

        return coverage

    def _count_potential_negatives(self, endpoints):
        """
        Estimates the number of potential negative test scenarios.
        Heuristic: each endpoint could have ~3 error scenarios
        (400 bad request, 404 not found, validation errors).
        POST/PUT endpoints have more potential errors.
        """
        count = 0
        for ep in endpoints:
            method = ep["method"].upper()
            if method in ("POST", "PUT", "PATCH"):
                count += 3  # 400 missing fields, 400 invalid data, 404 (for PUT/PATCH)
            elif method in ("GET", "DELETE"):
                count += 1  # 404 not found
        return count

    def _group_by_status(self, contracts):
        """Groups negative contracts by HTTP status code."""
        groups = {}
        for contract in contracts:
            status = str(self._get_contract_status(contract))
            groups[status] = groups.get(status, 0) + 1
        return groups

    def _load_history(self):
        """Loads coverage history from disk."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_history(self, history):
        """Saves coverage history to disk."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
