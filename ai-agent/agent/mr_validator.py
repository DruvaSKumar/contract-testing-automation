# ============================================================
# mr_validator.py — Pre-Merge MR Validation & Comment Poster
# ============================================================
# PURPOSE:
#   Runs a comprehensive validation suite on merge request pipelines
#   and posts a formatted summary comment on the MR with results.
#
# WHAT IT VALIDATES:
#   1. Contract drift detection (are contracts in sync with spec?)
#   2. Contract test results (did provider/consumer tests pass?)
#   3. Backward compatibility (any breaking API changes?)
#   4. Coverage summary (how many endpoints have contracts?)
#
# HOW IT WORKS:
#   - Collects results from drift detection, test reports, and
#     compatibility checks (reads artifact files from other CI jobs)
#   - Builds a Markdown summary table
#   - Posts it as a GitLab MR note (comment) via the API
#   - Updates an existing comment if re-running (avoids spam)
#
# PREREQUISITES:
#   - GITLAB_TOKEN environment variable
#   - CI_PROJECT_ID, CI_MERGE_REQUEST_IID (built-in GitLab CI vars)
#   - CI_PIPELINE_URL (optional, for linking back to pipeline)
# ============================================================

import os
import json
import glob
import xml.etree.ElementTree as ET
from datetime import datetime

import requests


