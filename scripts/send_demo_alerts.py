"""
Runs the synthetic invoices through the full pipeline (match -> draft ->
Slack alert) and actually sends Slack alerts for every flagged invoice.

This is separate from eval/run_eval.py on purpose: the eval script tests
matching *accuracy* and should stay a pure, side-effect-free check you can
run repeatedly without spamming Slack. This script is for demoing the
Slack step itself.

Run from repo root: python -m scripts.send_demo_alerts
Requires SLACK_WEBHOOK_URL to be set (falls back to console logging if not).
"""
import json
from pathlib import Path

from src.matcher import match_invoice_to_rc
from src.dispute_drafting import draft_dispute_email
from src.notifications import send_flagged_invoice_alert

DATA_DIR = Path(__file__).parent.parent / "data"


def main():
    with open(DATA_DIR / "invoices.json") as f:
        invoices = json.load(f)
    with open(DATA_DIR / "rate_confirmations.json") as f:
        rc_by_load = {rc["load_id"]: rc for rc in json.load(f)}

    sent = 0
    for invoice in invoices:
        rc = rc_by_load.get(invoice["load_id"])
        result = match_invoice_to_rc(invoice, rc)
        if result.status == "flagged":
            dispute_email = draft_dispute_email(invoice, result)
            ok = send_flagged_invoice_alert(invoice, result, dispute_email)
            print(f"{invoice['load_id']}: alert {'sent' if ok else 'FAILED'}")
            sent += 1

    print(f"\nDone — {sent} flagged invoice(s) alerted.")


if __name__ == "__main__":
    main()
