---
title: Customer Resolution Agent
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.20.0
app_file: src/app.py
pinned: false
license: mit
short_description: Deterministic offline safety engine for tier-1 support inquiries
---

# Customer Resolution Agent Prototype (Hugging Face Space)

> ⚠️ **PROTOTYPE NOTICE — SYNTHETIC DATA ONLY**
>
> This hosted space runs in **Deterministic Offline Engine Mode (`HOSTED_MODE=true`)**.
> It demonstrates the strict safety policy engine, allowlisted mock mutations, and read-after-write verification on synthetic benchmark cases.
> **No live model weights or local Ollama instances are accessed by this hosted space.**

## Key Safety Controls
- **Session Isolation:** Each visitor is assigned an ephemeral session identifier. Mock ticket mutations in your session will not alter any other visitor's state.
- **Bounded Inputs:** Customer messages are capped at 1,000 characters and are never persisted or logged.
- **Allowlisted Mutations:** Only `status`, `assigned_route`, `draft_reply`, `internal_notes`, and `updated_at` can be altered on simulated mock tickets.

## Run with Real Model Inference
To experience the genuine model-backed experience with local Ollama (`qwen2.5:2b`), run the application locally:
```bash
git clone https://github.com/Abhi-shek-010/customer-resolution-agent.git
cd customer-resolution-agent
pip install -r requirements.txt
python src/app.py
```
