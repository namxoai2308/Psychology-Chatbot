from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.vsm.reporting.report_builder import build_vsm_report
from benchmarks.vsm.reporting.sample_data import demo_summary
from benchmarks.vsm.scoring.aggregate import score_results_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build VSM benchmark report tables and figures.")
    parser.add_argument("--summary-json", default="", help="Optional VSM summary JSON. Uses demo data when omitted.")
    parser.add_argument("--results-dir", default="", help="Score and report from a real VSM inference result directory.")
    parser.add_argument("--judge-mode", default="heuristic", choices=["heuristic", "existing"])
    parser.add_argument("--out-dir", required=True, help="Output directory for report artifacts.")
    args = parser.parse_args()

    if args.results_dir:
        summary = score_results_dir(Path(args.results_dir), judge_mode=args.judge_mode)
    elif args.summary_json:
        summary = json.loads(Path(args.summary_json).read_text(encoding="utf-8"))
    else:
        summary = demo_summary()
    paths = build_vsm_report(summary, Path(args.out_dir))
    print(json.dumps({key: str(value) for key, value in paths.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
