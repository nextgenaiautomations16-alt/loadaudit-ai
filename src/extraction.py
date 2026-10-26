"""
Extraction layer: turns an unstructured carrier invoice (raw text, as if
pulled from an email body or OCR'd PDF) into the structured schema the
matcher expects.

Two modes:
  - LLM mode (used when ANTHROPIC_API_KEY is set): sends the raw text to
    Claude with a strict JSON-only instruction.
  - Fallback heuristic mode (used otherwise, e.g. for offline demos):
    a simple regex-based parser that handles the sample invoice format
    in data/sample_invoice_email.txt.

This split matters for the case study: it shows the pipeline degrades
gracefully rather than hard-failing when a model call isn't available,
and it keeps the demo runnable with zero API cost.
"""
import json
import os
import re

EXTRACTION_PROMPT = """You are a document extraction system for a freight brokerage.
Extract the following fields from the carrier invoice text below and return
ONLY valid JSON, no prose, no markdown fences:

{{
  "load_id": string,
  "carrier": string,
  "invoice_number": string,
  "linehaul_rate": number,
  "accessorials": [{{"type": string, "amount": number}}],
  "pod_attached": boolean
}}

Invoice text:
---
{invoice_text}
---
"""


def extract_with_llm(invoice_text: str) -> dict:
    import anthropic  # imported lazily so the module works without the SDK installed

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(invoice_text=invoice_text)}],
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text"))
    return json.loads(text)


def extract_with_heuristics(invoice_text: str) -> dict:
      invoice_text = "\n".join(l for l in invoice_text.splitlines() if not l.lstrip().startswith(">"))
    """Very simple regex fallback for demo/offline use."""
    def find(pattern, default=None, cast=str):
        m = re.search(pattern, invoice_text, re.IGNORECASE)
        return cast(m.group(1)) if m else default

    load_id = find(r"Load\s*(?:ID|#)?[:\s]+([A-Z0-9]+)")
    carrier = find(r"Carrier[:\s]+([A-Za-z &]+)")
    invoice_number = find(r"Invoice\s*(?:No\.?|#)?[:\s]+([A-Za-z0-9\-]+)")
    linehaul = find(r"Linehaul[:\s\$]+([\d,]+\.\d{2})", cast=lambda s: float(s.replace(",", "")))
    pod_attached = "no pod" not in invoice_text.lower() and "missing pod" not in invoice_text.lower()

    accessorials = []
    for m in re.finditer(r"(Detention|Layover|Lumper|Tarp|Fuel Surcharge)[:\s\$]+([\d,]+\.\d{2})", invoice_text, re.IGNORECASE):
        accessorials.append({"type": m.group(1).lower().replace(" ", "_"), "amount": float(m.group(2).replace(",", ""))})

    return {
        "load_id": load_id,
        "carrier": carrier,
        "invoice_number": invoice_number,
        "linehaul_rate": linehaul,
        "accessorials": accessorials,
        "pod_attached": pod_attached,
    }


def extract_invoice(invoice_text: str) -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return extract_with_llm(invoice_text)
        except Exception as e:
            print(f"[extraction] LLM extraction failed ({e}), falling back to heuristics")
    return extract_with_heuristics(invoice_text)


if __name__ == "__main__":
    sample = """
    Carrier: Apex Trucking
    Load ID: L1000
    Invoice #: INV-L1000
    Linehaul: $1,540.00
    Detention: $150.00
    """
    print(json.dumps(extract_invoice(sample), indent=2))
