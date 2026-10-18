"""Data models and typed contracts for the Customer Resolution Agent."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class OrderRecord:
    evidence_id: str
    status: str
    updated: Optional[str] = None
    delivery_scan: Optional[str] = None
    estimated_delivery: Optional[str] = None
    delivered_date: Optional[str] = None
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PolicyEvidence:
    evidence_id: str
    text: str
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class MockTicket:
    ticket_id: str
    customer_id: str
    subject: str
    message: str
    status: str = "open"  # open, draft_ready, awaiting_customer_info, pending_review
    assigned_route: str = "unassigned"  # unassigned, self_service, customer_question, human_review
    draft_reply: str = ""
    internal_notes: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def copy(self) -> MockTicket:
        return MockTicket(
            ticket_id=self.ticket_id,
            customer_id=self.customer_id,
            subject=self.subject,
            message=self.message,
            status=self.status,
            assigned_route=self.assigned_route,
            draft_reply=self.draft_reply,
            internal_notes=self.internal_notes,
            updated_at=self.updated_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TriageAssessment:
    intent: str
    missing_fields: List[str]
    evidence_refs: List[str]
    proposed_action: str
    route: str
    reply_draft: str
    confidence_band: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimulatedAction:
    action_type: str  # draft_ready, awaiting_customer_info, pending_review
    before_status: str
    target_status: str
    notes_added: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    verified: bool
    status: str  # VERIFIED, FAILED
    read_back_status: str
    read_back_route: str
    discrepancies: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestrationResult:
    ticket_id: str
    final_intent: str
    final_route: str
    final_action: str
    reply_draft: str
    evidence_refs: List[str]
    confidence_band: str
    rationale: str
    simulated_action: SimulatedAction
    verification: VerificationResult
    is_simulated: bool = True
    raw_model_proposal: Optional[Dict[str, Any]] = None
    triage_proposal: Optional[Dict[str, Any]] = None
    schema_valid: bool = True
    schema_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "ticket_id": self.ticket_id,
            "final_intent": self.final_intent,
            "final_route": self.final_route,
            "final_action": self.final_action,
            "reply_draft": self.reply_draft,
            "evidence_refs": self.evidence_refs,
            "confidence_band": self.confidence_band,
            "rationale": self.rationale,
            "simulated_action": self.simulated_action.to_dict(),
            "verification": self.verification.to_dict(),
            "is_simulated": self.is_simulated,
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
        }
        if self.raw_model_proposal is not None:
            payload["raw_model_proposal"] = self.raw_model_proposal
        if self.triage_proposal is not None:
            payload["triage_proposal"] = self.triage_proposal
        return payload
