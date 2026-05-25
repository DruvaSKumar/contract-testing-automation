# ============================================================
# notifier.py — Team Notification Module
# ============================================================
# PURPOSE:
#   Sends team notifications when contract tests fail or drift
#   is detected. Supports Microsoft Teams, Slack, GitLab, and SMTP.
#
# WHY IS THIS NEEDED?
#   When contract tests fail in CI, the team needs to know
#   immediately — not after checking the pipeline manually.
#   Notifications close the feedback loop so the right people
#   can fix breaking changes quickly.
#
# HOW IT WORKS:
#   1. Reads drift/test results (from DriftDetector or CI artifacts)
#   2. Formats a notification message with key details
#   3. Sends via Teams/Slack/GitLab/SMTP depending on config
#
# CONFIGURATION (environment variables):
#   Microsoft Teams (PRIMARY — most reliable):
#     TEAMS_WEBHOOK_URL  — Teams Incoming Webhook URL (from Workflows)
#   Slack:
#     SLACK_WEBHOOK_URL  — Incoming webhook URL from Slack app
#   GitLab Issue Notes:
#     GITLAB_TOKEN       — GitLab Personal Access Token (api scope)
#     CI_PROJECT_ID      — GitLab project ID (auto-set in CI)
#     GITLAB_MENTION_USERS — Comma-separated GitLab usernames to @mention
#   SMTP (corporate relay — only works from internal network):
#     SMTP_HOST          — Comma-separated SMTP hostnames
#     SMTP_PORT          — Comma-separated ports (default: 25,587)
#     SMTP_FROM          — Sender address (default: noreply@btbpo.net)
#     NOTIFY_EMAILS      — Comma-separated recipient email addresses
#
# DELIVERY ORDER:
#   1. Microsoft Teams webhook (works from any CI runner)
#   2. GitLab Issue Notes (@mentions guarantee email)
#   3. Slack webhook
#   4. Direct SMTP (only from corporate network)
#   5. Local file (last resort)
# ============================================================

import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


# Default notification sender and recipients
DEFAULT_SMTP_FROM = "noreply@btbpo.net"
DEFAULT_NOTIFY_EMAILS = "Druva.SKumar@bottomline.com"

# Corporate SMTP relays (in priority order)
DEFAULT_SMTP_HOSTS = [
    "inf-npr1-smtp01.saas-n.com",
    "inf-ny2-nonprod-smtplb02.dmz.saas-n.com",
]
DEFAULT_SMTP_PORTS = [25, 587]


