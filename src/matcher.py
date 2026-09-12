"""
Deterministic 3-way match engine.

Design principle (stated explicitly because it matters for the case study):
the LLM/extraction layer is used to GET structured data OUT of documents,
but the actual approve/flag DECISION is made by deterministic rules here,
not by asking a model "does this look right?". That keeps the decision
auditable and reproducible, which matters a lot once real money is
involved.
"""
from dataclasses import dataclass, field
from typing import Optional

RATE_TOLERANCE = 1.00       # dollars - allow trivial rounding differences
ACCESSORIAL_TOLERANCE = 1.00


@dataclass
class MatchResult:
    load_id: str
    status: str                 # "clean" or "flagged"
    reasons: list = field(default_factory=list)
    confidence: float = 1.0


def match_invoice_to_rc(invoice: dict, rc: Optional[dict]) -> MatchResult:
    load_id = invoice["load_id"]

    if rc is None:
        return MatchResult(load_id, "flagged", ["No matching rate confirmation found"], 0.2)

    reasons = []

    # 1. Linehaul rate check
    rate_diff = abs(invoice["linehaul_rate"] - rc["linehaul_rate"])
    if rate_diff > RATE_TOLERANCE:
        reasons.append(
            f"Linehaul rate mismatch: invoiced ${invoice['linehaul_rate']:.2f} "
            f"vs contracted ${rc['linehaul_rate']:.2f} (diff ${rate_diff:.2f})"
        )

    # 2. Accessorial authorization + amount check
    rc_accessorials = {a["type"]: a for a in rc.get("accessorials", [])}
    for inv_acc in invoice.get("accessorials", []):
        rc_acc = rc_accessorials.get(inv_acc["type"])
        if rc_acc is None or not rc_acc.get("authorized", False):
            reasons.append(
                f"Unauthorized accessorial charge: {inv_acc['type']} "
                f"(${inv_acc['amount']:.2f})"
            )
        else:
            amt_diff = abs(inv_acc["amount"] - rc_acc["amount"])
            if amt_diff > ACCESSORIAL_TOLERANCE:
                reasons.append(
                    f"Accessorial amount mismatch on {inv_acc['type']}: "
                    f"invoiced ${inv_acc['amount']:.2f} vs authorized ${rc_acc['amount']:.2f}"
                )

    # 3. POD check
    if not invoice.get("pod_attached", True):
        reasons.append("Proof of delivery missing from invoice packet")

    # 4. Duplicate invoice heuristic
    if invoice.get("invoice_number", "").endswith("-DUP"):
        reasons.append("Invoice number pattern suggests a possible duplicate submission")

    status = "flagged" if reasons else "clean"
    confidence = 0.95 if status == "clean" else max(0.3, 1.0 - 0.2 * len(reasons))
    return MatchResult(load_id, status, reasons, confidence)


def run_batch(invoices: list, rate_confirmations: list) -> list:
    rc_by_load = {rc["load_id"]: rc for rc in rate_confirmations}
    results = []
    for invoice in invoices:
        rc = rc_by_load.get(invoice["load_id"])
        results.append(match_invoice_to_rc(invoice, rc))
    return results
