from benchmarks.core.evaluator import BaseEvaluator
from benchmarks.evaluators.eval_yalom_factors import evaluate_yalom
from typing import Dict, Any

class YalomEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("Yalom")

    async def evaluate(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return evaluate_yalom(transcript)
