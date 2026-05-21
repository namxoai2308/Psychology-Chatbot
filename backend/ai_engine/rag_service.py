import json
import os
import re

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "clinical_kb.json")

class ClinicalRAG:
    def __init__(self):
        self.kb = []
        if os.path.exists(KB_PATH):
            with open(KB_PATH, "r", encoding="utf-8") as f:
                self.kb = json.load(f)

    def retrieve_guideline(self, user_message: str) -> str:
        """
        Tìm guideline phù hợp nhất dựa trên keyword matching cơ bản.
        Nếu có thư viện Vector/Embedding thì đổi code ở đây.
        """
        msg_lower = user_message.lower()
        best_match = ""
        max_score = 0
        
        for item in self.kb:
            topics = [t.strip().lower() for t in item["topic"].split(",")]
            score = sum(1 for t in topics if t in msg_lower)
            if score > max_score:
                max_score = score
                best_match = item["guideline"]
                
        return best_match if max_score > 0 else "Tuân thủ các nguyên tắc đắc nhân tâm và thấu cảm cốt lõi của CBT."

# Instantiate global service
rag_service = ClinicalRAG()
