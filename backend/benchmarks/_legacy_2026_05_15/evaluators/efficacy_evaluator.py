from benchmarks.core.evaluator import BaseEvaluator
from benchmarks.evaluators.eval_universal_efficacy import evaluate_universal_efficacy
from typing import Dict, Any
import asyncio

class EfficacyEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("Efficacy")

    async def evaluate(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        # The existing function is sync, so we run it in a thread if needed or just call it
        # Since it uses requests/generate_text, it might block. 
        # For simplicity we call it directly here.
        fsm_route = metadata.get("fsm_route", "CBT")
        return evaluate_universal_efficacy(transcript, fsm_route)
