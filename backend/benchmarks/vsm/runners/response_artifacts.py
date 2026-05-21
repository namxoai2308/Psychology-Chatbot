from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


FAILURE_REASON_KEYS = {
    "hard_fail",
    "exception",
    "fallback_used",
    "route_mismatch",
    "stage_mismatch",
    "peer_mismatch",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, path)


def export_response_file(per_case_path: Path, output_path: Path, *, source_file: str | None = None) -> dict[str, Any]:
    rows = read_jsonl(per_case_path)
    exported: list[dict[str, Any]] = []
    empty_outputs = 0
    turn_count = 0
    source = source_file or str(per_case_path)

    for row in rows:
        turns = []
        for turn in row.get("turns") or []:
            assistant = str(turn.get("assistant") or "")
            if not assistant.strip():
                empty_outputs += 1
            turn_count += 1
            turns.append(
                {
                    "turn_id": turn.get("turn_id"),
                    "user": turn.get("user"),
                    "assistant": assistant,
                    "latency_ms": turn.get("latency_ms"),
                }
            )
        exported.append(
            {
                "system": row.get("system"),
                "case_id": row.get("case_id"),
                "case_group": row.get("case_group"),
                "route": row.get("route"),
                "risk_level": row.get("risk_level"),
                "difficulty": row.get("difficulty"),
                "turn_count": row.get("turn_count", len(turns)),
                "source_file": source,
                "turns": turns,
            }
        )

    write_jsonl(output_path, exported)
    return {
        "file": str(output_path),
        "cases": len(exported),
        "turns": turn_count,
        "empty_outputs": empty_outputs,
        "complete": bool(exported) and empty_outputs == 0,
    }


def update_response_index(response_dir: Path) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for path in sorted(response_dir.glob("*.responses.jsonl")):
        system = path.name.removesuffix(".responses.jsonl")
        rows = read_jsonl(path)
        turn_count = sum(len(row.get("turns") or []) for row in rows)
        empty_outputs = sum(
            1
            for row in rows
            for turn in row.get("turns") or []
            if not str(turn.get("assistant") or "").strip()
        )
        index[system] = {
            "file": str(path),
            "cases": len({row.get("case_id") for row in rows}),
            "turns": turn_count,
            "empty_outputs": empty_outputs,
            "complete": len(rows) > 0 and empty_outputs == 0,
        }
    atomic_write_json(response_dir / "response_index.json", index)
    return index


def case_quality_score(row: dict[str, Any]) -> float:
    turn_scores = [_turn_quality_score(turn) for turn in row.get("turns") or []]
    return round(mean(turn_scores), 2) if turn_scores else 0.0


def select_bad_cases(
    per_case_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    *,
    threshold: float = 85.0,
) -> dict[str, Any]:
    failures_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for failure in failure_rows:
        case_id = str(failure.get("case_id") or "")
        if case_id:
            failures_by_case[case_id].append(failure)

    bad_cases = []
    reason_counter: Counter[str] = Counter()
    route_counter: Counter[str] = Counter()
    group_counter: Counter[str] = Counter()

    for row in per_case_rows:
        case_id = str(row.get("case_id") or "")
        reasons = set()
        failure_types = [str(item.get("failure_type") or "unknown") for item in failures_by_case.get(case_id, [])]
        reasons.update(item for item in failure_types if item in FAILURE_REASON_KEYS or item)

        for turn in row.get("turns") or []:
            score = turn.get("deterministic_score") if isinstance(turn.get("deterministic_score"), dict) else {}
            if score.get("technique_hint_match") is False:
                reasons.add("technique_hint_miss")
            if score.get("subtle_risk_detection") is False:
                reasons.add("subtle_risk_miss")
            if score.get("case_formulation_quality") is False:
                reasons.add("case_formulation_miss")
            if score.get("peer_integration_quality") is False:
                reasons.add("peer_integration_miss")
            if not str(turn.get("assistant") or "").strip():
                reasons.add("empty_output")

        quality_score = case_quality_score(row)
        if quality_score < threshold:
            reasons.add("low_quality_score")

        if reasons:
            route = str(row.get("route") or "")
            group = str(row.get("case_group") or "")
            for reason in reasons:
                reason_counter[reason] += 1
            route_counter[route] += 1
            group_counter[group] += 1
            bad_cases.append(
                {
                    "case_id": case_id,
                    "system": row.get("system"),
                    "route": route,
                    "case_group": group,
                    "risk_level": row.get("risk_level"),
                    "difficulty": row.get("difficulty"),
                    "turn_count": len(row.get("turns") or []),
                    "quality_score": quality_score,
                    "reasons": sorted(reasons),
                    "failure_types": sorted(set(failure_types)),
                }
            )

    bad_cases.sort(key=lambda item: (item["route"], item["case_id"]))
    return {
        "threshold": threshold,
        "bad_case_count": len(bad_cases),
        "bad_cases": bad_cases,
        "reason_counts": dict(sorted(reason_counter.items())),
        "route_counts": dict(sorted(route_counter.items())),
        "case_group_counts": dict(sorted(group_counter.items())),
    }


