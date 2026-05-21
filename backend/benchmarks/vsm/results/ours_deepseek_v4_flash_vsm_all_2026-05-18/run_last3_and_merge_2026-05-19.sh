#!/usr/bin/env bash
set -euo pipefail

cd "/home/xoai/Pysychology chatbot/cbt-ai-therapist-project"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=backend

RUN_ROOT="backend/benchmarks/vsm/results/ours_deepseek_v4_flash_vsm_all_2026-05-18"
LAST_DIR="$RUN_ROOT/remaining_last3_2026-05-19"
MISSING_FILE="$RUN_ROOT/remaining_missing_after_partial_2026-05-19.txt"

.venv/bin/python -m benchmarks.vsm.runners.run_chunked_inference \
  --dataset backend/benchmarks/vsm/data/vsm_all.jsonl \
  --systems ours_multi_agent \
  --case-id-file "$MISSING_FILE" \
  --model-type deepseek \
  --model deepseek-v4-flash \
  --selected-model deepseek \
  --out-dir "$LAST_DIR" \
  --chunk-size 3 \
  --resume \
  --no-central-export

.venv/bin/python - <<'PY'
import json
from pathlib import Path

from benchmarks.vsm.data.schema import load_vsm_cases
from benchmarks.vsm.runners.response_artifacts import (
    atomic_write_json,
    export_response_file,
    update_response_index,
    write_jsonl,
)

root = Path("backend/benchmarks/vsm/results/ours_deepseek_v4_flash_vsm_all_2026-05-18")
sources = [
    root / "partial_saved_2026-05-19/per_case_results.partial.jsonl",
    root / "remaining_2026-05-19/raw/chunk_000_004_attempt_01/per_case_results.jsonl",
    root / "remaining_last3_2026-05-19/final/per_case_results.jsonl",
    root / "remaining_last3_2026-05-19/merged/per_case_results.jsonl",
]
out_dir = root / "final_partial_plus_remaining_2026-05-19"
out_dir.mkdir(parents=True, exist_ok=True)
response_dir = Path("backend/benchmarks/vsm/results/responses_vsm_all_2026-05-18")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


rows_by_case: dict[str, dict] = {}
source_counts: dict[str, int] = {}
for source in sources:
    rows = read_jsonl(source)
    source_counts[str(source)] = len(rows)
    for row in rows:
        rows_by_case[str(row.get("case_id") or "")] = row

expected_ids = [case.case_id for case in load_vsm_cases(Path("backend/benchmarks/vsm/data/vsm_all.jsonl"))]
final_rows = [rows_by_case[case_id] for case_id in expected_ids if case_id in rows_by_case]
missing = [case_id for case_id in expected_ids if case_id not in rows_by_case]

write_jsonl(out_dir / "per_case_results.jsonl", final_rows)
atomic_write_json(
    out_dir / "merge_manifest.json",
    {
        "sources": source_counts,
        "final_cases": len(final_rows),
        "expected_cases": len(expected_ids),
        "missing_case_ids": missing,
    },
)

if len(final_rows) == len(expected_ids):
    export_response_file(
        out_dir / "per_case_results.jsonl",
        out_dir / "ours_multi_agent.responses.jsonl",
        source_file=str(out_dir / "per_case_results.jsonl"),
    )
    response_dir.mkdir(parents=True, exist_ok=True)
    export_response_file(
        out_dir / "per_case_results.jsonl",
        response_dir / "ours_multi_agent.responses.jsonl",
        source_file=str(out_dir / "per_case_results.jsonl"),
    )
    update_response_index(response_dir)
else:
    export_response_file(
        out_dir / "per_case_results.jsonl",
        out_dir / "ours_multi_agent.responses.partial.jsonl",
        source_file=str(out_dir / "per_case_results.jsonl"),
    )

print(
    json.dumps(
        {
            "final_cases": len(final_rows),
            "expected_cases": len(expected_ids),
            "missing_case_ids": missing,
            "out_dir": str(out_dir),
        },
        ensure_ascii=False,
        indent=2,
    )
)
PY
