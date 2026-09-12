"""
Drafts a dispute email for a flagged invoice. Template-based by default
(fast, free, deterministic); swap in an LLM call the same way extraction.py
does if you want more natural phrasing for the demo video.
"""

TEMPLATE = """Subject: Invoice Discrepancy - Load {load_id} / Invoice {invoice_number}

Hi {carrier} team,

Thanks for submitting invoice {invoice_number} for load {load_id}. Before we
can process payment, our automated audit flagged the following item(s) for
review against the original rate confirmation:

{reasons_block}

Could you please confirm these charges or send an updated invoice? Happy to
hop on a call if it's easier to sort out.

Thanks,
Accounts Payable
"""


def draft_dispute_email(invoice: dict, match_result) -> str:
    reasons_block = "\n".join(f"  - {r}" for r in match_result.reasons)
    return TEMPLATE.format(
        load_id=invoice["load_id"],
        invoice_number=invoice.get("invoice_number", "N/A"),
        carrier=invoice.get("carrier", "Carrier"),
        reasons_block=reasons_block,
    )
