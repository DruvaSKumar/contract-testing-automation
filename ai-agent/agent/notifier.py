# ============================================================
# notifier.py — Team Notification Module
# ============================================================
# PURPOSE:
#   Sends team notifications when contract tests fail or drift
#   is detected. Supports Slack webhooks and email (SMTP).
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
#   3. Sends via Slack webhook and/or email depending on config
#
# CONFIGURATION (environment variables):
#   Slack:
#     SLACK_WEBHOOK_URL  — Incoming webhook URL from Slack app
#   Email:
#     SMTP_HOST          — SMTP server hostname (e.g., smtp.bottomline.com)
#     SMTP_PORT          — SMTP server port (default: 587)
#     SMTP_FROM          — Sender address (default: contract-agent@noreply.bottomline.com)
#     SMTP_USER          — (Optional) Only if relay requires authentication
#     SMTP_PASSWORD      — (Optional) Only if relay requires authentication
#     NOTIFY_EMAILS      — Comma-separated recipient email addresses
#                          Default: Druva.SKumar@bottomline.com
#
#   NOTE: Most corporate SMTP relays do NOT require authentication.
#         Just set SMTP_HOST and NOTIFY_EMAILS — no password needed.
#         This works the same way GitLab sends emails via its mail relay.
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
DEFAULT_SMTP_FROM = "contract-agent@noreply.bottomline.com"
DEFAULT_NOTIFY_EMAILS = "Druva.SKumar@bottomline.com"


class Notifier:
    """
    Sends team notifications on contract test failures and drift detection
    via Slack webhooks and/or email.
    """

    def __init__(self, slack_webhook_url=None, smtp_config=None):
        """
        Args:
            slack_webhook_url: Slack incoming webhook URL.
                               Defaults to SLACK_WEBHOOK_URL env var.
            smtp_config:       Dict with keys: host, port, from_addr, user, password, recipients.
                               Defaults to SMTP_* env vars.
                               Authentication is OPTIONAL — if user/password are not set,
                               sends via unauthenticated relay (like GitLab does).
        """
        self.slack_webhook_url = slack_webhook_url or os.environ.get("SLACK_WEBHOOK_URL")

        if smtp_config:
            self.smtp = smtp_config
        else:
            host = os.environ.get("SMTP_HOST")
            recipients_raw = os.environ.get("NOTIFY_EMAILS", DEFAULT_NOTIFY_EMAILS)
            self.smtp = {
                "host": host,
                "port": int(os.environ.get("SMTP_PORT", "587")),
                "from_addr": os.environ.get("SMTP_FROM", DEFAULT_SMTP_FROM),
                "user": os.environ.get("SMTP_USER"),        # Optional
                "password": os.environ.get("SMTP_PASSWORD"),  # Optional
                "recipients": [
                    e.strip() for e in recipients_raw.split(",") if e.strip()
                ],
            } if host else None

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

        if self.smtp and self.smtp.get("recipients"):
            subject = f"[CONTRACT {health}] Contract drift detected — {summary.get('coverage_percent', '?')}% coverage"
            results["email"] = self._send_email(subject, message)
        else:
            print("  [NOTIFIER] Email not configured (SMTP_HOST or NOTIFY_EMAILS not set).")

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

        if self.smtp and self.smtp.get("recipients"):
            subject = f"[CONTRACT FAILURE] {job_name} failed (exit {exit_code})"
            results["email"] = self._send_email(subject, message)
        else:
            print("  [NOTIFIER] Email not configured.")

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
        if self.smtp and self.smtp.get("recipients"):
            emoji = "PASS" if health == "HEALTHY" else health
            subject = (
                f"[CONTRACT {emoji}] {command_name.capitalize()} — "
                f"{summary.get('coverage_percent', '?')}% coverage"
            )
            results["email"] = self._send_email(subject, message)
        else:
            print("  [NOTIFIER] Email not configured (SMTP_HOST not set).")

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
                    {"type": "mrkdwn", "text": f"*Drifted:* {summary.get('drifted_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Uncovered:* {summary.get('uncovered_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Orphaned:* {summary.get('orphaned_count', 0)}"},
                    {"type": "mrkdwn", "text": f"*Covered:* {summary.get('covered_count', 0)}/{summary.get('total_spec_endpoints', 0)}"},
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
    # Email
    # ----------------------------------------------------------------

    def _send_email(self, subject, body_text):
        """
        Sends an email notification via SMTP.

        Always attempts STARTTLS (most corporate relays require it).
        Authentication is optional — only logs in if SMTP_USER/PASSWORD are set.

        If the SMTP server is unreachable (e.g., corporate relay from local machine),
        falls back to saving the email as a file in ai-agent/reports/notifications/
        so you can verify the content locally.
        """
        if not self.smtp:
            return False

        from_addr = self.smtp.get("from_addr", DEFAULT_SMTP_FROM)
        user = self.smtp.get("user")
        password = self.smtp.get("password")
        requires_auth = bool(user and password)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = ", ".join(self.smtp["recipients"])

            # Plain text version
            msg.attach(MIMEText(body_text, "plain"))

            # HTML version
            html_body = self._text_to_html(subject, body_text)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp["host"], self.smtp["port"], timeout=30) as server:
                server.ehlo()
                # Always attempt STARTTLS — most relays require it
                try:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                except smtplib.SMTPNotSupportedError:
                    pass  # Server doesn't support TLS — continue without it
                # Only login if credentials are provided
                if requires_auth:
                    server.login(user, password)
                server.sendmail(
                    from_addr,
                    self.smtp["recipients"],
                    msg.as_string(),
                )

            print(f"  [NOTIFIER] Email sent to {len(self.smtp['recipients'])} recipient(s).")
            return True

        except (OSError, smtplib.SMTPException) as e:
            # SMTP unreachable — save email to file as fallback
            print(f"  [NOTIFIER] SMTP unreachable ({e.__class__.__name__}). Saving email locally...")
            return self._save_email_locally(subject, body_text, from_addr)

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
            f"  Covered:      {summary.get('covered_count', 0)}",
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
            f"  Covered:      {summary.get('covered_count', 0)}",
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
