from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engine.blackboard.route_response_validator import validate_therapist_response
from ai_engine.blackboard.yalom_persona_contract import route_peer_allowed


@dataclass(frozen=True)
class SupervisorAudit:
    valid: bool
    route_locked: bool
    stage_locked: bool
    technique_valid: bool
    peer_use_valid: bool
    safety_valid: bool
    notes: list[str]

    def model_dump(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "route_locked": self.route_locked,
            "stage_locked": self.stage_locked,
            "technique_valid": self.technique_valid,
            "peer_use_valid": self.peer_use_valid,
            "safety_valid": self.safety_valid,
            "notes": self.notes,
        }


def build_supervisor_audit(
    *,
    state: dict[str, Any],
    orchestrator_data: dict[str, Any],
    doctor_speech: str,
    final_output: list[dict[str, Any]],
    validator_enabled: bool = True,
) -> SupervisorAudit:
    route = str(state.get("therapy_route", "CBT"))
    current_stage = str(state.get("current_stage", ""))
    required_factors = state.get("required_yalom_factors", ["NONE"])
    if not isinstance(required_factors, list):
        required_factors = ["NONE"]

    notes: list[str] = []
    route_locked = route.upper() in {"CBT", "MBI", "BA"}
    stage_locked = bool(current_stage)
    if not str(orchestrator_data.get("stage_task", "")).strip():
        notes.append("Orchestrator did not expose stage_task; final response still checked by stage validator.")

    if validator_enabled:
        validation = validate_therapist_response(current_stage, doctor_speech, state.get("user_message", ""))
        technique_valid = validation.valid
        if not validation.valid:
            notes.append(validation.reason)
    else:
        technique_valid = True
        notes.append("Therapist response validator disabled for this system variant.")

    peer_use_valid = True
    for message in final_output:
        sender = message.get("sender")
        if sender in {"peer_mirror_agent", "veteran_peer_agent"} and not route_peer_allowed(route, current_stage, sender, required_factors):
            peer_use_valid = False
            notes.append(f"{sender} was included despite route/stage/factor policy.")

    safety_flags = state.get("safety_flags", {})
    psychosocial_safety = state.get("psychosocial_safety", {})
    safety_valid = not (
        (isinstance(safety_flags, dict) and safety_flags.get("unsafe_output"))
        or (isinstance(psychosocial_safety, dict) and psychosocial_safety.get("high_risk"))
    )
    if not safety_valid:
        notes.append("Safety flags or psychosocial critics indicate unsafe output risk.")

    valid = route_locked and stage_locked and technique_valid and peer_use_valid and safety_valid
    if valid:
        notes.append("Supervisor audit passed.")

    return SupervisorAudit(
        valid=valid,
        route_locked=route_locked,
        stage_locked=stage_locked,
        technique_valid=technique_valid,
        peer_use_valid=peer_use_valid,
        safety_valid=safety_valid,
        notes=notes,
    )
