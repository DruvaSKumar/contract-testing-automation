# ============================================================
# root_cause_analyzer.py — AI Root Cause Analysis for Failures
# ============================================================
# PURPOSE:
#   When contract tests fail, this module analyzes the failure
#   details and produces a human-readable root cause explanation.
#
# WHAT IT DOES:
#   1. Parses surefire test reports (XML) to extract failures
#   2. Analyzes the failure patterns (schema mismatch, missing
#      fields, status code mismatch, etc.)
#   3. Correlates failures with drift detection results
#   4. Generates a clear explanation of:
#      - WHAT failed (which contracts/tests)
#      - WHY it failed (root cause category)
#      - HOW to fix it (actionable recommendations)
#   5. Optionally includes the analysis in Teams notifications
#
# ROOT CAUSE CATEGORIES:
#   - SCHEMA_MISMATCH: Response body doesn't match contract
#   - STATUS_CODE_MISMATCH: Wrong HTTP status returned
#   - MISSING_ENDPOINT: Endpoint removed from Provider
#   - NEW_REQUIRED_FIELD: Consumer missing a required field
#   - HEADER_MISMATCH: Response headers don't match
#   - SERIALIZATION_ERROR: JSON parsing/format issues
#   - TIMEOUT: Provider didn't respond in time
#   - UNKNOWN: Unclassified failure
# ============================================================

import os
import re
import glob
import xml.etree.ElementTree as ET
from datetime import datetime


class RootCauseCategory:
    """Enumeration of root cause categories."""
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    STATUS_CODE_MISMATCH = "STATUS_CODE_MISMATCH"
    MISSING_ENDPOINT = "MISSING_ENDPOINT"
    NEW_REQUIRED_FIELD = "NEW_REQUIRED_FIELD"
    HEADER_MISMATCH = "HEADER_MISMATCH"
    SERIALIZATION_ERROR = "SERIALIZATION_ERROR"
    TIMEOUT = "TIMEOUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"


class FailureAnalysis:
    """Represents the analysis of a single test failure."""

    def __init__(self, test_name, category, description, suggestion, details=None):
        self.test_name = test_name
        self.category = category
        self.description = description
        self.suggestion = suggestion
        self.details = details or {}

    def __repr__(self):
        return f"[{self.category}] {self.test_name}: {self.description}"


