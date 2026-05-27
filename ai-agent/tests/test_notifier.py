# ============================================================
# test_notifier.py — Unit Tests for Notifier Module
# ============================================================

import pytest
from unittest.mock import patch, MagicMock

from agent.notifier import Notifier


class TestNotifier:
    """Tests for the Notifier module."""

    # ---- Initialization Tests ----

    def test_init_no_config(self):
        """Should initialize without any webhook configured."""
        notifier = Notifier()
        # Should not raise

    def test_init_with_teams_webhook(self):
        """Should accept Teams webhook URL."""
        notifier = Notifier(teams_webhook_url="https://teams.webhook.url/test")
        assert notifier.teams_webhook_url == "https://teams.webhook.url/test"

    def test_init_with_slack_webhook(self):
        """Should accept Slack webhook URL."""
        notifier = Notifier(slack_webhook_url="https://hooks.slack.com/test")
        assert notifier.slack_webhook_url == "https://hooks.slack.com/test"

    # ---- notify_drift Tests ----

    def test_notify_drift_healthy_skips(self):
        """Should skip notification when health is HEALTHY."""
        notifier = Notifier(teams_webhook_url="https://test")
        drift_report = {
            "uncovered": [],
            "orphaned": [],
            "drifted": [],
            "covered": [{"method": "GET", "url": "/api/users", "file": "x.yml"}],
            "summary": {
                "health": "HEALTHY",
                "uncovered_count": 0,
                "orphaned_count": 0,
                "drifted_count": 0,
                "covered_count": 5,
                "coverage_percent": 100.0,
                "total_spec_endpoints": 5,
                "total_contracts": 5,
            },
        }

        result = notifier.notify_drift(drift_report)
        assert result["slack"] is False
        assert result["email"] is False

    @patch("agent.notifier.requests.post")
    def test_notify_drift_warning_sends(self, mock_post):
        """Should send notification when health is WARNING."""
        mock_post.return_value = MagicMock(status_code=200, text="ok")

        notifier = Notifier(slack_webhook_url="https://hooks.slack.com/test")
        drift_report = {
            "uncovered": [{"method": "POST", "path": "/api/users"}],
            "orphaned": [],
            "drifted": [],
            "covered": [],
            "summary": {
                "health": "WARNING",
                "uncovered_count": 1,
                "orphaned_count": 0,
                "drifted_count": 0,
                "covered_count": 0,
                "coverage_percent": 0.0,
                "total_spec_endpoints": 1,
                "total_contracts": 0,
            },
        }

        with patch.dict("os.environ", {"GITLAB_TOKEN": "", "CI_PROJECT_ID": ""}, clear=False):
            result = notifier.notify_drift(drift_report)
        # Should have tried to send Slack
        assert mock_post.called

    def test_notify_drift_no_channels_no_error(self):
        """Should handle gracefully when no channels configured."""
        with patch.dict("os.environ", {
            "SLACK_WEBHOOK_URL": "",
            "TEAMS_WEBHOOK_URL": "",
            "GITLAB_TOKEN": "",
            "CI_PROJECT_ID": "",
            "SMTP_HOST": "",
            "NOTIFY_EMAILS": "",
        }, clear=False):
            notifier = Notifier()
            drift_report = {
                "uncovered": [{"method": "GET", "path": "/api/x"}],
                "orphaned": [],
                "drifted": [],
                "covered": [],
                "summary": {
                    "health": "WARNING",
                    "uncovered_count": 1,
                    "orphaned_count": 0,
                    "drifted_count": 0,
                    "covered_count": 0,
                    "coverage_percent": 0.0,
                    "total_spec_endpoints": 1,
                    "total_contracts": 0,
                },
            }
            # Should not raise even with no channels
            result = notifier.notify_drift(drift_report)
