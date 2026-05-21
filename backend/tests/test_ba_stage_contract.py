from __future__ import annotations

import unittest

from ai_engine.blackboard.ba_contract import ba_allowed_yalom, ba_default_yalom
from ai_engine.blackboard.route_response_validator import validate_therapist_response
from ai_engine.blackboard.stage_detector import detect_stage
from ai_engine.services.clinical_knowledge import stage_knowledge


GOLDEN_CASES = [
    ("Mình chẳng muốn làm gì, chỉ nằm cả ngày.", None, "ba_stage_1_energy_check", ["Universality", "Catharsis"]),
    ("Mình thấy mình lười quá và cứ trì hoãn.", None, "ba_stage_1_energy_check", ["Universality", "Catharsis"]),
    ("Mình hết pin, không muốn mở bài ra.", None, "ba_stage_1_energy_check", ["Universality", "Catharsis"]),
    ("Mình kiệt sức và cứ lướt điện thoại để né việc.", None, "ba_stage_1_energy_check", ["Universality", "Catharsis"]),
    ("Mình cạn năng lượng, thấy bản thân vô dụng.", None, "ba_stage_1_energy_check", ["Universality", "Catharsis"]),
    ("Pin mình khoảng 2/10 thôi.", "ba_stage_1_energy_check", "ba_stage_2_micro_action", ["Hope"]),
    ("Năng lượng chắc 4/10.", "ba_stage_1_energy_check", "ba_stage_2_micro_action", ["Hope"]),
    ("Mình còn khoảng 30% pin.", "ba_stage_1_energy_check", "ba_stage_2_micro_action", ["Hope"]),
    ("Mức pin của mình là 1/10.", "ba_stage_1_energy_check", "ba_stage_2_micro_action", ["Hope"]),
    ("Năng lượng khoảng 5/10 nhưng vẫn nản.", "ba_stage_1_energy_check", "ba_stage_2_micro_action", ["Hope"]),
    ("Mình chọn uống nước trước.", "ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", ["NONE"]),
    ("Mình sẽ mở tài liệu 2 phút.", "ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", ["NONE"]),
    ("Mình thử mở sách ra thôi.", "ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", ["NONE"]),
    ("Mình chọn rửa mặt.", "ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", ["NONE"]),
    ("Mình sẽ đứng dậy vươn vai.", "ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", ["NONE"]),
    ("Xong rồi.", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward", ["Hope"]),
    ("Mình làm rồi.", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward", ["Hope"]),
    ("Mình vừa uống nước.", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward", ["Hope"]),
    ("Mình mở rồi và thấy nhẹ hơn chút.", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward", ["Hope"]),
    ("Đã làm xong, tâm trạng đỡ hơn.", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward", ["Hope"]),
]


VALID_SPEECH = {
    "ba_stage_1_energy_check": "Nghe như bạn đang rất cạn pin. Nếu chấm năng lượng hiện tại từ 0/10 đến 10/10, bạn đang ở mức nào?",
    "ba_stage_2_micro_action": "Với mức pin đó, mình chọn một hành động nhỏ thôi: uống nước, rửa mặt, hoặc mở tài liệu 2 phút.",
    "ba_stage_3_barrier_schedule": "Rào cản lớn nhất là gì, và bạn sẽ bắt đầu việc nhỏ đó vào mấy giờ cụ thể?",
    "ba_stage_4_momentum_reward": "Mình ghi nhận bạn đã làm xong. Tâm trạng thay đổi chút nào, và bạn muốn nghỉ hay tiếp tục một bước nhỏ?",
}


INVALID_SPEECH = {
    "ba_stage_1_energy_check": "Có bằng chứng nào cho thấy bạn lười đúng 100% không?",
    "ba_stage_2_micro_action": "Mình đào sâu lỗi tư duy này trước nhé.",
    "ba_stage_3_barrier_schedule": "Bạn cứ cố lên là được.",
    "ba_stage_4_momentum_reward": "Như vậy chưa đủ, mình phân tích thảm họa hóa tiếp.",
}


class BAStageContractTests(unittest.TestCase):
    def test_20_golden_stage_and_yalom_cases(self) -> None:
        for message, previous, expected_stage, expected_yalom in GOLDEN_CASES:
            with self.subTest(message=message):
                decision = detect_stage("BA", previous, message)
                self.assertEqual(decision.current_stage, expected_stage)
                self.assertEqual(ba_default_yalom(expected_stage, message), expected_yalom)
                self.assertTrue(set(expected_yalom).issubset(ba_allowed_yalom(expected_stage)))

    def test_valid_ba_therapist_speech_passes(self) -> None:
        for stage, speech in VALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_therapist_response(stage, speech, "Mình nằm cả ngày.")
                self.assertTrue(result.valid, result.reason)

    def test_invalid_ba_therapist_speech_falls_back(self) -> None:
        for stage, speech in INVALID_SPEECH.items():
            with self.subTest(stage=stage):
                result = validate_therapist_response(stage, speech, "Mình nằm cả ngày.")
                self.assertFalse(result.valid)
                self.assertTrue(result.fallback_response)

    def test_ba_stage_knowledge_is_route_specific(self) -> None:
        energy = stage_knowledge("BA", "ba_stage_1_energy_check")
        self.assertIn("Route: BA", energy)
        self.assertIn("energy rating", energy)
        self.assertIn("Separate low energy from moral failure", energy)

        schedule = stage_knowledge("BA", "ba_stage_3_barrier_schedule")
        self.assertIn("implementation intention", schedule)
        self.assertIn("rào cản lớn nhất", schedule)

    def test_ba_peer_semantics_distinguish_barrier_shame_from_closing(self) -> None:
        self.assertEqual(
            ba_default_yalom("ba_stage_3_barrier_schedule", "Mình sợ không làm được rồi thấy thất bại hơn."),
            ["Universality"],
        )
        self.assertEqual(
            ba_default_yalom("ba_stage_4_momentum_reward", "Mood chưa tăng nhiều nhưng mình thấy bớt kẹt hơn."),
            ["NONE"],
        )
        self.assertEqual(
            ba_default_yalom("ba_stage_4_momentum_reward", "Mình muốn dừng ở đây để không quá sức, mai thử lại."),
            ["NONE"],
        )


if __name__ == "__main__":
    unittest.main()
