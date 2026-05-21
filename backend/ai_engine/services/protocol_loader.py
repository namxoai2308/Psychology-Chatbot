from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocols"


@lru_cache(maxsize=8)
def load_protocol(route: str) -> dict:
    route_key = (route or "CBT").lower()
    path = PROTOCOL_DIR / f"{route_key}_protocol.json"
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        protocol = {"modality": (route or "CBT").upper(), "phases": [], "rules": []}
    protocol["department"] = protocol.get("department") or protocol.get("modality", (route or "CBT").upper())
    protocol["goals"] = protocol.get("goals") or "; ".join(protocol.get("rules", []))
    return protocol