class RootCauseAnalyzer:
    """
    Analyzes contract test failures and provides human-readable
    root cause explanations with fix suggestions.
    """

    # Patterns for classifying failures
    PATTERNS = {
        RootCauseCategory.STATUS_CODE_MISMATCH: [
            r"expected.*status.*?(\d{3}).*?but was.*?(\d{3})",
            r"expected:.*?<(\d{3})>.*?but was:.*?<(\d{3})>",
            r"Status expected:<(\d{3})> but was:<(\d{3})>",
        ],
        RootCauseCategory.SCHEMA_MISMATCH: [
            r"expected.*but was.*null",
            r"json path.*didn.t match",
            r"expected:.*?<.*?>.*?but was:.*?<.*?>",
            r"Body.*doesn.t match",
            r"DocumentContext.*no results",
        ],
        RootCauseCategory.MISSING_ENDPOINT: [
            r"404.*Not Found",
            r"No mapping.*for.*request",
            r"Request method.*not supported",
        ],
        RootCauseCategory.HEADER_MISMATCH: [
            r"header.*expected.*but was",
            r"Content-Type.*expected.*but was",
        ],
        RootCauseCategory.SERIALIZATION_ERROR: [
            r"JSON parse error",
            r"Cannot deserialize",
            r"Unexpected character",
            r"json string can not be null",
        ],
        RootCauseCategory.TIMEOUT: [
            r"timed? ?out",
            r"SocketTimeoutException",
            r"ConnectException",
        ],
        RootCauseCategory.VALIDATION_ERROR: [
            r"ConstraintViolation",
            r"MethodArgumentNotValid",
            r"validation.*fail",
        ],
        RootCauseCategory.NEW_REQUIRED_FIELD: [
            r"must not be blank",
            r"must not be null",
            r"required.*field.*missing",
        ],
    }

    def __init__(self):
        self.analyses = []

    def analyze_failures(self, provider_report_dir=None, consumer_report_dir=None,
                         drift_results=None):
        """
        Analyzes all test failures from surefire reports.

        Args:
            provider_report_dir: Path to provider's surefire-reports/
            consumer_report_dir: Path to consumer's surefire-reports/
            drift_results: Optional drift detection results for correlation

        Returns:
            dict with:
                - failures: list of FailureAnalysis objects
                - summary: human-readable summary string
                - categories: dict of category → count
                - has_failures: bool
        """
        self.analyses = []

        # Parse provider test failures
        if provider_report_dir and os.path.isdir(provider_report_dir):
            self._parse_surefire_reports(provider_report_dir, "Provider")

        # Parse consumer test failures
        if consumer_report_dir and os.path.isdir(consumer_report_dir):
            self._parse_surefire_reports(consumer_report_dir, "Consumer")

        # Correlate with drift if available
        if drift_results and self.analyses:
            self._correlate_with_drift(drift_results)

        # Build category summary
        categories = {}
        for analysis in self.analyses:
            cat = analysis.category
            categories[cat] = categories.get(cat, 0) + 1

        # Build summary
        summary = self._build_summary()

        return {
            "failures": self.analyses,
            "summary": summary,
            "categories": categories,
            "has_failures": len(self.analyses) > 0,
            "total_failures": len(self.analyses),
        }

    # ================================================================
    # Surefire Report Parsing
    # ================================================================

    def _parse_surefire_reports(self, report_dir, source):
        """Parses JUnit XML reports for failures and errors."""
        xml_files = glob.glob(os.path.join(report_dir, "TEST-*.xml"))

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                for testcase in root.findall("testcase"):
                    failure_elem = testcase.find("failure")
                    error_elem = testcase.find("error")

                    if failure_elem is not None:
                        self._analyze_single_failure(testcase, failure_elem, source)
                    elif error_elem is not None:
                        self._analyze_single_failure(testcase, error_elem, source)

            except (ET.ParseError, OSError):
                continue

    def _analyze_single_failure(self, testcase, failure_elem, source):
        """Analyzes a single test failure and classifies it."""
        test_name = testcase.get("name", "unknown")
        class_name = testcase.get("classname", "")
        short_class = class_name.split(".")[-1] if class_name else ""
        full_name = f"{source}: {short_class}.{test_name}" if short_class else f"{source}: {test_name}"

        message = failure_elem.get("message", "") or ""
        stacktrace = failure_elem.text or ""
        full_text = f"{message}\n{stacktrace}"

        # Classify the failure
        category = self._classify_failure(full_text)

        # Generate description and suggestion
        description = self._generate_description(category, message, test_name)
        suggestion = self._generate_suggestion(category, message, test_name)

        analysis = FailureAnalysis(
            test_name=full_name,
            category=category,
            description=description,
            suggestion=suggestion,
            details={
                "message": message[:300],
                "source": source,
                "class": short_class,
                "method": test_name,
            },
        )

        self.analyses.append(analysis)

    def _classify_failure(self, text):
        """Classifies a failure based on pattern matching."""
        text_lower = text.lower()

        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category

        return RootCauseCategory.UNKNOWN

    # ================================================================
    # Description & Suggestion Generators
    # ================================================================

    def _generate_description(self, category, message, test_name):
        """Generates a human-readable description of the failure."""
        descriptions = {
            RootCauseCategory.STATUS_CODE_MISMATCH: self._describe_status_mismatch(message),
            RootCauseCategory.SCHEMA_MISMATCH: (
                "The response body doesn't match the expected schema in the contract. "
                "A field may have been added, removed, or changed type."
            ),
            RootCauseCategory.MISSING_ENDPOINT: (
                "The endpoint specified in the contract no longer exists in the Provider API. "
                "It may have been renamed, moved, or removed."
            ),
            RootCauseCategory.NEW_REQUIRED_FIELD: (
                "A new required field was added to the request body, but the contract "
                "doesn't include it. The Provider is now rejecting the request."
            ),
            RootCauseCategory.HEADER_MISMATCH: (
                "The response headers don't match the contract expectations. "
                "Content-Type or other headers may have changed."
            ),
            RootCauseCategory.SERIALIZATION_ERROR: (
                "The response body cannot be parsed as JSON. The Provider may be "
                "returning an error page or malformed response."
            ),
            RootCauseCategory.TIMEOUT: (
                "The Provider did not respond within the timeout period. "
                "It may be overloaded, stuck in a loop, or not running."
            ),
            RootCauseCategory.VALIDATION_ERROR: (
                "The Provider rejected the request due to validation constraints. "
                "The contract may be sending invalid data."
            ),
            RootCauseCategory.UNKNOWN: (
                f"Test failed with: {message[:150]}"
            ),
        }
        return descriptions.get(category, f"Unknown failure: {message[:100]}")

    def _describe_status_mismatch(self, message):
        """Extracts expected/actual status codes from the error message."""
        match = re.search(r"(\d{3}).*?(\d{3})", message)
        if match:
            expected, actual = match.group(1), match.group(2)
            return (
                f"Expected HTTP {expected} but got {actual}. "
                f"The Provider's behavior has changed for this endpoint."
            )
        return "The HTTP status code returned doesn't match the contract."

    def _generate_suggestion(self, category, message, test_name):
        """Generates actionable fix suggestions."""
        suggestions = {
            RootCauseCategory.STATUS_CODE_MISMATCH: (
                "1. Check if the Provider endpoint logic changed (new validation, different error handling)\n"
                "2. Run `python main.py fix` to regenerate the contract\n"
                "3. If intentional, update the contract's expected status code"
            ),
            RootCauseCategory.SCHEMA_MISMATCH: (
                "1. Run `python main.py drift` to identify which fields changed\n"
                "2. Run `python main.py fix` to auto-regenerate affected contracts\n"
                "3. Update Consumer code if the field change is intentional"
            ),
            RootCauseCategory.MISSING_ENDPOINT: (
                "1. Check if the endpoint was renamed or versioned (e.g., /v1/ → /v2/)\n"
                "2. Run `python main.py generate --overwrite` to regenerate all contracts\n"
                "3. If removed intentionally, delete the old contract file"
            ),
            RootCauseCategory.NEW_REQUIRED_FIELD: (
                "1. Add the new required field to the contract's request body\n"
                "2. Run `python main.py generate --overwrite` to pick up new fields\n"
                "3. Update Consumer to send the new required field"
            ),
            RootCauseCategory.HEADER_MISMATCH: (
                "1. Check if Content-Type or Accept headers changed in the Provider\n"
                "2. Run `python main.py fix` to update contract headers\n"
                "3. Verify @Produces/@Consumes annotations in the Controller"
            ),
            RootCauseCategory.SERIALIZATION_ERROR: (
                "1. Check if the Provider is actually running and healthy\n"
                "2. Verify the endpoint returns JSON (not HTML error page)\n"
                "3. Check for malformed response body or encoding issues"
            ),
            RootCauseCategory.TIMEOUT: (
                "1. Verify the Provider API is running and accessible\n"
                "2. Check for database connection issues or slow queries\n"
                "3. Increase timeout if the endpoint legitimately takes longer"
            ),
            RootCauseCategory.VALIDATION_ERROR: (
                "1. Review the contract's request body against Provider's @Valid annotations\n"
                "2. Ensure all required fields have valid values in the contract\n"
                "3. Run `python main.py generate --overwrite` to regenerate with valid data"
            ),
            RootCauseCategory.UNKNOWN: (
                "1. Check the full test output in surefire-reports/ for more details\n"
                "2. Run `python main.py drift` to check for spec/contract misalignment\n"
                "3. Verify the Provider is running correctly"
            ),
        }
        return suggestions.get(category, "Review the test output for details.")

    # ================================================================
    # Drift Correlation
    # ================================================================

    def _correlate_with_drift(self, drift_results):
        """Enriches failure analyses with drift correlation data."""
        drifted = drift_results.get("drifted", [])
        drifted_endpoints = set()
        for d in drifted:
            key = f"{d.get('method', '').upper()} {d.get('url', '')}"
            drifted_endpoints.add(key)

        for analysis in self.analyses:
            # Try to match test name to a drifted endpoint
            test_name_lower = analysis.test_name.lower()
            for endpoint in drifted_endpoints:
                # Heuristic: check if the test name contains parts of the endpoint
                method = endpoint.split(" ")[0].lower()
                if method in test_name_lower:
                    analysis.details["correlated_drift"] = endpoint
                    analysis.description += (
                        f"\n⚡ This failure correlates with detected drift on: {endpoint}"
                    )
                    break

    # ================================================================
    # Summary Builder
    # ================================================================

    def _build_summary(self):
        """Builds a formatted summary of all failure analyses."""
        if not self.analyses:
            return "✅ No test failures detected — all contracts pass!"

        lines = []
        lines.append("=" * 65)
        lines.append("  🔍 ROOT CAUSE ANALYSIS — Contract Test Failures")
        lines.append("=" * 65)
        lines.append("")
        lines.append(f"  Total Failures: {len(self.analyses)}")
        lines.append("")

        # Group by category
        by_category = {}
        for a in self.analyses:
            by_category.setdefault(a.category, []).append(a)

        for category, items in by_category.items():
            icon = {
                RootCauseCategory.STATUS_CODE_MISMATCH: "🔢",
                RootCauseCategory.SCHEMA_MISMATCH: "📋",
                RootCauseCategory.MISSING_ENDPOINT: "🚫",
                RootCauseCategory.NEW_REQUIRED_FIELD: "📝",
                RootCauseCategory.HEADER_MISMATCH: "📨",
                RootCauseCategory.SERIALIZATION_ERROR: "⚠️",
                RootCauseCategory.TIMEOUT: "⏱️",
                RootCauseCategory.VALIDATION_ERROR: "❌",
                RootCauseCategory.UNKNOWN: "❓",
            }.get(category, "•")

            lines.append(f"  {icon} {category} ({len(items)} failure{'s' if len(items) > 1 else ''})")
            lines.append("  " + "-" * 50)

            for item in items:
                lines.append(f"    Test: {item.test_name}")
                lines.append(f"    Cause: {item.description}")
                lines.append(f"    Fix:")
                for fix_line in item.suggestion.split("\n"):
                    lines.append(f"      {fix_line}")
                lines.append("")

        lines.append("=" * 65)
        lines.append("  💡 Quick Fix: Run `python main.py fix` to auto-regenerate")
        lines.append("     drifted contracts, then re-run the pipeline.")
        lines.append("=" * 65)

        return "\n".join(lines)

    # ================================================================
    # Notification-Friendly Output
    # ================================================================

    def get_notification_text(self):
        """
        Returns a concise version suitable for Teams/Slack notifications.
        Limited to key info to fit notification size limits.
        """
        if not self.analyses:
            return "All contract tests passed ✅"

        lines = []
        lines.append(f"🔍 **Root Cause Analysis** ({len(self.analyses)} failure{'s' if len(self.analyses) > 1 else ''})")
        lines.append("")

        # Show top 5 failures max
        for analysis in self.analyses[:5]:
            lines.append(f"• **{analysis.category}**: {analysis.test_name}")
            lines.append(f"  _{analysis.description[:100]}_")
            lines.append("")

        if len(self.analyses) > 5:
            lines.append(f"  ...and {len(self.analyses) - 5} more failures")

        lines.append("")
        lines.append("Run `python main.py fix` to auto-fix, or check the full report in CI artifacts.")

        return "\n".join(lines)

    def save_report(self, output_path=None):
        """Saves the full analysis report to a file."""
        if output_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_path = os.path.join(base, "reports", "root_cause_analysis.txt")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        summary = self._build_summary()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"  [ROOT CAUSE] Report saved: {output_path}")
        return output_path
