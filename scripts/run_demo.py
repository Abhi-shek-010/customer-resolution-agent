"""Automated verification script demonstrating the 3 canonical scenarios end-to-end."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on consoles when supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import OrderRecord, PolicyEvidence
from src.mock_system import MockSupportSystem
from src.agent import CustomerResolutionAgent


def run_scenario(agent: CustomerResolutionAgent, name: str, ticket_id: str, message: str, orders: list, policies: list):
    print("=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)

    # Before State
    ticket_before = agent.mock_system.read_ticket(ticket_id)
    print(f"1. BEFORE STATE [Ticket {ticket_id}]:")
    print(f"   Status: {ticket_before.status}")
    print(f"   Assigned Route: {ticket_before.assigned_route}")
    print(f"   Internal Notes: {ticket_before.internal_notes}")
    print(f"\n2. INPUT CUSTOMER MESSAGE:\n   \"{message}\"")

    if orders:
        print("\n   SUPPLIED ORDER EVIDENCE:")
        for o in orders:
            print(f"     - [{o.evidence_id}] Status: {o.status}, Scan: {o.delivery_scan}, Est: {o.estimated_delivery}")
    else:
        print("\n   SUPPLIED ORDER EVIDENCE: None")

    if policies:
        print("\n   SUPPLIED POLICY EVIDENCE:")
        for p in policies:
            print(f"     - [{p.evidence_id}] {p.text}")
    else:
        print("\n   SUPPLIED POLICY EVIDENCE: None")

    # Execute Workflow
    result = agent.process_request(
        ticket_id=ticket_id,
        customer_message=message,
        order_records=orders,
        policy_evidence=policies,
    )

    print("\n3. AGENT TRIAGE & SAFETY GUARDRAIL DECISION:")
    print(f"   Intent: {result.final_intent}")
    print(f"   Final Route: {result.final_route}")
    print(f"   Final Action: {result.final_action}")
    print(f"   Cited Evidence IDs: {result.evidence_refs}")
    print(f"   Rationale: {result.rationale}")
    print(f"   Draft Reply: \"{result.reply_draft}\"")

    print("\n4. SIMULATED MOCK TICKET UPDATE (Test Environment Only):")
    print(f"   Action Type: {result.simulated_action.action_type}")
    print(f"   Status Transition: '{result.simulated_action.before_status}' -> '{result.simulated_action.target_status}'")
    print(f"   Note Appended: \"{result.simulated_action.notes_added}\"")

    print("\n5. READ-AFTER-WRITE VERIFICATION:")
    print(f"   Verification Status: {result.verification.status}")
    print(f"   Verified: {result.verification.verified}")
    print(f"   Read-Back Status: {result.verification.read_back_status}")
    print(f"   Read-Back Route: {result.verification.read_back_route}")
    if result.verification.discrepancies:
        print(f"   Discrepancies: {result.verification.discrepancies}")

    ticket_after = agent.mock_system.read_ticket(ticket_id)
    print(f"\n6. PERSISTED AFTER-STATE [Ticket {ticket_id}]:")
    print(f"   Status: {ticket_after.status}")
    print(f"   Route: {ticket_after.assigned_route}")
    print(f"   Draft Reply: {ticket_after.draft_reply}")
    print(f"   Internal Notes: {ticket_after.internal_notes}")
    print(f"   Updated At: {ticket_after.updated_at}\n")

    return result.verification.verified


def test_illegal_write_protection(agent: CustomerResolutionAgent):
    print("=" * 80)
    print("TEST: Strict Allowlist & Security Boundary Check")
    print("=" * 80)
    try:
        agent.mock_system.update_ticket("TCK-1001", payment_card_number="4111222233334444")
        print("[FAIL] Illegal write was permitted!")
        return False
    except ValueError as e:
        print(f"[PASS] Illegal write correctly blocked: {e}\n")
        return True


def main():
    parser = argparse.ArgumentParser(description="Run canonical verification scenarios.")
    parser.add_argument("--offline", action="store_true", help="Force deterministic offline fallback without network probing.")
    args = parser.parse_args()

    mode_label = "OFFLINE" if args.offline else "AUTO"
    print(f"\nRunning Customer Resolution Agent -- Verification Suite (Mode: {mode_label})\n")
    mock_system = MockSupportSystem()
    agent = CustomerResolutionAgent(mock_system=mock_system, use_ollama=not args.offline)

    # Scenario 1: Routine Grounded Request
    ok1 = run_scenario(
        agent=agent,
        name="Scenario 1 - Routine Grounded Order Status (SYN-001)",
        ticket_id="TCK-1001",
        message="Where is order ORD-1042?",
        orders=[
            OrderRecord(evidence_id="ORD-1042", status="delayed", updated="2026-10-17", estimated_delivery="2026-10-21")
        ],
        policies=[
            PolicyEvidence(evidence_id="SHP-03", text="For a delayed shipment, share the latest estimate. Do not promise compensation.")
        ],
    )

    # Scenario 2: Missing Information
    ok2 = run_scenario(
        agent=agent,
        name="Scenario 2 - Missing Lookup Information (SYN-002)",
        ticket_id="TCK-1002",
        message="My package is late. Can you check it?",
        orders=[],
        policies=[],
    )

    # Scenario 3: Delivery Dispute
    ok3 = run_scenario(
        agent=agent,
        name="Scenario 3 - Delivery Dispute Requiring Mandatory Review (SYN-003)",
        ticket_id="TCK-1003",
        message="I never received order ORD-2098, even though tracking says delivered.",
        orders=[
            OrderRecord(evidence_id="ORD-2098", status="delivered", delivery_scan="2026-10-16")
        ],
        policies=[
            PolicyEvidence(evidence_id="DLV-02", text="A reported non-receipt after a delivered scan requires manual investigation.")
        ],
    )

    # Security Check
    ok_sec = test_illegal_write_protection(agent)

    all_passed = ok1 and ok2 and ok3 and ok_sec
    print("=" * 80)
    print(f"OVERALL RESULT: {'ALL CHECKS PASSED (100%)' if all_passed else 'SOME CHECKS FAILED'}")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
