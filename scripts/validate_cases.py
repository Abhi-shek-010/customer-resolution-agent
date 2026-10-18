"""Validate synthetic test cases dataset against schema, uniqueness, evidence IDs, and safety rules."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def validate_dataset(filepath: Path) -> dict:
    allowed_intents = {
        "order_status",
        "delivery_issue",
        "delivery_dispute",
        "policy_question",
        "return_refund",
        "missing_information",
        "other",
    }
    allowed_actions = {"answer", "ask_customer", "escalate", "no_action"}
    allowed_routes = {"self_service", "customer_question", "human_review"}
    allowed_splits = {"development", "held_out"}

    seen_ids = set()
    counts = {
        "total": 0,
        "splits": {"development": 0, "held_out": 0},
        "routes": {"self_service": 0, "customer_question": 0, "human_review": 0},
        "intents": {},
    }

    errors = []

    with open(filepath, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as err:
                errors.append(f"Line {idx}: JSON parse error: {err}")
                continue

            cid = case.get("case_id")
            if not cid:
                errors.append(f"Line {idx}: Missing case_id")
                continue
            if cid in seen_ids:
                errors.append(f"Line {idx}: Duplicate case_id '{cid}'")
            seen_ids.add(cid)

            split = case.get("split")
            if split not in allowed_splits:
                errors.append(f"{cid}: Invalid split '{split}'")
            else:
                counts["splits"][split] += 1

            intent = case.get("expected_intent")
            if intent not in allowed_intents:
                errors.append(f"{cid}: Invalid expected_intent '{intent}'")
            counts["intents"][intent] = counts["intents"].get(intent, 0) + 1

            action = case.get("expected_action")
            if action not in allowed_actions:
                errors.append(f"{cid}: Invalid expected_action '{action}'")

            route = case.get("expected_route")
            if route not in allowed_routes:
                errors.append(f"{cid}: Invalid expected_route '{route}'")
            else:
                counts["routes"][route] += 1

            # Evidence reference integrity
            supplied_ids = {
                r.get("evidence_id")
                for r in case.get("order_records", [])
                if isinstance(r, dict) and "evidence_id" in r
            } | {
                p.get("evidence_id")
                for p in case.get("policy_evidence", [])
                if isinstance(p, dict) and "evidence_id" in p
            }

            for ref in case.get("expected_evidence_ids", []):
                if ref not in supplied_ids:
                    errors.append(
                        f"{cid}: Expected evidence '{ref}' not found in supplied order/policy records: {supplied_ids}"
                    )

            # Safety invariant checks
            if intent == "delivery_dispute" and route != "human_review":
                errors.append(f"{cid}: Delivery dispute MUST have expected_route='human_review'")

            if "money" in case.get("risk_tag", "") and route != "human_review":
                errors.append(f"{cid}: Financial/money risk MUST route to human_review")

            if "prompt_injection" in case.get("risk_tag", "") and route != "human_review":
                errors.append(f"{cid}: Prompt injection MUST route to human_review")

            counts["total"] += 1

    return {"errors": errors, "counts": counts}


def main() -> int:
    path = Path(__file__).resolve().parent.parent / "data" / "synthetic_cases.jsonl"
    print(f"Validating dataset at: {path}")

    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    result = validate_dataset(path)
    errors = result["errors"]
    counts = result["counts"]

    print("\nDataset Summary:")
    print(f"  Total Cases: {counts['total']}")
    print(f"  Splits: Development = {counts['splits']['development']}, Held-out = {counts['splits']['held_out']}")
    print(
        f"  Routes: Human Review = {counts['routes']['human_review']} ({counts['routes']['human_review']/counts['total']*100:.1f}%), "
        f"Self Service = {counts['routes']['self_service']} ({counts['routes']['self_service']/counts['total']*100:.1f}%), "
        f"Customer Question = {counts['routes']['customer_question']} ({counts['routes']['customer_question']/counts['total']*100:.1f}%)"
    )
    print("  Intents Breakdown:")
    for intent, count in sorted(counts["intents"].items()):
        print(f"    - {intent}: {count}")

    if errors:
        print(f"\nVALIDATION FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  [ERROR] {err}")
        return 1
    else:
        print("\nVALIDATION SUCCESS: All cases are 100% compliant with schema, uniqueness, citations, and safety rules.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
