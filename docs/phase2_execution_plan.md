# Phase 2 Execution Plan — Local Mock Support System & Working Agent Workflow

## 1. Overview & Objective

Phase 2 builds the working local customer resolution workflow required by Challenge 07:
1. An agent that uses approved documents and sample records to understand customer requests.
2. Performs permitted simulated steps in a test environment (updating a mock support ticket).
3. Verifies the result via read-after-write comparison.
4. Escalate uncertainty, missing info, or safety triggers.

All operations run locally with synthetic fixtures. No real external APIs, CRM, payment, or emailing services are contacted.

---

## 2. Architecture & Component Blueprint

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Operator Interface (Gradio UI)                  │
│   • "Prototype — synthetic data only" Banner                           │
│   • Canonical Test Case Selector (SYN-001, SYN-002, SYN-003, Custom)  │
│   • Before/After Ticket State, Retrieved Evidence, Verified Action    │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│             CustomerResolutionAgent (src/agent.py)                     │
│                                                                        │
│  Step 1: Intake & Evidence Assembly                                   │
│    ├── Fetch Ticket, Order, and Policy evidence from mock fixture      │
│                                                                        │
│  Step 2: Model Assessment & Triage                                    │
│    ├── Calls local Ollama model (default: qwen3.5:2b)                 │
│    └── Fallback to local rule-based extractor if Ollama unavailable   │
│                                                                        │
│  Step 3: Schema & Reference Validation                                │
│    ├── Validates output format against Pydantic schema                │
│    └── Verifies all evidence_refs exist in supplied input              │
│                                                                        │
│  Step 4: Deterministic Guardrail Layer (Overrides Model)             │
│    ├── Delivery Dispute / Contradiction -> force human_review         │
│    ├── Financial / Account / Cancel -> force human_review             │
│    ├── Prompt Injection -> force human_review                         │
│    ├── Missing Lookup Info -> force customer_question                 │
│    └── Unambiguous & Grounded -> allow self_service                   │
│                                                                        │
│  Step 5: Simulated Action Selection                                   │
│    ├── self_service       -> draft_ready                              │
│    ├── customer_question  -> awaiting_customer_info                   │
│    └── human_review       -> pending_review                           │
│                                                                        │
│  Step 6: Execute Simulated Update on Mock Support System              │
│    └── Update strictly allowlisted fields (status, route, note, draft) │
│                                                                        │
│  Step 7: Read-After-Write Verification (VERIFY Requirement)           │
│    ├── Re-read ticket from store by ticket_id                          │
│    ├── Compare persisted fields with target state                     │
│    └── Status: VERIFIED or FAILED (with safety escalation)            │
│                                                                        │
│  Step 8: Structured Audit Log Entry                                   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 MockSupportSystem (src/mock_system.py)                 │
│   • Resettable synthetic database (Tickets, Orders, Policies)          │
│   • Strict field allowlist enforcement (rejects illegal field writes)  │
│   • Read ticket, update ticket, read-back verification                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Allowed Mock Ticket States & Transitions

| Initial Status | Target Mock Action | New Status | Assigned Route | Internal Note Content |
|---|---|---|---|---|
| `open` | `draft_ready` | `draft_ready` | `self_service` | Cites canonical evidence IDs (`ORD-*`, `SHP-*`) and attaches approved response draft. |
| `open` | `awaiting_customer_info` | `awaiting_customer_info` | `customer_question` | Records missing lookup identifiers required from customer. |
| `open` | `pending_review` | `pending_review` | `human_review` | Records explicit safety escalation reason (dispute, conflict, injection, refund). |

---

## 4. Verification & Fail-Closed Protocols

1. **Read-After-Write Check**:
   - Persisted `status`, `assigned_route`, and `internal_notes` are matched against expected values.
   - If equal: `verification_status="VERIFIED"`.
   - If unequal: `verification_status="FAILED"`, status forced to `pending_review`, draft cleared.
2. **Model Error / Timeout / Malformed Output**:
   - Automatically caught by orchestration layer.
   - Falls back safely to `human_review`, logs error to audit trail, and flags mock ticket for operator attention.
3. **Idempotency**:
   - Each execution receives a deterministic run token (`run_id`).
   - Re-running the same case produces consistent verified outcomes without corrupting existing records.

---

## 5. Implementation Roadmap & Deliverables

1. `src/models.py`: Data models and contracts.
2. `src/mock_system.py`: In-memory thread-safe mock ticketing and order store with strict field allowlist.
3. `src/agent.py`: Agent orchestrator with deterministic guardrails and read-after-write verification.
4. `src/app.py`: Gradio web demo with canonical scenario picker and clear audit view.
5. `scripts/run_demo.py`: Automated CLI runner demonstrating all 3 challenge scenarios end-to-end.
6. `requirements.txt`: Minimal pinned project dependencies.
