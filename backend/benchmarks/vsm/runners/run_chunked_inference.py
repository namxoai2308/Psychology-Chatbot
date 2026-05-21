from __future__ import annotations

import argparse
import json
import os
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.vsm.data.schema import VSMCase, load_vsm_cases, summarize_cases
from benchmarks.vsm.runners.merge_inference_results import merge_results
from benchmarks.vsm.runners.response_artifacts import (
    atomic_write_json,
    export_response_file,
    read_jsonl,
    update_response_index,
    write_bad_case_artifacts,
)
from benchmarks.vsm.runners.run_inference import run_inference
from benchmarks.vsm.scoring.aggregate import score_results_dir


DEFAULT_RESPONSE_DIR = Path("backend/benchmarks/vsm/results/responses_vsm_all_2026-05-18")


def run_chunked(args: argparse.Namespace) -> dict[str, Any]:
    systems = [item.strip() for item in args.systems.split(",") if item.strip()]
    if not systems:
        raise ValueError("--systems must contain at least one system")

    all_cases = load_vsm_cases(args.dataset)
    cases = _select_cases(all_cases, case_id=args.case_id, case_id_file=args.case_id_file)
    chunks = _make_chunks(cases, args.chunk_size)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    _write_manifest(
        args=args,
        systems=systems,
        cases=cases,
        chunks=chunks,
        raw_dir=raw_dir,
        status="started",
    )

    stopped = False
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        completed = _latest_valid_attempt(raw_dir, chunk_id, chunk["case_ids"], systems)
        if args.resume and completed:
            print(f"[skip] {chunk_id} already completed at {completed}")
            _write_manifest(args=args, systems=systems, cases=cases, chunks=chunks, raw_dir=raw_dir, status="running")
            continue

        attempt_dir = _next_attempt_dir(raw_dir, chunk_id)
        attempt_dir.mkdir(parents=True, exist_ok=True)
        status_path = attempt_dir / "chunk_status.json"
        atomic_write_json(
            status_path,
            {
                "status": "running",
                "chunk_id": chunk_id,
                "case_ids": chunk["case_ids"],
                "started_at": _now(),
            },
        )
        (attempt_dir / "run_config.json").write_text(
            json.dumps(_run_config(args, systems, chunk), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"[run] {chunk_id} -> {attempt_dir}")
        try:
            run_inference(
                dataset=args.dataset,
                out_dir=attempt_dir,
                systems=systems,
                limit=None,
                skip=0,
                case_group=None,
                case_id=",".join(chunk["case_ids"]),
                model_type=args.model_type,
                model=args.model,
                selected_model=args.selected_model,
            )
            validation = _validate_attempt(attempt_dir, chunk["case_ids"], systems)
            status = "completed" if validation["valid"] else "failed_validation"
            if status == "completed" and _bad_chunk(validation, args):
                status = "failed_quality_gate"
            validation["status"] = status
            validation["finished_at"] = _now()
            atomic_write_json(status_path, validation)
            print(f"[{status}] {chunk_id}: {json.dumps(validation, ensure_ascii=False, sort_keys=True)}")
            if status != "completed" and args.stop_on_failed_chunk:
                stopped = True
                break
        except Exception as exc:
            payload = {
                "status": "failed_exception",
                "chunk_id": chunk_id,
                "case_ids": chunk["case_ids"],
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "finished_at": _now(),
            }
            atomic_write_json(status_path, payload)
            print(f"[failed_exception] {chunk_id}: {exc}")
            if args.stop_on_failed_chunk:
                stopped = True
                break
        finally:
            _write_manifest(args=args, systems=systems, cases=cases, chunks=chunks, raw_dir=raw_dir, status="stopped" if stopped else "running")

    completed_dirs = _completed_attempt_dirs(raw_dir, chunks, systems)
    merged_summary: dict[str, Any] = {}
    if completed_dirs:
        merged_dir = args.out_dir / "merged"
        merged_summary = merge_results(completed_dirs, merged_dir)
        _score_and_analyze(merged_dir, args.bad_score_threshold, round_name="round_01", root_out_dir=args.out_dir)

    all_complete = len(completed_dirs) == len(chunks)
    if all_complete:
        final_dir = args.out_dir / "final"
        _copy_result_files(args.out_dir / "merged", final_dir)
        _score_and_analyze(final_dir, args.bad_score_threshold, round_name="round_01", root_out_dir=args.out_dir)
        response_system = systems[0] if len(systems) == 1 else "combined"
        response_summary = export_response_file(
            final_dir / "per_case_results.jsonl",
            final_dir / f"{response_system}.responses.jsonl",
            source_file=str(final_dir / "per_case_results.jsonl"),
        )
        if not args.no_central_export and len(systems) == 1:
            args.response_out_dir.mkdir(parents=True, exist_ok=True)
            central_path = args.response_out_dir / f"{response_system}.responses.jsonl"
            export_response_file(
                final_dir / "per_case_results.jsonl",
                central_path,
                source_file=str(final_dir / "per_case_results.jsonl"),
            )
            update_response_index(args.response_out_dir)
            response_summary["central_file"] = str(central_path)
        atomic_write_json(final_dir / "response_summary.json", response_summary)

    final_status = "completed" if all_complete else "partial"
    _write_manifest(args=args, systems=systems, cases=cases, chunks=chunks, raw_dir=raw_dir, status=final_status)
    return {
        "status": final_status,
        "out_dir": str(args.out_dir),
        "chunks": len(chunks),
        "completed_chunks": len(completed_dirs),
        "selected_cases": len(cases),
        "merged": merged_summary,
    }


def _score_and_analyze(results_dir: Path, threshold: float, *, round_name: str, root_out_dir: Path) -> None:
    score_results_dir(results_dir)
    per_case_rows = read_jsonl(results_dir / "per_case_results.jsonl")
    failure_rows = read_jsonl(results_dir / "failures.jsonl")
    write_bad_case_artifacts(
        output_dir=root_out_dir,
        per_case_rows=per_case_rows,
        failure_rows=failure_rows,
        threshold=threshold,
        round_name=round_name,
    )


def _select_cases(cases: list[VSMCase], *, case_id: str | None, case_id_file: Path | None) -> list[VSMCase]:
    wanted: list[str] = []
    if case_id:
        wanted.extend(item.strip() for item in case_id.split(",") if item.strip())
    if case_id_file:
        wanted.extend(line.strip() for line in case_id_file.read_text(encoding="utf-8").splitlines() if line.strip())
    if not wanted:
        return cases
    wanted_set = set(wanted)
    selected = [case for case in cases if case.case_id in wanted_set]
    missing = sorted(wanted_set - {case.case_id for case in selected})
    if missing:
        raise ValueError(f"Unknown case_id values: {missing}")
    return selected


def _make_chunks(cases: list[VSMCase], chunk_size: int) -> list[dict[str, Any]]:
    if chunk_size < 1:
        raise ValueError("--chunk-size must be >= 1")
    chunks = []
    for start in range(0, len(cases), chunk_size):
        chunk_cases = cases[start : start + chunk_size]
        end = start + len(chunk_cases) - 1
        chunks.append(
            {
                "index": len(chunks),
                "chunk_id": f"chunk_{start:03d}_{end:03d}",
                "start_index": start,
                "end_index": end,
                "case_ids": [case.case_id for case in chunk_cases],
                "turn_count": sum(len(case.turns) for case in chunk_cases),
            }
        )
    return chunks


def _run_config(args: argparse.Namespace, systems: list[str], chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": str(args.dataset),
        "systems": systems,
        "model_type": args.model_type,
        "model": args.model,
        "selected_model": args.selected_model,
        "env_fast_model": os.getenv("FAST_MODEL", ""),
        "env_smart_model": os.getenv("SMART_MODEL", ""),
        "chunk": chunk,
    }


def _attempt_dirs(raw_dir: Path, chunk_id: str) -> list[Path]:
    return sorted(path for path in raw_dir.glob(f"{chunk_id}_attempt_*") if path.is_dir())


def _next_attempt_dir(raw_dir: Path, chunk_id: str) -> Path:
    return raw_dir / f"{chunk_id}_attempt_{len(_attempt_dirs(raw_dir, chunk_id)) + 1:02d}"


def _latest_valid_attempt(raw_dir: Path, chunk_id: str, case_ids: list[str], systems: list[str]) -> Path | None:
    for attempt in reversed(_attempt_dirs(raw_dir, chunk_id)):
        status = _read_json(attempt / "chunk_status.json")
        if status.get("status") == "completed":
            validation = _validate_attempt(attempt, case_ids, systems)
            if validation["valid"]:
                return attempt
    return None


def _completed_attempt_dirs(raw_dir: Path, chunks: list[dict[str, Any]], systems: list[str]) -> list[Path]:
    out = []
    for chunk in chunks:
        attempt = _latest_valid_attempt(raw_dir, chunk["chunk_id"], chunk["case_ids"], systems)
        if attempt:
            out.append(attempt)
    return out


def _validate_attempt(attempt_dir: Path, case_ids: list[str], systems: list[str]) -> dict[str, Any]:
    rows = read_jsonl(attempt_dir / "per_case_results.jsonl")
    failures = read_jsonl(attempt_dir / "failures.jsonl")
    expected_pairs = {(system, case_id) for system in systems for case_id in case_ids}
    actual_pairs = {(str(row.get("system") or ""), str(row.get("case_id") or "")) for row in rows}
    turn_count = sum(len(row.get("turns") or []) for row in rows)
    empty_outputs = sum(
        1
        for row in rows
        for turn in row.get("turns") or []
        if not str(turn.get("assistant") or "").strip()
    )
    exception_count = sum(1 for failure in failures if failure.get("failure_type") == "exception")
    return {
        "attempt_dir": str(attempt_dir),
        "valid": actual_pairs == expected_pairs and len(rows) == len(expected_pairs),
        "expected_rows": len(expected_pairs),
        "actual_rows": len(rows),
        "missing_pairs": sorted([list(pair) for pair in (expected_pairs - actual_pairs)]),
        "extra_pairs": sorted([list(pair) for pair in (actual_pairs - expected_pairs)]),
        "turn_count": turn_count,
        "empty_outputs": empty_outputs,
        "exception_count": exception_count,
        "empty_rate": round(empty_outputs / turn_count, 4) if turn_count else 1.0,
        "exception_rate": round(exception_count / turn_count, 4) if turn_count else 1.0,
    }


def _bad_chunk(validation: dict[str, Any], args: argparse.Namespace) -> bool:
    return (
        float(validation.get("empty_rate") or 0.0) > args.max_empty_rate
        or float(validation.get("exception_rate") or 0.0) > args.max_exception_rate
    )


def _write_manifest(
    *,
    args: argparse.Namespace,
    systems: list[str],
    cases: list[VSMCase],
    chunks: list[dict[str, Any]],
    raw_dir: Path,
    status: str,
) -> None:
    chunk_records = []
    completed_cases = 0
    completed_turns = 0
    for chunk in chunks:
        attempts = []
        latest_status = "pending"
        for attempt in _attempt_dirs(raw_dir, chunk["chunk_id"]):
            status_payload = _read_json(attempt / "chunk_status.json")
            attempts.append({"dir": str(attempt), **status_payload})
            if status_payload.get("status"):
                latest_status = str(status_payload["status"])
        completed = _latest_valid_attempt(raw_dir, chunk["chunk_id"], chunk["case_ids"], systems)
        if completed:
            latest_status = "completed"
            completed_cases += len(chunk["case_ids"])
            completed_turns += chunk["turn_count"]
        chunk_records.append({**chunk, "status": latest_status, "attempts": attempts, "completed_dir": str(completed) if completed else ""})

    summary = summarize_cases(cases)
    manifest = {
        "status": status,
        "updated_at": _now(),
        "dataset": str(args.dataset),
        "out_dir": str(args.out_dir),
        "systems": systems,
        "model_type": args.model_type,
        "model": args.model,
        "selected_model": args.selected_model,
        "env_fast_model": os.getenv("FAST_MODEL", ""),
        "env_smart_model": os.getenv("SMART_MODEL", ""),
        "chunk_size": args.chunk_size,
        "summary": summary,
        "chunks": chunk_records,
    }
    progress = {
        "status": status,
        "updated_at": manifest["updated_at"],
        "case_count": len(cases),
        "turn_count": summary["turns"],
        "chunk_count": len(chunks),
        "completed_chunks": sum(1 for chunk in chunk_records if chunk["status"] == "completed"),
        "completed_cases": completed_cases,
        "completed_turns": completed_turns,
        "remaining_cases": len(cases) - completed_cases,
        "remaining_turns": summary["turns"] - completed_turns,
    }
    atomic_write_json(args.out_dir / "run_manifest.json", manifest)
    atomic_write_json(args.out_dir / "progress.json", progress)


def _copy_result_files(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "per_case_results.jsonl",
        "failures.jsonl",
        "inference_summary.json",
        "judge_results.jsonl",
        "score_summary.json",
        "score_summary.csv",
        "human_audit_template.csv",
    ):
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, dst_dir / name)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VSM inference in resumable chunks.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--systems", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--case-id")
    parser.add_argument("--case-id-file", type=Path)
    parser.add_argument("--model-type", default="deepseek")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--selected-model", default="deepseek")
    parser.add_argument("--bad-score-threshold", type=float, default=85.0)
    parser.add_argument("--max-empty-rate", type=float, default=0.5)
    parser.add_argument("--max-exception-rate", type=float, default=0.5)
    parser.add_argument("--stop-on-failed-chunk", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--response-out-dir", type=Path, default=DEFAULT_RESPONSE_DIR)
    parser.add_argument("--no-central-export", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_chunked(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
