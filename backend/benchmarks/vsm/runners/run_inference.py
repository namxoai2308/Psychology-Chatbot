from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.vsm.adapters.systems import Conversation, build_adapter
from benchmarks.vsm.data.schema import VSMCase, default_dataset_path, load_vsm_cases
from benchmarks.vsm.scoring.deterministic import DeterministicTurnScore, score_turn_output


DEFAULT_OUT_DIR = Path("backend/benchmarks/vsm/results/latest")
SYSTEM_VARIANT_BY_NAME = {
    "ours_full": "ours_full",
    "ours_multi_agent": "ours_full",
    "ours_no_peer": "ours_no_peer",
    "ours_no_validator": "ours_no_validator",
    "ours_no_safety_critic": "ours_no_safety_critic",
    "single_agent_stage_prompt": "single_agent_stage_prompt",
    "single_agent_plain": "single_agent_plain",
}
NO_PEER_SYSTEMS = {
    "ours_no_peer",
    "single_agent_stage_prompt",
    "single_agent_plain",
    "base_model",
    "prompt_1_1",
    "mindchat",
    "soulchat",
    "seallm",
    "camel_cbt",
    "camel",
}


def run_inference(
    *,
    dataset: Path,
    out_dir: Path,
    systems: list[str],
    limit: int | None = None,
    skip: int = 0,
    case_group: str | None = None,
    case_id: str | None = None,
    model_type: str = "deepseek",
    model: str = "deepseek-chat",
    selected_model: str = "deepseek",
) -> dict[str, Any]:
    cases = _filter_cases(load_vsm_cases(dataset), limit=limit, skip=skip, case_group=case_group, case_id=case_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_config = _build_run_config(
        dataset=dataset,
        out_dir=out_dir,
        systems=systems,
        cases=cases,
        limit=limit,
        skip=skip,
        case_group=case_group,
        case_id=case_id,
        model_type=model_type,
        model=model,
        selected_model=selected_model,
    )
    (out_dir / "run_config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    per_case_path = out_dir / "per_case_results.jsonl"
    failures_path = out_dir / "failures.jsonl"

    summary_counter: Counter[str] = Counter()
    latency_by_system: dict[str, list[float]] = defaultdict(list)

    with per_case_path.open("w", encoding="utf-8") as per_case_file, failures_path.open("w", encoding="utf-8") as failure_file:
        for system_name in systems:
            adapter = build_adapter(
                system_name,
                model_type=model_type,
                model=model,
                selected_model=selected_model,
            )
            for case in cases:
                adapter.start_case(case)
                case_result, failures, latencies = _run_case(system_name, adapter, case)
                per_case_file.write(json.dumps(case_result, ensure_ascii=False, sort_keys=True) + "\n")
                for failure in failures:
                    failure_file.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
                summary_counter["turns"] += len(case.turns)
                summary_counter["cases"] += 1
                summary_counter["failures"] += len(failures)
                summary_counter["reliability_failures"] += sum(
                    1 for failure in failures if failure.get("counts_toward_failure_rate", True)
                )
                summary_counter["hard_failures"] += sum(1 for failure in failures if failure["failure_type"] == "hard_fail")
                summary_counter[f"system:{system_name}:cases"] += 1
                summary_counter[f"system:{system_name}:turns"] += len(case.turns)
                summary_counter[f"system:{system_name}:failures"] += len(failures)
                summary_counter[f"system:{system_name}:reliability_failures"] += sum(
                    1 for failure in failures if failure.get("counts_toward_failure_rate", True)
                )
                latency_by_system[system_name].extend(latencies)

    summary = _build_summary(
        systems=systems,
        cases=cases,
        counters=summary_counter,
        latency_by_system=latency_by_system,
        dataset=dataset,
        out_dir=out_dir,
    )
    (out_dir / "inference_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def _run_case(system_name: str, adapter: Any, case: VSMCase) -> tuple[dict[str, Any], list[dict[str, Any]], list[float]]:
    history: Conversation = []
    turns: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    latencies: list[float] = []

    for turn in case.turns:
        started = time.perf_counter()
        try:
            response = adapter.generate(case=case, turn=turn, history=history)
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            metadata = _normalize_turn_metadata(system_name, response.metadata, response.text, latency_ms)
            score = score_turn_output(
                case,
                turn,
                response.text,
                observed_stage=metadata.get("observed_stage"),
                observed_route=metadata.get("observed_route"),
                observed_peer=metadata.get("observed_peer"),
                fallback_used=bool(metadata.get("fallback_used")),
                metadata=metadata,
            )
            turn_result = _turn_result(turn, response.text, metadata, score, latency_ms)
            turns.append(turn_result)
            failures.extend(_failures_for_turn(system_name, case, turn, score, metadata))
            history.append({"role": "user", "content": turn.user})
            history.append({"role": "assistant", "content": response.text})
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            error = {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": "exception",
                "severity": "runtime",
                "counts_toward_failure_rate": True,
                "error": str(exc),
            }
            failures.append(error)
            turns.append(
                {
                    "turn_id": turn.turn_id,
                    "user": turn.user,
                    "assistant": "",
                    "latency_ms": round(latency_ms, 2),
                    "error": str(exc),
                    "deterministic_score": None,
                }
            )
            history.append({"role": "user", "content": turn.user})
            history.append({"role": "assistant", "content": ""})

    case_result = {
        "system": system_name,
        "case_id": case.case_id,
        "case_group": case.case_group,
        "route": case.route,
        "risk_level": case.risk_level,
        "difficulty": case.difficulty,
        "benchmark_intent": case.benchmark_intent,
        "turn_count": len(case.turns),
        "turns": turns,
    }
    return case_result, failures, latencies


def _turn_result(
    turn: Any,
    assistant_text: str,
    metadata: dict[str, Any],
    score: DeterministicTurnScore,
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "turn_id": turn.turn_id,
        "user": turn.user,
        "assistant": assistant_text,
        "expected_stage": turn.expected_stage,
        "expected_yalom": turn.expected_yalom,
        "expected_peer": turn.expected_peer,
        "required_technique": turn.required_technique,
        "forbidden_patterns": turn.forbidden_patterns,
        "judge_focus": turn.judge_focus,
        "metadata": metadata,
        "deterministic_score": score.as_dict(),
        "latency_ms": round(latency_ms, 2),
    }


def _normalize_turn_metadata(
    system_name: str,
    metadata: dict[str, Any],
    assistant_text: str,
    latency_ms: float,
) -> dict[str, Any]:
    normalized = dict(metadata)
    normalized["latency_ms"] = round(latency_ms, 2)
    normalized.setdefault("system_variant", SYSTEM_VARIANT_BY_NAME.get(system_name))
    normalized.setdefault("observed_route", None)
    normalized.setdefault("observed_stage", None)
    normalized.setdefault("observed_peer", "NONE" if system_name in NO_PEER_SYSTEMS else None)
    normalized.setdefault("peer_used", False)
    normalized.setdefault("validator_enabled", False)
    normalized.setdefault("safety_critic_enabled", False)
    normalized.setdefault("fallback_used", False)
    normalized.setdefault("crisis_protocol_used", False)
    if not normalized.get("final_output_messages"):
        normalized["final_output_messages"] = (
            [{"sender": "assistant", "text": assistant_text}]
            if assistant_text
            else []
        )
    return normalized


def _failures_for_turn(
    system_name: str,
    case: VSMCase,
    turn: Any,
    score: DeterministicTurnScore,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if score.hard_fail:
        failures.append(
            {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": "hard_fail",
                "severity": "runtime",
                "counts_toward_failure_rate": True,
                "reason": "forbidden_pattern",
                "forbidden_hits": score.forbidden_hits,
            }
        )
    if score.stage_match is False:
        failures.append(
            {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": "stage_mismatch",
                "severity": "contract",
                "counts_toward_failure_rate": False,
                "expected": turn.expected_stage,
                "actual": metadata.get("observed_stage"),
            }
        )
    if score.route_match is False:
        failures.append(
            {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": "route_mismatch",
                "severity": "runtime",
                "counts_toward_failure_rate": True,
                "expected": case.route,
                "actual": metadata.get("observed_route"),
            }
        )
    if score.peer_match is False:
        failure_type = (
            "peer_capability_absent"
            if system_name in NO_PEER_SYSTEMS and metadata.get("observed_peer") == "NONE" and turn.expected_peer != "NONE"
            else "peer_mismatch"
        )
        failures.append(
            {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": failure_type,
                "severity": "capability" if failure_type == "peer_capability_absent" else "contract",
                "counts_toward_failure_rate": False,
                "expected": turn.expected_peer,
                "actual": metadata.get("observed_peer"),
            }
        )
    if score.fallback_used:
        failures.append(
            {
                "system": system_name,
                "case_id": case.case_id,
                "turn_id": turn.turn_id,
                "failure_type": "fallback_used",
                "severity": "runtime",
                "counts_toward_failure_rate": True,
            }
        )
    return failures


def _filter_cases(
    cases: list[VSMCase],
    *,
    limit: int | None,
    skip: int = 0,
    case_group: str | None,
    case_id: str | None,
) -> list[VSMCase]:
    filtered = cases
    if case_group:
        filtered = [case for case in filtered if case.case_group == case_group]
    if case_id:
        wanted = {item.strip() for item in case_id.split(",") if item.strip()}
        filtered = [case for case in filtered if case.case_id in wanted]
    if skip:
        filtered = filtered[skip:]
    if limit is not None:
        filtered = filtered[:limit]
    if not filtered:
        raise ValueError("No VSM cases matched the requested filters.")
    return filtered


def _build_summary(
    *,
    systems: list[str],
    cases: list[VSMCase],
    counters: Counter[str],
    latency_by_system: dict[str, list[float]],
    dataset: Path,
    out_dir: Path,
) -> dict[str, Any]:
    system_summary = {}
    for system in systems:
        latencies = latency_by_system.get(system, [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        system_summary[system] = {
            "cases": counters[f"system:{system}:cases"],
            "turns": counters[f"system:{system}:turns"],
            "failures": counters[f"system:{system}:failures"],
            "reliability_failures": counters[f"system:{system}:reliability_failures"],
            "avg_latency_ms": round(avg_latency, 2),
        }
    return {
        "dataset": str(dataset),
        "out_dir": str(out_dir),
        "run_config": "run_config.json",
        "selected_case_ids": [case.case_id for case in cases],
        "systems": system_summary,
        "case_count": len(cases),
        "turn_count": sum(len(case.turns) for case in cases),
        "result_rows": counters["cases"],
        "result_turns": counters["turns"],
        "failures": counters["failures"],
        "reliability_failures": counters["reliability_failures"],
        "hard_failures": counters["hard_failures"],
    }


def _build_run_config(
    *,
    dataset: Path,
    out_dir: Path,
    systems: list[str],
    cases: list[VSMCase],
    limit: int | None,
    skip: int,
    case_group: str | None,
    case_id: str | None,
    model_type: str,
    model: str,
    selected_model: str,
) -> dict[str, Any]:
    return {
        "dataset": str(dataset),
        "out_dir": str(out_dir),
        "systems": systems,
        "filters": {
            "limit": limit,
            "skip": skip,
            "case_group": case_group,
            "case_id": case_id,
        },
        "model_type": model_type,
        "model": model,
        "selected_model": selected_model,
        "env": {
            "FAST_MODEL": os.getenv("FAST_MODEL", ""),
            "SMART_MODEL": os.getenv("SMART_MODEL", ""),
        },
        "git_commit": _git_commit(),
        "selected_case_ids": [case.case_id for case in cases],
        "case_count": len(cases),
        "turn_count": sum(len(case.turns) for case in cases),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VSM inference for one or more systems.")
    parser.add_argument("--dataset", type=Path, default=default_dataset_path())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--systems", default="dry_run")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--case-group")
    parser.add_argument("--case-id")
    parser.add_argument("--model-type", default="deepseek")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--selected-model", default="deepseek")
    args = parser.parse_args()

    systems = [system.strip() for system in args.systems.split(",") if system.strip()]
    summary = run_inference(
        dataset=args.dataset,
        out_dir=args.out_dir,
        systems=systems,
        limit=args.limit,
        skip=args.skip,
        case_group=args.case_group,
        case_id=args.case_id,
        model_type=args.model_type,
        model=args.model,
        selected_model=args.selected_model,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
