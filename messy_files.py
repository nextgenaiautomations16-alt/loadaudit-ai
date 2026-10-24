"""Messy-invoice test files for LoadAudit AI (all names and amounts are FAKE).

  python messy_files.py create          writes the folder  messy_invoices/
  python messy_files.py run             checks every file with the regex extractor
  python messy_files.py run ollama      checks with your local model (OLLAMA_MODEL, default qwen2.5:7b)

Tip: open any .txt file in messy_invoices/ with Notepad to see what the system has to read.
Add your own: save a new invoice as a .txt file, add its answer to answers.csv and its
rate confirmation to rate_confirmations.json.
"""
import csv, json, os, sys

FOLDER = "messy_invoices"


def rc(load, rate, acc=None):
    return {"load_id": load, "carrier": "Test Carrier", "linehaul_rate": rate,
            "accessorials": [{"type": t, "amount": a, "authorized": True} for t, a in (acc or {}).items()]}


# (file name, correct decision, invoice text, rate confirmation)
CASES = [
    ("01_polite_email", "clean", "Hello AP team,\nCarrier: Blue Fox Logistics\nLoad ID: T5001\nInvoice #: BF-7731\nLinehaul charge: $2,100.00\nPOD attached. Thanks!", rc("T5001", 2100)),
    ("02_line_haul_two_words", "clean", "Carrier: Northline Haulers\nLoad ID: T5002\nInvoice #: NH-220\nLine haul: $1,800.00\nPOD attached", rc("T5002", 1800)),
    ("03_no_cents", "clean", "Carrier: Redwood Transport\nLoad ID: T5003\nInvoice #: RW-18\nLinehaul: $1,540\nPOD attached", rc("T5003", 1540)),
    ("04_dotted_table", "clean", "Carrier: Summit Freight\nLoad ID: T5004\nInvoice #: SF-902\nLinehaul ........ 1,200.00\nDelivered, signed BOL attached", rc("T5004", 1200)),
    ("05_fuel_surcharge_ok", "clean", "Carrier: Prairie Express\nLoad ID: T5005\nInvoice #: PE-55\nLinehaul: $2,250.00\nFuel Surcharge: $180.00\nPOD attached", rc("T5005", 2250, {"fuel_surcharge": 180})),
    ("06_unauthorized_lumper", "flagged", "Carrier: Harbor Lines\nLoad ID: T5006\nInvoice #: HL-3\nLinehaul: $900.00\nLumper: $120.00\nPOD attached", rc("T5006", 900)),
    ("07_overbilled_rate", "flagged", "Carrier: Granite Carriers\nLoad ID: T5007\nInvoice #: GC-410\nLinehaul: $3,350.00\nPOD attached", rc("T5007", 3100)),
    ("08_pod_to_follow", "flagged", "Carrier: Lone Pine Trucking\nLoad ID: T5008\nInvoice #: LP-61\nLinehaul: $1,675.00\nPOD to follow once driver sends it", rc("T5008", 1675)),
    ("09_load_no_wording", "clean", "Carrier: Delta Run\nLoad No. 5009\nInvoice #: DR-8\nLinehaul: $1,425.00\nPOD attached", rc("5009", 1425)),
    ("10_duplicate_invoice_number", "flagged", "Carrier: Copper State\nLoad ID: T5010\nInvoice #: CS-77-DUP\nLinehaul: $1,990.00\nPOD attached", rc("T5010", 1990)),
    ("11_company_name_punctuation", "clean", "Carrier: J&R Transport, LLC.\nLoad ID: T5011\nInvoice #: JR-1043\nLinehaul: $2,400.00\nPOD attached", rc("T5011", 2400)),
    ("12_detention_by_the_hour", "flagged", "Carrier: Silver Creek\nLoad ID: T5012\nInvoice #: SC-12\nLinehaul: $1,310.00\nDetention 5 hrs @ $50 = $250.00\nPOD attached", rc("T5012", 1310, {"detention": 150})),
    ("13_ALL_CAPS_with_signature", "clean", "CARRIER: SKYLINE FREIGHT\nLOAD ID: M013\nINVOICE #: SK-1\nLINEHAUL: $1,250.00\nPOD ATTACHED\n\nSent from my iPhone", rc("M013", 1250)),
    ("14_scanner_typo_letter_O", "flagged", "Carrier: Pine Ridge\nLoad ID: M014\nInvoice #: PR-5\nLinehaul: $1,8O0.00\nPOD attached", rc("M014", 1800)),
    ("15_forwarded_email_old_load", "clean", "Fwd: invoice\n> Earlier note about Load ID: M099 (old, ignore)\nCarrier: Cedar Haul\nLoad ID: M015\nInvoice #: CH-9\nLinehaul: $2,200.00\nPOD attached", rc("M015", 2200)),
]


def create():
    os.makedirs(FOLDER, exist_ok=True)
    for name, _, text, _ in CASES:
        open(f"{FOLDER}/{name}.txt", "w", encoding="utf-8").write(text)
    json.dump([c[3] for c in CASES], open(f"{FOLDER}/rate_confirmations.json", "w"), indent=2)
    with open(f"{FOLDER}/answers.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "correct_decision"])
        w.writerows([(c[0], c[1]) for c in CASES])
    print(f"Created {len(CASES)} invoices in {FOLDER}/  (open them in Notepad!)")


def run(mode):
    from src.extraction import extract_invoice
    from src.matcher import match_invoice_to_rc
    rcs = {r["load_id"]: r for r in json.load(open(f"{FOLDER}/rate_confirmations.json"))}
    answers = {r["file"]: r["correct_decision"] for r in csv.DictReader(open(f"{FOLDER}/answers.csv"))}
    ok = wrongly_cleared = 0
    print(f"extractor: {mode}\n{'file':32}{'correct':9}{'system said':13}result")
    for name, correct in answers.items():
        text = open(f"{FOLDER}/{name}.txt", encoding="utf-8").read()
        inv = extract_invoice(text, mode=mode)
        got = match_invoice_to_rc(inv, rcs.get(inv.get("load_id"))).status
        tag = "PASS" if got == correct else ("FAIL - WRONGLY CLEARED (dangerous)" if got == "clean" else "FAIL - sent to review unnecessarily (safe)")
        ok += got == correct; wrongly_cleared += (correct == "flagged" and got == "clean")
        print(f"{name:32}{correct:9}{got:13}{tag}")
    print(f"\nCorrect: {ok}/{len(answers)}   Bad invoices wrongly cleared: {wrongly_cleared}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "create": create()
    elif cmd == "run": run(sys.argv[2] if len(sys.argv) > 2 else "regex")
    else: print(__doc__)
