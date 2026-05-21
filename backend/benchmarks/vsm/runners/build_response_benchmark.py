from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.vsm.data.schema import VSMCase, load_vsm_cases
from benchmarks.vsm.runners.response_artifacts import read_jsonl, write_jsonl
from benchmarks.vsm.runners.run_inference import _failures_for_turn, _turn_result
from benchmarks.vsm.scoring.deterministic import score_turn_output


BASELINE_SYSTEMS = ("base_model", "prompt_1_1", "seallm", "camel_cbt")


def build_response_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = load_vsm_cases(args.dataset)
    case_by_id = {case.case_id: case for case in cases}
    selected_case_ids = _selected_case_ids_from_ours(args.ours_raw_dir, case_by_id)
    if args.limit_cases:
        selected_case_ids = selected_case_ids[: args.limit_cases]
    selected = [case_by_id[case_id] for case_id in selected_case_ids]

    per_case_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []

    for system in BASELINE_SYSTEMS:
        rows, failures = _baseline_rows(system, args.responses_dir / f"{system}.responses.jsonl", selected)
        per_case_rows.extend(rows)
        failure_rows.extend(failures)

    ours_rows, ours_failures = _ours_rows(args.ours_raw_dir, set(selected_case_ids))
    per_case_rows.extend(ours_rows)
    failure_rows.extend(ours_failures)

    write_jsonl(out_dir / "per_case_results.jsonl", per_case_rows)
    write_jsonl(out_dir / "failures.jsonl", failure_rows)
    summary = _summary(per_case_rows, failure_rows, args.dataset, out_dir, selected_case_ids)
    (out_dir / "inference_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "selected_case_ids.txt").write_text("\n".join(selected_case_ids) + "\n", encoding="utf-8")
    return summary


def _selected_case_ids_from_ours(ours_raw_dir: Path, case_by_id: dict[str, VSMCase]) -> list[str]:
    completed_case_ids: set[str] = set()
    for status_path in sorted(ours_raw_dir.glob("chunk_*_attempt_*/chunk_status.json")):
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status.get("status") != "completed":
            continue
        for row in read_jsonl(status_path.parent / "per_case_results.jsonl"):
            case_id = str(row.get("case_id") or "")
            if case_id:
                completed_case_ids.add(case_id)
    ordered = [case_id for case_id in case_by_id if case_id in completed_case_ids]
    if not ordered:
        raise ValueError(f"No completed ours cases found under {ours_raw_dir}")
    return ordered


def _baseline_rows(system: str, response_path: Path, cases: list[VSMCase]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    response_by_case = {str(row.get("case_id") or ""): row for row in read_jsonl(response_path)}
    per_case_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for case in cases:
        response_case = response_by_case.get(case.case_id)
        if not response_case:
            raise ValueError(f"{system}: missing response for {case.case_id} in {response_path}")
        response_turns = {int(turn.get("turn_id") or 0): turn for turn in response_case.get("turns") or []}
        turns = []
        for turn in case.turns:
            response_turn = response_turns.get(turn.turn_id)
            if not response_turn:
                raise ValueError(f"{system}: missing turn {turn.turn_id} for {case.case_id}")
            assistant = str(response_turn.get("assistant") or "")
            latency_ms = float(response_turn.get("latency_ms") or 0.0)
            score = score_turn_output(case, turn, assistant, metadata={})
            turns.append(_turn_result(turn, assistant, {}, score, latency_ms))
            failure_rows.extend(_failures_for_turn(system, case, turn, score, {}))
        per_case_rows.append(_case_result(system, case, turns))
    return per_case_rows, failure_rows


def _ours_rows(ours_raw_dir: Path, selected_case_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_case: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for status_path in sorted(ours_raw_dir.glob("chunk_*_attempt_*/chunk_status.json")):
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status.get("status") != "completed":
            continue
        for row in read_jsonl(status_path.parent / "per_case_results.jsonl"):
            case_id = str(row.get("case_id") or "")
            if case_id in selected_case_ids:
                rows_by_case[case_id] = row
        for failure in read_jsonl(status_path.parent / "failures.jsonl"):
            if str(failure.get("case_id") or "") in selected_case_ids:
                failures.append(failure)
    ordered_rows = [rows_by_case[case_id] for case_id in selected_case_ids if case_id in rows_by_case]
    return ordered_rows, failures


def _case_result(system: str, case: VSMCase, turns: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "system": system,
        "case_id": case.case_id,
        "case_group": case.case_group,
        "route": case.route,
        "risk_level": case.risk_level,
        "difficulty": case.difficulty,
        "benchmark_intent": case.benchmark_intent,
        "turn_count": len(case.turns),
        "turns": turns,
    }


def _summary(
    per_case_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    dataset: Path,
    out_dir: Path,
    selected_case_ids: list[str],
) -> dict[str, Any]:
    cases_by_system = Counter(str(row.get("system") or "") for row in per_case_rows)
    turns_by_system: Counter[str] = Counter()
    latency_by_system: dict[str, list[float]] = defaultdict(list)
    for row in per_case_rows:
        system = str(row.get("system") or "")
        for turn in row.get("turns") or []:
            turns_by_system[system] += 1
            latency_by_system[system].append(float(turn.get("latency_ms") or 0.0))
    failures_by_system = Counter(str(row.get("system") or "") for row in failure_rows)
    systems = sorted(cases_by_system)
    return {
        "dataset": str(dataset),
        "out_dir": str(out_dir),
        "selected_cases": len(selected_case_ids),
        "selected_case_ids": selected_case_ids,
        "result_rows": len(per_case_rows),
        "result_turns": sum(turns_by_system.values()),
        "failures": len(failure_rows),
        "hard_failures": sum(1 for row in failure_rows if row.get("failure_type") == "hard_fail"),
        "systems": {
            system: {
                "cases": cases_by_system[system],
                "turns": turns_by_system[system],
                "failures": failures_by_system[system],
                "avg_latency_ms": round(sum(latency_by_system[system]) / len(latency_by_system[system]), 2)
                if latency_by_system[system]
                else 0.0,
            }
            for system in systems
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a scored VSM result directory from stored response files.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--responses-dir", required=True, type=Path)
    parser.add_argument("--ours-raw-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--limit-cases", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(build_response_benchmark(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
