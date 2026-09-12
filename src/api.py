"""
Minimal FastAPI service exposing the LoadAudit pipeline as a webhook.

Run: uvicorn src.api:app --reload
Then: POST a raw invoice text (or structured JSON) to /invoices/audit
"""
import json
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from .extraction import extract_invoice
from .matcher import match_invoice_to_rc
from .dispute_drafting import draft_dispute_email
from .notifications import send_flagged_invoice_alert

app = FastAPI(title="LoadAudit AI")

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_rate_confirmations():
    with open(DATA_DIR / "rate_confirmations.json") as f:
        return {rc["load_id"]: rc for rc in json.load(f)}


class RawInvoice(BaseModel):
    text: str


class StructuredInvoice(BaseModel):
    load_id: str
    carrier: str
    invoice_number: str
    linehaul_rate: float
    accessorials: list = []
    pod_attached: bool = True


@app.post("/invoices/audit/raw")
def audit_raw_invoice(payload: RawInvoice):
    """Accepts unstructured invoice text (e.g. an email body) and runs it
    through extraction -> matching -> (optional) dispute drafting."""
    invoice = extract_invoice(payload.text)
    return _audit(invoice)


@app.post("/invoices/audit")
def audit_structured_invoice(invoice: StructuredInvoice):
    """Accepts an already-structured invoice (e.g. from a TMS webhook)."""
    return _audit(invoice.model_dump())


def _audit(invoice: dict):
    rc_by_load = _load_rate_confirmations()
    rc = rc_by_load.get(invoice.get("load_id"))
    result = match_invoice_to_rc(invoice, rc)

    response = {
        "load_id": result.load_id,
        "status": result.status,
        "confidence": result.confidence,
        "reasons": result.reasons,
    }
    if result.status == "flagged":
        dispute_email = draft_dispute_email(invoice, result)
        response["dispute_email_draft"] = dispute_email
        response["slack_alert_sent"] = send_flagged_invoice_alert(invoice, result, dispute_email)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
