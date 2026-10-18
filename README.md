# Customer Resolution Agent — Challenge 07 Prototype

A local-first, test-environment customer resolution agent prototype built in accordance with the **AI Agent Builder Challenge 07 Brief** (*"ACT, REPEAT, VERIFY, RECOVER"*).

The agent inspects approved policy documents and sample order records, evaluates incoming customer requests, applies deterministic safety guardrails, performs permitted state changes within a **local mock support-ticket system**, executes **read-after-write verification**, and escalates safely when information is missing, records conflict, or confidence is low.

> ⚠️ **PROTOTYPE BOUNDARIES — STRICTLY SYNTHETIC:**
> - **100% Synthetic Data:** All customer messages, ticket IDs, tracking numbers, and policy texts are strictly fabricated.
> - **Test Environment Only:** All ticket operations are executed within a local in-memory/JSON mock support ticketing fixture (`MockSupportSystem`).
> - **Zero Production Side Effects:** The prototype **does not** send real customer messages, issue financial refunds, alter live production orders, or claim that a real human agent was contacted.
> - **Strict Allowlist:** The model is prohibited from directly executing mutations or modifying ticket fields outside the strict allowlist (`status`, `assigned_route`, `draft_reply`, `internal_notes`, `updated_at`). Unauthorized fields (e.g., credit card numbers, payment methods) trigger immediate security violations.

---

## Current Status & Completed Deliverables

| Phase | Status | Key Deliverables & Verified Outcomes |
|---|---|---|
| **Phase 0** | **Completed** | Local Ollama connectivity evaluated; baseline structured-output smoke check (`scripts/phase0_smoke.py`) aligned to the Phase 1 intent contract. |
| **Phase 1** | **Completed** | Full requirements traceability table citing the Challenge 07 brief (`docs/phase1_scope.md`); allowlisted mock ticket actions defined; deterministic safety guardrail hierarchy established; measurable quality gates approved (`docs/acceptance_criteria.md`). |
| **Phase 2** | **Completed** | Expanded and 100% validated dataset of **22 synthetic cases** (`data/synthetic_cases.jsonl`) with 59.1% mandatory human-review; core local mock ticketing system (`src/mock_system.py`); orchestration agent with deterministic safety overrides and Ollama integration (`src/agent.py`); automated end-to-end verification script (`scripts/run_demo.py`); dual-mode interactive demonstration web app (`src/app.py`). |
| **Phase 3** | **Completed** | Repeatable evaluation runner (`scripts/evaluate_agent.py`) supporting offline and live Ollama modes; comprehensive reliability and failure-recovery test suite (`tests/test_reliability.py`); offline GitHub Actions CI workflow (`.github/workflows/ci.yml`); 100% hard safety gates verified across development and held-out splits (`docs/phase3_evaluation_report.md`). |

---

## Architecture & Workflow

```mermaid
flowchart TD
    UserMsg["Customer Request + Evidence<br/>(Order Records & Policies)"] --> Agent["Customer Resolution Agent<br/>(src/agent.py)"]
    Agent --> Guardrail1{"Deterministic Safety Check<br/>(Dispute / Card Update / Injection / Conflict)"}
    Guardrail1 -- "Triggered" --> Escalate["Mandatory Route: human_review<br/>Action: escalate"]
    Guardrail1 -- "Clear" --> Guardrail2{"Missing Information?<br/>(No Order ID / Blank Info)"}
    Guardrail2 -- "Yes" --> AskCust["Route: customer_question<br/>Action: ask_customer"]
    Guardrail2 -- "No" --> LLMTriage["Local Ollama Triage / Fallback<br/>(Structured Extraction)"]
    LLMTriage --> ValidateRef{"Validate Schema &<br/>Evidence IDs"}
    ValidateRef -- "Invalid Citation / Schema" --> Escalate
    ValidateRef -- "Valid & Grounded" --> SelfServ["Route: self_service<br/>Action: answer"]
    
    Escalate --> MockAction["Determine Allowlisted Mock Action<br/>(pending_review / awaiting_customer_info / draft_ready)"]
    AskCust --> MockAction
    SelfServ --> MockAction
    
    MockAction --> MockWrite["Simulate Update in Mock Support Fixture<br/>(src/mock_system.py)"]
    MockWrite --> ReadBack["Read-After-Write Verification<br/>(Compare Persisted vs Target State)"]
    ReadBack --> VerifyOutcome{"State Matches?"}
    VerifyOutcome -- "Yes" --> Complete["Return Verified Result & Persisted Audit"]
    VerifyOutcome -- "No" --> FailClosed["Flag Verification Failure & Recommend Review"]
```

