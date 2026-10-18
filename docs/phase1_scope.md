# Phase 1 Scope & Architecture — Customer Resolution Agent

## 1. Document Status & Purpose

This document freezes the Phase 1 problem definition, requirements traceability, allowed simulated actions, routing hierarchy, and contracts for the Customer Resolution Agent. It defines simulated actions, safety guardrails, and verification contracts.

---

## 2. Requirements Traceability Matrix

| Source / Level | Requirement | Reference | Satisfying Mechanism / Artifact | Status |
|---|---|---|---|---|
| **Core Spec** | Multi-step agent doing real useful work using tools, not just answering | Core Mission | Mock ticket lookup, policy retrieval, structured triage, simulated ticket update, and read-after-write verification in local Python architecture. | **Confirmed** |
| **Core Spec** | Understand request using approved documents & sample records | Core Specification | Explicitly supplied synthetic order records (`ORD-*`) and policy documents (`SHP-*`, `RET-*`, `DLV-*`, `SEC-*`). | **Confirmed** |
| **Core Spec** | Perform permitted steps in a test environment | ACT Standard | Local mock ticket system allowing strict status/note updates (`draft_ready`, `awaiting_customer_info`, `pending_review`). | **Confirmed** |
| **Core Spec** | Verify the result | VERIFY Standard | Read-after-write verification comparing persisted ticket state against intended update. Mismatch fails closed. | **Confirmed** |
| **Core Spec** | Escalate when information is missing or confidence is low | RECOVER Standard | Missing info routes to `customer_question`; low confidence, disputes, or contradictions route to `human_review`. | **Confirmed** |
| **Core Spec** | Repeat on new input | REPEAT Standard | Parameterized test suite & interactive Gradio interface executing across 22 synthetic scenarios without code change. | **Confirmed** |
| **Core Spec** | Deliverables: prototype, short demo, 3 test cases, brief user/problem note | Project Deliverables | Web UI, 3 canonical test cases, `docs/`, `scripts/`, `README.md`. | **Confirmed** |
| **Project Decision** | Local-first inference via Ollama | Team Decision | Local inference against open-weight model (`qwen3.5:2b` baseline) with deterministic fallback; no external LLM APIs. | **Confirmed** |
| **Project Decision** | Strictly isolated synthetic mock system | Team Decision | In-memory / JSON ticket store with allowlisted fields only. No real CRM, customer messaging, or payment integrations. | **Confirmed** |
| **Project Decision** | 7-Intent / 3-Route / 4-Action Taxonomy | Team Decision | Fixed Pydantic / JSON schema ensuring deterministic post-processing and guardrails. | **Confirmed** |
| **Assumption (Open)** | Model quantization and host hardware performance | Team Assumption | Hardware-dependent cold/warm latency to be measured in Phase 4/5. | **Open** |
| **Assumption (Open)** | Optional fine-tuning (LoRA) or hosted web space | Team Assumption | To be considered only if baseline evaluation reveals persistent gaps. | **Open** |

---

## 3. Project Objective & Persona

- **Mission**: Build an AI customer resolution agent for a frontline customer-support operator. The agent relieves the operator of routine repetitive lookups by inspecting synthetic order records, applying approved store policies, proposing grounded draft replies, updating the mock ticket to the correct lifecycle status in a test environment, and verifying the write.
- **Boundaries**: All operations run in a local test fixture. The prototype is explicitly marked: **"Prototype — synthetic data only"**. It does not contact customers, issue financial refunds, mutate real customer accounts, or claim a human has been contacted in the real world.

---

## 4. Permitted Mock Actions (Test Environment)

The agent operates on a local mock support ticket. To satisfy the core requirement that *"an agent must act and verify"*, the agent is permitted to perform exactly three strictly allowlisted simulated mutations on the mock ticket:

1. **`draft_ready`**:
   - **Trigger**: Safe, unambiguous request with full evidence and policy support (`self_service` / `answer`).
   - **Simulated Ticket Update**: Sets `status="draft_ready"`, `assigned_route="self_service"`, attaches the verified `reply_draft`, and logs canonical evidence citations in internal notes.
2. **`awaiting_customer_info`**:
   - **Trigger**: Lookup identifier or essential detail missing, with no safety risk (`customer_question` / `ask_customer`).
   - **Simulated Ticket Update**: Sets `status="awaiting_customer_info"`, `assigned_route="customer_question"`, records missing fields in internal notes, and attaches the clarifying question.
3. **`pending_review`**:
   - **Trigger**: Delivery dispute, conflicting records, missing policy, financial refund/cancellation request, prompt injection, or low confidence (`human_review` / `escalate`).
   - **Simulated Ticket Update**: Sets `status="pending_review"`, `assigned_route="human_review"`, records the explicit risk rationale in internal notes, and blocks automated resolution.

**Strict Allowlist Constraint**: The mock ticket system strictly rejects any write targeting fields outside `status`, `assigned_route`, `draft_reply`, and `internal_notes`. Modifying customer email, billing information, or payment amounts is strictly prohibited by code.

---

## 5. Route & Action Hierarchy (Deterministic Safety Guardrails)

The local language model provides structured classification, but **deterministic application code enforces the final route and action**. The model is never permitted to bypass safety gates or execute tools directly.

