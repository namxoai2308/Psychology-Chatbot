#!/usr/bin/env python3
"""Multi-system conversational rollout + trajectory judge.

From repo `backend/`:
  python -m benchmarks.runners.run_rollout_benchmark \\
    --input benchmarks/data/sample_benchmark_input.jsonl \\
    --out-dir benchmarks/results/rollout_run1 \\
    --model-type deepseek

Optional: --systems base_llm,prompt_1_1 (comma-separated subset).
MindChat/SoulChat: với --model-type deepseek dùng cùng API DeepSeek + persona nhẹ (không cần ngrok).

Systems: base_llm, prompt_1_1, mindchat, soulchat, ours_multi_agent.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from benchmarks.evaluators.axis_summary import axes_from_judge, build_full_axes_report
from benchmarks.evaluators.eval_rollout_judge import judge_trajectory, route_gate, weighted_total
from benchmarks.rollout.adapters import run_baseline_trajectory, run_ours_trajectory
from benchmarks.rollout.schema_cases import load_cases

SYSTEMS = ("base_llm", "prompt_1_1", "mindchat", "soulchat", "ours_multi_agent")


def _flatten_transcript(turns: list[dict]) -> str:
    parts = []
    for t in turns:
        parts.append(f"User: {t['user_msg']}\nAssistant: {t.get('assistant_msg', '')}")
    return "\n\n".join(parts)


async def _one_case_system(case, system: str, model_type: str) -> dict:
    if system == "ours_multi_agent":
        raw = await run_ours_trajectory(case, model_type=model_type)
    else:
        raw = run_baseline_trajectory(system, case.expected_route, case.user_turns, model_type=model_type)
    transcript = raw.get("transcript") or _flatten_transcript(raw["turns"])
    judge = judge_trajectory(
        transcript=transcript,
        expected_route=case.expected_route,
        risk_level=case.risk_level,
        group_track=case.group_track,
        model_type=model_type,
    )
    pred = raw.get("predicted_route") or judge.get("predicted_route")
    rg = route_gate(system, case.expected_route, pred if isinstance(pred, str) else None)
    total = weighted_total(expected_route=case.expected_route, judge=judge, route_gate=rg)
    axes = axes_from_judge(judge, case.expected_route)
    return {
        "case_id": case.case_id,
        "expected_route": case.expected_route,
        "risk_level": case.risk_level,
        "group_track": case.group_track,
        "system_name": system,
        "predicted_route": raw.get("predicted_route"),
        "route_gate": rg,
        "axes": axes,
        "judge": judge,
        "weighted_total": total,
        "turns": raw["turns"],
    }


async def main_async(args: argparse.Namespace) -> None:
    cases = load_cases(Path(args.input))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    systems = tuple(s.strip() for s in args.systems.split(",") if s.strip())
    for s in systems:
        if s not in SYSTEMS:
            raise SystemExit(f"Unknown system {s}. Choose from: {SYSTEMS}")

    rows_by_system: dict[str, list[dict]] = {s: [] for s in systems}

    for system in systems:
        rows = []
        for case in cases:
            row = await _one_case_system(case, system, args.model_type)
            rows.append(row)
        rows_by_system[system] = rows
        out_path = out_dir / f"rollout_{system}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = build_full_axes_report(systems, str(out_dir.resolve()), rows_by_system)
    weighted_only = {s: report["by_system"][s]["weighted_total_mean"] for s in systems}
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "weighted_total_mean_by_system": weighted_only,
                "full_axes_report_file": "benchmark_axes_report.json",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "benchmark_axes_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model-type", default="deepseek")
    ap.add_argument(
        "--systems",
        default=",".join(SYSTEMS),
        help=f"Comma-separated subset of: {','.join(SYSTEMS)}",
    )
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
