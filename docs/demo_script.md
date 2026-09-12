# Demo Script (3-5 minutes)

**0:00-0:30 — The problem**
"Freight brokers manually check every carrier invoice against the rate
confirmation before paying it. Industry benchmarks put 5-10% of invoices
at having at least one billing error, and each manual check takes several
minutes. This is LoadAudit AI — it automates that check."

**0:30-1:30 — Show the pipeline running**
Run `python -m eval.run_eval` live (or hit the `/invoices/audit` endpoint
with a couple of sample payloads via curl/Postman). Narrate: invoice comes
in, gets parsed into structured fields, gets checked against the rate
confirmation on file.

**1:30-3:00 — Zoom into one flagged case**
Pick a load with an "unauthorized_accessorial" or "wrong_linehaul_rate"
discrepancy. Show the JSON response: status=flagged, the plain-language
reason, and the auto-drafted dispute email. This is the moment that sells
it — a real dollar-saving catch, explained in a sentence a non-technical AP
person can act on immediately.

**3:00-4:00 — Show the eval numbers**
Run `python -m eval.run_eval` and show precision/recall on the labeled
synthetic set. Be explicit that these are test-set numbers, not claimed
production results, and explain what precision/recall mean for an AP
manager (a false positive wastes a human's time reviewing a fine invoice;
a false negative means a real overbilling gets paid).

**4:00-4:30 — Close**
"This same extract -> match -> human-review-on-exceptions pattern applies
beyond freight — AP invoice matching, insurance claims intake, contract
review. I picked freight first because I had existing infrastructure and
market research pointing there, but the architecture generalizes."
