from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.vsm.reporting.report_builder import build_vsm_report
from benchmarks.vsm.runners.run_inference import run_inference
from benchmarks.vsm.scoring.aggregate import build_score_summary, score_results_dir
from benchmarks.vsm.scoring.judge import JUDGE_METRICS


class VSMBenchmarkHardeningTest(unittest.TestCase):
    def test_score_results_creates_judge_ci_and_audit_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            run_inference(
                dataset=Path("backend/benchmarks/vsm/data/vsm_probe.jsonl"),
                out_dir=out_dir,
                systems=["dry_run"],
                limit=3,
            )

            summary = score_results_dir(out_dir)

            self.assertTrue((out_dir / "judge_results.jsonl").exists())
            self.assertTrue((out_dir / "human_audit_template.csv").exists())
            self.assertTrue((out_dir / "score_summary.json").exists())
            self.assertTrue((out_dir / "score_summary.csv").exists())
            self.assertIn("confidence_intervals", summary)
            self.assertIn("dry_run", summary["confidence_intervals"])
            self.assertIn("deterministic_total", summary["overall"]["dry_run"])
            self.assertIn("llm_judge_total", summary["overall"]["dry_run"])
            self.assertIn("final_hybrid_score", summary["overall"]["dry_run"])

    def test_report_builder_uses_real_summary_without_blank_result_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            run_inference(
                dataset=Path("backend/benchmarks/vsm/data/vsm_probe.jsonl"),
                out_dir=out_dir,
                systems=["dry_run"],
                limit=3,
            )
            before = (out_dir / "per_case_results.jsonl").read_text(encoding="utf-8")
            summary = score_results_dir(out_dir)

            build_vsm_report(summary, out_dir)

            after = (out_dir / "per_case_results.jsonl").read_text(encoding="utf-8")
            report = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertIn("Table 6. Confidence Intervals", report)
            self.assertIn("Table 7. Human Audit Status", report)
            self.assertTrue((out_dir / "tables/table_6_confidence_intervals.csv").exists())
            self.assertTrue((out_dir / "tables/table_7_human_audit.csv").exists())

    def test_score_summary_and_report_include_ablation_deltas(self) -> None:
        per_case_rows = [
            _case_row("ours_full", final_hybrid_hint=True, latency_ms=1000.0),
            _case_row("ours_no_peer", final_hybrid_hint=False, latency_ms=500.0),
        ]
        judge_rows = [
            _judge_row("ours_full", score=5),
            _judge_row("ours_no_peer", score=3),
        ]
        summary = build_score_summary(per_case_rows, [], judge_rows)

        self.assertEqual("ours_full", summary["ablation_deltas"][0]["baseline"])
        self.assertEqual("ours_no_peer", summary["ablation_deltas"][0]["variant"])
        self.assertGreater(summary["ablation_deltas"][0]["final_hybrid_delta"], 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            build_vsm_report(summary, out_dir)
            self.assertTrue((out_dir / "tables/table_8_ablation_deltas.csv").exists())
            report = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("Table 8. Ablation Deltas", report)

    def test_failure_rate_excludes_stage_peer_contract_mismatch(self) -> None:
        per_case_rows = [_case_row("ours_full", final_hybrid_hint=False, latency_ms=1000.0)]
        judge_rows = [_judge_row("ours_full", score=3)]
        failure_rows = [
            {
                "system": "ours_full",
                "case_id": "case_1",
                "turn_id": 1,
                "failure_type": "stage_mismatch",
                "severity": "contract",
                "counts_toward_failure_rate": False,
            },
            {
                "system": "ours_full",
                "case_id": "case_1",
                "turn_id": 1,
                "failure_type": "peer_mismatch",
                "severity": "contract",
                "counts_toward_failure_rate": False,
            },
            {
                "system": "ours_full",
                "case_id": "case_1",
                "turn_id": 1,
                "failure_type": "fallback_used",
                "severity": "runtime",
                "counts_toward_failure_rate": True,
            },
        ]

        summary = build_score_summary(per_case_rows, failure_rows, judge_rows)

        self.assertEqual(100.0, summary["overall"]["ours_full"]["failure_rate"])
        self.assertEqual(100.0, summary["overall"]["ours_full"]["contract_mismatch_rate"])
        self.assertEqual(1, summary["failure_taxonomy"]["stage_mismatch"]["ours_full"])
        self.assertEqual(1, summary["failure_taxonomy"]["wrong_peer"]["ours_full"])

    def test_legacy_failure_rows_treat_peer_stage_as_contract_not_runtime(self) -> None:
        per_case_rows = [_case_row("ours_no_peer", final_hybrid_hint=False, latency_ms=1000.0)]
        judge_rows = [_judge_row("ours_no_peer", score=3)]
        failure_rows = [
            {"system": "ours_no_peer", "case_id": "case_1", "turn_id": 1, "failure_type": "peer_mismatch"},
        ]

        summary = build_score_summary(per_case_rows, failure_rows, judge_rows)

        self.assertEqual(0.0, summary["overall"]["ours_no_peer"]["failure_rate"])
        self.assertEqual(100.0, summary["overall"]["ours_no_peer"]["contract_mismatch_rate"])

    def test_crisis_protocol_is_reported_separately_from_fallback(self) -> None:
        per_case_rows = [_case_row("ours_full", final_hybrid_hint=True, latency_ms=1000.0, route="CRISIS")]
        per_case_rows[0]["risk_level"] = "CRISIS"
        per_case_rows[0]["turns"][0]["expected_stage"] = "crisis_response"
        per_case_rows[0]["turns"][0]["deterministic_score"]["crisis_protocol_used"] = True
        judge_rows = [_judge_row("ours_full", score=5)]

        summary = build_score_summary(per_case_rows, [], judge_rows)

        self.assertEqual(100.0, summary["overall"]["ours_full"]["crisis_protocol_rate"])
        self.assertEqual(0.0, summary["overall"]["ours_full"]["fallback_rate"])
        self.assertEqual(100.0, summary["safety"]["ours_full"]["crisis_protocol_rate"])


def _case_row(system: str, *, final_hybrid_hint: bool, latency_ms: float, route: str = "CBT") -> dict:
    score = {
        "forbidden_violation": False,
        "forbidden_hits": [],
        "technique_hint_match": final_hybrid_hint,
        "stage_match": final_hybrid_hint,
        "route_match": True,
        "peer_match": final_hybrid_hint,
        "fallback_used": False,
        "crisis_protocol_used": None,
        "case_formulation_quality": final_hybrid_hint,
        "subtle_risk_detection": None,
        "over_agreement_resistance": True,
        "peer_integration_quality": final_hybrid_hint,
        "cultural_fit_vietnamese_student": True,
        "actionability": final_hybrid_hint,
        "hard_fail": False,
    }
    return {
        "system": system,
        "case_id": "case_1",
        "case_group": "yalom_group_cases",
        "route": route,
        "risk_level": "SAFE",
        "turns": [
            {
                "turn_id": 1,
                "user": "Mình thấy áp lực thi.",
                "assistant": "[Nhà trị liệu]: Mình nghe thấy áp lực thi đang nặng.",
                "expected_peer": "peer_mirror_agent",
                "expected_yalom": ["Universality"],
                "expected_stage": "cbt_stage_1_venting",
                "deterministic_score": score,
                "latency_ms": latency_ms,
            }
        ],
    }


def _judge_row(system: str, *, score: int) -> dict:
    return {
        "system": system,
        "case_id": "case_1",
        "turn_id": 1,
        "scores": {metric: score for metric in JUDGE_METRICS},
    }


if __name__ == "__main__":
    unittest.main()
