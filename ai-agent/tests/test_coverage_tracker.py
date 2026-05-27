# ============================================================
# test_coverage_tracker.py — Unit Tests for Coverage Tracker
# ============================================================

import os
import json
import pytest

from agent.coverage_tracker import CoverageTracker


class TestCoverageTracker:
    """Tests for the CoverageTracker module."""

    @pytest.fixture
    def tracker(self, tmp_path):
        history_file = str(tmp_path / "coverage_history.json")
        return CoverageTracker(history_file=history_file)

    # ---- calculate_coverage Tests ----

    def test_calculate_coverage_full(self, tracker, sample_endpoints, populated_contracts_dir):
        """Should calculate coverage when contracts exist for endpoints."""
        metrics = tracker.calculate_coverage(sample_endpoints, populated_contracts_dir)

        assert "endpoint_coverage" in metrics
        assert "total_endpoints" in metrics["endpoint_coverage"]
        assert metrics["endpoint_coverage"]["total_endpoints"] == 5

    def test_calculate_coverage_empty_contracts(self, tracker, sample_endpoints, contracts_dir):
        """Should report 0% coverage when no contracts exist."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)

        assert metrics["endpoint_coverage"]["percentage"] == 0.0
        assert metrics["endpoint_coverage"]["covered_endpoints"] == 0

    def test_calculate_coverage_returns_dict(self, tracker, sample_endpoints, contracts_dir):
        """Should always return a dictionary."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        assert isinstance(metrics, dict)

    def test_calculate_coverage_has_timestamp(self, tracker, sample_endpoints, contracts_dir):
        """Should include a timestamp."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        assert "timestamp" in metrics

    def test_calculate_coverage_has_combined_score(self, tracker, sample_endpoints, contracts_dir):
        """Should include a combined score."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        assert "combined_score" in metrics

    # ---- record_snapshot Tests ----

    def test_record_snapshot_creates_file(self, tracker, sample_endpoints, contracts_dir):
        """Should create history file on first snapshot."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        tracker.record_snapshot(metrics)
        assert os.path.exists(tracker.history_file)

    def test_record_snapshot_appends(self, tracker, sample_endpoints, contracts_dir):
        """Should append to history on subsequent snapshots."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        tracker.record_snapshot(metrics)
        tracker.record_snapshot(metrics)

        with open(tracker.history_file, "r") as f:
            history = json.load(f)

        assert len(history) == 2

    # ---- get_trends Tests ----

    def test_get_trends_empty(self, tracker):
        """Should return a direction indicating no data when no history."""
        trends = tracker.get_trends()
        assert trends["direction"] in ("stable", "unknown", "no_data", "insufficient_data")

    def test_get_trends_stable(self, tracker, sample_endpoints, contracts_dir):
        """Should detect stable trend when coverage doesn't change."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        tracker.record_snapshot(metrics)
        tracker.record_snapshot(metrics)
        tracker.record_snapshot(metrics)

        trends = tracker.get_trends()
        assert trends["direction"] == "stable"

    def test_get_trends_returns_dict(self, tracker, sample_endpoints, contracts_dir):
        """Should always return a dict with direction key."""
        metrics = tracker.calculate_coverage(sample_endpoints, contracts_dir)
        tracker.record_snapshot(metrics)

        trends = tracker.get_trends()
        assert isinstance(trends, dict)
        assert "direction" in trends
