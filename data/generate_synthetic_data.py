"""
Generates a synthetic dataset of rate confirmations + carrier invoices
for the LoadAudit AI reconciliation engine.

~70% of invoices match their rate confirmation cleanly.
~30% carry a deliberate, labeled discrepancy so the matcher/eval pipeline
has real signal to score against.

Run: python generate_synthetic_data.py
Outputs: rate_confirmations.json, invoices.json, ground_truth.csv
"""
import json
import random
import csv
from pathlib import Path

random.seed(42)

CARRIERS = ["Apex Trucking", "Blue Ridge Freight", "Cascade Logistics",
            "Delta Haul", "Evergreen Transport", "Frontier Carriers"]
LANES = [("Dallas, TX", "Chicago, IL"), ("Atlanta, GA", "Newark, NJ"),
         ("Los Angeles, CA", "Phoenix, AZ"), ("Memphis, TN", "Columbus, OH"),
         ("Houston, TX", "Denver, CO"), ("Seattle, WA", "Portland, OR")]
ACCESSORIAL_TYPES = ["detention", "layover", "lumper", "tarp", "fuel_surcharge"]

DISCREPANCY_TYPES = [
    "wrong_linehaul_rate",
    "unauthorized_accessorial",
    "accessorial_amount_mismatch",
    "duplicate_invoice",
    "missing_pod_flag",
]

N_LOADS = 30


def make_rate_confirmation(load_id):
    origin, dest = random.choice(LANES)
    linehaul = round(random.uniform(900, 3200), 2)
    n_accessorials = random.choice([0, 0, 1, 1, 2])
    accessorials = []
    for acc_type in random.sample(ACCESSORIAL_TYPES, n_accessorials):
        accessorials.append({
            "type": acc_type,
            "amount": round(random.uniform(50, 350), 2),
            "authorized": True,
        })
    return {
        "load_id": load_id,
        "carrier": random.choice(CARRIERS),
        "origin": origin,
        "destination": dest,
        "linehaul_rate": linehaul,
        "accessorials": accessorials,
        "pod_on_file": True,
    }


def make_invoice_from_rc(rc, discrepancy_type=None):
    invoice = {
        "load_id": rc["load_id"],
        "carrier": rc["carrier"],
        "invoice_number": f"INV-{rc['load_id']}",
        "linehaul_rate": rc["linehaul_rate"],
        "accessorials": [dict(a) for a in rc["accessorials"]],
        "pod_attached": True,
    }

    if discrepancy_type == "wrong_linehaul_rate":
        invoice["linehaul_rate"] = round(rc["linehaul_rate"] + random.uniform(75, 400), 2)

    elif discrepancy_type == "unauthorized_accessorial":
        invoice["accessorials"].append({
            "type": random.choice(ACCESSORIAL_TYPES),
            "amount": round(random.uniform(100, 300), 2),
            "authorized": False,
        })

    elif discrepancy_type == "accessorial_amount_mismatch" and invoice["accessorials"]:
        idx = 0
        invoice["accessorials"][idx]["amount"] = round(
            invoice["accessorials"][idx]["amount"] + random.uniform(40, 150), 2
        )

    elif discrepancy_type == "duplicate_invoice":
        invoice["invoice_number"] = invoice["invoice_number"] + "-DUP"

    elif discrepancy_type == "missing_pod_flag":
        invoice["pod_attached"] = False

    return invoice


def main():
    rate_confirmations = []
    invoices = []
    ground_truth_rows = []

    # decide which loads get a discrepancy (~30%)
    n_discrepant = max(1, round(N_LOADS * 0.3))
    discrepant_indices = set(random.sample(range(N_LOADS), n_discrepant))

    for i in range(N_LOADS):
        load_id = f"L{1000 + i}"
        rc = make_rate_confirmation(load_id)
        rate_confirmations.append(rc)

        if i in discrepant_indices:
            candidate_types = list(DISCREPANCY_TYPES)
            if not rc["accessorials"]:
                # accessorial_amount_mismatch needs an existing accessorial to alter
                candidate_types.remove("accessorial_amount_mismatch")
            d_type = random.choice(candidate_types)
            invoice = make_invoice_from_rc(rc, discrepancy_type=d_type)
            expected_status = "flagged"
        else:
            invoice = make_invoice_from_rc(rc, discrepancy_type=None)
            d_type = "none"
            expected_status = "clean"

        invoices.append(invoice)
        ground_truth_rows.append({
            "load_id": load_id,
            "expected_status": expected_status,
            "discrepancy_type": d_type,
        })

    out_dir = Path(__file__).parent
    with open(out_dir / "rate_confirmations.json", "w") as f:
        json.dump(rate_confirmations, f, indent=2)
    with open(out_dir / "invoices.json", "w") as f:
        json.dump(invoices, f, indent=2)
    with open(out_dir / "ground_truth.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["load_id", "expected_status", "discrepancy_type"])
        writer.writeheader()
        writer.writerows(ground_truth_rows)

    print(f"Generated {N_LOADS} loads ({n_discrepant} with a discrepancy).")
    print("Wrote rate_confirmations.json, invoices.json, ground_truth.csv")


if __name__ == "__main__":
    main()
