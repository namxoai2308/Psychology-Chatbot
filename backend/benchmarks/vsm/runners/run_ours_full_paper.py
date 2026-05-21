from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO


BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.vsm.data.schema import load_vsm_cases, summarize_cases
from benchmarks.vsm.runners.run_chunked_inference import run_chunked
from benchmarks.vsm.runners.run_llm_comparative_judge import run_comparative_judge
from benchmarks.vsm.scoring.aggregate import score_results_dir


DEFAULT_DATASET = Path("backend/benchmarks/vsm/data/vsm_session_core.jsonl")
DEFAULT_SYSTEM = "ours_full"
DEFAULT_MODEL_TYPE = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_SELECTED_MODEL = "deepseek"
DEFAULT_RESPONSE_DIR = Path("backend/benchmarks/vsm/results/responses_vsm_all_2026-05-18")


class Tee:
    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams

    def write(self, data: str) -> int:
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


@contextmanager
def tee_output(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = Tee(old_stdout, log_file)  # type: ignore[assignment]
        sys.stderr = Tee(old_stderr, log_file)  # type: ignore[assignment]
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def load_dotenv_safe(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def timestamped_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(f"backend/benchmarks/vsm/results/ours_full_vsm_core_100_{stamp}")


def selected_case_arg(dataset: Path, *, case_id: str | None, limit_cases: int | None) -> str | None:
    cases = load_vsm_cases(dataset)
    if case_id:
        wanted = [item.strip() for item in case_id.split(",") if item.strip()]
        wanted_set = set(wanted)
        known = {case.case_id for case in cases}
        missing = sorted(wanted_set - known)
        if missing:
            raise ValueError(f"Unknown case_id values: {missing}")
        selected = [case.case_id for case in cases if case.case_id in wanted_set]
        selected.sort(key=wanted.index)
    else:
        selected = [case.case_id for case in cases]
    if limit_cases is not None:
        if limit_cases < 1:
            raise ValueError("--limit-cases must be >= 1")
        selected = selected[:limit_cases]
    if len(selected) == len(cases) and not case_id and limit_cases is None:
        return None
    return ",".join(selected)


def result_dir_for_judge(out_dir: Path) -> Path:
    final_dir = out_dir / "final"
    merged_dir = out_dir / "merged"
    if final_dir.exists() and (final_dir / "per_case_results.jsonl").exists():
        return final_dir
    if merged_dir.exists() and (merged_dir / "per_case_results.jsonl").exists():
        return merged_dir
    if (out_dir / "per_case_results.jsonl").exists():
        return out_dir
    raise FileNotFoundError(f"No per_case_results.jsonl found under {out_dir}")


def print_json(label: str, payload: Any) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def preflight(args: argparse.Namespace) -> list[str]:
    load_dotenv_safe(REPO_ROOT / ".env")
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("[warn] DEEPSEEK_API_KEY is not set. DeepSeek calls may fail.")
    cases = load_vsm_cases(args.dataset)
    case_arg = selected_case_arg(args.dataset, case_id=args.case_id, limit_cases=args.limit_cases)
    selected_ids = set(case_arg.split(",")) if case_arg else {case.case_id for case in cases}
    selected_cases = [case for case in cases if case.case_id in selected_ids]
    print_json("dataset", summarize_cases(selected_cases))
    print(f"[config] system={DEFAULT_SYSTEM}")
    print(f"[config] model_type={args.model_type} model={args.model} selected_model={args.selected_model}")
    print(f"[config] out_dir={args.out_dir}")
    print(f"[config] chunk_size={args.chunk_size} resume={args.resume}")
    return [case.case_id for case in selected_cases]


def run_inference_chunks(args: argparse.Namespace, case_ids: list[str]) -> dict[str, Any]:
    chunk_args = argparse.Namespace(
        dataset=args.dataset,
        systems=DEFAULT_SYSTEM,
        out_dir=args.out_dir,
        chunk_size=args.chunk_size,
        resume=args.resume,
        case_id=",".join(case_ids) if case_ids else None,
        case_id_file=None,
        model_type=args.model_type,
        model=args.model,
        selected_model=args.selected_model,
        bad_score_threshold=args.bad_score_threshold,
        max_empty_rate=args.max_empty_rate,
        max_exception_rate=args.max_exception_rate,
        stop_on_failed_chunk=args.stop_on_failed_chunk,
        response_out_dir=args.response_out_dir,
        no_central_export=args.no_central_export,
    )
    return run_chunked(chunk_args)


def run_judge(args: argparse.Namespace, results_dir: Path) -> dict[str, Any]:
    judge_args = argparse.Namespace(
        results_dir=results_dir,
        dataset=args.dataset,
        systems=DEFAULT_SYSTEM,
        model_type=args.model_type,
        model=args.model,
        limit_cases=args.judge_limit_cases or 0,
        max_response_chars=args.max_response_chars,
        sleep_seconds=args.judge_sleep_seconds,
        resume=True,
    )
    return run_comparative_judge(judge_args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-command paper runner for ours_full on VSM core with resumable chunks and readable logs."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--run-judge", action="store_true")
    parser.add_argument("--judge-only", action="store_true")
    parser.add_argument("--limit-cases", type=int)
    parser.add_argument("--case-id")
    parser.add_argument("--model-type", default=DEFAULT_MODEL_TYPE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--selected-model", default=DEFAULT_SELECTED_MODEL)
    parser.add_argument("--judge-limit-cases", type=int, default=0)
    parser.add_argument("--judge-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--max-response-chars", type=int, default=900)
    parser.add_argument("--bad-score-threshold", type=float, default=85.0)
    parser.add_argument("--max-empty-rate", type=float, default=0.5)
    parser.add_argument("--max-exception-rate", type=float, default=0.5)
    parser.add_argument("--stop-on-failed-chunk", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--response-out-dir", type=Path, default=DEFAULT_RESPONSE_DIR)
    parser.add_argument("--no-central-export", action="store_true")
    args = parser.parse_args()

    args.out_dir = args.out_dir or timestamped_out_dir()
    log_path = args.out_dir / "run.log"

    with tee_output(log_path):
        print("=" * 80)
        print("ours_full VSM paper runner")
        print(f"started_at={datetime.now().isoformat(timespec='seconds')}")
        print(f"log_path={log_path}")
        print("=" * 80)

        case_ids = preflight(args)

        if not args.judge_only:
            print("\n=== inference ===")
            summary = run_inference_chunks(args, case_ids)
            print_json("inference_result", summary)
        else:
            print("\n=== inference skipped: judge-only mode ===")

        results_dir = result_dir_for_judge(args.out_dir)
        print(f"\n[results] active_results_dir={results_dir}")

        if args.run_judge or args.judge_only:
            print("\n=== llm judge ===")
            judge_summary = run_judge(args, results_dir)
            print_json("judge_result", judge_summary)
            print("\n=== score with existing judge ===")
            score_summary = score_results_dir(results_dir, judge_mode="existing")
        else:
            print("\n=== score with heuristic judge ===")
            score_summary = score_results_dir(results_dir, judge_mode="heuristic")

        overall = score_summary.get("overall", {})
        print_json("score_overall", overall)
        print("\nDone.")
        print(f"PDF paper work can continue while logs live at: {log_path}")


if __name__ == "__main__":
    main()
