from __future__ import annotations

from typing import Any


CBT_BOOL_FIELDS = {
    "emotion_present",
    "event_present",
    "abc_present",
    "automatic_thought_present",
    "distortion_reflection",
    "socratic_reasoning",
    "insight_present",
    "balanced_reframe",
    "action_step",
    "action_commitment",
    "peer_boundary_intent",
    "overload",
    "hope_request",
}


def normalize_cbt_assessor_payload(raw: Any) -> dict[str, Any]:
    """Coerce LLM JSON into the strict CBT assessor schema without changing the schema itself."""
    payload = raw if isinstance(raw, dict) else {}
    evidence = payload.get("cbt_evidence")
    if not isinstance(evidence, dict):
        evidence = {}

    normalized_evidence = dict(evidence)
    for field in CBT_BOOL_FIELDS:
        normalized_evidence[field] = _coerce_bool(normalized_evidence.get(field, False))

    normalized_evidence["automatic_thought"] = _coerce_str(normalized_evidence.get("automatic_thought", ""))
    normalized_evidence["distortion_candidates"] = _coerce_str_list(normalized_evidence.get("distortion_candidates", []))
    normalized_evidence["evidence_quotes"] = _coerce_str_list(normalized_evidence.get("evidence_quotes", []))
    normalized_evidence["source"] = _coerce_str(normalized_evidence.get("source", "llm")) or "llm"
    normalized_evidence["confidence"] = _coerce_confidence(normalized_evidence.get("confidence", 0.68))

    return {
        "clinical_summary": _coerce_str(payload.get("clinical_summary", "")),
        "safety_flags": payload.get("safety_flags") if isinstance(payload.get("safety_flags"), dict) else {},
        "cbt_evidence": normalized_evidence,
    }


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "0", "false", "no", "none", "null", "không", "khong"}:
            return False
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return False


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = value.strip()
        return [item] if item else []
    if isinstance(value, dict):
        items: list[str] = []
        for nested in value.values():
            items.extend(_coerce_str_list(nested))
        return items
    if isinstance(value, (list, tuple, set)):
        items = []
        for nested in value:
            items.extend(_coerce_str_list(nested))
        return items
    item = _coerce_str(value)
    return [item] if item else []


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.68
    return min(1.0, max(0.0, confidence))
