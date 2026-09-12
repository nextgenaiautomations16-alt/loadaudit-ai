"""
Scores the matcher's clean/flagged predictions against ground_truth.csv.

Run from repo root: python -m eval.run_eval
"""
import csv
import json
from pathlib import Path

from src.matcher import run_batch

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(name):
    with open(DATA_DIR / name) as f:
        return json.load(f)


def load_ground_truth():
    rows = {}
    with open(DATA_DIR / "ground_truth.csv") as f:
        for row in csv.DictReader(f):
            rows[row["load_id"]] = row
    return rows


def main():
    invoices = load_json("invoices.json")
    rate_confirmations = load_json("rate_confirmations.json")
    ground_truth = load_ground_truth()

    results = run_batch(invoices, rate_confirmations)

    tp = fp = tn = fn = 0
    mismatches = []

    for r in results:
        expected = ground_truth[r.load_id]["expected_status"]
        if expected == "flagged" and r.status == "flagged":
            tp += 1
        elif expected == "clean" and r.status == "flagged":
            fp += 1
            mismatches.append((r.load_id, "false positive", r.reasons))
        elif expected == "clean" and r.status == "clean":
            tn += 1
        elif expected == "flagged" and r.status == "clean":
            fn += 1
            mismatches.append((r.load_id, "false negative (missed discrepancy)", []))

    total = len(results)
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")

    print("=== LoadAudit AI — Evaluation Report ===")
    print(f"Total invoices evaluated: {total}")
    print(f"Accuracy:  {accuracy:.1%}")
    print(f"Precision (of flagged, how many were real discrepancies): {precision:.1%}")
    print(f"Recall (of real discrepancies, how many were caught):       {recall:.1%}")
    print(f"TP={tp}  FP={fp}  TN={tn}  FN={fn}")

    if mismatches:
        print("\n--- Mismatches vs. ground truth ---")
        for load_id, kind, reasons in mismatches:
            print(f"  {load_id}: {kind} {reasons if reasons else ''}")
    else:
        print("\nNo mismatches — matcher agreed with ground truth on every load.")


if __name__ == "__main__":
    main()
