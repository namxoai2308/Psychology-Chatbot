"""Chạy full rollout benchmark trong package `benchmarks` (DeepSeek mặc định).

Notebook / script:
    from benchmarks.rollout_full import run_rollout_full_sync
    summary = run_rollout_full_sync()
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# backend/ (chứa package benchmarks)
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = _BACKEND.parent
    load_dotenv(root / ".env")
    load_dotenv(_BACKEND / ".env")


async def run_rollout_full(
    *,
    input_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    model_type: str = "deepseek",
    systems: str = "base_llm,prompt_1_1,mindchat,soulchat,ours_multi_agent",
) -> dict[str, Any]:
    _load_env()
    if not os.getenv("DEEPSEEK_API_KEY") and model_type == "deepseek":
        print("Cảnh báo: DEEPSEEK_API_KEY chưa set.")

    inp = Path(input_path) if input_path else _BACKEND / "benchmarks" / "data" / "sample_benchmark_input.jsonl"
    out = Path(out_dir) if out_dir else _BACKEND / "benchmarks" / "results" / "rollout_notebook"
    inp = inp.resolve()
    out = out.resolve()

    from argparse import Namespace

    from benchmarks.runners.run_rollout_benchmark import main_async

    await main_async(
        Namespace(
            input=str(inp),
            out_dir=str(out),
            model_type=model_type,
            systems=systems,
        )
    )
    summary_file = out / "summary.json"
    axes_file = out / "benchmark_axes_report.json"
    return {
        "summary": json.loads(summary_file.read_text(encoding="utf-8")),
        "axes_report": json.loads(axes_file.read_text(encoding="utf-8")),
        "out_dir": str(out),
    }


def run_rollout_full_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_rollout_full(**kwargs))


if __name__ == "__main__":
    r = run_rollout_full_sync()
    print(json.dumps(r["axes_report"], ensure_ascii=False, indent=2))
    print("out_dir:", r["out_dir"])
