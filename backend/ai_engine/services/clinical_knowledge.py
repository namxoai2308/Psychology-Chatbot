from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


@lru_cache(maxsize=8)
def _load_techniques(route: str) -> dict[str, dict[str, Any]]:
    route_key = (route or "CBT").lower()
    path = _KNOWLEDGE_DIR / f"{route_key}_techniques.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def stage_knowledge(route: str, current_stage: str, context: str = "None") -> str:
    route_key = (route or "CBT").upper()
    data = _load_techniques(route_key).get(current_stage, {})
    if not data:
        return f"No stage-specific {route_key} knowledge available."

    lines = [
        f"Route: {route_key}",
        f"Stage task: {data.get('stage_task', '')}",
        "Micro-skills:",
        *[f"- {item}" for item in data.get("micro_skills", [])],
        "Avoid:",
        *[f"- {item}" for item in data.get("avoid", [])],
        "Good moves:",
        *[f"- {item}" for item in data.get("good_moves", [])],
    ]
    if data.get("validator_anchors"):
        lines.append("Validator anchors that should appear in doctor_speech:")
        lines.extend(f"- {item}" for item in data.get("validator_anchors", []))
    if route_key == "CBT" and context and context != "None":
        lines.append(f"Current distortion candidate: {context}")
    if data.get("good_examples"):
        lines.append("Good examples:")
        lines.extend(f"- {item}" for item in data.get("good_examples", []))
    if data.get("bad_examples"):
        lines.append("Bad examples to avoid:")
        lines.extend(f"- {item}" for item in data.get("bad_examples", []))
    if data.get("example"):
        lines.append(f"Example style: {data['example']}")
    return "\n".join(line for line in lines if line)


def cbt_stage_knowledge(current_stage: str, distortion: str = "None") -> str:
    return stage_knowledge("CBT", current_stage, distortion)
