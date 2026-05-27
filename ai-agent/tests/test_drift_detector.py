# ============================================================
# test_drift_detector.py — Unit Tests for Drift Detector
# ============================================================

import os
import pytest
import yaml

from agent.drift_detector import DriftDetector


class TestDriftDetector:
    """Tests for the DriftDetector module."""

    # ---- Initialization Tests ----

    def test_init_custom_dir(self, contracts_dir):
        """Should accept a custom contracts directory."""
        detector = DriftDetector(contracts_dir=contracts_dir)
        assert detector.contracts_dir == os.path.normpath(contracts_dir)

    # ---- load_existing_contracts Tests ----

    def test_load_existing_contracts_empty(self, contracts_dir):
        """Should return empty list for empty directory."""
        detector = DriftDetector(contracts_dir=contracts_dir)
        contracts = detector.load_existing_contracts()
        assert contracts == []

    def test_load_existing_contracts_finds_all(self, populated_contracts_dir):
        """Should load all YAML contract files."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        contracts = detector.load_existing_contracts()
        assert len(contracts) == 5

    def test_load_existing_contracts_extracts_method(self, populated_contracts_dir):
        """Should extract HTTP method from each contract."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        contracts = detector.load_existing_contracts()

        methods = {c["method"] for c in contracts}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_load_existing_contracts_extracts_url(self, populated_contracts_dir):
        """Should extract URL from each contract."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        contracts = detector.load_existing_contracts()

        urls = {c["url"] for c in contracts}
        assert "/api/users" in urls
        assert "/api/users/1" in urls

    def test_load_nonexistent_dir(self, tmp_path):
        """Should return empty list for non-existent directory."""
        detector = DriftDetector(contracts_dir=str(tmp_path / "nonexistent"))
        contracts = detector.load_existing_contracts()
        assert contracts == []

    # ---- detect_drift Tests ----

    def test_detect_drift_no_drift(self, populated_contracts_dir, sample_endpoints):
        """Should report no drift when contracts match spec."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        report = detector.detect_drift(sample_endpoints)

        assert len(report["orphaned"]) == 0
        # May have uncovered if negative cases not present

    def test_detect_drift_finds_uncovered(self, contracts_dir, sample_endpoints):
        """Should find endpoints with no contracts (uncovered)."""
        # Empty contracts dir → all endpoints are uncovered
        detector = DriftDetector(contracts_dir=contracts_dir)
        report = detector.detect_drift(sample_endpoints)

        assert len(report["uncovered"]) == len(sample_endpoints)

    def test_detect_drift_finds_orphaned(self, tmp_path, sample_endpoints):
        """Should find contracts with no matching spec endpoint (orphaned)."""
        # Create a contract for a non-existent endpoint
        orphan_dir = tmp_path / "contracts" / "user"
        orphan_dir.mkdir(parents=True)

        orphan_contract = {
            "description": "Should return archived users",
            "name": "should_return_archived_users",
            "request": {"method": "GET", "url": "/api/archived-users"},
            "response": {"status": 200},
        }
        with open(orphan_dir / "should_return_archived_users.yml", "w") as f:
            yaml.dump(orphan_contract, f)

        detector = DriftDetector(contracts_dir=str(tmp_path / "contracts"))
        report = detector.detect_drift(sample_endpoints)

        assert len(report["orphaned"]) >= 1
        orphaned_urls = [o["url"] for o in report["orphaned"]]
        assert "/api/archived-users" in orphaned_urls

    def test_detect_drift_report_has_summary(self, populated_contracts_dir, sample_endpoints):
        """Should include a summary in the drift report."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        report = detector.detect_drift(sample_endpoints)

        assert "summary" in report

    def test_detect_drift_covered_endpoints(self, populated_contracts_dir, sample_endpoints):
        """Should list covered endpoints that are healthy."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        report = detector.detect_drift(sample_endpoints)

        assert "covered" in report
        assert len(report["covered"]) > 0

    def test_detect_drift_report_structure(self, populated_contracts_dir, sample_endpoints):
        """Should return all expected keys in drift report."""
        detector = DriftDetector(contracts_dir=populated_contracts_dir)
        report = detector.detect_drift(sample_endpoints)

        expected_keys = {"uncovered", "orphaned", "drifted", "covered", "summary"}
        assert expected_keys.issubset(set(report.keys()))
