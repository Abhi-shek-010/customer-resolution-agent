# Challenge 07 — Project Execution & Git Publication Guide

This guide documents the audit of Phase 1 artifacts against the official **AI Agent Builder Challenge 07 Brief**, the implementation of the Phase 2 local mock support workflow, and reviewed, step-by-step instructions for publishing this repository to GitHub.

---

## 1. Executive Summary of Work Completed

### Phase 1 Audit & Scope Correction
- **Brief Alignment:** Addressed the core mandate from Challenge 07 Page 1 (*"ACT, REPEAT, VERIFY, RECOVER"*). A pure passive chatbot is insufficient. The agent must take permitted, simulated actions in a test environment, verify the state outcome, and recover gracefully when data is missing or confidence is low.
- **Traceability Table:** Updated `docs/phase1_scope.md` with an exhaustive traceability matrix categorizing brief-stated requirements, prototype implementation decisions, and verified assumptions.
- **Mock Support Ticket Actions:** Explicitly defined allowlisted mock ticket mutations (`draft_ready`, `awaiting_customer_info`, `pending_review`). Disallowed production mutations (no real customer messaging, refund transactions, or production order modifications).
- **Safety Priority Hierarchy:** Formulated a 4-tier deterministic guardrail engine:
  - **Priority 1 (Mandatory Escalation):** Delivery disputes, unauthorized payment/account mutations, prompt injections, and conflicting records strictly override model triage to `human_review` / `escalate`.
  - **Priority 2 (Missing Information):** Missing lookup identifiers route to `customer_question` / `ask_customer`.
  - **Priority 3 (Grounded Answer):** Clear, unambiguous records with matching approved policies route to `self_service` / `answer`.
  - **Priority 4 (Fail-Closed Default):** Schema parse errors, invalid evidence references, or unknown states route to `human_review`.
- **Read-After-Write Verification:** Implemented verification logic that inspects the persisted ticket record immediately after a simulated write. Any discrepancy flags a verification failure and prompts human review.
- **Acceptance Criteria:** Updated `docs/acceptance_criteria.md` with quantifiable quality gates (100% schema compliance, 100% safety routing, 0 unknown evidence citations, 100% allowlisted actions, 100% read-after-write verification, and >=90% routine accuracy).
- **Smoke Check Alignment:** Aligned `scripts/phase0_smoke.py` intents (`delivery_issue` and `delivery_dispute` added) and documented its status as a smoke check rather than a safety certification.

### Phase 2 Implementation & Dataset Reconciliation
- **Synthetic Cases Expansion:** Reconciled `data/synthetic_cases.jsonl` from 12 to **22 unique scenarios** (`SYN-001` through `SYN-022`), spanning 13 development cases and 9 held-out cases. 13 of 22 cases (59.1%) represent mandatory human review scenarios.
- **Dataset Validation Script:** Created `scripts/validate_cases.py` to cryptographically verify JSON integrity, unique case IDs, evidence reference validity, and safety routing compliance.
- **Execution Plan:** Authored `docs/phase2_execution_plan.md` defining data contracts, allowlisted field mutations, and error handling.
- **Mock Support System:** Implemented `src/mock_system.py` providing in-memory/JSON ticket management with an immutable field allowlist (`ALLOWED_TICKET_FIELDS = {"status", "assigned_route", "draft_reply", "internal_notes", "updated_at"}`).
- **Orchestration Agent:** Built `src/agent.py` integrating deterministic safety guardrails, local Ollama LLM triage with non-blocking alive probe, deterministic fallback parsing, simulated ticket writes, and read-after-write verification.
- **End-to-End Verification Suite:** Created `scripts/run_demo.py` demonstrating the 3 canonical Challenge 07 scenarios (Routine Grounded, Missing Info, Delivery Dispute) plus illegal field write protection.
- **Local Demonstration UI:** Built `src/app.py` featuring a dual-mode interface (Gradio with built-in zero-dependency HTTP server fallback) running locally on port 7860.

---

## 2. Verified Test Suite Results

Running `python scripts/run_demo.py` verifies all canonical Challenge 07 requirements:

| Scenario / Check | Customer Input | Final Route | Simulated Action | Verified Status | Result |
|---|---|---|---|---|---|
| **Scenario 1 (SYN-001)** | *"Where is order ORD-1042?"* | `self_service` | `draft_ready` | `draft_ready` | ✅ **100% VERIFIED** |
| **Scenario 2 (SYN-002)** | *"My package is late. Can you check it?"* | `customer_question` | `awaiting_customer_info` | `awaiting_customer_info` | ✅ **100% VERIFIED** |
| **Scenario 3 (SYN-003)** | *"I never received order ORD-2098, even though tracking says delivered."* | `human_review` | `pending_review` | `pending_review` | ✅ **100% VERIFIED** |
| **Security Check** | Unauthorized field: `payment_card_number` | Blocked | Blocked | N/A | ✅ **SECURITY VIOLATION** |

---

## 3. Step-by-Step Git Publication Walkthrough

When you are ready to publish this project to GitHub, execute the following commands in PowerShell from the project root:

### Step 1: Open Terminal in the Project Directory
```powershell
Set-Location 'C:\Users\abhi0\Desktop\Customer Resolution Agent'
```

### Step 2: Initialize Git Repository
```powershell
git init -b main
```

### Step 3: Inspect Staged / Untracked Files
Check the git status to confirm only authorized files are tracked and that temporary caches or large binaries are excluded via `.gitignore`:
```powershell
git status --short
```

Expected untracked files:
- `.gitignore`
- `README.md`
- `Phase_1_Execution_Guide.md`
- `requirements.txt`
- `data/synthetic_cases.jsonl`
- `docs/acceptance_criteria.md`
- `docs/phase1_scope.md`
- `docs/phase2_execution_plan.md`
- `scripts/phase0_smoke.py`
- `scripts/run_demo.py`
- `scripts/validate_cases.py`
- `src/__init__.py`
- `src/agent.py`
- `src/app.py`
- `src/mock_system.py`
- `src/models.py`

### Step 4: Stage Authorized Files
```powershell
git add .
```

Verify that no sensitive files (API keys, personal credentials, model weights, or scratch files) are staged:
```powershell
git diff --cached --stat
```

### Step 5: Create Initial Commit
```powershell
git commit -m "Implement Challenge 07 customer resolution agent prototype (Phase 1 & Phase 2)"
```

### Step 6: Create and Link Your GitHub Repository
1. Log into your GitHub account and create a new repository named `customer-resolution-agent`.
2. Leave the repository empty (do **not** check "Add README", "Add .gitignore", or "Choose a license", as these already exist).
3. Connect your local repository to GitHub by running (replace `<your-username>` with your GitHub handle):

```powershell
git remote add origin https://github.com/<your-username>/customer-resolution-agent.git
git branch -M main
git push -u origin main
```

---

## 4. How to Run the Local Demonstration

To start the interactive demonstration server locally:

```powershell
python src/app.py
```

Open your browser at **`http://localhost:7860`** to test all pre-configured Challenge 07 scenarios, observe simulated mock ticket updates in real time, and review persisted audit states with read-after-write verification.
