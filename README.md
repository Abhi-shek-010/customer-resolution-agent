# Customer Resolution Agent — Challenge 07

A local-first, read-only prototype that helps a support agent triage routine order questions using supplied order records and approved policy text. It drafts grounded replies, asks for missing lookup information, and routes disputes or uncertain cases to human review.

> **Prototype boundaries:** All included examples are synthetic. The app does not contact customers, issue refunds, change orders, or create support tickets. A route is a recommendation for a human operator, not proof that a handoff occurred.

## Current status

- **Phase 0 (Completed)**: Local Ollama connectivity and structured-output smoke checks explored (`scripts/phase0_smoke.py`). Qwen3.5 2B is a provisional local baseline; deterministic application guardrails are established to override the model for mandatory safety routing.
- **Phase 1 (Completed & Frozen)**: Problem definition, 7-intent taxonomy, 3-route hierarchy, deterministic decision rules, JSON schema contracts, acceptance criteria, and 22 synthetic evaluation cases (13 dev, 9 held-out) verified and frozen.
- **Upcoming Phases**:
  - Phase 2: Domain policy expansion & full mock record fixture.
  - Phase 3: Deterministic guardrail layer & mock lookup engine.
  - Phase 4: Local Ollama integration & Gradio web interface.
  - Phase 5: Automated test evaluation & metrics reporting.
  - Phase 6: Release packaging & optional documentation page.

## Scope and project specifications

- [Phase 1 Execution Guide](Phase_1_Execution_Guide.md)
- [Phase 1 Scope & Architecture](docs/phase1_scope.md)
- [Acceptance Criteria & Quality Gates](docs/acceptance_criteria.md)
- [Synthetic Evaluation Dataset](data/synthetic_cases.jsonl)
- [Phase 0 Preflight Smoke Script](scripts/phase0_smoke.py)

## Planned local demo

The planned interface is a Gradio app whose Python backend calls Ollama on the same computer (`http://localhost:11434`). The browser UI will show the input, supplied synthetic evidence, proposed route, evidence references, and draft reply without executing any destructive side effects.

## Repository contents

```text
Customer Resolution Agent/
  data/
    synthetic_cases.jsonl        # 22 hand-authored synthetic test fixtures
  docs/
    acceptance_criteria.md       # Measurable functional, safety, and evaluation gates
    phase1_scope.md              # Scope definition, contract, intent map, and safety rules
  scripts/
    phase0_smoke.py              # Local Ollama structured output smoke test
  .gitignore                     # Standard Python, environment, and model ignore rules
  Phase_1_Execution_Guide.md     # Step-by-step phase execution instructions
  README.md                      # Project overview and roadmap
```

## How to publish to GitHub (When ready)

When you are ready to publish this local folder to a GitHub repository, run the following commands in PowerShell from the project folder:

```powershell
# 1. Initialize local Git repository
git init -b main

# 2. Stage all authored project files
git add .gitignore README.md Phase_1_Execution_Guide.md docs/ data/ scripts/

# 3. Create your initial commit
git commit -m "Complete Phase 1: Define customer resolution agent scope, contract, and test fixtures"

# 4. Link to your empty GitHub repository (create one on github.com first)
git remote add origin https://github.com/<your-username>/customer-resolution-agent.git

# 5. Push to GitHub
git push -u origin main
```

