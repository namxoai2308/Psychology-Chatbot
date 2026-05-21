from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseEvaluator(ABC):
    """Base class for all evaluators."""
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def evaluate(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a single transcript."""
        pass

class EvaluationEngine:
    """Handles running multiple evaluators on transcripts."""
    
    def __init__(self, evaluators: List[BaseEvaluator]):
        self.evaluators = evaluators

    async def evaluate_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates all models in a single case across all evaluators."""
        case_id = case_data["case_id"]
        transcripts = case_data["transcripts"]
        metadata = {
            "fsm_route": case_data.get("fsm_route", "CBT"),
            "case_id": case_id
        }
        
        results = {}
        for model_name, transcript in transcripts.items():
            model_results = {}
            for evaluator in self.evaluators:
                print(f"    > Eval {evaluator.name} for {model_name}...")
                eval_res = await evaluator.evaluate(transcript, metadata)
                model_results[evaluator.name] = eval_res
            results[model_name] = model_results
            
        return results
