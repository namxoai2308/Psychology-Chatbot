from benchmarks.core.evaluator import BaseEvaluator
from benchmarks.evaluators.eval_cape_ii import evaluate_cape
from typing import Dict, Any

class CAPEEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("CAPE_II")

    async def evaluate(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return evaluate_cape(transcript)
