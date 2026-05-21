from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.vsm.runners.response_artifacts import (
    atomic_write_json,
    case_quality_score,
    export_response_file,
    read_jsonl,
    update_response_index,
    write_jsonl,
)
from benchmarks.vsm.scoring.aggregate import score_results_dir


DEFAULT_RESPONSE_DIR = Path("backend/benchmarks/vsm/results/responses_vsm_all_2026-05-18")


def replace_cases(args: argparse.Namespace) -> dict[str, Any]:
    base_rows = read_jsonl(args.base_dir / "per_case_results.jsonl")
    repair_rows = read_jsonl(args.repair_dir / "per_case_results.jsonl")
    base_failures = read_jsonl(args.base_dir / "failures.jsonl")
    repair_failures = read_jsonl(args.repair_dir / "failures.jsonl")
    if not base_rows:
        raise ValueError(f"No base rows found in {args.base_dir}")
    if not repair_rows:
        raise ValueError(f"No repair rows found in {args.repair_dir}")

    repair_by_case = {str(row.get("case_id") or ""): row for row in repair_rows}
    repair_failures_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    base_failures_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for failure in repair_failures:
        repair_failures_by_case[str(failure.get("case_id") or "")].append(failure)
    for failure in base_failures:
        base_failures_by_case[str(failure.get("case_id") or "")].append(failure)

    final_rows: list[dict[str, Any]] = []
    replaced_case_ids: set[str] = set()
    replacement_report = []
    for base_row in base_rows:
        case_id = str(base_row.get("case_id") or "")
        repair_row = repair_by_case.get(case_id)
        if not repair_row:
            final_rows.append(base_row)
            continue

        base_score = case_quality_score(base_row)
        repair_score = case_quality_score(repair_row)
        repair_blocked = _has_blocking_failure(repair_failures_by_case.get(case_id, []))
        accepted = not repair_blocked and (repair_score >= base_score or args.allow_lower_score)
        final_rows.append(repair_row if accepted else base_row)
        if accepted:
            replaced_case_ids.add(case_id)
        replacement_report.append(
            {
                "case_id": case_id,
                "accepted": accepted,
                "base_score": base_score,
                "repair_score": repair_score,
                "repair_blocked": repair_blocked,
                "base_failures": [item.get("failure_type") for item in base_failures_by_case.get(case_id, [])],
                "repair_failures": [item.get("failure_type") for item in repair_failures_by_case.get(case_id, [])],
            }
        )

    final_failures = [
        failure for failure in base_failures if str(failure.get("case_id") or "") not in replaced_case_ids
    ] + [
        failure for failure in repair_failures if str(failure.get("case_id") or "") in replaced_case_ids
    ]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "per_case_results.jsonl", final_rows)
    write_jsonl(args.out_dir / "failures.jsonl", final_failures)
    _write_inference_summary(args.out_dir / "inference_summary.json", final_rows, final_failures)
    score_results_dir(args.out_dir)

    response_summary = export_response_file(
        args.out_dir / "per_case_results.jsonl",
        args.out_dir / "ours_multi_agent.responses.jsonl",
        source_file=str(args.out_dir / "per_case_results.jsonl"),
    )
    if not args.no_central_export:
        args.response_out_dir.mkdir(parents=True, exist_ok=True)
        central_path = args.response_out_dir / "ours_multi_agent.responses.jsonl"
        export_response_file(
            args.out_dir / "per_case_results.jsonl",
            central_path,
            source_file=str(args.out_dir / "per_case_results.jsonl"),
        )
        update_response_index(args.response_out_dir)
        response_summary["central_file"] = str(central_path)

    atomic_write_json(
        args.out_dir / "replacement_report.json",
        {
            "base_dir": str(args.base_dir),
            "repair_dir": str(args.repair_dir),
            "out_dir": str(args.out_dir),
            "replaced_cases": len(replaced_case_ids),
            "kept_original_cases": len(replacement_report) - len(replaced_case_ids),
            "cases": replacement_report,
            "response_summary": response_summary,
        },
    )
    return {
        "out_dir": str(args.out_dir),
        "cases": len(final_rows),
        "replaced_cases": len(replaced_case_ids),
        "response_summary": response_summary,
    }


def _has_blocking_failure(failures: list[dict[str, Any]]) -> bool:
    return any(str(item.get("failure_type") or "") in {"exception", "hard_fail"} for item in failures)


def _write_inference_summary(path: Path, rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    systems = sorted({str(row.get("system") or "") for row in rows if row.get("system")})
    cases_by_system = Counter(str(row.get("system") or "") for row in rows)
    turns_by_system: Counter[str] = Counter()
    latency_by_system: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        system = str(row.get("system") or "")
        for turn in row.get("turns") or []:
            turns_by_system[system] += 1
            latency_by_system[system].append(float(turn.get("latency_ms") or 0.0))
    failures_by_system = Counter(str(row.get("system") or "") for row in failures)
    payload = {
        "out_dir": str(path.parent),
        "case_count": len({row.get("case_id") for row in rows}),
        "result_rows": len(rows),
        "result_turns": sum(turns_by_system.values()),
        "failures": len(failures),
        "hard_failures": sum(1 for row in failures if row.get("failure_type") == "hard_fail"),
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
    atomic_write_json(path, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace weak VSM cases with repair rerun results.")
    parser.add_argument("--base-dir", required=True, type=Path)
    parser.add_argument("--repair-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--allow-lower-score", action="store_true")
    parser.add_argument("--response-out-dir", type=Path, default=DEFAULT_RESPONSE_DIR)
    parser.add_argument("--no-central-export", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replace_cases(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
