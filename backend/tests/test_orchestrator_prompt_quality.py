from __future__ import annotations

import unittest
from pathlib import Path

from ai_engine.services.clinical_knowledge import stage_knowledge


PROMPT_PATH = Path(__file__).resolve().parents[1] / "ai_engine" / "prompts" / "group_therapy" / "orchestrator.txt"


class OrchestratorPromptQualityTests(unittest.TestCase):
    def test_prompt_contains_validator_anchor_section(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.assertIn("VALIDATOR ANCHORS", prompt)
        self.assertIn("CBT Stage 5", prompt)
        self.assertIn("MBI Stage 4", prompt)
        self.assertIn("BA Stage 1", prompt)
        self.assertIn("doctor_speech có chứa validator anchor", prompt)

    def test_stage_knowledge_exposes_anchors_for_recent_fallback_stages(self) -> None:
        cbt = stage_knowledge("CBT", "cbt_stage_5_action")
        self.assertIn("Validator anchors", cbt)
        self.assertIn("không có nghĩa", cbt)
        self.assertIn("bước nhỏ", cbt)

        mbi = stage_knowledge("MBI", "mbi_stage_4_mindful_action")
        self.assertIn("Validator anchors", mbi)
        self.assertIn("uống nước", mbi)
        self.assertIn("vươn vai", mbi)

        ba = stage_knowledge("BA", "ba_stage_1_energy_check")
        self.assertIn("Validator anchors", ba)
        self.assertIn("năng lượng", ba)
        self.assertIn("0 đến 10", ba)

    def test_anchor_examples_pass_existing_validators(self) -> None:
        from ai_engine.blackboard.route_response_validator import validate_therapist_response

        cases = [
            (
                "cbt_stage_5_action",
                "Một kết quả chưa tốt không có nghĩa là hết cơ hội. Một bước nhỏ hôm nay bạn muốn thử là gì?",
            ),
            (
                "mbi_stage_4_mindful_action",
                "Mình khép lại bằng một việc nhỏ: uống nước hoặc vươn vai chậm 30 giây.",
            ),
            (
                "ba_stage_1_energy_check",
                "Nghe như bạn đang rất cạn pin. Nếu chấm năng lượng từ 0 đến 10, bạn đang ở mức nào?",
            ),
        ]
        for stage, speech in cases:
            with self.subTest(stage=stage):
                self.assertTrue(validate_therapist_response(stage, speech, "").valid)


if __name__ == "__main__":
    unittest.main()
