# ============================================================
# mr_creator.py — Automated GitLab Merge Request Creator
# ============================================================
# PURPOSE:
#   Automates the full contract-fix workflow:
#   1. Detects drift between the OpenAPI spec and existing contracts
#   2. Regenerates contracts that are drifted or missing
#   3. Creates a GitLab branch with the updated contract files
#   4. Opens a Merge Request with a detailed description
#
# WHY IS THIS NEEDED?
#   When the Provider API changes, contracts go stale. Manually
#   updating contracts is tedious. This module closes the loop:
#     API change detected → contracts auto-fixed → MR created
#   A human reviews and merges — keeping the process safe but fast.
#
# HOW IT WORKS:
#   Uses the GitLab REST API (v4) to:
#     - Create a branch from the default branch
#     - Commit updated contract files
#     - Open a merge request with a summary of changes
#
# PREREQUISITES:
#   - GITLAB_TOKEN environment variable (Personal Access Token with api scope)
#   - CI_PROJECT_ID environment variable (built-in GitLab CI variable)
#   - Optionally GITLAB_URL (defaults to https://gitlab.com)
# ============================================================

import os
import json
import base64
from datetime import datetime

import requests
import yaml


class MRCreator:
    """
    Creates GitLab Merge Requests with auto-fixed contract files
    when drift is detected between the API spec and existing contracts.
    """

    def __init__(self, gitlab_url=None, project_id=None, token=None):
        """
        Args:
            gitlab_url:  GitLab instance URL (default: GITLAB_URL env or https://gitlab.com)
            project_id:  Numeric GitLab project ID (default: CI_PROJECT_ID env)
            token:       GitLab Personal Access Token (default: GITLAB_TOKEN env)
        """
        self.gitlab_url = (gitlab_url or os.environ.get("GITLAB_URL", "https://gitlab.com")).rstrip("/")
        self.project_id = project_id or os.environ.get("CI_PROJECT_ID")
        self.token = token or os.environ.get("GITLAB_TOKEN")

        if not self.project_id:
            raise ValueError(
                "GitLab project ID not configured.\n"
                "  Set CI_PROJECT_ID environment variable (auto-set in GitLab CI).\n"
                "  For local use, set it manually or pass project_id parameter."
            )
        if not self.token:
            raise ValueError(
                "GitLab token not configured.\n"
                "  Set GITLAB_TOKEN environment variable or pass token parameter.\n"
                "  Create one at: GitLab → User Settings → Access Tokens (api scope)"
            )

        self.api_base = f"{self.gitlab_url}/api/v4/projects/{self.project_id}"
        self.headers = {"PRIVATE-TOKEN": self.token}

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def create_fix_mr(self, drift_results, regenerated_files, target_branch="main"):
        """
        Creates a GitLab MR with auto-fixed contract files.

        Args:
            drift_results:     The drift report dict from DriftDetector.detect_drift()
            regenerated_files: Dict mapping relative file paths to their new content
                               e.g. {"provider-api/src/.../should_return_all_users.yml": "<yaml>"}
            target_branch:     Branch to merge into (default: main)

        Returns:
            dict: Result with keys:
                - success (bool)
                - branch_name (str)
                - mr_url (str) — URL of the created MR
                - mr_iid (int) — MR internal ID
                - message (str) — Human-readable summary
        """
        if not regenerated_files:
            return {
                "success": False,
                "message": "No files to commit — nothing to fix.",
            }

        # Step 1: Generate a descriptive branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/contract-drift-{timestamp}"

        # Step 2: Create the branch
        print(f"\n  [MR CREATOR] Creating branch: {branch_name}")
        self._create_branch(branch_name, target_branch)

        # Step 3: Commit all updated contract files
        print(f"  [MR CREATOR] Committing {len(regenerated_files)} file(s)...")
        commit_message = self._build_commit_message(drift_results)
        self._commit_files(branch_name, regenerated_files, commit_message)

        # Step 4: Create the Merge Request
        print(f"  [MR CREATOR] Creating Merge Request...")
        title = self._build_mr_title(drift_results)
        description = self._build_mr_description(drift_results, regenerated_files)
        mr_data = self._create_merge_request(branch_name, target_branch, title, description)

        mr_url = mr_data.get("web_url", "")
        mr_iid = mr_data.get("iid", 0)

        print(f"  [MR CREATOR] MR created successfully!")
        print(f"  [MR CREATOR] URL: {mr_url}")

        return {
            "success": True,
            "branch_name": branch_name,
            "mr_url": mr_url,
            "mr_iid": mr_iid,
            "message": f"Merge Request !{mr_iid} created with {len(regenerated_files)} updated contract(s).",
        }

    # ----------------------------------------------------------------
    # GitLab API calls
    # ----------------------------------------------------------------

    def _create_branch(self, branch_name, ref):
        """Creates a new branch from the given ref."""
        url = f"{self.api_base}/repository/branches"
        payload = {"branch": branch_name, "ref": ref}
        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)

        if resp.status_code == 400 and "already exists" in resp.text:
            print(f"  [MR CREATOR] Branch '{branch_name}' already exists, reusing it.")
            return

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to create branch '{branch_name}': {resp.status_code} — {resp.text}"
            )

    def _commit_files(self, branch_name, files, commit_message):
        """
        Commits multiple files to a branch in a single commit
        using the GitLab Commits API.

        Args:
            branch_name:    Target branch
            files:          Dict of {relative_path: content_string}
            commit_message: Commit message
        """
        url = f"{self.api_base}/repository/commits"

        actions = []
        for file_path, content in files.items():
            # Determine if file exists (update) or is new (create)
            action = "update" if self._file_exists(branch_name, file_path) else "create"
            actions.append({
                "action": action,
                "file_path": file_path,
                "content": content,
            })

        payload = {
            "branch": branch_name,
            "commit_message": commit_message,
            "actions": actions,
        }

        resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to commit files: {resp.status_code} — {resp.text}"
            )

    def _file_exists(self, branch, file_path):
        """Checks if a file exists in the given branch."""
        url = f"{self.api_base}/repository/files/{requests.utils.quote(file_path, safe='')}"
        resp = requests.head(url, headers=self.headers, params={"ref": branch}, timeout=10)
        return resp.status_code == 200

    def _create_merge_request(self, source_branch, target_branch, title, description):
        """Creates a merge request and returns the response data."""
        url = f"{self.api_base}/merge_requests"
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "remove_source_branch": True,
            "squash": True,
        }

        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to create MR: {resp.status_code} — {resp.text}"
            )
        return resp.json()

    # ----------------------------------------------------------------
    # Message builders
    # ----------------------------------------------------------------

    def _build_commit_message(self, drift_results):
        """Builds a commit message summarizing the contract fixes."""
        summary = drift_results.get("summary", {})
        drifted = summary.get("drifted_count", 0)
        uncovered = summary.get("uncovered_count", 0)

        parts = []
        if drifted:
            parts.append(f"{drifted} drifted")
        if uncovered:
            parts.append(f"{uncovered} missing")

        detail = " and ".join(parts) if parts else "contracts"
        return f"fix(BTIQ-0000): auto-fix {detail} contract(s)\n\nGenerated by AI Agent drift detection."

    def _build_mr_title(self, drift_results):
        """Builds a concise MR title."""
        summary = drift_results.get("summary", {})
        drifted = summary.get("drifted_count", 0)
        uncovered = summary.get("uncovered_count", 0)
        total_fixes = drifted + uncovered

        return f"fix(BTIQ-0000): Auto-fix {total_fixes} contract(s) — AI Agent drift resolution"

    def _build_mr_description(self, drift_results, regenerated_files):
        """Builds a detailed MR description in Markdown."""
        summary = drift_results.get("summary", {})
        drifted_list = drift_results.get("drifted", [])
        uncovered_list = drift_results.get("uncovered", [])

        lines = [
            "## 🤖 AI Agent — Contract Drift Auto-Fix",
            "",
            "This MR was **automatically created** by the Contract Testing AI Agent",
            "after detecting drift between the OpenAPI spec and existing contracts.",
            "",
            "### Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Spec Endpoints | {summary.get('total_spec_endpoints', '?')} |",
            f"| Contracts Updated | {len(regenerated_files)} |",
            f"| Drifted (schema mismatch) | {summary.get('drifted_count', 0)} |",
            f"| Uncovered (new endpoints) | {summary.get('uncovered_count', 0)} |",
            f"| Previous Coverage | {summary.get('coverage_percent', '?')}% |",
            "",
        ]

        if drifted_list:
            lines.append("### Drifted Contracts Fixed")
            lines.append("")
            for item in drifted_list:
                lines.append(f"- **{item['method']} {item['url']}** (`{item['file']}`)")
                for issue in item.get("issues", []):
                    lines.append(f"  - {issue}")
            lines.append("")

        if uncovered_list:
            lines.append("### New Contracts Generated")
            lines.append("")
            for item in uncovered_list:
                lines.append(f"- **{item['method'].upper()} {item['path']}** — {item.get('summary', 'No description')}")
            lines.append("")

        lines.extend([
            "### Files Changed",
            "",
        ])
        for file_path in sorted(regenerated_files.keys()):
            lines.append(f"- `{file_path}`")

        lines.extend([
            "",
            "### How to Review",
            "",
            "1. Check the updated contract YAML files for correctness",
            "2. Ensure sample values and matchers are appropriate",
            "3. Run the contract tests locally: `cd provider-api && mvn clean test`",
            "4. Merge when satisfied — the CI pipeline will verify everything",
            "",
            "---",
            "*Generated by Contract Testing AI Agent*",
        ])

        return "\n".join(lines)