```text
Priority 1: Mandatory Human Review (Safety & Policy Invariants)
├── Trigger conditions:
│   ├── Delivery disputes (e.g. marked delivered but customer reports non-receipt)
│   ├── Conflicting or ambiguous order records
│   ├── Missing, contradictory, or absent policy evidence
│   ├── Consequential actions (refunds, cancellations, address/payment changes)
│   └── Prompt injection or system instruction manipulation
└── Outcome: route = human_review | proposed_action = escalate | mock_action = pending_review
    (Cannot be overridden by model confidence or missing lookup information)

Priority 2: Missing Information
├── Trigger conditions:
│   ├── Required lookup identifier (e.g. order number) missing
│   └── No Priority 1 safety issue present
└── Outcome: route = customer_question | proposed_action = ask_customer | mock_action = awaiting_customer_info

Priority 3: Grounded Self-Service
├── Trigger conditions:
│   ├── Intent is supported and evidence is complete and unambiguous
│   ├── Approved policy explicitly permits the draft response
│   └── Every cited evidence ID exists in the supplied case
└── Outcome: route = self_service | proposed_action = answer | mock_action = draft_ready

Priority 4: Fail-Closed Exception Handling
├── Trigger conditions:
│   ├── Model JSON parse error or schema invalidity
│   ├── Unknown evidence IDs cited
│   ├── Read-after-write verification mismatch
│   └── Low confidence or unexpected exception
└── Outcome: route = human_review | proposed_action = escalate | mock_action = pending_review
    (Simulated action reports verification failure; no draft is approved)
```

---

## 6. Read-After-Write Verification (VERIFY Requirement)

To satisfy the brief's mandatory **VERIFY** standard:
1. When a mock ticket action is commanded (`draft_ready`, `awaiting_customer_info`, or `pending_review`), the system applies the update via the mock storage layer.
2. The agent immediately re-queries the ticket by its ID (`read_ticket(ticket_id)`).
3. The returned record's `status`, `assigned_route`, and `internal_notes` are compared directly against the expected post-condition.
4. **Verification Outcome**:
   - **`VERIFIED`**: Persisted state matches expected state exactly.
   - **`FAILED`**: Any mismatch, unpersisted change, or storage exception. The agent logs an audit alert, marks `verification_status="FAILED"`, and flags the ticket for emergency human review.

---

## 7. Supported Intents Taxonomy

| Intent | Description | Default Route | Allowed Mock Action |
|---|---|---|---|
| `order_status` | Inquiry regarding order progress, shipment tracking, or delivery date | `self_service` (if grounded) | `draft_ready` (or `pending_review` if conflict) |
| `delivery_issue` | Inquiry about shipment in transit or transit delays | `self_service` (if grounded) | `draft_ready` (or `pending_review` if dispute) |
| `delivery_dispute` | Claim of non-receipt after tracking marked delivered | `human_review` (Mandatory) | `pending_review` |
| `policy_question` | Questions on return windows, shipping guidelines, or store rules | `self_service` (if grounded) | `draft_ready` (or `pending_review` if missing policy) |
| `return_refund` | Request for refund, replacement, or return processing | `human_review` (Mandatory for funds) | `pending_review` |
| `missing_information`| Customer request lacking order number, email, or item details | `customer_question` | `awaiting_customer_info` |
| `other` | Out-of-scope requests, account changes, adversarial prompts | `human_review` | `pending_review` |

---

## 8. Data Contracts

### 8.1 Input Payload

```json
{
  "ticket_id": "TCK-1001",
  "customer_message": "Where is order ORD-1042?",
  "order_records": [
    {
      "evidence_id": "ORD-1042",
      "status": "delayed",
      "updated": "2026-10-17",
      "estimated_delivery": "2026-10-21"
    }
  ],
  "policy_evidence": [
    {
      "evidence_id": "SHP-03",
      "text": "For a delayed shipment, share the latest estimate. Do not promise compensation."
    }
  ]
}
```

### 8.2 Model Triage Output (Internal)

```json
{
  "intent": "order_status",
  "missing_fields": [],
  "evidence_refs": ["ORD-1042", "SHP-03"],
  "proposed_action": "answer",
  "route": "self_service",
  "reply_draft": "Your order ORD-1042 is delayed. The latest estimated delivery date is October 21, 2026.",
  "confidence_band": "high",
  "rationale": "Grounded in supplied order status and shipping policy SHP-03."
}
```

### 8.3 Final Orchestration & Verification Output (Operator & UI)

```json
{
  "ticket_id": "TCK-1001",
  "final_intent": "order_status",
  "final_route": "self_service",
  "final_action": "answer",
  "reply_draft": "Your order ORD-1042 is delayed. The latest estimated delivery date is October 21, 2026.",
  "evidence_refs": ["ORD-1042", "SHP-03"],
  "confidence_band": "high",
  "rationale": "Grounded in supplied order status and shipping policy SHP-03.",
  "simulated_action": {
    "action_type": "draft_ready",
    "before_status": "open",
    "target_status": "draft_ready"
  },
  "verification": {
    "verified": true,
    "status": "VERIFIED",
    "read_back_status": "draft_ready",
    "timestamp": "2026-10-18T15:10:00Z"
  },
  "is_simulated": true
}
```