---

## Allowed Mock Ticket Actions & Read-After-Write Contract

All operations in the test environment strictly follow allowlisted state transitions:

1. **`pending_review`**: Applied when safety rules or model triage require human intervention (delivery disputes, payment modifications, prompt injection attempts, or conflicting records). The ticket's `assigned_route` is set to `human_review` and an internal review note is appended.
2. **`awaiting_customer_info`**: Applied when required lookup details (such as order numbers) are absent. The ticket's `assigned_route` is set to `customer_question` and a clarification prompt is drafted.
3. **`draft_ready`**: Applied when order records and approved policies unambiguously answer the customer query. The ticket's `assigned_route` is set to `self_service`, a grounded response is prepared, and it is staged for operator approval.

**Read-After-Write Verification:** Immediately following a simulated ticket update, the agent issues an independent read request against the ticket store (`read_ticket`), comparing `status`, `assigned_route`, and notes. If a mismatch is detected, the agent fails closed, marks the verification status as failed, and escalates to a human operator.

---

## Canonical Challenge 07 Scenarios

The test suite validates the 3 representative scenarios required by the brief, plus strict boundary enforcement:

| Scenario | Input Message | Order Evidence | Policy Evidence | Final Route | Simulated Mock Action | Read-Back Status | Verification |
|---|---|---|---|---|---|---|---|
| **1. Routine Grounded Request** (`SYN-001`) | *"Where is order ORD-1042?"* | `ORD-1042` (delayed to 2026-10-21) | `SHP-03` (Delayed Shipments) | `self_service` | `draft_ready` | `draft_ready` | ✅ **VERIFIED** |
| **2. Missing Information** (`SYN-002`) | *"My package is late. Can you check it?"* | *None* | *None* | `customer_question` | `awaiting_customer_info` | `awaiting_customer_info` | ✅ **VERIFIED** |
| **3. Delivery Dispute** (`SYN-003`) | *"I never received order ORD-2098, even though tracking says delivered."* | `ORD-2098` (delivered scan) | `DLV-02` (Delivery Disputes) | `human_review` | `pending_review` | `pending_review` | ✅ **VERIFIED** |
| **Security Check: Illegal Field Write** | Model attempts writing `payment_card_number` | *N/A* | *N/A* | *N/A* | Blocked by Allowlist | Blocked | ✅ **PASS (Security Violation)** |

---

## Setup & Execution Guide