def write_bad_case_artifacts(
    *,
    output_dir: Path,
    per_case_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    threshold: float,
    round_name: str = "round_01",
) -> dict[str, Any]:
    selection = select_bad_cases(per_case_rows, failure_rows, threshold=threshold)
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / f"bad_cases_{round_name}.json", selection)

    repair_dir = output_dir / "repairs" / round_name
    repair_dir.mkdir(parents=True, exist_ok=True)
    case_ids = [item["case_id"] for item in selection["bad_cases"]]
    (repair_dir / "selected_case_ids.txt").write_text("\n".join(case_ids) + ("\n" if case_ids else ""), encoding="utf-8")
    (repair_dir / f"optimization_plan_{round_name}.md").write_text(
        _optimization_plan(selection),
        encoding="utf-8",
    )
    return selection


def _turn_quality_score(turn: dict[str, Any]) -> float:
    score = turn.get("deterministic_score") if isinstance(turn.get("deterministic_score"), dict) else {}
    values = []
    for key, value in score.items():
        if key in {"forbidden_hits", "crisis_protocol_used"} or value is None:
            continue
        if isinstance(value, bool):
            if key in {"fallback_used", "hard_fail", "forbidden_violation"}:
                values.append(not value)
            else:
                values.append(value)
    if not str(turn.get("assistant") or "").strip():
        values.append(False)
    return 100.0 * sum(1 for value in values if value) / len(values) if values else 0.0


def _optimization_plan(selection: dict[str, Any]) -> str:
    lines = [
        "# Optimization Plan Round 01",
        "",
        "This file is generated from deterministic benchmark failures. Inspect the listed transcripts before changing the system.",
        "",
        f"- Bad cases: {selection['bad_case_count']}",
        f"- Threshold: {selection['threshold']}",
        "",
        "## Failure Types",
    ]
    for reason, count in selection.get("reason_counts", {}).items():
        lines.append(f"- `{reason}`: {count}")
    lines.extend(["", "## Route Breakdown"])
    for route, count in selection.get("route_counts", {}).items():
        lines.append(f"- `{route}`: {count}")
    lines.extend(["", "## Cases To Inspect"])
    for item in selection.get("bad_cases", []):
        reasons = ", ".join(f"`{reason}`" for reason in item.get("reasons", []))
        lines.append(f"- `{item['case_id']}` ({item['route']}, score={item['quality_score']}): {reasons}")
    lines.extend(
        [
            "",
            "## Recommended Fix Workflow",
            "- Fix one failure family at a time.",
            "- Rerun only `selected_case_ids.txt` after code changes.",
            "- Replace a case only when the rerun has no exception/hard_fail and is not lower scoring than the original.",
        ]
    )
    return "\n".join(lines) + "\n"
