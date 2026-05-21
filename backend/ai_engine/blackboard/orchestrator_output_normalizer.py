from __future__ import annotations

from typing import Any


STRING_FIELDS = {
    "clinical_reasoning_scratchpad",
    "case_formulation",
    "stage_task",
    "response_strategy",
    "selected_technique",
    "route_alignment",
    "risk_check",
    "cognitive_distortion",
    "therapist_plan",
    "doctor_speech",
}


def normalize_orchestrator_payload(raw: Any) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    normalized: dict[str, Any] = {}
    for field in STRING_FIELDS:
        value = payload.get(field, "")
        if field == "cognitive_distortion" and value is None:
            value = "None"
        normalized[field] = _coerce_str(value)
    normalized["draft_decisions"] = _coerce_draft_decisions(payload.get("draft_decisions", []))
    return normalized


def _coerce_draft_decisions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    decisions: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        decisions.append(
            {
                "sender": _coerce_str(item.get("sender", "")),
                "action": _coerce_action(item.get("action", "discard")),
                "reason": _coerce_str(item.get("reason", "")),
                "rewritten_text": _coerce_str(item.get("rewritten_text", "")),
            }
        )
    return decisions


def _coerce_action(value: Any) -> str:
    action = _coerce_str(value).lower()
    return action if action in {"include", "rewrite", "discard"} else "discard"


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
