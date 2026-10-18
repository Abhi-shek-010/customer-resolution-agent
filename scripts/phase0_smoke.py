r"""Local-only Phase 0 smoke check for the Customer Resolution Agent.

Requires Ollama running locally and a model already pulled. Uses only synthetic
examples. It never executes tools or performs customer/account actions.

Example:
    python .\scripts\phase0_smoke.py --model qwen3.5:2b
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request


API_URL = "http://localhost:11434/api/chat"

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "order_status",
                "delivery_issue",
                "delivery_dispute",
                "policy_question",
                "return_refund",
                "missing_information",
                "other",
            ],
        },
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "proposed_action": {
            "type": "string",
            "enum": ["answer", "ask_customer", "escalate", "no_action"],
        },
        "route": {
            "type": "string",
            "enum": ["self_service", "customer_question", "human_review"],
        },
        "reply_draft": {"type": "string"},
        "confidence_band": {"type": "string", "enum": ["low", "medium", "high"]},
        "rationale": {"type": "string"},
    },
    "required": [
        "intent",
        "missing_fields",
        "evidence_refs",
        "proposed_action",
        "route",
        "reply_draft",
        "confidence_band",
        "rationale",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a customer-support triage assistant in a local prototype.
All examples are synthetic. Use only the customer message, supplied order data,
and supplied policy text. Never invent policy, order facts, refunds, promises,
or completed actions. If a required identifier or fact is missing, ask the
customer for it and set route=customer_question. If supplied records conflict,
do not choose one as true: escalate to human review. Cite supplied evidence IDs
in evidence_refs. Do not call tools or claim that an action was performed.
Return only one object matching the supplied JSON schema. Keep rationale to one
brief evidence-based sentence; do not provide hidden chain-of-thought."""

TEST_CASES = [
    {
        "name": "known_order_answer",
        "expected_action": "answer",
        "expected_route": "self_service",
        "required_refs": ["ORD-1042", "SHP-03"],
        "input": """Customer message: Where is order ORD-1042?
Order record [ORD-1042]: status=delayed; updated=2026-10-17; estimated delivery=2026-10-21.
Policy [SHP-03]: For a delayed shipment, share the latest estimate. Do not promise compensation.
Classify and draft a concise customer reply using only this evidence.""",
    },
    {
        "name": "missing_order_identifier",
        "expected_action": "ask_customer",
        "expected_route": "customer_question",
        "required_refs": [],
        "input": """Customer message: My package is late. Can you check it?
No order record, order number, email address, or other lookup information was supplied.
Identify what is missing and draft the next safe reply.""",
    },
    {
        "name": "conflicting_delivery_evidence",
        "expected_action": "escalate",
        "expected_route": "human_review",
        "required_refs": ["ORD-2098"],
        "input": """Customer message: I did not receive my package.
Order record [ORD-2098]: status=delivered; delivery scan=2026-10-16.
The customer statement and delivery record conflict. No proof-of-delivery detail or further policy was supplied.
Do not decide which statement is correct. Route this safely and draft a concise reply.""",
    },
]


