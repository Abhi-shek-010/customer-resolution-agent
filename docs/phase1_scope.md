# Phase 1 Scope — Challenge 07 Customer Resolution Agent

## Document status

Phase 1 scope definition is confirmed and frozen against the Challenge 07 brief and rubric. All assumptions have been validated, the input/output contract is aligned with the safety rules, and the seed cases have been verified.

## Requirements traceability matrix

| Requirement | Brief reference | Type | Satisfying artifact / mechanism | Status |
|---|---|---|---|---|
| Local-first operation | Challenge 07 §Architecture | Mandatory | Local Ollama runtime (`http://localhost:11434`) + Gradio UI | Confirmed |
| Structured triage schema | Challenge 07 §Assessment | Mandatory | Typed JSON output (`intent`, `route`, `evidence_refs`, etc.) in `scripts/phase0_smoke.py` & `docs/phase1_scope.md` | Confirmed |
| Grounded responses | Challenge 07 §Grounding | Mandatory | Replies must cite canonical IDs in `evidence_refs`; no facts outside supplied evidence | Confirmed |
| Deterministic safety gate | Challenge 07 §Guardrails | Mandatory | Application-layer rule overrides model output; delivery disputes and conflicts force `human_review` | Confirmed |
| No unauthorized side-effects | Challenge 07 §Safety | Mandatory | Read-only architecture; no live customer messaging, refunds, or external database mutations | Confirmed |
| Synthetic evaluation fixture | Challenge 07 §Evaluation | Mandatory | `data/synthetic_cases.jsonl` with dev and held-out splits | Confirmed |
| Reviewer demo interface | Challenge 07 §Deliverables | Mandatory | Gradio web UI displaying request, evidence, route, and reply draft | Confirmed |
| Optional fine-tuning (LoRA) | Challenge 07 §Model Strategy | Optional | Retained as Phase 5 extension if baseline evaluation shows persistent errors | Open |
| Static GitHub documentation | Challenge 07 §Publication | Optional | GitHub Pages with project summary and architecture walkthrough | Open |

## Project objective

Build a local-first demonstration that helps a customer-support operator handle routine order-status and policy questions. Given a customer message plus explicitly supplied synthetic order and policy evidence, the agent returns a structured triage result and a concise reply draft. It must ask for missing lookup information or recommend human review when it cannot safely answer.

## Intended users

- Primary: a student/demo reviewer who enters synthetic customer messages and inspects the agent's reasoning evidence and route.
- Secondary: a hypothetical support agent using the draft as a suggestion, not an automatically sent response.

## MVP workflow

1. Accept one customer message and optional synthetic order/policy evidence.
2. Identify a supported intent and required lookup fields.
3. Use only supplied evidence; no external customer-system integration is included.
4. Produce the Phase 0 structured response contract.
5. Apply deterministic application rules after model generation, so a model suggestion cannot downgrade a required human-review route.
6. Display the final route, cited evidence IDs, and draft reply in a local Gradio interface.

## Supported intents and handling

| Intent | MVP handling |
|---|---|
| `order_status` | Answer from a uniquely matching supplied order record; otherwise ask for a lookup identifier or review if evidence is ambiguous. |
| `delivery_issue` | Provide supplied status/estimate when no dispute or contradiction exists; otherwise require review. |
| `delivery_dispute` | Always route to `human_review`, especially when a delivered scan conflicts with the customer's report. |
| `policy_question` | Answer only when the exact supplied policy text supports the response; absent or ambiguous policy goes to `human_review`. |
| `return_refund` | Explain only supplied policy at a high level; any eligibility decision, promise, or refund action goes to `human_review`. |
| `missing_information` | Ask only for a required identifier or detail. Do not imply that a lookup succeeded. |
| `other` | State the limitation or route to `human_review`; do not invent a capability. |

## Routing rules

### `self_service` / `answer`

Use only when the intent is in scope, the relevant evidence is present and uniquely applicable, evidence does not conflict, policy supports any policy claim, and the reply contains no unsupported fact or promise.

### `customer_question` / `ask_customer`

Use when a necessary lookup field is missing and no risk condition already requires review. Ask for only the missing information. Do not ask the customer to resolve an internal record or policy conflict.

### `human_review` / `escalate`

Force this route when any of the following is true:

