from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.vsm.runners.response_artifacts import read_jsonl, write_jsonl


DEFAULT_SYSTEMS = (
    "ours_full",
    "ours_no_peer",
    "ours_no_validator",
    "ours_no_safety_critic",
    "single_agent_stage_prompt",
    "single_agent_plain",
    "base_model",
    "prompt_1_1",
    "seallm",
    "camel_cbt",
)


def build_package(
    *,
    trace_full_dir: Path,
    ablation_dir: Path,
    legacy_dir: Path,
    out_dir: Path,
    systems: list[str],
) -> dict[str, Any]:
    trace_rows = read_jsonl(trace_full_dir / "per_case_results.jsonl")
    ablation_rows = read_jsonl(ablation_dir / "per_case_results.jsonl")
    legacy_rows = read_jsonl(legacy_dir / "per_case_results.jsonl")
    trace_failures = read_jsonl(trace_full_dir / "failures.jsonl")
    ablation_failures = read_jsonl(ablation_dir / "failures.jsonl")
    legacy_failures = read_jsonl(legacy_dir / "failures.jsonl")
    if not trace_rows:
        raise ValueError(f"No TRACE-Full rows found in {trace_full_dir}")
    if not ablation_rows:
        raise ValueError(f"No ablation rows found in {ablation_dir}")
    if not legacy_rows:
        raise ValueError(f"No legacy baseline rows found in {legacy_dir}")

    core_case_ids = [str(row.get("case_id") or "") for row in trace_rows if row.get("case_id")]
    if len(core_case_ids) != len(set(core_case_ids)):
        raise ValueError("TRACE-Full rows contain duplicate case IDs.")
    core_case_set = set(core_case_ids)

    all_rows = trace_rows + ablation_rows + legacy_rows
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_keys: list[tuple[str, str]] = []
    for row in all_rows:
        case_id = str(row.get("case_id") or "")
        system = str(row.get("system") or "")
        if case_id not in core_case_set or system not in systems:
            continue
        key = (system, case_id)
        if key in rows_by_key:
            duplicate_keys.append(key)
            continue
        rows_by_key[key] = row

    missing: dict[str, list[str]] = {}
    final_rows: list[dict[str, Any]] = []
    for system in systems:
        system_missing = [case_id for case_id in core_case_ids if (system, case_id) not in rows_by_key]
        if system_missing:
            missing[system] = system_missing
            continue
        final_rows.extend(rows_by_key[(system, case_id)] for case_id in core_case_ids)
    if missing:
        preview = {system: case_ids[:5] for system, case_ids in missing.items()}
        raise ValueError(f"Missing system/case rows for paper package: {json.dumps(preview, ensure_ascii=False)}")
    if duplicate_keys:
        raise ValueError(f"Duplicate system/case rows in sources: {duplicate_keys[:5]}")

    failures = [
        row
        for row in trace_failures + ablation_failures + legacy_failures
        if str(row.get("case_id") or "") in core_case_set and str(row.get("system") or "") in systems
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "per_case_results.jsonl", final_rows)
    write_jsonl(out_dir / "failures.jsonl", failures)
    summary = _summary(final_rows, failures, out_dir, systems, core_case_ids)
    (out_dir / "inference_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def _summary(
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    out_dir: Path,
    systems: list[str],
    core_case_ids: list[str],
) -> dict[str, Any]:
    cases_by_system: dict[str, set[str]] = defaultdict(set)
    turns_by_system: Counter[str] = Counter()
    for row in rows:
        system = str(row.get("system") or "")
        case_id = str(row.get("case_id") or "")
        cases_by_system[system].add(case_id)
        turns_by_system[system] += len(row.get("turns") or [])
    failure_counts = Counter(str(row.get("system") or "") for row in failures)
    return {
        "out_dir": str(out_dir),
        "protocol_version": "VSM-Core-100-v1-final",
        "case_count": len(core_case_ids),
        "result_rows": len(rows),
        "result_turns": sum(turns_by_system.values()),
        "failure_rows": len(failures),
        "systems": {
            system: {
                "cases": len(cases_by_system[system]),
                "turns": turns_by_system[system],
                "failures": failure_counts[system],
            }
            for system in systems
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the VSM paper comparative package from frozen runs.")
    parser.add_argument("--trace-full-dir", required=True, type=Path)
    parser.add_argument("--ablation-dir", required=True, type=Path)
    parser.add_argument("--legacy-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--systems", default=",".join(DEFAULT_SYSTEMS))
    args = parser.parse_args()
    systems = [item.strip() for item in args.systems.split(",") if item.strip()]
    print(
        json.dumps(
            build_package(
                trace_full_dir=args.trace_full_dir,
                ablation_dir=args.ablation_dir,
                legacy_dir=args.legacy_dir,
                out_dir=args.out_dir,
                systems=systems,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
