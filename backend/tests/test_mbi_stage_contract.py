from __future__ import annotations

import unittest

from ai_engine.blackboard.mbi_contract import mbi_allowed_yalom, mbi_default_yalom
from ai_engine.blackboard.route_response_validator import validate_therapist_response
from ai_engine.blackboard.stage_detector import detect_stage
from ai_engine.services.clinical_knowledge import stage_knowledge


GOLDEN_CASES = [
    ("Mình đang hoảng, tim đập nhanh và khó thở.", None, "mbi_stage_1_grounding", ["NONE"]),
    ("Đầu mình quay cuồng, người run lên.", None, "mbi_stage_1_grounding", ["NONE"]),
    ("Mình ngộp quá, không thở nổi.", None, "mbi_stage_1_grounding", ["NONE"]),
    ("Mình thấy hoảng trước khi vào phòng thi.", None, "mbi_stage_1_grounding", ["NONE"]),
    ("Tim mình đập mạnh, tay cứ run.", None, "mbi_stage_1_grounding", ["NONE"]),
    ("Mình đỡ hơn một chút nhưng suy nghĩ vẫn chạy vòng vòng.", "mbi_stage_1_grounding", "mbi_stage_2_decentering", ["NONE"]),
    ("Ý nghĩ đó cứ xuất hiện lại và mình bị cuốn theo.", "mbi_stage_1_grounding", "mbi_stage_2_decentering", ["NONE"]),
    ("Mình thở chậm lại rồi, nhưng vẫn nghĩ nhiều.", "mbi_stage_1_grounding", "mbi_stage_2_decentering", ["NONE"]),
    ("Mình đang có suy nghĩ rằng mọi thứ sẽ tệ.", "mbi_stage_1_grounding", "mbi_stage_2_decentering", ["NONE"]),
    ("Mình biết đó là ý nghĩ nhưng vẫn bị cuốn.", "mbi_stage_1_grounding", "mbi_stage_2_decentering", ["NONE"]),
    ("Mình thấy nặng ở ngực.", "mbi_stage_2_decentering", "mbi_stage_3_body_scan", ["NONE"]),
    ("Vai mình căng và cổ họng nghẹn.", "mbi_stage_2_decentering", "mbi_stage_3_body_scan", ["NONE"]),
    ("Cảm giác nằm ở bụng, hơi đau và co lại.", "mbi_stage_2_decentering", "mbi_stage_3_body_scan", ["NONE"]),
    ("Mình nhận ra vai gáy rất mỏi.", "mbi_stage_2_decentering", "mbi_stage_3_body_scan", ["NONE"]),
    ("Ngực mình nhẹ hơn nhưng vẫn còn căng.", "mbi_stage_2_decentering", "mbi_stage_3_body_scan", ["NONE"]),
    ("Mình thấy dịu hơn rồi, có thể uống nước một chút.", "mbi_stage_3_body_scan", "mbi_stage_4_mindful_action", ["Hope"]),
    ("Mình ổn hơn và muốn vươn vai chậm.", "mbi_stage_3_body_scan", "mbi_stage_4_mindful_action", ["Hope"]),
    ("Mình bớt hoảng rồi, nhìn ra cửa sổ 30 giây được.", "mbi_stage_3_body_scan", "mbi_stage_4_mindful_action", ["Hope"]),
    ("Mình nhẹ hơn, chắc đứng dậy đi chậm một vòng được.", "mbi_stage_3_body_scan", "mbi_stage_4_mindful_action", ["Hope"]),
    ("Mình đã cảm nhận bàn chân chạm sàn và đỡ hơn.", "mbi_stage_3_body_scan", "mbi_stage_4_mindful_action", ["Hope"]),
]


VALID_SPEECH = {
    "mbi_stage_1_grounding": "Mình tạm chưa phân tích nhé. Bạn thử thở ra chậm và cảm nhận bàn chân đang chạm sàn.",
    "mbi_stage_2_decentering": "Bạn thử gọi tên nhẹ: mình đang có suy nghĩ rằng mọi thứ sẽ tệ, rồi quan sát ý nghĩ đó đi qua.",
    "mbi_stage_3_body_scan": "Mình đưa chú ý về cơ thể: cảm giác ở ngực hay vai đang rõ hơn?",
    "mbi_stage_4_mindful_action": "Bạn chọn một bước nhỏ có chánh niệm: uống nước, vươn vai, hoặc nhìn ra xa 30 giây.",
}


INVALID_SPEECH = {
    "mbi_stage_1_grounding": "Có bằng chứng nào cho thấy suy nghĩ đó đúng 100% không?",
    "mbi_stage_2_decentering": "Đây là lỗi tư duy thảm họa hóa, mình phân tích nhé.",
    "mbi_stage_3_body_scan": "Mình sẽ hỏi bằng chứng để phản biện suy nghĩ này.",
    "mbi_stage_4_mindful_action": "Mình phân tích thêm lỗi tư duy trước khi làm gì.",
}


class MBIStageContractTests(unittest.TestCase):
    def test_20_golden_stage_and_yalom_cases(self) -> None:
        for message, previous, expected_stage, expected_yalom in GOLDEN_CASES:
            with self.subTest(message=message):
                decision = detect_stage("MBI", previous, message)
                self.assertEqual(decision.current_stage, expected_stage)
                self.assertEqual(mbi_default_yalom(expected_stage, message), expected_yalom)
                self.assertTrue(set(expected_yalom).issubset(mbi_allowed_yalom(expected_stage)))

    def test_valid_mbi_therapist_speech_passes(self) -> None:
        for stage, speech in VALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_therapist_response(stage, speech, "Mình đang hoảng.")
                self.assertTrue(result.valid, result.reason)

    def test_invalid_mbi_therapist_speech_falls_back(self) -> None:
        for stage, speech in INVALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_therapist_response(stage, speech, "Mình đang hoảng.")
                self.assertFalse(result.valid)
                self.assertTrue(result.fallback_response)

    def test_mbi_grounding_rejects_generic_listening_response(self) -> None:
        result = validate_therapist_response(
            "mbi_stage_1_grounding",
            "Tôi đang lắng nghe bạn. Điều quan trọng nhất lúc này với bạn là phần nào trong chuyện vừa xảy ra?",
            "Mình đang hoảng, tim đập nhanh và khó thở.",
        )
        self.assertFalse(result.valid)
        self.assertIn("missing required route technique pattern", result.reason)

    def test_mbi_stage_knowledge_is_route_specific(self) -> None:
        grounding = stage_knowledge("MBI", "mbi_stage_1_grounding")
        self.assertIn("Route: MBI", grounding)
        self.assertIn("feet-on-floor anchoring", grounding)
        self.assertIn("cognitive disputation", grounding)

        decentering = stage_knowledge("MBI", "mbi_stage_2_decentering")
        self.assertIn("decentering phrase", decentering)
        self.assertIn("mình đang có suy nghĩ rằng", decentering)


if __name__ == "__main__":
    unittest.main()
