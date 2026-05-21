from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SafetyFlags(BaseModel):
    crisis: bool = False
    self_harm: bool = False
    medication: bool = False
    unsafe_output: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)


class StageDetectionRecord(BaseModel):
    previous_stage: str = ""
    current_stage: str = ""
    stage_transition: Literal["STAY", "ADVANCE", "REGRESS", "RESET"] = "STAY"
    stage_completion_status: Literal["not_started", "in_progress", "ready_to_advance", "completed"] = "in_progress"
    stage_confidence: float = 0.0
    stage_evidence: list[str] = Field(default_factory=list)
    stage_transition_reason: str = ""
    stage_goal: str = ""


class PeerDraft(BaseModel):
    sender: Literal["peer_mirror_agent", "veteran_peer_agent"]
    contribution_type: str = "NONE"
    therapeutic_function: str = ""
    yalom_factor: str = "NONE"
    text: str = ""
    reason: str = ""
    confidence: float = 0.0
    safety_risk: bool = False
    typing_time_ms: int = 3000


class PeerContributionDecision(BaseModel):
    sender: Literal["peer_mirror_agent", "veteran_peer_agent"]
    decision: Literal["CONTRIBUTE", "NO_CONTRIBUTION"] = "NO_CONTRIBUTION"
    reason: str = ""
    yalom_factor: str = "NONE"
    confidence: float = 0.0
    safety_risk: bool = False


class TherapistDraftDecision(BaseModel):
    sender: Literal["peer_mirror_agent", "veteran_peer_agent"]
    action: Literal["include", "rewrite", "discard"] = "discard"
    reason: str = ""
    rewritten_text: str = ""
