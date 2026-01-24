"""
Approval Gate - Hard gates requiring explicit human approval.

No progression in the pipeline without explicit approval events.
Gates are checkpoints where humans review and approve/reject artifacts.

Key concepts:
- Gate: A decision point requiring human input
- Approval: Explicit "yes" with optional feedback
- Rejection: Explicit "no" with required reason
- Auto-approve: For testing only, explicitly flagged
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Any
from uuid import uuid4


class ApprovalStatus(str, Enum):
    """Status of an approval gate."""
    
    PENDING = "pending"      # Waiting for human decision
    APPROVED = "approved"    # Human approved
    REJECTED = "rejected"    # Human rejected
    AUTO_APPROVED = "auto"   # Auto-approved (testing only)


@dataclass
class ApprovalEvent:
    """
    Record of an approval decision.
    
    Immutable once created - provides audit trail.
    """
    
    id: str
    gate_id: str
    status: ApprovalStatus
    decided_at: datetime
    decided_by: str  # user_id or "auto"
    
    # Feedback
    feedback: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Context
    artifact_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "gate_id": self.gate_id,
            "status": self.status.value,
            "decided_at": self.decided_at.isoformat(),
            "decided_by": self.decided_by,
            "feedback": self.feedback,
            "rejection_reason": self.rejection_reason,
            "artifact_ids": self.artifact_ids,
            "metadata": self.metadata,
        }


@dataclass
class Gate:
    """
    A single approval gate in the pipeline.
    
    Gates block progression until approved.
    """
    
    id: str
    name: str
    description: str
    stage: str  # Which pipeline stage this gates
    
    # What to show for approval
    artifact_types: list[str]  # Types of artifacts to review
    
    # State
    status: ApprovalStatus = ApprovalStatus.PENDING
    events: list[ApprovalEvent] = field(default_factory=list)
    
    # Callbacks (set by orchestrator)
    on_approve: Optional[Callable[["Gate"], None]] = None
    on_reject: Optional[Callable[["Gate", str], None]] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stage": self.stage,
            "artifact_types": self.artifact_types,
            "status": self.status.value,
            "events": [e.to_dict() for e in self.events],
        }


class ApprovalGate:
    """
    Manages approval gates for the pipeline.
    
    Provides:
    - Gate registration
    - Approval/rejection handling
    - Blocking until approval
    - Audit trail of all decisions
    """
    
    # Standard gates for shorts factory
    GATE_SCRIPT = "script_approval"
    GATE_EVIDENCE_URLS = "evidence_urls_approval"
    GATE_SCREENSHOTS = "screenshots_approval"
    GATE_RENDER = "render_approval"
    
    def __init__(
        self,
        auto_approve: bool = False,
        approval_handler: Optional[Callable[[Gate], ApprovalStatus]] = None,
    ):
        """
        Initialize the approval gate manager.
        
        Args:
            auto_approve: If True, auto-approve all gates (testing only)
            approval_handler: Callback to get approval decision.
                             If None, gates block until explicit approve/reject call.
        """
        self._gates: dict[str, Gate] = {}
        self._auto_approve = auto_approve
        self._approval_handler = approval_handler
        
        # Initialize standard gates
        self._init_standard_gates()
    
    def _init_standard_gates(self) -> None:
        """Initialize the standard gates for shorts factory."""
        self.register_gate(Gate(
            id=self.GATE_SCRIPT,
            name="Script Approval",
            description="Review and approve the generated script before evidence gathering",
            stage="script",
            artifact_types=["script"],
        ))
        
        self.register_gate(Gate(
            id=self.GATE_EVIDENCE_URLS,
            name="Evidence URLs Approval",
            description="Review and approve the discovered evidence URLs before capture",
            stage="investigate",
            artifact_types=["evidence_url", "search_query"],
        ))
        
        self.register_gate(Gate(
            id=self.GATE_SCREENSHOTS,
            name="Screenshots Approval",
            description="Review and approve captured screenshots before render",
            stage="capture",
            artifact_types=["screenshot", "screenshot_bundle"],
        ))
        
        self.register_gate(Gate(
            id=self.GATE_RENDER,
            name="Render Approval",
            description="Final approval before video render",
            stage="render",
            artifact_types=["render_manifest"],
        ))
    
    def register_gate(self, gate: Gate) -> None:
        """Register a gate."""
        self._gates[gate.id] = gate
    
    def get_gate(self, gate_id: str) -> Optional[Gate]:
        """Get a gate by ID."""
        return self._gates.get(gate_id)
    
    def get_pending_gates(self) -> list[Gate]:
        """Get all gates that are pending approval."""
        return [g for g in self._gates.values() if g.status == ApprovalStatus.PENDING]
    
    def request_approval(
        self,
        gate_id: str,
        artifact_ids: list[str],
        metadata: dict[str, Any] = None,
    ) -> ApprovalStatus:
        """
        Request approval at a gate.
        
        If auto_approve is True, immediately returns APPROVED.
        If approval_handler is set, calls it and returns result.
        Otherwise, returns PENDING (caller must call approve/reject later).
        
        Args:
            gate_id: ID of the gate
            artifact_ids: Artifacts being submitted for approval
            metadata: Additional context for reviewer
        
        Returns:
            Current status after request.
        """
        gate = self._gates.get(gate_id)
        if not gate:
            raise ValueError(f"Gate {gate_id} not found")
        
        # Auto-approve mode (testing)
        if self._auto_approve:
            return self.approve(gate_id, "auto", artifact_ids, metadata)
        
        # Handler mode (interactive)
        if self._approval_handler:
            status = self._approval_handler(gate)
            if status == ApprovalStatus.APPROVED:
                return self.approve(gate_id, "handler", artifact_ids, metadata)
            elif status == ApprovalStatus.REJECTED:
                return self.reject(gate_id, "handler", "Rejected by handler", artifact_ids, metadata)
        
        # Blocking mode - return pending, wait for explicit call
        return ApprovalStatus.PENDING
    
    def approve(
        self,
        gate_id: str,
        approved_by: str,
        artifact_ids: list[str] = None,
        metadata: dict[str, Any] = None,
        feedback: str = None,
    ) -> ApprovalStatus:
        """
        Approve a gate.
        
        Args:
            gate_id: ID of the gate
            approved_by: Who approved (user_id)
            artifact_ids: Artifacts being approved
            metadata: Additional context
            feedback: Optional feedback from reviewer
        
        Returns:
            APPROVED status.
        """
        gate = self._gates.get(gate_id)
        if not gate:
            raise ValueError(f"Gate {gate_id} not found")
        
        status = ApprovalStatus.AUTO_APPROVED if approved_by == "auto" else ApprovalStatus.APPROVED
        
        event = ApprovalEvent(
            id=f"event_{uuid4().hex[:8]}",
            gate_id=gate_id,
            status=status,
            decided_at=datetime.now(),
            decided_by=approved_by,
            feedback=feedback,
            artifact_ids=artifact_ids or [],
            metadata=metadata or {},
        )
        
        gate.status = status
        gate.events.append(event)
        
        # Call callback if set
        if gate.on_approve:
            gate.on_approve(gate)
        
        return status
    
    def reject(
        self,
        gate_id: str,
        rejected_by: str,
        reason: str,
        artifact_ids: list[str] = None,
        metadata: dict[str, Any] = None,
    ) -> ApprovalStatus:
        """
        Reject a gate.
        
        Args:
            gate_id: ID of the gate
            rejected_by: Who rejected (user_id)
            reason: Required reason for rejection
            artifact_ids: Artifacts being rejected
            metadata: Additional context
        
        Returns:
            REJECTED status.
        """
        gate = self._gates.get(gate_id)
        if not gate:
            raise ValueError(f"Gate {gate_id} not found")
        
        if not reason:
            raise ValueError("Rejection reason is required")
        
        event = ApprovalEvent(
            id=f"event_{uuid4().hex[:8]}",
            gate_id=gate_id,
            status=ApprovalStatus.REJECTED,
            decided_at=datetime.now(),
            decided_by=rejected_by,
            rejection_reason=reason,
            artifact_ids=artifact_ids or [],
            metadata=metadata or {},
        )
        
        gate.status = ApprovalStatus.REJECTED
        gate.events.append(event)
        
        # Call callback if set
        if gate.on_reject:
            gate.on_reject(gate, reason)
        
        return ApprovalStatus.REJECTED
    
    def reset_gate(self, gate_id: str) -> None:
        """Reset a gate to pending (for retry after rejection)."""
        gate = self._gates.get(gate_id)
        if gate:
            gate.status = ApprovalStatus.PENDING
    
    def is_approved(self, gate_id: str) -> bool:
        """Check if a gate is approved."""
        gate = self._gates.get(gate_id)
        return gate is not None and gate.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.AUTO_APPROVED
        )
    
    def can_proceed_to(self, stage: str) -> tuple[bool, list[str]]:
        """
        Check if all prerequisite gates for a stage are approved.
        
        Args:
            stage: Target stage to proceed to
        
        Returns:
            (can_proceed, blocking_gates) tuple.
        """
        stage_order = ["script", "investigate", "capture", "render"]
        
        if stage not in stage_order:
            return True, []
        
        target_idx = stage_order.index(stage)
        blocking = []
        
        for gate in self._gates.values():
            if gate.stage in stage_order:
                gate_idx = stage_order.index(gate.stage)
                if gate_idx < target_idx and gate.status == ApprovalStatus.PENDING:
                    blocking.append(gate.id)
        
        return len(blocking) == 0, blocking
    
    def summary(self) -> dict:
        """Get a summary of all gates."""
        return {
            "gates": {g.id: g.to_dict() for g in self._gates.values()},
            "pending": [g.id for g in self.get_pending_gates()],
            "auto_approve": self._auto_approve,
        }
