import re

from app.models import EvaluationResult
from app.services.llm import LLMClient


class EvaluatorAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def evaluate(self, question: str, expected: str, actual: str, trace_id: str | None = None) -> EvaluationResult:
        try:
            data = await self.llm.json(
                "Você é um avaliador rigoroso de respostas de atendimento. Compare significado, não palavras exatas. Avalie factual_correctness, completeness, relevance e safety de 0 a 1. Retorne JSON: passed (bool), score (0..1), reason (português, curta), criteria (objeto com as quatro notas). Exija score >= 0.75 para passed.",
                f"PERGUNTA: {question}\nRESPOSTA ESPERADA: {expected}\nRESPOSTA REAL: {actual}",
            )
            criteria = {k: max(0.0, min(1.0, float(v))) for k, v in data["criteria"].items()}
            score = max(0.0, min(1.0, float(data["score"])))
            return EvaluationResult(passed=bool(data["passed"]) and score >= 0.75, score=score, reason=data["reason"], criteria=criteria, actual_answer=actual, trace_id=trace_id)
        except Exception:
            return self._lexical_fallback(expected, actual, trace_id)

    @staticmethod
    def _lexical_fallback(expected: str, actual: str, trace_id: str | None) -> EvaluationResult:
        normalize = lambda text: set(re.findall(r"[a-zá-ú0-9]+", text.lower())) - {"a", "o", "de", "da", "do", "e", "em", "para", "com", "um", "uma"}
        expected_tokens, actual_tokens = normalize(expected), normalize(actual)
        coverage = len(expected_tokens & actual_tokens) / max(1, len(expected_tokens))
        score = round(min(1.0, 0.35 + 0.75 * coverage), 2)
        criteria = {"factual_correctness": score, "completeness": round(coverage, 2), "relevance": score, "safety": 1.0}
        return EvaluationResult(passed=score >= 0.75, score=score, reason="Avaliação semântica indisponível; aplicado comparador lexical determinístico.", criteria=criteria, actual_answer=actual, trace_id=trace_id)

