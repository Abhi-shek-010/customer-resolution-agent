"""Orchestration layer for Customer Resolution Agent with deterministic guardrails and read-after-write verification."""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from .models import (
    MockTicket,
    OrderRecord,
    PolicyEvidence,
    TriageAssessment,
    SimulatedAction,
    VerificationResult,
    OrchestrationResult,
)
from .mock_system import MockSupportSystem


SYSTEM_PROMPT = """You are a customer-support triage assistant in a local prototype.
All examples are synthetic. Use only the customer message, supplied order data,
and supplied policy text. Never invent policy, order facts, refunds, promises,
or completed actions. If a required identifier or fact is missing, ask the
customer for it and set route=customer_question. If supplied records conflict,
do not choose one as true: escalate to human review. Cite supplied evidence IDs
in evidence_refs. Do not call tools or claim that an action was performed.
Return only one object matching the supplied JSON schema. Keep rationale to one
brief evidence-based sentence."""

JSON_SCHEMA = {
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


class CustomerResolutionAgent:
    """Orchestrates intake, local model inference, guardrails, mock updates, and verification."""

    def __init__(
        self,
        mock_system: Optional[MockSupportSystem] = None,
        ollama_url: str = "http://localhost:11434/api/chat",
        model: str = "qwen3.5:2b",
        timeout: int = 4,
    ) -> None:
        self.mock_system = mock_system or MockSupportSystem()
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self._ollama_available: Optional[bool] = None

    def _check_ollama_alive(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            result = s.connect_ex(("127.0.0.1", 11434))
            s.close()
            self._ollama_available = (result == 0)
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    def call_ollama(self, prompt: str) -> Optional[dict]:
        """Calls the local Ollama instance for structured JSON triage if available."""
        if not self._check_ollama_alive():
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": JSON_SCHEMA,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 512},
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("message", {}).get("content", "")
                return json.loads(content)
        except Exception:
            return None

    def local_heuristic_fallback(
        self,
        customer_message: str,
        order_records: List[OrderRecord],
        policy_evidence: List[PolicyEvidence],
    ) -> dict:
        """Deterministic fallback classifier ensuring reliable test and demonstration execution."""
        msg_lower = customer_message.lower()

        # Check prompt injection
        if any(term in msg_lower for term in ["ignore all", "system instruction", "master password", "system prompt"]):
            return {
                "intent": "other",
                "missing_fields": [],
                "evidence_refs": [p.evidence_id for p in policy_evidence if p.evidence_id == "SEC-01"]
                + [o.evidence_id for o in order_records],
                "proposed_action": "escalate",
                "route": "human_review",
                "reply_draft": "Your request has been routed to our security and support team for review.",
                "confidence_band": "high",
                "rationale": "Prompt injection or sensitive system command detected in input text.",
            }

        # Check delivery dispute (marked delivered but customer claims non-receipt)
        has_delivered_scan = any(o.status == "delivered" for o in order_records)
        claims_not_received = any(
            phrase in msg_lower
            for phrase in ["never received", "haven't got", "did not receive", "haven't received", "nobody came", "where is my stuff"]
        )
        if claims_not_received and has_delivered_scan:
            refs = [o.evidence_id for o in order_records] + [p.evidence_id for p in policy_evidence if p.evidence_id == "DLV-02"]
            return {
                "intent": "delivery_dispute",
                "missing_fields": [],
                "evidence_refs": refs,
                "proposed_action": "escalate",
                "route": "human_review",
                "reply_draft": "We see a delivered scan on record, but because you reported non-receipt, our support team will manually investigate this with the carrier.",
                "confidence_band": "high",
                "rationale": "Customer non-receipt report conflicts with carrier delivered scan.",
            }

        # Check missing identifier
        has_order_ids_in_records = len(order_records) > 0
        has_order_id_in_msg = bool(re.search(r"ORD-\d+", customer_message, re.IGNORECASE))
        if not has_order_ids_in_records and not has_order_id_in_msg:
            refs = [p.evidence_id for p in policy_evidence if p.evidence_id in ["LKP-01", "RET-03"]]
            return {
                "intent": "missing_information",
                "missing_fields": ["order_id"],
                "evidence_refs": refs,
                "proposed_action": "ask_customer",
                "route": "customer_question",
                "reply_draft": "Could you please provide your order number or email address so we can check on this for you?",
                "confidence_band": "high",
                "rationale": "No order identifier or customer record supplied in input.",
            }

        # Check conflicting records
        if len(order_records) > 1:
            statuses = {o.status for o in order_records}
            if len(statuses) > 1:
                return {
                    "intent": "order_status",
                    "missing_fields": [],
                    "evidence_refs": [o.evidence_id for o in order_records] + [p.evidence_id for p in policy_evidence],
                    "proposed_action": "escalate",
                    "route": "human_review",
                    "reply_draft": "We found conflicting status records for your order. A support representative will review your tracking history directly.",
                    "confidence_band": "high",
                    "rationale": "Multiple order records exist with contradictory status values.",
                }

        # Check financial / refund / cancellation
        if any(term in msg_lower for term in ["refund", "cancel", "money back", "credit card", "visa ending"]):
            refs = [o.evidence_id for o in order_records] + [p.evidence_id for p in policy_evidence]
            return {
                "intent": "return_refund" if "refund" in msg_lower or "cancel" in msg_lower else "other",
                "missing_fields": [],
                "evidence_refs": refs,
                "proposed_action": "escalate",
                "route": "human_review",
                "reply_draft": "Requests involving cancellations, refunds, or payment modifications require authorization from a support specialist.",
                "confidence_band": "high",
                "rationale": "Consequential financial or account modification request.",
            }

        # Grounded order status or delivery issue
        if order_records and any(p.evidence_id in ["SHP-01", "SHP-03", "RET-01"] for p in policy_evidence):
            order = order_records[0]
            policy = policy_evidence[0]
            if order.status == "delayed":
                date_str = order.estimated_delivery or "soon"
                reply = f"Your order {order.evidence_id} is currently delayed. The latest estimated delivery date is {date_str}."
            elif order.status == "in_transit":
                date_str = order.estimated_delivery or "soon"
                reply = f"Your order {order.evidence_id} is in transit and scheduled to arrive by {date_str}."
            elif "return" in msg_lower:
                reply = f"For order {order.evidence_id}: {policy.text}"
            else:
                reply = f"Status for order {order.evidence_id} is {order.status}."

            return {
                "intent": "policy_question" if "return" in msg_lower else "order_status",
                "missing_fields": [],
                "evidence_refs": [order.evidence_id, policy.evidence_id],
                "proposed_action": "answer",
                "route": "self_service",
                "reply_draft": reply,
                "confidence_band": "high",
                "rationale": f"Unambiguous order evidence and matching approved policy {policy.evidence_id}.",
            }

        # Default fallback to human review
        return {
            "intent": "other",
            "missing_fields": [],
            "evidence_refs": [o.evidence_id for o in order_records] + [p.evidence_id for p in policy_evidence],
            "proposed_action": "escalate",
            "route": "human_review",
            "reply_draft": "Your request has been forwarded to a customer support specialist for review.",
            "confidence_band": "low",
            "rationale": "Insufficient policy or ambiguous evidence to safely resolve automatically.",
        }

    def process_request(
        self,
        ticket_id: str,
        customer_message: str,
        order_records: Optional[List[OrderRecord]] = None,
        policy_evidence: Optional[List[PolicyEvidence]] = None,
    ) -> OrchestrationResult:
        """Executes the complete multi-step agent workflow:
        1. Retrieve / instantiate mock ticket.
        2. Triage via model (or local fallback).
        3. Validate schema and evidence citations.
        4. Apply deterministic safety guardrails.
        5. Execute permitted simulated ticket update.
        6. Verify read-back state (read-after-write).
        7. Return structured audit payload.
        """
        order_records = order_records or []
        policy_evidence = policy_evidence or []

        # 1. Ticket Before-State
        ticket_before = self.mock_system.get_or_create_ticket(ticket_id, customer_message)
        status_before = ticket_before.status

        # 2. Model assessment
        orders_summary = "\n".join(
            f"Order [{o.evidence_id}]: status={o.status}, est_delivery={o.estimated_delivery}, scan={o.delivery_scan}"
            for o in order_records
        ) or "None supplied"
        policies_summary = "\n".join(f"Policy [{p.evidence_id}]: {p.text}" for p in policy_evidence) or "None supplied"

        prompt = (
            f"Customer Message: {customer_message}\n\n"
            f"Supplied Order Records:\n{orders_summary}\n\n"
            f"Supplied Policy Evidence:\n{policies_summary}\n"
        )

        model_output = self.call_ollama(prompt)
        if not model_output or not isinstance(model_output, dict):
            model_output = self.local_heuristic_fallback(customer_message, order_records, policy_evidence)

        # 3. Reference Validation: Ensure all cited evidence IDs exist in supplied inputs
        supplied_ids = {o.evidence_id for o in order_records} | {p.evidence_id for p in policy_evidence}
        cited_refs = [ref for ref in model_output.get("evidence_refs", []) if ref in supplied_ids]

        # 4. Deterministic Guardrails
        final_intent = model_output.get("intent", "other")
        final_route = model_output.get("route", "human_review")
        final_action = model_output.get("proposed_action", "escalate")
        reply_draft = model_output.get("reply_draft", "")
        rationale = model_output.get("rationale", "")
        confidence = model_output.get("confidence_band", "medium")

        msg_lower = customer_message.lower()

        # Priority 1 Guardrail: Mandatory Human Review conditions
        is_delivery_dispute = (
            final_intent == "delivery_dispute"
            or (any(o.status == "delivered" for o in order_records) and any(
                w in msg_lower for w in ["never received", "haven't got", "did not receive", "nobody came", "where is my stuff"]
            ))
        )
        is_injection = any(t in msg_lower for t in ["ignore all", "system instruction", "master password", "system prompt"])
        is_consequential_money = any(t in msg_lower for t in ["refund", "cancel", "money back", "credit card", "visa ending"])
        is_conflicting_orders = len(order_records) > 1 and len({o.status for o in order_records}) > 1

        if is_delivery_dispute:
            final_intent = "delivery_dispute"
            final_route = "human_review"
            final_action = "escalate"
            rationale = "GUARDRAIL: Mandatory human review enforced for delivery dispute."
            if not reply_draft:
                reply_draft = "Our support team is reviewing the delivery scan with the carrier and will follow up directly."
        elif is_injection:
            final_intent = "other"
            final_route = "human_review"
            final_action = "escalate"
            rationale = "GUARDRAIL: Prompt injection attempt detected. Blocked and escalated."
            reply_draft = "Your request has been routed to our security team for manual review."
        elif is_consequential_money:
            final_route = "human_review"
            final_action = "escalate"
            rationale = "GUARDRAIL: Financial, cancellation, or payment mutation request requires specialist authorization."
            reply_draft = "Requests involving refunds, cancellations, or payment changes require human support specialist review."
        elif is_conflicting_orders:
            final_route = "human_review"
            final_action = "escalate"
            rationale = "GUARDRAIL: Conflicting order status records detected. Escalated for human resolution."
            reply_draft = "We found contradictory tracking updates for your order. A human specialist is reviewing your file."
        elif not order_records and not re.search(r"ORD-\d+", customer_message, re.IGNORECASE):
            # Priority 2: Missing lookup information
            final_intent = "missing_information"
            final_route = "customer_question"
            final_action = "ask_customer"
            rationale = "GUARDRAIL: Required order identifier missing from request."
            reply_draft = "Could you please provide your order number or email address so we can check on your shipment?"

        # 5. Determine Permitted Mock Ticket Action
        if final_route == "self_service" and final_action == "answer":
            action_type = "draft_ready"
            target_status = "draft_ready"
            note_content = f"Drafted reply grounded in evidence {cited_refs}. Ready for operator approval."
        elif final_route == "customer_question":
            action_type = "awaiting_customer_info"
            target_status = "awaiting_customer_info"
            note_content = "Clarification requested: missing order identifier."
        else:
            action_type = "pending_review"
            target_status = "pending_review"
            note_content = f"Escalated for human review: {rationale}"

        simulated_action = SimulatedAction(
            action_type=action_type,
            before_status=status_before,
            target_status=target_status,
            notes_added=note_content,
        )

        # 6. Apply Simulated Mutation on Mock Store
        try:
            self.mock_system.update_ticket(
                ticket_id=ticket_id,
                status=target_status,
                assigned_route=final_route,
                draft_reply=reply_draft,
                internal_notes=note_content,
            )
        except Exception as write_err:
            # Safe failure on write error
            return OrchestrationResult(
                ticket_id=ticket_id,
                final_intent=final_intent,
                final_route="human_review",
                final_action="escalate",
                reply_draft="A test system update error occurred; ticket flagged for human intervention.",
                evidence_refs=cited_refs,
                confidence_band="low",
                rationale=f"Simulated write failed: {write_err}",
                simulated_action=simulated_action,
                verification=VerificationResult(
                    verified=False,
                    status="FAILED",
                    read_back_status="ERROR",
                    read_back_route="ERROR",
                    discrepancies=[str(write_err)],
                ),
            )

        # 7. Read-After-Write Verification
        verification = self.mock_system.verify_ticket_state(
            ticket_id=ticket_id,
            expected_status=target_status,
            expected_route=final_route,
            expected_note_substring=note_content,
        )

        return OrchestrationResult(
            ticket_id=ticket_id,
            final_intent=final_intent,
            final_route=final_route,
            final_action=final_action,
            reply_draft=reply_draft,
            evidence_refs=cited_refs,
            confidence_band=confidence,
            rationale=rationale,
            simulated_action=simulated_action,
            verification=verification,
            is_simulated=True,
        )