def post_json(url: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_output(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["response is not a JSON object"]

    required = set(SCHEMA["required"])
    actual = set(value)
    if missing := required - actual:
        errors.append(f"missing fields: {', '.join(sorted(missing))}")
    if extra := actual - required:
        errors.append(f"unexpected fields: {', '.join(sorted(extra))}")

    enums = {
        "intent": set(SCHEMA["properties"]["intent"]["enum"]),
        "proposed_action": set(SCHEMA["properties"]["proposed_action"]["enum"]),
        "route": set(SCHEMA["properties"]["route"]["enum"]),
        "confidence_band": set(SCHEMA["properties"]["confidence_band"]["enum"]),
    }
    for key, allowed in enums.items():
        if key in value and value[key] not in allowed:
            errors.append(f"{key} has invalid value: {value[key]!r}")

    for key in ("missing_fields", "evidence_refs"):
        if key in value and (
            not isinstance(value[key], list)
            or any(not isinstance(item, str) for item in value[key])
        ):
            errors.append(f"{key} must be a list of strings")
    for key in ("reply_draft", "rationale"):
        if key in value and not isinstance(value[key], str):
            errors.append(f"{key} must be a string")
    return errors


def run_case(model: str, case: dict, timeout: int) -> tuple[bool, float]:
    prompt = (
        f"Return one JSON object matching this schema:\n{json.dumps(SCHEMA)}\n\n"
        f"Case:\n{case['input']}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "format": SCHEMA,
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 512},
    }

    print(f"\nRunning {case['name']}; waiting for the local model...", flush=True)
    start = time.perf_counter()
    response = post_json(API_URL, payload, timeout)
    elapsed = time.perf_counter() - start
    message = response.get("message", {})
    content = message.get("content", "")

    print(f"\n=== {case['name']} ({elapsed:.2f}s) ===")
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        print("SCHEMA/JSON: FAIL — model content could not be parsed as JSON")
        thinking = message.get("thinking") or ""
        if thinking:
            print(f"A separate thinking field was returned ({len(thinking)} characters); its contents are not displayed.")
        print("Raw content:")
        print(content)
        return False, elapsed

    schema_errors = validate_output(value)
    schema_ok = not schema_errors
    action_ok = value.get("proposed_action") == case["expected_action"]
    route_ok = value.get("route") == case["expected_route"]
    refs_text = "\n".join(
        item for item in value.get("evidence_refs", []) if isinstance(item, str)
    )
    missing_refs = [
        ref
        for ref in case["required_refs"]
        if not re.search(rf"(?<![A-Za-z0-9]){re.escape(ref)}(?![A-Za-z0-9])", refs_text, re.IGNORECASE)
    ]
    refs_ok = not missing_refs

    print(f"JSON/schema: {'PASS' if schema_ok else 'FAIL'}")
    if schema_errors:
        for error in schema_errors:
            print(f"  - {error}")
    print(
        f"Expected action ({case['expected_action']}): "
        f"{'PASS' if action_ok else 'REVIEW'} — got {value.get('proposed_action')!r}"
    )
    print(
        f"Expected route ({case['expected_route']}): "
        f"{'PASS' if route_ok else 'REVIEW'} — got {value.get('route')!r}"
    )
    print(
        "Required evidence references: PASS"
        if refs_ok
        else f"Required evidence references: REVIEW — missing {', '.join(missing_refs)}"
    )
    print("Model output:")
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return schema_ok and action_ok and route_ok and refs_ok, elapsed


def check_tool_call(model: str, timeout: int) -> bool:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_order",
                "description": "Read-only lookup in a mock order system. This preflight does not execute it.",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            },
        }
    ]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "When an order ID is supplied, request the lookup_order tool exactly once. Do not invent or state lookup results. The tool call is only being inspected and will not be executed.",
            },
            {"role": "user", "content": "Please look up order ORD-1042."},
        ],
        "tools": tools,
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 256},
    }
    print("\nRunning tool_call_probe; waiting for the local model...", flush=True)
    response = post_json(API_URL, payload, timeout)
    calls = response.get("message", {}).get("tool_calls") or []
    valid = False
    for call in calls:
        function = call.get("function", {})
        arguments = function.get("arguments", {})
        if function.get("name") == "lookup_order" and arguments.get("order_id") == "ORD-1042":
            valid = True
            break
    print("\n=== tool_call_probe ===")
    print(f"Tool-call structure: {'PASS' if valid else 'REVIEW'}")
    print("No tool was executed.")
    print(json.dumps(calls, indent=2, ensure_ascii=False))
    return valid


def main() -> int:
    global API_URL
    parser = argparse.ArgumentParser(description="Run local synthetic Phase 0 model checks.")
    parser.add_argument("--model", default="qwen3.5:2b", help="Exact local Ollama model tag")
    parser.add_argument("--url", default=API_URL, help="Local Ollama chat API URL")
    parser.add_argument("--timeout", type=int, default=180, help="Per-request timeout in seconds")
    parser.add_argument("--skip-tools", action="store_true", help="Skip the non-executing tool-call probe")
    args = parser.parse_args()

    API_URL = args.url

    print(f"Model: {args.model}")
    print(f"Endpoint: {API_URL}")
    print("Data: synthetic examples only")
    print("Actions: no tools or customer actions will be executed")

    try:
        results = [run_case(args.model, case, args.timeout) for case in TEST_CASES]
        tool_ok = True if args.skip_tools else check_tool_call(args.model, args.timeout)
    except urllib.error.URLError as error:
        print("\nCould not reach the local Ollama API.")
        print("Confirm Ollama is installed and running, and that the model tag has been pulled.")
        print(f"Details: {error}")
        return 2
    except TimeoutError:
        print("\nThe request timed out. Try a smaller model or increase --timeout.")
        return 2
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"\nUnexpected API response: {error}")
        return 2

    passed = sum(1 for ok, _ in results if ok)
    total_time = sum(seconds for _, seconds in results)
    print(f"\nSummary: {passed}/{len(results)} behavior cases passed; text checks took {total_time:.2f}s total.")
    if not args.skip_tools:
        print(f"Tool-call probe: {'PASS' if tool_ok else 'REVIEW'}")
    print("Treat any REVIEW as a prompt/model investigation item; this smoke check is not a safety certification.")
    return 0 if passed == len(results) and tool_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
