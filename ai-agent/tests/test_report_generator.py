# ============================================================
# test_report_generator.py — Unit Tests for Report Generator
# ============================================================

import pytest

from agent.report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for the ReportGenerator module."""

    @pytest.fixture
    def reporter(self):
        return ReportGenerator()

    # ---- Generation Report Tests ----

    def test_generation_report_all_generated(self, reporter):
        """Should produce a report when all contracts generated."""
        results = {
            "generated": ["/path/to/contract1.yml", "/path/to/contract2.yml"],
            "skipped": [],
            "errors": [],
        }
        report = reporter.generate_generation_report(results)

        assert "CONTRACT GENERATION REPORT" in report
        assert "Total Generated:  2" in report
        assert "Total Skipped:    0" in report
        assert "Total Errors:     0" in report

    def test_generation_report_some_skipped(self, reporter):
        """Should report skipped contracts."""
        results = {
            "generated": ["/path/to/new.yml"],
            "skipped": ["/path/to/existing.yml"],
            "errors": [],
        }
        report = reporter.generate_generation_report(results)

        assert "Total Skipped:    1" in report
        assert "already exist" in report

    def test_generation_report_with_errors(self, reporter):
        """Should report errors encountered during generation."""
        results = {
            "generated": [],
            "skipped": [],
            "errors": [
                ({"method": "get", "path": "/fail"}, "Schema parse error")
            ],
        }
        report = reporter.generate_generation_report(results)

        assert "Total Errors:     1" in report

    def test_generation_report_empty_results(self, reporter):
        """Should handle empty results gracefully."""
        results = {"generated": [], "skipped": [], "errors": []}
        report = reporter.generate_generation_report(results)

        assert "CONTRACT GENERATION REPORT" in report
        assert "Total Generated:  0" in report

    # ---- Drift Report Tests ----

    def test_drift_report_healthy(self, reporter):
        """Should produce a report with health status when no issues found."""
        drift_results = {
            "uncovered": [],
            "orphaned": [],
            "drifted": [],
            "covered": [
                {"method": "GET", "url": "/api/users", "file": "get_users.yml"}
            ],
            "summary": {
                "total_spec_endpoints": 1,
                "total_contracts": 1,
                "uncovered_count": 0,
                "orphaned_count": 0,
                "drifted_count": 0,
                "covered_count": 1,
                "coverage_percent": 100.0,
                "health": "HEALTHY",
            },
        }
        report = reporter.generate_drift_report(drift_results)

        assert "DRIFT DETECTION REPORT" in report
        assert "HEALTHY" in report

    def test_drift_report_with_uncovered(self, reporter):
        """Should report uncovered endpoints."""
        drift_results = {
            "uncovered": [
                {"method": "POST", "path": "/api/users", "summary": "Create user",
                 "reason": "No contract exists"}
            ],
            "orphaned": [],
            "drifted": [],
            "covered": [],
            "summary": {
                "total_spec_endpoints": 1,
                "total_contracts": 0,
                "uncovered_count": 1,
                "orphaned_count": 0,
                "drifted_count": 0,
                "covered_count": 0,
                "coverage_percent": 0.0,
                "health": "WARNING",
            },
        }
        report = reporter.generate_drift_report(drift_results)

        assert "UNCOVERED" in report or "uncovered" in report.lower()

    def test_drift_report_with_orphaned(self, reporter):
        """Should report orphaned contracts."""
        drift_results = {
            "uncovered": [],
            "orphaned": [
                {"method": "GET", "url": "/api/old", "file": "old.yml",
                 "file_path": "/path/old.yml", "reason": "Endpoint removed"}
            ],
            "drifted": [],
            "covered": [],
            "summary": {
                "total_spec_endpoints": 0,
                "total_contracts": 1,
                "uncovered_count": 0,
                "orphaned_count": 1,
                "drifted_count": 0,
                "covered_count": 0,
                "coverage_percent": 0.0,
                "health": "WARNING",
            },
        }
        report = reporter.generate_drift_report(drift_results)

        assert "ORPHANED" in report or "orphaned" in report.lower()

    def test_drift_report_returns_string(self, reporter):
        """Report should always be a string."""
        drift_results = {
            "uncovered": [], "orphaned": [], "drifted": [], "covered": [],
            "summary": {
                "total_spec_endpoints": 0, "total_contracts": 0,
                "uncovered_count": 0, "orphaned_count": 0,
                "drifted_count": 0, "covered_count": 0,
                "coverage_percent": 0.0, "health": "HEALTHY",
            },
        }
        report = reporter.generate_drift_report(drift_results)
        assert isinstance(report, str)
        assert len(report) > 0
