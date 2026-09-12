# Architecture

```
Carrier invoice (email/PDF/upload/API)
      |
      v
Extraction layer (src/extraction.py)
  - LLM (Claude) when ANTHROPIC_API_KEY is set
  - heuristic regex fallback otherwise
      |
      v
Normalized invoice JSON
      |
      v
3-way match engine (src/matcher.py)
  - deterministic rules: linehaul rate, accessorial authorization,
    accessorial amount tolerance, POD presence, duplicate detection
  - the DECISION is rule-based, not model-judged, so it's auditable
      |
      +--> clean  --> auto-approve --> (accounting export, not yet built)
      |
      +--> flagged --> dispute email drafted (src/dispute_drafting.py)
                        --> human approval step (Slack/email — not yet wired,
                            see Roadmap in README)
      |
      v
Monitoring / evaluation (eval/run_eval.py)
  - precision/recall against labeled ground truth
  - this is what you'd replace with a live dashboard in production
```

## Why the decision layer is rule-based, not LLM-judged

An LLM is good at turning messy text into structured data, and at explaining
*why* something looks wrong in plain language. It is not the right tool for
"is $1,540 close enough to $1,600 to approve automatically" — that's a
deterministic business rule with a real dollar consequence if it's wrong.
Keeping the match decision rule-based means every approval/flag is
reproducible and explainable after the fact, which is what you'd actually
need to defend in front of an AP manager or auditor.

## What's stubbed vs. real

- Real: extraction (LLM + fallback), matching, dispute email drafting, a
  working FastAPI webhook, an evaluation harness with real precision/recall
  numbers on synthetic data.
- Stubbed/roadmap: TMS integration (currently reads a local JSON file
  standing in for "the rate confirmation store"), Slack human-approval step,
  accounting-system export, a persistent database (currently flat files).

Being explicit about this split is intentional — a hiring manager can see
exactly how far the MVP goes and what the next integration step would be.
