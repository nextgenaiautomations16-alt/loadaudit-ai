"""
Sends a flagged invoice to a Slack channel via an Incoming Webhook, so a
human can see the discrepancy and the drafted dispute email without having
to poll the API.

Setup: create a Slack Incoming Webhook (api.slack.com/apps -> your app ->
Incoming Webhooks) and set it as an environment variable:

    export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

If SLACK_WEBHOOK_URL isn't set, this module logs to stdout instead of
failing, so the rest of the pipeline still runs in a dev/demo environment
without Slack configured.

Note on scope: this posts a rich message with the discrepancy and the
drafted dispute email so a human can act on it immediately (copy the
email, reply in-thread, etc). It does NOT yet include clickable
Approve/Dispute buttons wired back into the app -- that requires a Slack
app with an Interactivity request URL (a public endpoint Slack can call
back), which is a reasonable next step but out of scope for this MVP.
That's listed in the README roadmap rather than faked here.
"""
import os
import requests

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def send_flagged_invoice_alert(invoice: dict, match_result, dispute_email: str) -> bool:
    """Posts a formatted alert to Slack. Returns True if sent (or logged
    locally when no webhook is configured), False on a real send failure."""

    reasons_text = "\n".join(f"• {r}" for r in match_result.reasons)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚩 Invoice flagged — {invoice.get('load_id')}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Carrier:*\n{invoice.get('carrier', 'N/A')}"},
                {"type": "mrkdwn", "text": f"*Invoice #:*\n{invoice.get('invoice_number', 'N/A')}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Reasons flagged:*\n{reasons_text}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Confidence:* {match_result.confidence:.0%}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Drafted dispute email:*\n```{dispute_email}```"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "React with ✅ to approve payment anyway, or reply in-thread to edit the dispute email before sending."}]
        }
    ]

    payload = {"text": f"Invoice flagged for load {invoice.get('load_id')}", "blocks": blocks}

    if not SLACK_WEBHOOK_URL:
        print("[notifications] SLACK_WEBHOOK_URL not set — logging alert instead of sending:")
        print(reasons_text)
        return True

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[notifications] Failed to send Slack alert: {e}")
        return False
