# Phase 4 Deployment Guide & Architectural Specifications

## 1. Deployment Shape Analysis & Platform Comparison

This document analyzes the deployment options for the **Customer Resolution Agent (Challenge 07)**, establishes strict safety boundaries for public exposure, and specifies the deployment architecture.

### Platform Comparison Matrix

| Attribute | Option A: GitHub Pages (Recommended) | Option B: Hugging Face Spaces (Gradio) | Option C: Self-Hosted Cloud VM / Docker |
| :--- | :--- | :--- | :--- |
| **Hosting Model** | Static Documentation + Client-Side Offline Simulator | Containerized Python Gradio Application (`src/app.py`) | Containerized VM running Ollama + Python |
| **Official Platform Terms** | Free on GitHub Free plans for public repositories. Soft limit: 100 GB/month bandwidth, 10 builds/hour. | Free CPU-Basic tier (2 vCPU, 16 GB RAM). Spaces sleep after inactivity. | Paid compute (requires ongoing cloud billing for GPU/CPU). |
| **Inference Mode** | **Deterministic Offline Simulator** (Client-side JS mirroring `SafetyPolicyEngine`). | **Deterministic Offline Engine** (`HOSTED_MODE=true`, `SafetyPolicyEngine`). | Real model inference via hosted Ollama container. |
| **Security & Privacy Risk** | **Zero server-side risk.** Runs in visitor's browser sandbox. No credentials, tokens, or server compute exposed. | **Low.** Server runs Python app without persistence. Input length bounded (1000 chars); no logging. | **High risk.** High operational cost, potential prompt injection, GPU resource exhaustion, Ollama port exposure. |
| **Session Isolation** | **Complete.** Uses browser `sessionStorage` isolated per tab. Visitor mutations cannot affect other users. | **Complete.** Server-side thread-safe `SESSION_STORES` keyed by session UUID with 2-hour TTL eviction. | Requires complex multi-tenant queueing and state isolation. |
| **Local Ollama Port Exposure** | **None.** No connection to `localhost:11434`. | **None.** No connection to `localhost:11434`. | N/A. |
| **Maintenance & Longevity** | Zero maintenance. Indefinite uptime, no server dependencies. | Moderate. Python dependencies and Space awake/sleep lifecycle. | High. Container updates, cloud bills, security patches. |

---

## 2. Recommended Deployment Shape

### Primary Public Showcase: GitHub Pages (`docs/index.html`)
- **Recommendation**: Deploy `docs/index.html` via GitHub Pages.
- **Rationale**: Meets all student project constraints with zero recurring cost, zero server vulnerability surface, and complete reliability. It delivers a comprehensive project presentation (Challenge 07 objective, architecture, canonical cases, safety policies) and an embedded, browser-isolated deterministic simulator for interactive walkthroughs.
- **Inference Mode**: Clearly labeled as **Static Documentation & Offline Deterministic Simulator (No LLM in browser)**.

### Secondary Interactive Showcase: Hugging Face Spaces (Optional)
- **Recommendation**: Document the option to host `src/app.py` on Hugging Face Spaces under the Gradio SDK with environment variable `HOSTED_MODE=true`.
- **Inference Mode**: Clearly labeled as **Deterministic Offline Safety Policy Engine (No LLM hosted)**.
- **Inference Boundary**: The genuine model-backed experience remains exclusively the **local Ollama environment** (`ollama run qwen2.5:2b`), preserving privacy and eliminating hosting compute costs.

---

## 3. Threat Model & Safety Boundaries for Public Visitors

### 1. Prototype Notice & Synthetic Data Only
- The persistent banner: `PROTOTYPE - SYNTHETIC DATA ONLY. Fabricated records for testing.` is displayed prominently across all interfaces (public landing page, standalone app, Gradio app).
- No real customer names, real emails, payment credentials, or production APIs are included or reachable.

### 2. Visitor Session State Isolation
- **Mechanism**: Every visitor is assigned an ephemeral session identifier (UUIDv4).
- **Isolation Guarantee**: Mock ticket store (`MockTicketSystem`) instances are instantiated per session. If Visitor A modifies ticket `TCK-1001` or clicks "Reset", Visitor B's ticket `TCK-1001` remains completely unaltered in its seed state (`status="open"`).
- **TTL Eviction**: In server mode (`src/app.py`), sessions expire automatically after 2 hours of inactivity to prevent memory leaks.

### 3. Input Bounding & Zero Persistence
- Maximum customer message input length is enforced at **1,000 characters**.
- Visitor inputs are processed strictly in-memory for the duration of the request; they are **never written to disk, logged to permanent files, or sent to third-party endpoints**.

### 4. Deterministic Fail-Closed Safety Policy
- In hosted mode, all decisions flow through the `SafetyPolicyEngine`.
- Sensitive operations (delivery disputes, fraud claims, damaged goods, unauthorized changes) are deterministically routed to `human_review`.
- Mock ticket mutations are restricted to an allowlist of permitted fields (`status`, `assigned_route`, `draft_reply`, `internal_notes`, `updated_at`). Field values are validated against strict enums.

### 5. Localhost & Port Isolation
- The hosted applications never attempt to connect to `localhost:11434` or any visitor's local Ollama instance.
- Port 11434 is never forwarded or exposed publicly.

---

## 4. GitHub Actions Deployment Specifications

The GitHub Pages deployment is kept strictly isolated from the CI validation pipeline (`ci.yml`):
- **Workflow File**: `.github/workflows/deploy_pages.yml`
- **Trigger**: Manual trigger via `workflow_dispatch` (and optional release tagging), keeping public deployment disabled by default until the repository owner explicitly activates it.
- **Least Privilege Permissions**:
  ```yaml
  permissions:
    contents: read
    pages: write
    id-token: write
  ```
- **Deployment Artifact**: The static contents of the `docs/` directory (`index.html` and related documentation assets).