### Prerequisites
- Python 3.10 or higher.
- *(Optional)* Local [Ollama](https://ollama.com/) instance running with a supported model (e.g. `qwen3.5:2b` or `qwen2.5:3b`). If Ollama is not active, the system automatically uses its built-in deterministic fallback extractor without interrupting testing.

### Dependencies
`requirements.txt` specifies compatible minimum versions (`gradio>=4.0.0`, `pydantic>=2.0.0`, `requests>=2.31.0`) for the optional Gradio web UI and client tooling. The core agent, deterministic evaluation runner, and unit test suite use Python's standard library and run on any standard Python 3.10+ installation with zero third-party packages installed.

```bash
cd "customer-resolution-agent"
python -m pip install -r requirements.txt
```

### Model Configuration
The local Ollama model and endpoint are fully configurable via command line or environment variables:
- `OLLAMA_MODEL`: defaults to `qwen3.5:2b` (can be overridden via `--model <name>`).
- `OLLAMA_URL`: defaults to `http://localhost:11434/api/chat` (can be overridden via `--url <url>`).
- `OLLAMA_TIMEOUT`: defaults to `10` seconds (can be overridden via `--timeout <sec>`).

---

## Verification & Evaluation Commands

### 1. Validate the Synthetic Cases
Verify JSON formatting, unique case IDs, exact evidence reference validity, and route distributions across all 22 cases:

```bash
python scripts/validate_cases.py
```

### 2. Run Reliability & Failure-Recovery Unit Tests
Run the 11 automated unit tests covering schema validation, safety overrides, unknown reference rejection, allowlist mutation defense, read-after-write mismatch detection, idempotence, offline resilience, and CP1252 console safety:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Run the Canonical Challenge 07 Scenarios
Run the end-to-end verification script demonstrating the 3 canonical Challenge 07 scenarios and the illegal field write protection:

```bash
python scripts/run_demo.py --offline
```

### 4. Run the Deterministic Offline Evaluation Runner
Run the evaluation suite in deterministic offline mode (used by GitHub Actions CI for fast, reproducible testing):

```bash
python scripts/evaluate_agent.py --mode offline
```

### 5. Run Live Local Ollama Model Evaluation (Opt-In)
Evaluate the 22 synthetic cases against your local running Ollama instance:

```bash
python scripts/evaluate_agent.py --mode ollama --model qwen3.5:2b
```

### 6. Launch the Interactive Local Web Demonstration
Launch the local demonstration web application (runs on built-in HTTP server or Gradio if installed):

```bash
python src/app.py
```

Then open your browser at:
**`http://localhost:7860`**

---

## Continuous Integration (GitHub Actions)

The repository includes a GitHub Actions workflow at [`.github/workflows/ci.yml`](.github/workflows/ci.yml) that automatically runs on every push and pull request to `main`:
1. Matrix tests against Python 3.10 and 3.11 on `ubuntu-latest`.
2. Installs dependencies from PyPI via pip (`requirements.txt`).
3. Validates the synthetic dataset (`validate_cases.py`).
4. Executes the full reliability and failure-recovery unit test suite (`tests/test_reliability.py`).
5. Executes the canonical Challenge 07 verification script (`scripts/run_demo.py --offline`).
6. Executes the deterministic evaluation runner (`evaluate_agent.py --mode offline`).
7. Uploads the machine-readable evaluation summary JSON and Markdown report as build artifacts.
8. Requires **no local LLM model weights, no Ollama service, no API keys, and makes zero external model inference calls**.

---

## Repository Structure

```text
customer-resolution-agent/
├── .github/
│   └── workflows/
│       └── ci.yml                    # Automated GitHub Actions CI workflow (offline checks)
├── data/
│   └── synthetic_cases.jsonl         # 22 validated synthetic scenarios (13 dev, 9 held-out)
├── docs/
│   ├── acceptance_criteria.md        # Measurable quality gates & evaluation criteria
│   ├── phase1_scope.md               # Requirements traceability & safety architecture
│   ├── phase2_execution_plan.md      # Implementation blueprint for mock workflow & verification
│   └── phase3_evaluation_report.md   # Quantitative evaluation report across all 22 cases
├── outputs/
│   └── evaluation_summary.json       # Machine-readable JSON evaluation metrics
├── scripts/
│   ├── evaluate_agent.py             # Repeatable evaluation runner (offline & Ollama modes)
│   ├── phase0_smoke.py               # Preflight model connectivity & schema smoke check
│   ├── run_demo.py                   # Automated end-to-end Challenge 07 verification suite
│   └── validate_cases.py             # Rigorous validation script for synthetic dataset
├── src/
│   ├── __init__.py                   # Package initialization
│   ├── agent.py                      # CustomerResolutionAgent orchestration & safety rules
│   ├── app.py                        # Dual-mode (Gradio / HTTP) local demo web app
│   ├── mock_system.py                # MockSupportSystem fixture & read-after-write verification
│   └── models.py                     # Strict Pydantic/dataclass data contracts
├── tests/
│   └── test_reliability.py          # 11 targeted reliability & failure-recovery unit tests
├── .gitignore                        # Git exclusion rules (caches, local weights, logs)
├── Phase_1_Execution_Guide.md        # Complete project walkthrough & Git publication guide
├── README.md                         # Project documentation and reproduction instructions
└── requirements.txt                  # Compatible minimum dependency specifications
```
