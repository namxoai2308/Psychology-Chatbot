def calculate_dass21(answers: list[int]):
    """
    Nhận mảng 21 câu trả lời (0-3). Tính điểm và phân loại mức độ.
    Lưu ý: Mảng Python bắt đầu từ index 0.
    """
    if len(answers) != 21:
        raise ValueError("Phải cung cấp đủ 21 câu trả lời.")

    # 1. TÍNH TỔNG ĐIỂM (Cộng các câu tương ứng và Nhân 2)
    # Stress (S): Các câu 1, 6, 8, 11, 12, 14, 18 -> Index: 0, 5, 7, 10, 11, 13, 17
    # Note from original code: Stress indices were: [0, 5, 7, 8, 10, 17, 20]
    # Let's align with the user's provided math: 1, 6, 8, 11, 12, 14, 18
    # User's provided indices:
    score_s = (answers[0] + answers[5] + answers[7] + answers[10] + answers[11] + answers[13] + answers[17]) * 2
    
    # Anxiety (A - Lo âu): Các câu 2, 4, 7, 9, 15, 19, 20
    # User's provided indices:
    score_a = (answers[1] + answers[3] + answers[6] + answers[8] + answers[14] + answers[18] + answers[19]) * 2
    
    # Depression (D - Trầm cảm): Các câu 3, 5, 10, 13, 16, 17, 21
    # User's provided indices:
    score_d = (answers[2] + answers[4] + answers[9] + answers[12] + answers[15] + answers[16] + answers[20]) * 2

    # 2. HÀM QUY ĐỔI MỨC ĐỘ (Theo chuẩn Y khoa)
    # Trả về level: 0 (Bình thường), 1 (Nhẹ), 2 (Vừa), 3 (Nặng), 4 (Rất nặng)
    def get_level(score, thresholds):
        for level, limit in enumerate(thresholds):
            if score <= limit:
                return level
        return 4 # Lớn hơn mốc cuối là Rất nặng

    # Các mốc điểm chuẩn từ bảng của bạn
    lvl_s = get_level(score_s,[14, 18, 25, 33])
    lvl_a = get_level(score_a,[7, 9, 14, 19])
    lvl_d = get_level(score_d,[9, 13, 20, 27])

    return {
        "scores": {"S": score_s, "A": score_a, "D": score_d},
        "levels": {"S": lvl_s, "A": lvl_a, "D": lvl_d}
    }

def assign_department(dass_result: dict) -> dict:
    lvl_s = dass_result["levels"]["S"]
    lvl_a = dass_result["levels"]["A"]
    lvl_d = dass_result["levels"]["D"]

    assigned_dept = "CBT" # Mặc định
    persona_mode = "THERAPIST"

    # KIỂM TRA TRƯỜNG HỢP: KHÔNG BỊ BỆNH TÂM LÝ (Sinh viên bình thường)
    if lvl_s == 0 and lvl_a == 0 and lvl_d == 0:
        return {
            "assigned_dept": "CBT", 
            "persona_mode": "LIFE_COACH" # Kích hoạt chế độ Cố vấn (Stealth CBT)
        }

    # KIỂM TRA CÁC ƯU TIÊN LÂM SÀNG
    # Ưu tiên 1: Lo âu (A) ở mức Nặng/Rất Nặng (Cơ thể đang hoảng loạn, rối loạn nhịp thở)
    if lvl_a >= 3:
        assigned_dept = "MBI" # Khoa Chánh niệm (Cấp cứu hệ thần kinh)
    
    # Ưu tiên 2: Trầm cảm (D) lớn hơn Stress và ở mức Vừa trở lên (Tê liệt, mất động lực)
    elif lvl_d >= 2 and lvl_d > lvl_s:
        assigned_dept = "BA" # Khoa Hành vi (Kích hoạt từ việc siêu nhỏ)
    
    # Ưu tiên 3: Stress (S) cao, overthinking (Áp lực thi cử, cãi nhau)
    else:
        assigned_dept = "CBT" # Khoa Nhận thức (Gỡ rối suy nghĩ)

    return {
        "assigned_dept": assigned_dept,
        "persona_mode": persona_mode
    }
