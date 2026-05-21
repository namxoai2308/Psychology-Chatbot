from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.graph.variants import SystemVariant
from benchmarks.vsm.adapters.systems import OursVariantAdapter, _final_output_to_text, _observed_peer, build_adapter
from benchmarks.vsm.data.schema import load_vsm_cases
from benchmarks.vsm.runners.run_inference import _normalize_turn_metadata, run_inference


class FakeBenchmarkApp:
    def __init__(self, final_state: dict):
        self.final_state = final_state
        self.last_input_state = {}

    async def ainvoke(self, input_state: dict, config: dict):
        self.last_input_state = input_state
        return self.final_state


class VSMInferenceRunnerTest(unittest.TestCase):
    def test_ours_output_preserves_approved_group_messages(self) -> None:
        final_output = [
            {"sender": "Nam", "text": "Nghe như áp lực này khiến bạn thấy mình khá đơn độc."},
            {"sender": "Nhà trị liệu", "text": "Mình nghe thấy áp lực thi đang rất nặng với bạn."},
            {"sender": "Linh", "text": "Chị từng có lúc thấy bế tắc, rồi bắt đầu lại từ một bước rất nhỏ."},
        ]

        text = _final_output_to_text(final_output)

        self.assertIn("[Nam]: Nghe như áp lực", text)
        self.assertIn("[Nhà trị liệu]: Mình nghe thấy", text)
        self.assertIn("[Linh]: Chị từng", text)
        self.assertEqual("MULTIPLE", _observed_peer(final_output))

    def test_ours_output_maps_display_peer_to_internal_peer_id(self) -> None:
        self.assertEqual(
            "peer_mirror_agent",
            _observed_peer([{"sender": "Nam", "text": "Một phản chiếu ngắn."}]),
        )
        self.assertEqual(
            "veteran_peer_agent",
            _observed_peer([{"sender": "Linh", "text": "Một hy vọng ngắn."}]),
        )

    def test_dry_run_writes_result_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "results"
            summary = run_inference(
                dataset=Path("backend/benchmarks/vsm/data/vsm_cases.jsonl"),
                out_dir=out_dir,
                systems=["dry_run"],
                limit=3,
            )

            per_case_path = out_dir / "per_case_results.jsonl"
            failures_path = out_dir / "failures.jsonl"
            summary_path = out_dir / "inference_summary.json"

            self.assertTrue(per_case_path.exists())
            self.assertTrue(failures_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertEqual(3, summary["case_count"])
            self.assertEqual(3, summary["systems"]["dry_run"]["cases"])

            rows = [
                json.loads(line)
                for line in per_case_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(3, len(rows))
            self.assertTrue(all(row["system"] == "dry_run" for row in rows))
            self.assertTrue(all(row["turns"] for row in rows))
            self.assertTrue(all("deterministic_score" in row["turns"][0] for row in rows))

    def test_dry_run_supports_case_group_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "results"
            summary = run_inference(
                dataset=Path("backend/benchmarks/vsm/data/vsm_cases.jsonl"),
                out_dir=out_dir,
                systems=["dry_run"],
                case_group="safety_adversarial_cases",
                limit=2,
            )

            self.assertEqual(2, summary["case_count"])
            rows = [
                json.loads(line)
                for line in (out_dir / "per_case_results.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual({"safety_adversarial_cases"}, {row["case_group"] for row in rows})

    def test_ours_structural_runs_without_llm_metadata_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "results"
            summary = run_inference(
                dataset=Path("backend/benchmarks/vsm/data/vsm_probe.jsonl"),
                out_dir=out_dir,
                systems=["ours_structural"],
                limit=1,
            )

            self.assertEqual(1, summary["case_count"])
            rows = [
                json.loads(line)
                for line in (out_dir / "per_case_results.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            metadata = rows[0]["turns"][0]["metadata"]
            self.assertTrue(metadata["llm_disabled"])
            self.assertIn("observed_stage", metadata)
            self.assertIn("observed_route", metadata)
            self.assertIn("observed_peer", metadata)

    def test_metadata_normalizer_gives_text_baselines_full_contract(self) -> None:
        metadata = _normalize_turn_metadata("prompt_1_1", {}, "Một phản hồi hỗ trợ.", 12.345)

        self.assertIsNone(metadata["system_variant"])
        self.assertIsNone(metadata["observed_stage"])
        self.assertIsNone(metadata["observed_route"])
        self.assertEqual("NONE", metadata["observed_peer"])
        self.assertFalse(metadata["peer_used"])
        self.assertFalse(metadata["validator_enabled"])
        self.assertFalse(metadata["safety_critic_enabled"])
        self.assertFalse(metadata["fallback_used"])
        self.assertFalse(metadata["crisis_protocol_used"])
        self.assertEqual(12.35, metadata["latency_ms"])
        self.assertEqual([{"sender": "assistant", "text": "Một phản hồi hỗ trợ."}], metadata["final_output_messages"])

    def test_metadata_normalizer_maps_legacy_ours_alias_to_full_variant(self) -> None:
        metadata = _normalize_turn_metadata("ours_multi_agent", {}, "Một phản hồi hỗ trợ.", 1.0)

        self.assertEqual("ours_full", metadata["system_variant"])

    def test_build_adapter_supports_paper_variant_names(self) -> None:
        expected = {
            "ours_full": SystemVariant.OURS_FULL,
            "ours_multi_agent": SystemVariant.OURS_FULL,
            "ours_no_peer": SystemVariant.OURS_NO_PEER,
            "ours_no_validator": SystemVariant.OURS_NO_VALIDATOR,
            "ours_no_safety_critic": SystemVariant.OURS_NO_SAFETY_CRITIC,
            "single_agent_stage_prompt": SystemVariant.SINGLE_AGENT_STAGE_PROMPT,
            "single_agent_plain": SystemVariant.SINGLE_AGENT_PLAIN,
        }
        for system_name, variant in expected.items():
            with self.subTest(system_name=system_name):
                adapter = build_adapter(system_name)
                self.assertIsInstance(adapter, OursVariantAdapter)
                self.assertEqual(adapter.system_name, system_name)
                self.assertEqual(adapter.system_variant, variant)

    def test_build_adapter_rejects_unknown_system(self) -> None:
        with self.assertRaises(ValueError):
            build_adapter("not_a_real_system")

    def test_ours_no_peer_metadata_is_explicit_without_peer(self) -> None:
        case = load_vsm_cases("backend/benchmarks/vsm/data/vsm_probe.jsonl")[0]
        turn = case.turns[0]
        adapter = OursVariantAdapter(
            system_name="ours_no_peer",
            system_variant=SystemVariant.OURS_NO_PEER,
            selected_model="gemini",
        )
        fake_app = FakeBenchmarkApp(
            {
                "system_variant": "ours_no_peer",
                "current_stage": turn.expected_stage,
                "therapy_route": case.route,
                "peer_used": False,
                "validator_enabled": True,
                "safety_critic_enabled": True,
                "fallback_used": False,
                "required_yalom_factors": turn.expected_yalom,
                "final_output": [{"sender": "Nhà trị liệu", "text": "Mình nghe bạn đang rất áp lực."}],
            }
        )
        adapter._app = fake_app

        response = adapter.generate(case=case, turn=turn, history=[])

        self.assertEqual(response.metadata["system_variant"], "ours_no_peer")
        self.assertEqual(response.metadata["observed_peer"], "NONE")
        self.assertFalse(response.metadata["peer_used"])
        self.assertTrue(response.metadata["validator_enabled"])
        self.assertTrue(response.metadata["safety_critic_enabled"])
        self.assertEqual(fake_app.last_input_state["system_variant"], "ours_no_peer")
        self.assertFalse(fake_app.last_input_state["peer_enabled"])

    def test_ours_full_metadata_marks_visible_peer_used(self) -> None:
        case = load_vsm_cases("backend/benchmarks/vsm/data/vsm_probe.jsonl")[0]
        turn = case.turns[0]
        adapter = OursVariantAdapter(
            system_name="ours_full",
            system_variant=SystemVariant.OURS_FULL,
            selected_model="gemini",
        )
        fake_app = FakeBenchmarkApp(
            {
                "system_variant": "ours_full",
                "current_stage": turn.expected_stage,
                "therapy_route": case.route,
                "peer_used": False,
                "validator_enabled": True,
                "safety_critic_enabled": True,
                "fallback_used": False,
                "required_yalom_factors": turn.expected_yalom,
                "final_output": [
                    {"sender": "Nam", "text": "Nghe như bạn không phải người duy nhất thấy áp lực thi như vậy."},
                    {"sender": "Nhà trị liệu", "text": "Mình nghe bạn đang rất áp lực."},
                ],
            }
        )
        adapter._app = fake_app

        response = adapter.generate(case=case, turn=turn, history=[])

        self.assertEqual(response.metadata["observed_peer"], "peer_mirror_agent")
        self.assertTrue(response.metadata["peer_used"])

    def test_single_agent_plain_metadata_does_not_fake_stage_or_peer(self) -> None:
        case = load_vsm_cases("backend/benchmarks/vsm/data/vsm_probe.jsonl")[0]
        turn = case.turns[0]
        adapter = OursVariantAdapter(
            system_name="single_agent_plain",
            system_variant=SystemVariant.SINGLE_AGENT_PLAIN,
            selected_model="gemini",
        )
        fake_app = FakeBenchmarkApp(
            {
                "system_variant": "single_agent_plain",
                "current_stage": None,
                "therapy_route": None,
                "peer_used": False,
                "validator_enabled": False,
                "safety_critic_enabled": True,
                "fallback_used": False,
                "final_output": [{"sender": "Nhà trị liệu", "text": "Mình đang lắng nghe bạn."}],
            }
        )
        adapter._app = fake_app

        response = adapter.generate(case=case, turn=turn, history=[])

        self.assertIn("Mình đang lắng nghe", response.text)
        self.assertEqual(response.metadata["system_variant"], "single_agent_plain")
        self.assertEqual(response.metadata["observed_peer"], "NONE")
        self.assertIsNone(response.metadata["observed_stage"])
        self.assertFalse(response.metadata["peer_used"])
        self.assertFalse(response.metadata["validator_enabled"])

    def test_crisis_protocol_metadata_is_preserved_for_scoring(self) -> None:
        case = next(case for case in load_vsm_cases() if case.case_id == "vsm_safety_001_direct_self_harm")
        turn = case.turns[0]
        adapter = OursVariantAdapter(
            system_name="ours_full",
            system_variant=SystemVariant.OURS_FULL,
            selected_model="gemini",
        )
        fake_app = FakeBenchmarkApp(
            {
                "system_variant": "ours_full",
                "current_stage": "crisis_response",
                "therapy_route": "CRISIS",
                "peer_used": False,
                "validator_enabled": True,
                "safety_critic_enabled": True,
                "fallback_used": False,
                "crisis_protocol_used": True,
                "required_yalom_factors": ["NONE"],
                "final_output": [
                    {
                        "sender": "Nhà trị liệu",
                        "text": "Nếu bạn đang gặp nguy hiểm, hãy gọi dịch vụ khẩn cấp và liên hệ người tin cậy ngay.",
                    }
                ],
            }
        )
        adapter._app = fake_app

        response = adapter.generate(case=case, turn=turn, history=[])

        self.assertTrue(response.metadata["crisis_protocol_used"])
        self.assertFalse(response.metadata["fallback_used"])


if __name__ == "__main__":
    unittest.main()
