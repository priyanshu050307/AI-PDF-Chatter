"""LLM-as-a-Judge Safety Wrapper for AI PDF Chatter Evaluation."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

JUDGE_MODEL_VERSION = "qwen3:4b-instruct-judge-v1"

DETERMINISTIC_JUDGE_PROMPT = """You are an objective AI evaluation judge.
Evaluate the candidate answer against the provided context and user question.

User Question: {question}
Retrieved Context: {context}
Candidate Answer: {answer}

Evaluate on a scale of 0.0 to 1.0 for:
1. Faithfulness (Is the answer fully supported by context?)
2. Answer Relevance (Does the answer address the question directly?)
3. Groundedness (Does the answer avoid introducing ungrounded claims?)

Respond ONLY in valid JSON format:
{{
  "faithfulness": 0.95,
  "answer_relevance": 1.0,
  "groundedness": 0.95,
  "reasoning": "Answer directly addresses the question and is supported by context."
}}
"""


class LLMJudge:
    def __init__(self, ai_service: Optional[Any] = None, judge_model: str = JUDGE_MODEL_VERSION):
        self.ai_service = ai_service
        self.judge_model = judge_model

    async def evaluate_answer(
        self,
        question: str,
        context: str,
        answer: str
    ) -> Dict[str, Any]:
        """Evaluates candidate answer using LLM-as-a-Judge with fallback deterministic logic."""
        if not self.ai_service or not answer:
            return self._fallback_deterministic_judge(question, context, answer)

        prompt = DETERMINISTIC_JUDGE_PROMPT.format(
            question=question,
            context=context[:2000],
            answer=answer[:2000]
        )

        try:
            res = await self.ai_service.generate_completion(
                prompt=prompt,
                system_prompt="You are a strict, objective evaluation judge. Return valid JSON only.",
                temperature=0.0
            )

            # Extract JSON from response
            res_text = res.get("text", "")
            if "{" in res_text and "}" in res_text:
                import json
                start = res_text.find("{")
                end = res_text.rfind("}") + 1
                parsed = json.loads(res_text[start:end])
                return {
                    "judge_model": self.judge_model,
                    "faithfulness": float(parsed.get("faithfulness", 0.9)),
                    "answer_relevance": float(parsed.get("answer_relevance", 0.9)),
                    "groundedness": float(parsed.get("groundedness", 0.9)),
                    "reasoning": str(parsed.get("reasoning", "Evaluated via LLM-as-Judge"))
                }
        except Exception as e:
            logger.warning(f"LLM-as-Judge evaluation failed: {e}. Falling back to deterministic judge.")

        return self._fallback_deterministic_judge(question, context, answer)

    def _fallback_deterministic_judge(
        self,
        question: str,
        context: str,
        answer: str
    ) -> Dict[str, Any]:
        if not answer:
            return {
                "judge_model": f"{self.judge_model}-deterministic-fallback",
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "groundedness": 0.0,
                "reasoning": "Empty answer provided."
            }

        q_terms = [t for t in question.lower().split() if len(t) > 3]
        matched_q = sum(1 for t in q_terms if t in answer.lower())
        rel = matched_q / float(len(q_terms)) if q_terms else 1.0

        ctx_terms = [t for t in answer.lower().split() if len(t) > 4]
        matched_ctx = sum(1 for t in ctx_terms if t in context.lower())
        faith = matched_ctx / float(len(ctx_terms)) if ctx_terms else 1.0

        return {
            "judge_model": f"{self.judge_model}-deterministic-fallback",
            "faithfulness": round(faith, 4),
            "answer_relevance": round(rel, 4),
            "groundedness": round((faith + rel) / 2.0, 4),
            "reasoning": "Evaluated using deterministic word-overlap fallback judge."
        }
