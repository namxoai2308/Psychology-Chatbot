"""Load and validate benchmark_input.jsonl."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_engine.dass_triage import assign_department, calculate_dass21


@dataclass
class BenchmarkCase:
    case_id: str
    dass21_answers: list[int]
    expected_route: str
    risk_level: str
    user_turns: list[str]
    group_track: bool
    raw: dict[str, Any]


def expected_route_from_dass(answers: list[int]) -> str:
    r = calculate_dass21(answers)
    return str(assign_department(r)["assigned_dept"])


def load_cases(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ans = row["dass21_answers"]
        if len(ans) != 21 or any(not isinstance(x, int) or x < 0 or x > 3 for x in ans):
            raise ValueError(f"{row.get('case_id')}: dass21_answers must be 21 ints in 0..3")
        exp = str(row["expected_route"]).upper()
        if exp not in ("CBT", "MBI", "BA"):
            raise ValueError(f"{row.get('case_id')}: expected_route must be CBT|MBI|BA")
        if expected_route_from_dass(ans) != exp:
            raise ValueError(f"{row.get('case_id')}: expected_route does not match DASS triage")
        turns = row["user_turns"]
        if not isinstance(turns, list) or not turns:
            raise ValueError(f"{row.get('case_id')}: user_turns must be non-empty list")
        cases.append(
            BenchmarkCase(
                case_id=str(row["case_id"]),
                dass21_answers=ans,
                expected_route=exp,
                risk_level=str(row.get("risk_level", "R1")),
                user_turns=[str(t) for t in turns],
                group_track=bool(row.get("group_track", False)),
                raw=row,
            )
        )
    return cases
