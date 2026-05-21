from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.vsm.scoring.aggregate import score_results_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Score VSM inference results and create judge/audit artifacts.")
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--judge-mode", default="heuristic", choices=["heuristic", "existing"])
    args = parser.parse_args()

    summary = score_results_dir(args.results_dir, judge_mode=args.judge_mode)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