class MRValidator:
    """
    Validates contract testing results and posts a summary comment
    on the GitLab Merge Request.
    """

    # Signature used to identify our comment (for updating instead of duplicating)
    COMMENT_SIGNATURE = "<!-- contract-testing-ai-agent-validation -->"

    def __init__(self, gitlab_url=None, project_id=None, token=None, mr_iid=None):
        """
        Args:
            gitlab_url:  GitLab instance URL
            project_id:  Numeric GitLab project ID
            token:       GitLab Personal Access Token
            mr_iid:      Merge Request internal ID
        """
        self.gitlab_url = (gitlab_url or os.environ.get("GITLAB_URL", "https://gitlab.com")).rstrip("/")
        self.project_id = project_id or os.environ.get("CI_PROJECT_ID")
        self.token = token or os.environ.get("GITLAB_TOKEN")
        self.mr_iid = mr_iid or os.environ.get("CI_MERGE_REQUEST_IID")

        if not self.project_id:
            raise ValueError("CI_PROJECT_ID not set. Run this in a GitLab CI MR pipeline.")
        if not self.token:
            raise ValueError("GITLAB_TOKEN not set. Required for posting MR comments.")
        if not self.mr_iid:
            raise ValueError("CI_MERGE_REQUEST_IID not set. This job only runs on MR pipelines.")

        self.api_base = f"{self.gitlab_url}/api/v4/projects/{self.project_id}"
        self.headers = {"PRIVATE-TOKEN": self.token}

    # ================================================================
    # Public API
    # ================================================================

    def validate_and_comment(self, results_dir=None, provider_report_dir=None,
                             consumer_report_dir=None, compat_report_file=None):
        """
        Collects all validation results and posts/updates the MR comment.

        Args:
            results_dir:         Path to ai-agent/reports/ (drift report)
            provider_report_dir: Path to provider surefire-reports/
            consumer_report_dir: Path to consumer surefire-reports/
            compat_report_file:  Path to compatibility_report.txt

        Returns:
            dict with validation summary and comment URL
        """
        # Collect results from all sources
        validation = {
            "drift": self._collect_drift_results(results_dir),
            "provider_tests": self._collect_test_results(provider_report_dir, "Provider"),
            "consumer_tests": self._collect_test_results(consumer_report_dir, "Consumer"),
            "compatibility": self._collect_compat_results(compat_report_file),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "pipeline_url": os.environ.get("CI_PIPELINE_URL", ""),
        }

        # Determine overall status
        validation["overall_status"] = self._determine_overall_status(validation)

        # Build the Markdown comment
        comment_body = self._build_comment(validation)

        # Post or update the MR comment
        comment_url = self._post_or_update_comment(comment_body)

        validation["comment_url"] = comment_url
        return validation

    # ================================================================
    # Result Collectors
    # ================================================================

    def _collect_drift_results(self, results_dir):
        """Reads drift detection results from saved report."""
        result = {"status": "skipped", "details": "No drift report found"}

        if not results_dir:
            return result

        # Try to read the drift report JSON
        drift_file = os.path.join(results_dir, "drift_report.json")
        if os.path.exists(drift_file):
            with open(drift_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            drifted = len(data.get("drifted", []))
            uncovered = len(data.get("uncovered", []))
            if drifted == 0 and uncovered == 0:
                result = {"status": "passed", "details": "All contracts in sync"}
            else:
                result = {
                    "status": "warning",
                    "details": f"{drifted} drifted, {uncovered} uncovered",
                    "drifted": drifted,
                    "uncovered": uncovered,
                }
            return result

        # Fallback: try the text report
        txt_file = os.path.join(results_dir, "drift_report.txt")
        if os.path.exists(txt_file):
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "no drift" in content.lower() or "all contracts aligned" in content.lower():
                result = {"status": "passed", "details": "All contracts in sync"}
            elif "CRITICAL" in content:
                result = {"status": "failed", "details": "Critical drift detected"}
            elif "WARNING" in content:
                result = {"status": "warning", "details": "Drift warnings found"}
            else:
                result = {"status": "passed", "details": "No issues found"}

        return result

    def _collect_test_results(self, report_dir, name):
        """Parses JUnit XML (surefire-reports) for test results."""
        result = {"status": "skipped", "details": f"No {name} test reports found",
                  "tests": 0, "failures": 0, "errors": 0, "skipped_count": 0}

        if not report_dir or not os.path.isdir(report_dir):
            return result

        xml_files = glob.glob(os.path.join(report_dir, "TEST-*.xml"))
        if not xml_files:
            return result

        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        failed_tests = []

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                tests = int(root.get("tests", 0))
                failures = int(root.get("failures", 0))
                errors = int(root.get("errors", 0))
                skipped = int(root.get("skipped", 0))

                total_tests += tests
                total_failures += failures
                total_errors += errors
                total_skipped += skipped

                # Collect failed test names
                for testcase in root.findall("testcase"):
                    failure = testcase.find("failure")
                    error = testcase.find("error")
                    if failure is not None or error is not None:
                        test_name = testcase.get("name", "unknown")
                        class_name = testcase.get("classname", "")
                        short_class = class_name.split(".")[-1] if class_name else ""
                        msg = ""
                        if failure is not None:
                            msg = failure.get("message", "")[:100]
                        elif error is not None:
                            msg = error.get("message", "")[:100]
                        failed_tests.append({
                            "name": f"{short_class}.{test_name}" if short_class else test_name,
                            "message": msg,
                        })
            except (ET.ParseError, OSError):
                continue

        if total_tests == 0:
            return result

        if total_failures == 0 and total_errors == 0:
            status = "passed"
            details = f"{total_tests} tests passed"
        else:
            status = "failed"
            details = f"{total_failures + total_errors} of {total_tests} tests failed"

        return {
            "status": status,
            "details": details,
            "tests": total_tests,
            "failures": total_failures,
            "errors": total_errors,
            "skipped_count": total_skipped,
            "failed_tests": failed_tests,
        }

    def _collect_compat_results(self, compat_report_file):
        """Reads backward compatibility check results."""
        result = {"status": "skipped", "details": "No compatibility check performed"}

        if not compat_report_file or not os.path.exists(compat_report_file):
            return result

        with open(compat_report_file, "r", encoding="utf-8") as f:
            content = f.read()

        if "BREAKING CHANGES DETECTED" in content:
            result = {"status": "failed", "details": "Breaking API changes detected"}
        elif "COMPATIBLE (with warnings)" in content:
            result = {"status": "warning", "details": "Compatible with warnings"}
        elif "FULLY COMPATIBLE" in content:
            result = {"status": "passed", "details": "Fully backward compatible"}
        else:
            result = {"status": "passed", "details": "No breaking changes"}

        result["report"] = content
        return result

    # ================================================================
    # Status Determination
    # ================================================================

    def _determine_overall_status(self, validation):
        """Determines the overall MR validation status."""
        statuses = [
            validation["drift"]["status"],
            validation["provider_tests"]["status"],
            validation["consumer_tests"]["status"],
            validation["compatibility"]["status"],
        ]

        if "failed" in statuses:
            return "failed"
        if "warning" in statuses:
            return "warning"
        if all(s == "skipped" for s in statuses):
            return "skipped"
        return "passed"

    # ================================================================
    # Comment Builder
    # ================================================================

    def _build_comment(self, validation):
        """Builds the Markdown comment body for the MR."""
        status = validation["overall_status"]
        icon = {"passed": "✅", "failed": "❌", "warning": "⚠️", "skipped": "⏭️"}.get(status, "❓")

        lines = [
            self.COMMENT_SIGNATURE,
            f"## {icon} Contract Testing Validation Report",
            "",
            f"**Status:** {status.upper()} | **Time:** {validation['timestamp']}",
            "",
        ]

        if validation["pipeline_url"]:
            lines.append(f"🔗 [View Pipeline]({validation['pipeline_url']})")
            lines.append("")

        # Summary Table
        lines.append("### Results Summary")
        lines.append("")
        lines.append("| Check | Status | Details |")
        lines.append("|-------|--------|---------|")

        checks = [
            ("Contract Drift", validation["drift"]),
            ("Provider Tests", validation["provider_tests"]),
            ("Consumer Tests", validation["consumer_tests"]),
            ("Backward Compat", validation["compatibility"]),
        ]

        for name, check in checks:
            check_icon = {
                "passed": "✅", "failed": "❌", "warning": "⚠️", "skipped": "⏭️"
            }.get(check["status"], "❓")
            lines.append(f"| {name} | {check_icon} {check['status'].upper()} | {check['details']} |")

        lines.append("")

        # Failed Tests Detail
        for label, key in [("Provider", "provider_tests"), ("Consumer", "consumer_tests")]:
            test_data = validation[key]
            failed_tests = test_data.get("failed_tests", [])
            if failed_tests:
                lines.append(f"### ❌ Failed {label} Tests")
                lines.append("")
                lines.append("| Test | Error |")
                lines.append("|------|-------|")
                for ft in failed_tests[:10]:  # Limit to 10
                    msg = ft["message"].replace("|", "\\|").replace("\n", " ")
                    lines.append(f"| `{ft['name']}` | {msg} |")
                if len(failed_tests) > 10:
                    lines.append(f"| ... | +{len(failed_tests) - 10} more |")
                lines.append("")

        # Recommendations
        if status == "failed":
            lines.append("### 💡 Recommendations")
            lines.append("")
            if validation["provider_tests"]["status"] == "failed":
                lines.append("- **Provider tests failed**: Contracts don't match the Provider implementation. "
                             "Run `python main.py fix` to auto-fix drifted contracts.")
            if validation["consumer_tests"]["status"] == "failed":
                lines.append("- **Consumer tests failed**: Consumer expectations don't match Provider stubs. "
                             "Update Consumer code to match the new API contract.")
            if validation["compatibility"]["status"] == "failed":
                lines.append("- **Breaking changes**: This MR introduces breaking API changes. "
                             "Consider versioning the endpoint or providing a migration path.")
            if validation["drift"]["status"] == "failed":
                lines.append("- **Critical drift**: Contracts are significantly out of sync. "
                             "Run `python main.py generate --overwrite` to regenerate.")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by Contract Testing AI Agent* 🤖")
        lines.append("")

        return "\n".join(lines)

    # ================================================================
    # GitLab API — MR Notes (Comments)
    # ================================================================

    def _post_or_update_comment(self, body):
        """
        Posts a new comment or updates the existing one (identified by signature).
        This prevents duplicate comments on re-runs.
        """
        existing_note_id = self._find_existing_comment()

        if existing_note_id:
            return self._update_comment(existing_note_id, body)
        else:
            return self._create_comment(body)

    def _find_existing_comment(self):
        """Finds our previously posted comment by looking for the signature."""
        url = f"{self.api_base}/merge_requests/{self.mr_iid}/notes"
        params = {"per_page": 100, "sort": "desc"}

        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code != 200:
                return None

            for note in resp.json():
                if self.COMMENT_SIGNATURE in note.get("body", ""):
                    return note["id"]
        except (requests.RequestException, ValueError):
            pass

        return None

    def _create_comment(self, body):
        """Creates a new MR comment."""
        url = f"{self.api_base}/merge_requests/{self.mr_iid}/notes"
        payload = {"body": body}

        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            note_url = resp.json().get("web_url", "")
            print(f"  [MR VALIDATOR] Comment posted on MR !{self.mr_iid}")
            return note_url
        else:
            print(f"  [MR VALIDATOR] Failed to post comment: {resp.status_code} — {resp.text}")
            return None

    def _update_comment(self, note_id, body):
        """Updates an existing MR comment."""
        url = f"{self.api_base}/merge_requests/{self.mr_iid}/notes/{note_id}"
        payload = {"body": body}

        resp = requests.put(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code == 200:
            note_url = resp.json().get("web_url", "")
            print(f"  [MR VALIDATOR] Comment updated on MR !{self.mr_iid}")
            return note_url
        else:
            print(f"  [MR VALIDATOR] Failed to update comment: {resp.status_code} — {resp.text}")
            return None
