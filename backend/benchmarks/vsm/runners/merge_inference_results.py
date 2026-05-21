from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def merge_results(input_dirs: list[Path], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    per_case_out = out_dir / "per_case_results.jsonl"
    failures_out = out_dir / "failures.jsonl"

    per_case_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for input_dir in input_dirs:
        per_case_path = input_dir / "per_case_results.jsonl"
        failures_path = input_dir / "failures.jsonl"
        if per_case_path.exists():
            per_case_rows.extend(_read_jsonl(per_case_path))
        if failures_path.exists():
            failure_rows.extend(_read_jsonl(failures_path))

    with per_case_out.open("w", encoding="utf-8") as f:
        for row in per_case_rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with failures_out.open("w", encoding="utf-8") as f:
        for row in failure_rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = _summary(per_case_rows, failure_rows, out_dir)
    (out_dir / "inference_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _summary(per_case_rows: list[dict[str, Any]], failure_rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    cases_by_system = Counter(row.get("system", "") for row in per_case_rows)
    turns_by_system: Counter[str] = Counter()
    latency_by_system: dict[str, list[float]] = defaultdict(list)
    unique_cases = set()
    for row in per_case_rows:
        system = row.get("system", "")
        unique_cases.add(row.get("case_id", ""))
        for turn in row.get("turns", []):
            turns_by_system[system] += 1
            latency_by_system[system].append(float(turn.get("latency_ms") or 0))

    failures_by_system = Counter(row.get("system", "") for row in failure_rows)
    hard_failures = sum(1 for row in failure_rows if row.get("failure_type") == "hard_fail")
    systems = sorted(cases_by_system)
    return {
        "out_dir": str(out_dir),
        "case_count": len(unique_cases),
        "result_rows": len(per_case_rows),
        "result_turns": sum(turns_by_system.values()),
        "failures": len(failure_rows),
        "hard_failures": hard_failures,
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
    parser = argparse.ArgumentParser(description="Merge VSM inference result directories.")
    parser.add_argument("--inputs", required=True, help="Comma-separated result directories.")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    input_dirs = [Path(item.strip()) for item in args.inputs.split(",") if item.strip()]
    print(json.dumps(merge_results(input_dirs, args.out_dir), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
