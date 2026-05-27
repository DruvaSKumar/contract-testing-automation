# ============================================================
# test_root_cause_analyzer.py — Unit Tests for Root Cause Analyzer
# ============================================================

import os
import pytest

from agent.root_cause_analyzer import RootCauseAnalyzer, RootCauseCategory


class TestRootCauseAnalyzer:
    """Tests for the RootCauseAnalyzer module."""

    @pytest.fixture
    def analyzer(self):
        return RootCauseAnalyzer()

    @pytest.fixture
    def surefire_dir(self, tmp_path):
        """Creates a temp dir with sample surefire XML reports."""
        reports_dir = tmp_path / "surefire-reports"
        reports_dir.mkdir()

        # A passing test
        passing_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.contracttest.provider.UserTest" tests="5" failures="0" errors="0" time="1.234">
  <testcase name="validate_shouldReturnAllUsers" classname="com.contracttest.provider.UserTest" time="0.5"/>
  <testcase name="validate_shouldCreateUser" classname="com.contracttest.provider.UserTest" time="0.3"/>
</testsuite>"""
        (reports_dir / "TEST-com.contracttest.provider.UserTest.xml").write_text(passing_xml)

        return str(reports_dir)

    @pytest.fixture
    def surefire_dir_with_failures(self, tmp_path):
        """Creates a temp dir with failed surefire XML reports."""
        reports_dir = tmp_path / "surefire-reports"
        reports_dir.mkdir()

        failing_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.contracttest.provider.UserTest" tests="3" failures="2" errors="0" time="2.1">
  <testcase name="validate_shouldReturnAllUsers" classname="com.contracttest.provider.UserTest" time="0.5"/>
  <testcase name="validate_shouldCreateUser" classname="com.contracttest.provider.UserTest" time="0.3">
    <failure message="Status expected:&lt;201&gt; but was:&lt;400&gt;" type="java.lang.AssertionError">
java.lang.AssertionError: Status expected:&lt;201&gt; but was:&lt;400&gt;
\tat org.springframework.cloud.contract.verifier.tests.UserTest.validate_shouldCreateUser(UserTest.java:45)
    </failure>
  </testcase>
  <testcase name="validate_shouldReturnUserById" classname="com.contracttest.provider.UserTest" time="0.2">
    <failure message="expected: &lt;Sample User&gt; but was: &lt;null&gt;" type="java.lang.AssertionError">
java.lang.AssertionError: expected: &lt;Sample User&gt; but was: &lt;null&gt;
\tat org.springframework.cloud.contract.verifier.tests.UserTest.validate_shouldReturnUserById(UserTest.java:62)
    </failure>
  </testcase>
</testsuite>"""
        (reports_dir / "TEST-com.contracttest.provider.UserTest.xml").write_text(failing_xml)

        return str(reports_dir)

    # ---- analyze_failures Tests ----

    def test_analyze_no_failures(self, analyzer, surefire_dir):
        """Should report no failures for passing tests."""
        result = analyzer.analyze_failures(provider_report_dir=surefire_dir)
        assert result["has_failures"] is False
        assert result["total_failures"] == 0

    def test_analyze_with_failures(self, analyzer, surefire_dir_with_failures):
        """Should detect failures from surefire reports."""
        result = analyzer.analyze_failures(provider_report_dir=surefire_dir_with_failures)
        assert result["has_failures"] is True
        assert result["total_failures"] >= 1

    def test_analyze_nonexistent_dir(self, analyzer, tmp_path):
        """Should handle non-existent directory gracefully."""
        result = analyzer.analyze_failures(
            provider_report_dir=str(tmp_path / "nonexistent")
        )
        assert result["has_failures"] is False

    def test_analyze_returns_categories(self, analyzer, surefire_dir_with_failures):
        """Should categorize failures."""
        result = analyzer.analyze_failures(provider_report_dir=surefire_dir_with_failures)
        assert "categories" in result

    def test_analyze_returns_summary(self, analyzer, surefire_dir_with_failures):
        """Should include a human-readable summary."""
        result = analyzer.analyze_failures(provider_report_dir=surefire_dir_with_failures)
        assert "summary" in result

    def test_analyze_failures_structure(self, analyzer, surefire_dir_with_failures):
        """Should return expected keys."""
        result = analyzer.analyze_failures(provider_report_dir=surefire_dir_with_failures)
        expected_keys = {"failures", "summary", "categories", "has_failures", "total_failures"}
        assert expected_keys.issubset(set(result.keys()))

    # ---- Internal _classify_failure Tests ----

    def test_classify_status_code_mismatch(self, analyzer):
        """Should classify status code mismatches correctly."""
        failure_msg = "Status expected:<201> but was:<400>"
        category = analyzer._classify_failure(failure_msg)
        assert category == RootCauseCategory.STATUS_CODE_MISMATCH

    def test_classify_schema_mismatch(self, analyzer):
        """Should classify schema/null mismatches correctly."""
        failure_msg = "expected: <Sample User> but was: <null>"
        category = analyzer._classify_failure(failure_msg)
        assert category in (
            RootCauseCategory.SCHEMA_MISMATCH,
            RootCauseCategory.NEW_REQUIRED_FIELD,
        )

    def test_classify_unknown(self, analyzer):
        """Should return UNKNOWN for unrecognizable failures."""
        failure_msg = "Some completely unexpected error occurred"
        category = analyzer._classify_failure(failure_msg)
        assert category == RootCauseCategory.UNKNOWN

    # ---- RootCauseCategory Tests ----

    def test_categories_are_strings(self):
        """All category values should be uppercase strings."""
        categories = [
            RootCauseCategory.SCHEMA_MISMATCH,
            RootCauseCategory.STATUS_CODE_MISMATCH,
            RootCauseCategory.MISSING_ENDPOINT,
            RootCauseCategory.UNKNOWN,
        ]
        for cat in categories:
            assert isinstance(cat, str)
            assert cat == cat.upper()