class Notifier:
    """
    Sends team notifications on contract test failures and drift detection
    via Slack webhooks and/or email.
    """

    def __init__(self, slack_webhook_url=None, smtp_config=None, teams_webhook_url=None):
        """
        Args:
            slack_webhook_url:  Slack incoming webhook URL.
            smtp_config:        Dict with SMTP config.
            teams_webhook_url:  Microsoft Teams incoming webhook URL.
        """
        # Microsoft Teams webhook (PRIMARY — most reliable from cloud CI)
        self.teams_webhook_url = teams_webhook_url or os.environ.get("TEAMS_WEBHOOK_URL")

        self.slack_webhook_url = slack_webhook_url or os.environ.get("SLACK_WEBHOOK_URL")

        # GitLab API config (primary email method — GitLab sends emails from gitlab@mg.gitlab.com)
        self.gitlab_token = os.environ.get("GITLAB_TOKEN")
        self.gitlab_project_id = os.environ.get("CI_PROJECT_ID")
        self.gitlab_commit_sha = os.environ.get("CI_COMMIT_SHA")
        self.gitlab_api_url = os.environ.get("CI_API_V4_URL", "https://gitlab.com/api/v4")

        # GitLab users to @mention in every note (guarantees email delivery)
        mention_env = os.environ.get("GITLAB_MENTION_USERS", "")
        self.gitlab_mention_users = [
            u.strip() for u in mention_env.split(",") if u.strip()
        ]
        self._gitlab_username_resolved = False

        # SMTP config — primary email delivery via corporate relay
        if smtp_config:
            self.smtp = smtp_config
        else:
            # Support comma-separated hosts in SMTP_HOST, or fall back to defaults
            host_env = os.environ.get("SMTP_HOST", "")
            if host_env:
                hosts = [h.strip() for h in host_env.split(",") if h.strip()]
            else:
                hosts = list(DEFAULT_SMTP_HOSTS)

            # Support comma-separated ports, or fall back to defaults
            port_env = os.environ.get("SMTP_PORT", "")
            if port_env:
                ports = [int(p.strip()) for p in port_env.split(",") if p.strip()]
            else:
                ports = list(DEFAULT_SMTP_PORTS)

            recipients_raw = os.environ.get("NOTIFY_EMAILS", DEFAULT_NOTIFY_EMAILS)
            self.smtp = {
                "hosts": hosts,
                "ports": ports,
                "from_addr": os.environ.get("SMTP_FROM", DEFAULT_SMTP_FROM),
                "user": os.environ.get("SMTP_USER"),        # Optional
                "password": os.environ.get("SMTP_PASSWORD"),  # Optional
                "recipients": [
                    e.strip() for e in recipients_raw.split(",") if e.strip()
                ],
            }

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def notify_drift(self, drift_results, pipeline_url=None):
        """
        Sends a notification about drift detection results.
        Only sends if there are issues (drifted, uncovered, or orphaned).

        Args:
            drift_results: Dict from DriftDetector.detect_drift()
            pipeline_url:  Optional GitLab pipeline URL for context

        Returns:
            dict: {slack: bool, email: bool} — True if sent successfully
        """
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")

        # Only notify on WARNING or CRITICAL
        if health == "HEALTHY":
            print("  [NOTIFIER] Health is HEALTHY — no notification needed.")
            return {"slack": False, "email": False}

        message = self._build_drift_message(drift_results, pipeline_url)
        slack_msg = self._build_drift_slack_payload(drift_results, pipeline_url)

        results = {"slack": False, "email": False}

        if self.slack_webhook_url:
            results["slack"] = self._send_slack(slack_msg)
        else:
            print("  [NOTIFIER] Slack not configured (SLACK_WEBHOOK_URL not set).")

        # Primary: GitLab commit comment (triggers email from gitlab@mg.gitlab.com)
        # Fallback: Direct SMTP → local file
        subject = f"[CONTRACT {health}] Contract drift detected — {summary.get('coverage_percent', '?')}% coverage"
        results["email"] = self._send_notification(subject, message)

        return results

    def notify_test_failure(self, job_name, exit_code, log_snippet=None, pipeline_url=None):
        """
        Sends a notification about a contract test failure in CI.

        Args:
            job_name:     Name of the failed CI job
            exit_code:    Exit code of the failed job
            log_snippet:  Last few lines of job output (optional)
            pipeline_url: GitLab pipeline URL (optional)

        Returns:
            dict: {slack: bool, email: bool}
        """
        message = self._build_failure_message(job_name, exit_code, log_snippet, pipeline_url)
        slack_msg = self._build_failure_slack_payload(job_name, exit_code, log_snippet, pipeline_url)

        results = {"slack": False, "email": False}

        if self.slack_webhook_url:
            results["slack"] = self._send_slack(slack_msg)
        else:
            print("  [NOTIFIER] Slack not configured.")

        subject = f"[CONTRACT FAILURE] {job_name} failed (exit {exit_code})"
        results["email"] = self._send_notification(subject, message)

        return results

    def notify_report(self, drift_results, command_name="report", pipeline_url=None):
        """
        Sends a summary notification after any command that produces drift results.
        Unlike notify_drift(), this ALWAYS sends — even for HEALTHY status — so
        the developer gets a confirmation email after every pipeline run.

        Args:
            drift_results: Dict from DriftDetector.detect_drift()
            command_name:  Which CLI command triggered this (drift/report/validate/fix)
            pipeline_url:  Optional GitLab pipeline URL

        Returns:
            dict: {slack: bool, email: bool}
        """
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")

        message = self._build_report_message(drift_results, command_name, pipeline_url)
        slack_msg = self._build_report_slack_payload(drift_results, command_name, pipeline_url)

        results = {"slack": False, "email": False}

        # Slack: only on WARNING/CRITICAL (avoid noise for healthy)
        if health != "HEALTHY" and self.slack_webhook_url:
            results["slack"] = self._send_slack(slack_msg)
        elif health == "HEALTHY" and self.slack_webhook_url:
            print("  [NOTIFIER] Slack: Skipped (HEALTHY — no issues to report).")

        # Email: always send so the developer has a record
        emoji = "PASS" if health == "HEALTHY" else health
        subject = (
            f"[CONTRACT {emoji}] {command_name.capitalize()} — "
            f"{summary.get('coverage_percent', '?')}% coverage"
        )
        results["email"] = self._send_notification(subject, message)

        return results

    def auto_notify(self, drift_results, command_name="drift", pipeline_url=None):
        """
        Convenience method called automatically by CLI commands when --notify is set.
        Decides which notification type to use based on health status:
          - HEALTHY  → summary email only (confirmation)
          - WARNING  → Slack + email with drift details
          - CRITICAL → Slack + email with drift details (urgent)

        Args:
            drift_results: Dict from DriftDetector.detect_drift()
            command_name:  Which CLI command triggered this
            pipeline_url:  Optional GitLab pipeline URL

        Returns:
            dict: {slack: bool, email: bool}
        """
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")

        print(f"\n  [AUTO-NOTIFY] Health is {health} — sending notifications...")

        if health in ("WARNING", "CRITICAL"):
            # Send detailed drift alert
            return self.notify_drift(drift_results, pipeline_url)
        else:
            # Send summary report (HEALTHY confirmation)
            return self.notify_report(drift_results, command_name, pipeline_url)

    def notify_custom(self, subject, body, pipeline_url=None):
        """
        Sends a custom notification with arbitrary subject and body.
        Used by root cause analysis and other modules.

        Returns:
            dict: {slack: bool, email: bool}
        """
        results = {"slack": False, "email": False}

        # Teams (primary)
        teams_sent = self._send_teams(subject, body, pipeline_url)
        if teams_sent:
            results["teams"] = True

        # Slack
        if self.slack_webhook_url:
            payload = {"text": f"*{subject}*\n\n{body}"}
            results["slack"] = self._send_slack(payload)

        # Email
        results["email"] = self._send_notification(subject, body)

        return results

    # ----------------------------------------------------------------
    # Microsoft Teams (PRIMARY notification method)
    # ----------------------------------------------------------------

    def _send_teams(self, subject, body_text, pipeline_url=None):
        """
        Sends a notification to Microsoft Teams via Incoming Webhook.
        Uses Adaptive Card format (works with both legacy connectors
        and the new Workflows-based webhooks).
        """
        if not self.teams_webhook_url:
            return False

        # Build Adaptive Card payload
        card = self._build_teams_adaptive_card(subject, body_text, pipeline_url)

        try:
            resp = requests.post(
                self.teams_webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            # Teams webhooks return 200 or 202 on success
            if resp.status_code in (200, 202):
                print("  [NOTIFIER] Teams notification sent successfully.")
                return True
            else:
                print(f"  [NOTIFIER] Teams failed: {resp.status_code} — {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            print(f"  [NOTIFIER] Teams error: {e}")
            return False

    def _build_teams_adaptive_card(self, subject, body_text, pipeline_url=None):
        """
        Builds a Microsoft Teams Adaptive Card payload.
        Compatible with both Workflows webhooks and legacy Office 365 connectors.
        Includes buttons for Pipeline, Dashboard, and Report artifacts.
        """
        # Determine color based on subject content
        if "CRITICAL" in subject or "FAILURE" in subject:
            color = "attention"  # Red
        elif "WARNING" in subject:
            color = "warning"   # Yellow
        else:
            color = "good"      # Green

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Truncate body for Teams (max ~28KB per card)
        display_body = body_text[:3000]
        if len(body_text) > 3000:
            display_body += "\n... (truncated)"

        # Build card body elements
        card_body = [
            {
                "type": "TextBlock",
                "text": subject,
                "weight": "Bolder",
                "size": "Medium",
                "color": color,
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": display_body,
                "wrap": True,
                "fontType": "Monospace",
                "size": "Small",
            },
            {
                "type": "TextBlock",
                "text": f"Contract Testing AI Agent • {timestamp}",
                "isSubtle": True,
                "size": "Small",
                "wrap": True,
            },
        ]

        # Build action buttons
        actions = []
        if pipeline_url:
            actions.append({
                "type": "Action.OpenUrl",
                "title": "View Pipeline",
                "url": pipeline_url,
            })

            # Build artifact URLs from pipeline URL
            # GitLab pipeline URL: .../pipelines/12345
            # Job browse URL: .../-/jobs/<id>/artifacts/browse (we use the job artifacts path)
            project_path = os.environ.get("CI_PROJECT_PATH", "")
            job_id = os.environ.get("CI_JOB_ID", "")
            gitlab_base = os.environ.get("CI_SERVER_URL", "https://gitlab.com")

            if project_path and job_id:
                artifacts_base = f"{gitlab_base}/{project_path}/-/jobs/{job_id}/artifacts/file"
                actions.append({
                    "type": "Action.OpenUrl",
                    "title": "View Dashboard",
                    "url": f"{artifacts_base}/ai-agent/reports/dashboard.html",
                })
                actions.append({
                    "type": "Action.OpenUrl",
                    "title": "View Report",
                    "url": f"{artifacts_base}/ai-agent/reports/full_report.txt",
                })

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": card_body,
                        "actions": actions,
                    },
                }
            ],
        }

        return card

    # ----------------------------------------------------------------
    # Slack
    # ----------------------------------------------------------------

    def _send_slack(self, payload):
        """Sends a message to Slack via incoming webhook."""
        try:
            resp = requests.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                print("  [NOTIFIER] Slack notification sent successfully.")
                return True
            else:
                print(f"  [NOTIFIER] Slack failed: {resp.status_code} — {resp.text}")
                return False
        except requests.RequestException as e:
            print(f"  [NOTIFIER] Slack error: {e}")
            return False

    def _build_drift_slack_payload(self, drift_results, pipeline_url=None):
        """Builds a Slack Block Kit message for drift notifications."""
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")
        emoji = ":red_circle:" if health == "CRITICAL" else ":warning:"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Contract Drift Detected",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Health:* {health}"},
                    {"type": "mrkdwn", "text": f"*Coverage:* {summary.get('coverage_percent', '?')}%"},
                    {"type": "mrkdwn", "text": f"*Contracts:* {summary.get('total_contracts', 0)}"},
                    {"type": "mrkdwn", "text": f"*Endpoints:* {summary.get('covered_count', 0)}/{summary.get('total_spec_endpoints', 0)} covered"},
                    {"type": "mrkdwn", "text": f"*Drifted:* {summary.get('drifted_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Uncovered:* {summary.get('uncovered_count', 0)}"},
                ],
            },
        ]

        # Add drifted details
        drifted = drift_results.get("drifted", [])
        if drifted:
            details = "\n".join(
                f"• `{d['method']} {d['url']}` — {', '.join(d.get('issues', []))}"
                for d in drifted[:5]  # Limit to 5 to avoid Slack message limits
            )
            if len(drifted) > 5:
                details += f"\n_...and {len(drifted) - 5} more_"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Drifted Contracts:*\n{details}"},
            })

        # Add pipeline link
        if pipeline_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Pipeline"},
                        "url": pipeline_url,
                    }
                ],
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Contract Testing AI Agent • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"},
            ],
        })

        return {"blocks": blocks}

    def _build_failure_slack_payload(self, job_name, exit_code, log_snippet=None, pipeline_url=None):
        """Builds a Slack Block Kit message for test failure notifications."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":x: Contract Test Failed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Job:* `{job_name}`"},
                    {"type": "mrkdwn", "text": f"*Exit Code:* {exit_code}"},
                ],
            },
        ]

        if log_snippet:
            # Truncate to avoid Slack's 3000 char block limit
            snippet = log_snippet[:2000]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Log:*\n```{snippet}```"},
            })

        if pipeline_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Pipeline"},
                        "url": pipeline_url,
                    }
                ],
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Contract Testing AI Agent • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"},
            ],
        })

        return {"blocks": blocks}

    # ----------------------------------------------------------------
    # GitLab API (primary notification method)
    # ----------------------------------------------------------------
    # Uses GitLab Issue Notes — posting a comment on an issue you're
    # subscribed to ALWAYS triggers an email from gitlab@mg.gitlab.com.
    # Much more reliable than commit comments which only email the author.
    # ----------------------------------------------------------------

    def _get_or_create_notification_issue(self):
        """
        Finds or creates a dedicated 'Contract Testing Notifications' issue.
        Auto-subscribes the token owner so they receive email notifications.
        Returns the issue IID (internal ID) or None on failure.
        """
        headers = {"PRIVATE-TOKEN": self.gitlab_token}
        base_url = f"{self.gitlab_api_url}/projects/{self.gitlab_project_id}"
        label = "contract-notifications"
        title = "Contract Testing — Automated Notifications"

        issue_iid = None

        # Search for existing open notification issue
        try:
            search_url = f"{base_url}/issues"
            params = {"labels": label, "state": "opened", "per_page": 1}
            resp = requests.get(search_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200 and resp.json():
                issue = resp.json()[0]
                issue_iid = issue["iid"]
        except requests.RequestException:
            pass

        # Create a new notification issue if none exists
        if not issue_iid:
            try:
                create_url = f"{base_url}/issues"
                body = {
                    "title": title,
                    "description": (
                        "This issue receives automated notifications from the "
                        "Contract Testing AI Agent.\n\n"
                        "**Subscribe to this issue** to receive email notifications "
                        "for contract drift, test failures, and health reports.\n\n"
                        "Each pipeline run posts a comment here with the results.\n\n"
                        "_Do not close this issue — it is used for ongoing notifications._"
                    ),
                    "labels": label,
                }
                resp = requests.post(
                    create_url, headers=headers, json=body, timeout=15
                )
                if resp.status_code in (200, 201):
                    issue = resp.json()
                    issue_iid = issue["iid"]
                    print(f"  [NOTIFIER] Created notification issue #{issue_iid}: {issue['web_url']}")
                else:
                    print(f"  [NOTIFIER] Failed to create issue: {resp.status_code} — {resp.text[:200]}")
                    return None
            except requests.RequestException as e:
                print(f"  [NOTIFIER] Error creating issue: {e}")
                return None

        # Auto-subscribe the token owner to the issue so they get emails
        if issue_iid:
            self._subscribe_to_issue(issue_iid)

        return issue_iid

    def _subscribe_to_issue(self, issue_iid):
        """
        Subscribes the GITLAB_TOKEN owner to the notification issue.
        GitLab sends email notifications to all subscribers when a new
        note (comment) is posted. This is idempotent — subscribing
        when already subscribed returns 304 (no error).
        """
        headers = {"PRIVATE-TOKEN": self.gitlab_token}
        url = (
            f"{self.gitlab_api_url}/projects/{self.gitlab_project_id}"
            f"/issues/{issue_iid}/subscribe"
        )
        try:
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                print(f"  [NOTIFIER] Subscribed to notification issue #{issue_iid}.")
            elif resp.status_code == 304:
                pass  # Already subscribed — no action needed
            else:
                print(f"  [NOTIFIER] Subscribe warning: {resp.status_code} — {resp.text[:100]}")
        except requests.RequestException:
            pass  # Non-critical — don't block notification

    def _resolve_gitlab_username(self):
        """
        Resolves the GitLab username from the GITLAB_TOKEN via GET /user.
        Called once, result is cached. If GITLAB_MENTION_USERS is already
        set, this is skipped.
        """
        if self._gitlab_username_resolved or self.gitlab_mention_users:
            return
        self._gitlab_username_resolved = True

        if not self.gitlab_token:
            return

        try:
            headers = {"PRIVATE-TOKEN": self.gitlab_token}
            resp = requests.get(
                f"{self.gitlab_api_url}/user",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                username = resp.json().get("username")
                if username:
                    self.gitlab_mention_users = [username]
                    print(f"  [NOTIFIER] Resolved GitLab user: @{username}")
            else:
                print(f"  [NOTIFIER] Could not resolve GitLab user (status {resp.status_code}).")
        except requests.RequestException:
            pass

    def _build_mention_line(self):
        """
        Builds a Markdown @mention line for all configured users.
        @mentioning in a GitLab note GUARANTEES email delivery
        regardless of subscription or notification settings.
        """
        if not self.gitlab_mention_users:
            return ""
        mentions = " ".join(f"@{u}" for u in self.gitlab_mention_users)
        return f"\n\n/cc {mentions}"

    def _send_gitlab_note(self, subject, body_text):
        """
        Posts a note (comment) on the dedicated notification issue.
        @mentions configured users to guarantee email delivery from
        gitlab@mg.gitlab.com — works regardless of subscription status.
        """
        if not all([self.gitlab_token, self.gitlab_project_id]):
            print("  [NOTIFIER] GitLab API not configured (missing GITLAB_TOKEN/CI_PROJECT_ID).")
            return False

        headers = {"PRIVATE-TOKEN": self.gitlab_token}

        # Resolve the token owner's username (first call only)
        self._resolve_gitlab_username()

        # Get or create the notification issue
        issue_iid = self._get_or_create_notification_issue()
        if not issue_iid:
            return False

        # Post a comment on the issue
        url = (
            f"{self.gitlab_api_url}/projects/{self.gitlab_project_id}"
            f"/issues/{issue_iid}/notes"
        )

        # Build Markdown note with pipeline context
        pipeline_url = os.environ.get("CI_PIPELINE_URL", "")
        commit_sha = self.gitlab_commit_sha or "unknown"
        pipeline_link = f"[Pipeline]({pipeline_url})" if pipeline_url else ""
        commit_link = f"`{commit_sha[:8]}`" if commit_sha != "unknown" else ""

        # @mention users to guarantee email delivery
        mention_line = self._build_mention_line()

        note_body = (
            f"## {subject}\n\n"
            f"**Commit:** {commit_link} | {pipeline_link}\n\n"
            f"```\n{body_text}\n```\n\n"
            f"---\n"
            f"_Posted automatically by Contract Testing AI Agent — "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
            f"{mention_line}"
        )

        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"body": note_body},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                note_data = resp.json()
                issue_url = (
                    f"{self.gitlab_api_url.replace('/api/v4', '')}"
                    f"/{os.environ.get('CI_PROJECT_PATH', '')}"
                    f"/-/issues/{issue_iid}"
                )
                print(f"  [NOTIFIER] Posted to notification issue #{issue_iid} — GitLab will email subscribers.")
                print(f"  [NOTIFIER] Issue URL: {issue_url}")
                return True
            else:
                print(f"  [NOTIFIER] GitLab API failed: {resp.status_code} — {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            print(f"  [NOTIFIER] GitLab API error: {e}")
            return False

    def _send_notification(self, subject, body_text):
        """
        Unified notification delivery (tries each method in order):
          1. Microsoft Teams webhook (primary — works from any CI runner)
          2. GitLab Issue Notes (@mention → guaranteed email)
          3. Slack webhook
          4. SMTP corporate relay (only from corp network)
          5. Local file (last resort)
        """
        sent = False
        pipeline_url = os.environ.get("CI_PIPELINE_URL", "")

        # 1. Microsoft Teams (primary — most reliable)
        if self.teams_webhook_url:
            if self._send_teams(subject, body_text, pipeline_url):
                sent = True

        # 2. GitLab issue note (supplementary — also creates audit trail)
        if self.gitlab_token and self.gitlab_project_id:
            if self._send_gitlab_note(subject, body_text):
                sent = True

        # 3. Slack (supplementary)
        # Note: Slack is also tried in the public API methods with rich formatting,
        # but we try plain notification here as fallback if not sent yet

        # 4. SMTP (supplementary — only works from self-hosted runners)
        if self.smtp and self.smtp.get("recipients"):
            if self._send_email(subject, body_text):
                sent = True

        if sent:
            return True

        # 5. Last resort: save locally
        from_addr = (self.smtp or {}).get("from_addr", DEFAULT_SMTP_FROM)
        return self._save_email_locally(subject, body_text, from_addr)

    # ----------------------------------------------------------------
    # Email (SMTP — primary delivery)
    # ----------------------------------------------------------------

    def _send_email(self, subject, body_text):
        """
        Sends an email notification via SMTP corporate relay.

        Tries each configured host + port combination in order until one succeeds:
          1. inf-npr1-smtp01.saas-n.com (port 25, then 587)
          2. inf-ny2-nonprod-smtplb02.dmz.saas-n.com (port 25, then 587)

        Port 25  — plain SMTP relay (no TLS, no auth — standard for internal relays)
        Port 587 — submission port (attempts STARTTLS, then auth if configured)

        Falls back to saving email locally if all hosts are unreachable.
        """
        if not self.smtp:
            return False

        from_addr = self.smtp.get("from_addr", DEFAULT_SMTP_FROM)
        user = self.smtp.get("user")
        password = self.smtp.get("password")
        requires_auth = bool(user and password)
        hosts = self.smtp.get("hosts", DEFAULT_SMTP_HOSTS)
        ports = self.smtp.get("ports", DEFAULT_SMTP_PORTS)

        # Build the email message once
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(self.smtp["recipients"])

        # Plain text version
        msg.attach(MIMEText(body_text, "plain"))

        # HTML version
        html_body = self._text_to_html(subject, body_text)
        msg.attach(MIMEText(html_body, "html"))

        # Try each host + port combination
        for host in hosts:
            for port in ports:
                try:
                    print(f"  [NOTIFIER] Trying SMTP: {host}:{port} ...")
                    with smtplib.SMTP(host, port, timeout=15) as server:
                        server.ehlo()

                        # Port 587 typically requires STARTTLS
                        # Port 25 internal relays usually don't support TLS
                        if port == 587:
                            try:
                                context = ssl.create_default_context()
                                server.starttls(context=context)
                                server.ehlo()
                            except (smtplib.SMTPNotSupportedError, smtplib.SMTPException):
                                print(f"  [NOTIFIER] STARTTLS not supported on {host}:{port}, continuing without TLS.")
                        # For port 25, skip TLS entirely (corporate relay)

                        # Only login if credentials are provided
                        if requires_auth:
                            server.login(user, password)

                        server.sendmail(
                            from_addr,
                            self.smtp["recipients"],
                            msg.as_string(),
                        )

                    recipient_count = len(self.smtp["recipients"])
                    print(f"  [NOTIFIER] Email sent successfully via {host}:{port} to {recipient_count} recipient(s).")
                    return True

                except (OSError, smtplib.SMTPException) as e:
                    print(f"  [NOTIFIER] SMTP failed on {host}:{port} — {e.__class__.__name__}: {e}")
                    continue

        # All host+port combinations failed
        print(f"  [NOTIFIER] All SMTP hosts unreachable. Tried: {', '.join(f'{h}:{p}' for h in hosts for p in ports)}")
        return False

    def _save_email_locally(self, subject, body_text, from_addr):
        """
        Saves the email content to a file when SMTP is unreachable.
        Useful for local development — the corporate relay is typically
        only accessible from CI runners inside the network.
        """
        try:
            reports_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "reports", "notifications",
            )
            os.makedirs(reports_dir, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(reports_dir, f"email_{timestamp}.txt")

            recipients = ", ".join(self.smtp["recipients"])
            content = (
                f"{'=' * 60}\n"
                f"  EMAIL NOTIFICATION (saved locally — SMTP unreachable)\n"
                f"{'=' * 60}\n"
                f"  From:    {from_addr}\n"
                f"  To:      {recipients}\n"
                f"  Subject: {subject}\n"
                f"{'=' * 60}\n\n"
                f"{body_text}\n\n"
                f"{'=' * 60}\n"
                f"  NOTE: This email will be sent automatically in the CI\n"
                f"  pipeline where the SMTP relay is reachable.\n"
                f"{'=' * 60}\n"
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            # Also save the HTML version
            html_path = os.path.join(reports_dir, f"email_{timestamp}.html")
            html_body = self._text_to_html(subject, body_text)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_body)

            print(f"  [NOTIFIER] Email saved to: {filepath}")
            print(f"  [NOTIFIER] HTML preview:   {html_path}")
            print(f"  [NOTIFIER] This email will be sent in CI where SMTP is reachable.")
            return True

        except Exception as save_err:
            print(f"  [NOTIFIER] Could not save email locally: {save_err}")
            return False

    # ----------------------------------------------------------------
    # Message builders
    # ----------------------------------------------------------------

    def _build_drift_message(self, drift_results, pipeline_url=None):
        """Builds a plain-text drift notification message."""
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"CONTRACT DRIFT ALERT — {health}",
            f"Time: {timestamp}",
            "",
            "Summary:",
            f"  Health:       {health}",
            f"  Coverage:     {summary.get('coverage_percent', '?')}%",
            f"  Endpoints:    {summary.get('total_spec_endpoints', 0)}",
            f"  Contracts:    {summary.get('total_contracts', 0)}",
            f"  Covered:      {summary.get('covered_count', 0)}/{summary.get('total_spec_endpoints', 0)} endpoints",
            f"  Drifted:      {summary.get('drifted_count', 0)}",
            f"  Uncovered:    {summary.get('uncovered_count', 0)}",
            f"  Orphaned:     {summary.get('orphaned_count', 0)}",
        ]

        drifted = drift_results.get("drifted", [])
        if drifted:
            lines.append("")
            lines.append("Drifted Contracts:")
            for d in drifted:
                lines.append(f"  {d['method']} {d['url']} ({d['file']})")
                for issue in d.get("issues", []):
                    lines.append(f"    - {issue}")
                if d.get("suggestion"):
                    lines.append(f"    💡 Fix: {d['suggestion']}")

        uncovered = drift_results.get("uncovered", [])
        if uncovered:
            lines.append("")
            lines.append("Uncovered Endpoints:")
            for u in uncovered:
                lines.append(f"  {u['method'].upper()} {u['path']}")

        if pipeline_url:
            lines.append("")
            lines.append(f"Pipeline: {pipeline_url}")

        lines.extend([
            "",
            "Action Required:",
            "  Run: python main.py fix --create-mr",
            "  Or click the 'auto-fix-contracts' job in the pipeline.",
            "",
            "— Contract Testing AI Agent",
        ])

        return "\n".join(lines)

    def _build_report_message(self, drift_results, command_name, pipeline_url=None):
        """Builds a plain-text report summary notification."""
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"CONTRACT TEST REPORT — {health}",
            f"Command: {command_name}",
            f"Time: {timestamp}",
            "",
            "Summary:",
            f"  Health:       {health}",
            f"  Coverage:     {summary.get('coverage_percent', '?')}%",
            f"  Endpoints:    {summary.get('total_spec_endpoints', 0)}",
            f"  Contracts:    {summary.get('total_contracts', 0)}",
            f"  Covered:      {summary.get('covered_count', 0)}/{summary.get('total_spec_endpoints', 0)} endpoints",
            f"  Drifted:      {summary.get('drifted_count', 0)}",
            f"  Uncovered:    {summary.get('uncovered_count', 0)}",
            f"  Orphaned:     {summary.get('orphaned_count', 0)}",
        ]

        drifted = drift_results.get("drifted", [])
        if drifted:
            lines.append("")
            lines.append("Drifted Contracts:")
            for d in drifted:
                lines.append(f"  {d['method']} {d['url']} ({d['file']})")
                for issue in d.get("issues", []):
                    lines.append(f"    - {issue}")
                if d.get("suggestion"):
                    lines.append(f"    💡 Fix: {d['suggestion']}")

        uncovered = drift_results.get("uncovered", [])
        if uncovered:
            lines.append("")
            lines.append("Uncovered Endpoints (no contracts):")
            for u in uncovered:
                lines.append(f"  {u['method'].upper()} {u['path']}")

        if health == "HEALTHY":
            lines.extend([
                "",
                "Status: All contracts are in sync with the API. No action needed.",
            ])
        else:
            lines.extend([
                "",
                "Action Required:",
                "  Run: python main.py fix --create-mr",
                "  Or click the 'auto-fix-contracts' job in the pipeline.",
            ])

        if pipeline_url:
            lines.extend(["", f"Pipeline: {pipeline_url}"])

        lines.extend(["", "— Contract Testing AI Agent"])
        return "\n".join(lines)

    def _build_report_slack_payload(self, drift_results, command_name, pipeline_url=None):
        """Builds a Slack Block Kit payload for report summary notifications."""
        summary = drift_results.get("summary", {})
        health = summary.get("health", "UNKNOWN")

        emoji_map = {"HEALTHY": ":white_check_mark:", "WARNING": ":warning:", "CRITICAL": ":red_circle:"}
        emoji = emoji_map.get(health, ":question:")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} Contract Report — {health}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Command:* `{command_name}`"},
                    {"type": "mrkdwn", "text": f"*Coverage:* {summary.get('coverage_percent', '?')}%"},
                    {"type": "mrkdwn", "text": f"*Covered:* {summary.get('covered_count', 0)}/{summary.get('total_spec_endpoints', 0)}"},
                    {"type": "mrkdwn", "text": f"*Drifted:* {summary.get('drifted_count', 0)}"},
                ],
            },
        ]

        if pipeline_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "View Pipeline"}, "url": pipeline_url}
                ],
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Contract Testing AI Agent • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"},
            ],
        })

        return {"blocks": blocks}

    def _build_failure_message(self, job_name, exit_code, log_snippet=None, pipeline_url=None):
        """Builds a plain-text test failure notification message."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"CONTRACT TEST FAILURE",
            f"Time: {timestamp}",
            "",
            f"  Job:       {job_name}",
            f"  Exit Code: {exit_code}",
        ]

        if log_snippet:
            lines.extend([
                "",
                "Log Output (last lines):",
                log_snippet[:2000],
            ])

        if pipeline_url:
            lines.extend(["", f"Pipeline: {pipeline_url}"])

        lines.extend([
            "",
            "Action Required:",
            "  1. Check the pipeline for details",
            "  2. Run: python main.py drift",
            "  3. Fix the contract or revert the API change",
            "",
            "— Contract Testing AI Agent",
        ])

        return "\n".join(lines)

    def _text_to_html(self, subject, text):
        """Converts plain text notification to a simple HTML email."""
        # Escape HTML entities
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pre_block = escaped.replace("\n", "<br>\n")

        return f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #333; }}
  .container {{ max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e1e4e8; border-radius: 6px; }}
  h2 {{ color: #d73a49; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }}
  .content {{ font-family: monospace; font-size: 13px; line-height: 1.6; }}
  .footer {{ margin-top: 20px; font-size: 12px; color: #6a737d; }}
</style></head>
<body>
  <div class="container">
    <h2>{subject}</h2>
    <div class="content">{pre_block}</div>
    <div class="footer">Sent by Contract Testing AI Agent</div>
  </div>
</body>
</html>"""
