from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from benchmarks.vsm.reporting.report_builder import build_vsm_report
from benchmarks.vsm.reporting.sample_data import demo_summary


class VSMReportBuilderTests(unittest.TestCase):
    def test_report_builder_creates_tables_figures_and_markdown_without_axis_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            build_vsm_report(demo_summary(), out_dir)

            expected_tables = [
                "table_1_overall_leaderboard.csv",
                "table_2_route_performance.csv",
                "table_3_safety.csv",
                "table_4_yalom_group.csv",
                "table_5_failure_taxonomy.csv",
            ]
            expected_figures = [
                "fig_1_overall_radar.png",
                "fig_2_route_grouped_bar.png",
                "fig_3_safety_heatmap.png",
                "fig_4_yalom_dynamics.png",
                "fig_5_failure_stacked_bar.png",
                "fig_6_fallback_by_stage.png",
                "fig_7_cost_latency_scatter.png",
            ]

            for filename in expected_tables:
                path = out_dir / "tables" / filename
                self.assertTrue(path.exists(), filename)
                self.assertGreater(path.stat().st_size, 0)
            for filename in expected_figures:
                path = out_dir / "figures" / filename
                self.assertTrue(path.exists(), filename)
                self.assertGreater(path.stat().st_size, 0)

            report = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("Clinical Safety", report)
            self.assertIn("Therapeutic Quality", report)
            self.assertIn("Group Therapy Dynamics", report)
            self.assertNotIn("Axis A", report)
            self.assertNotIn("Axis B", report)
            self.assertNotIn("Axis 1", report)
            self.assertNotIn("Axis 2", report)

    def test_overall_leaderboard_has_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            build_vsm_report(demo_summary(), out_dir)
            with (out_dir / "tables" / "table_1_overall_leaderboard.csv").open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertEqual(
                    reader.fieldnames,
                    [
                        "System",
                        "VSM Total",
                        "Clinical Safety",
                        "Therapeutic Quality",
                        "Modality Fidelity",
                        "Group Therapy Dynamics",
                        "Reliability",
                        "Fallback Rate",
                        "Avg Latency",
                    ],
                )


if __name__ == "__main__":
    unittest.main()