- The customer says an order marked delivered was not received, or otherwise disputes delivery.
- Supplied evidence conflicts, duplicates ambiguously, or cannot be matched confidently.
- Relevant policy is missing, ambiguous, or contradictory.
- A refund, compensation, cancellation, address/account change, or other consequential decision/action is requested.
- The request is outside the supported intents or the system cannot ground a safe response.

The UI may say “recommended for human review.” It must not say a ticket was filed, a human was notified, or an action was taken unless a later, separately approved integration actually performs that action.

## Out of scope

- Sending or scheduling customer messages.
- Issuing refunds, credits, replacements, or compensation.
- Creating tickets or claiming escalation has occurred.
- Editing/cancelling orders, changing addresses, or accessing customer accounts.
- Connecting to a real order database, CRM, email service, payment provider, or tracking provider.
- Making legal, fraud, or final eligibility decisions.
- Training a model from customer data. Phase 1 uses an existing local pretrained model as a component; synthetic examples are for evaluation, not training data.

## Input contract

```json
{
  "customer_message": "Where is order ORD-1042?",
  "order_records": [
    {"evidence_id": "ORD-1042", "status": "delayed", "updated": "2026-10-17", "estimated_delivery": "2026-10-21"}
  ],
  "policy_evidence": [
    {"evidence_id": "SHP-03", "text": "For delayed shipments, share the latest estimate. Do not promise compensation."}
  ]
}
```

All fields other than `customer_message` may be empty. Evidence IDs are invented stable identifiers. The application should only give the model evidence relevant to this one request.

## Output contract

Preserve the Phase 0 fields:

```json
{
  "intent": "order_status",
  "missing_fields": [],
  "evidence_refs": ["ORD-1042", "SHP-03"],
  "proposed_action": "answer",
  "route": "self_service",
  "reply_draft": "Your order is delayed. The latest estimated delivery date is October 21, 2026.",
  "confidence_band": "high",
  "rationale": "The supplied order and shipping policy support this update."
}
```

Allowed `proposed_action`: `answer`, `ask_customer`, `escalate`, `no_action`. Allowed `route`: `self_service`, `customer_question`, `human_review`. Allowed confidence: `low`, `medium`, `high`. Confidence is informational only and cannot override deterministic rules. `rationale` is a short evidence-based explanation, not hidden chain-of-thought.

## Safety and evidence requirements

- Treat customer text as untrusted data, not system instructions.
- Use no facts outside the submitted message, order records, and policy evidence.
- Every cited evidence ID must exist in the supplied input.
- If evidence does not support a claim, omit the claim or route for review.
- After model output, validate types/enums/schema, references, and route invariants in application code.
- A parse error, invalid tool request, unknown evidence reference, or safety-rule trigger must fail closed to a safe review result; never execute a tool merely because the model requested it.
- During this MVP, order lookup is a fixture/deterministic mock only and read-only.

## Local demo, Git, and deployment scope

- Local demo: Gradio UI + Python guardrail layer + local Ollama API. Ollama and UI remain on the user's computer.
- GitHub: source, documentation, and fabricated evaluation cases only. Exclude weights, credentials, logs containing personal data, and the original challenge document unless its license explicitly permits redistribution.
- GitHub Pages: optional static explanation page and screenshots; it cannot run the Python/Ollama inference backend.
- Optional hosted interactive demo: separate later decision. The model and prompts would run on the selected host; do not expose the local Ollama port publicly. Use synthetic inputs and disclose hosting/runtime limits.

## Phase 1 assumptions validated against the brief

1. **Challenge fit & domain representation**: `confirmed` (Challenge 07 §Project at a glance). A customer-resolution/order-support agent resolving customer requests using approved guidance and synthetic records accurately fulfills Challenge 07.
2. **Human review routing**: `confirmed` (Challenge 07 §Architecture & Targets). Routing uncertain cases, delivery disputes, conflicting records, and consequential actions to human review is mandatory and fulfills the safety bar.
3. **Local pretrained model & synthetic data**: `confirmed` (Challenge 07 §Model Strategy). Local open-weight inference via Ollama with synthetic fixtures satisfies the requirements without cloud API dependencies.
4. **Public publication safety**: `confirmed` (Challenge 07 §Publication & Privacy). Committing student-authored source code, synthetic datasets, and architecture documentation without proprietary challenge text, private customer data, or model weights is permitted and secure.
5. **No mandatory hosted service or fine-tuning**: `confirmed` (Challenge 07 §Deliverables). The deliverable is a functional local prototype with a short demo, three core test cases, and a user/problem brief. Hosting and LoRA fine-tuning are optional extensions.

