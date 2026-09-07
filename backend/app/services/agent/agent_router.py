import re
from enum import Enum
from typing import Dict, Any, Tuple


class AgentRoute(str, Enum):
    SIMPLE_FACTUAL = "SIMPLE_FACTUAL"
    MULTI_STEP_INVESTIGATION = "MULTI_STEP_INVESTIGATION"
    CHARACTER_NARRATIVE = "CHARACTER_NARRATIVE"
    COMPARISON = "COMPARISON"
    ANNOTATION_ANALYSIS = "ANNOTATION_ANALYSIS"
    MULTI_DOC_FACTUAL = "MULTI_DOC_FACTUAL"
    MULTI_DOC_COMPARISON = "MULTI_DOC_COMPARISON"
    MULTI_DOC_CONTRADICTION = "MULTI_DOC_CONTRADICTION"
    MULTI_DOC_SYNTHESIS = "MULTI_DOC_SYNTHESIS"


class AgentRouter:
    """
    Lightweight, deterministic query router.
    Routes fast factual queries to Normal RAG, and multi-step / narrative / comparison / multi-doc queries to Agentic RAG.
    """

    COMPARISON_KEYWORDS = ["compare", "difference", "vs", "versus", "contrast", "both", "differ"]
    CHARACTER_KEYWORDS = ["character", "who is", "relationship", "betray", "trust", "ally", "enemy", "timeline", "plot", "event", "motive"]
    ANNOTATION_KEYWORDS = ["highlight", "annotation", "note", "my notes", "what did i note"]
    MULTI_STEP_KEYWORDS = ["investigate", "how did", "why did", "explain in detail", "trace", "evolution", "across chapter", "all occurrences"]
    CONTRADICTION_KEYWORDS = ["disagree", "conflict", "contradict", "differ", "oppose", "disagreement"]

    def route_query(self, query: str, mode_override: str = "auto", is_multi_doc: bool = False) -> Tuple[AgentRoute, bool]:
        """
        Classifies user query and determines whether Agentic RAG is required.
        Returns Tuple of (AgentRoute, is_agentic_required).
        """
        q_lower = query.lower()

        if is_multi_doc:
            if any(kw in q_lower for kw in self.CONTRADICTION_KEYWORDS):
                return AgentRoute.MULTI_DOC_CONTRADICTION, True
            if any(kw in q_lower for kw in self.COMPARISON_KEYWORDS):
                return AgentRoute.MULTI_DOC_COMPARISON, True
            if any(kw in q_lower for kw in self.MULTI_STEP_KEYWORDS) or len(q_lower.split()) > 10:
                return AgentRoute.MULTI_DOC_SYNTHESIS, True
            if mode_override in ["always_agentic", "agentic"]:
                return AgentRoute.MULTI_DOC_SYNTHESIS, True
            return AgentRoute.MULTI_DOC_FACTUAL, False

        if mode_override in ["always_agentic", "agentic"]:
            return AgentRoute.MULTI_STEP_INVESTIGATION, True
        if mode_override in ["always_normal", "normal"]:
            return AgentRoute.SIMPLE_FACTUAL, False

        # 1. Annotation Queries
        if any(kw in q_lower for kw in self.ANNOTATION_KEYWORDS):
            return AgentRoute.ANNOTATION_ANALYSIS, True

        # 2. Comparison Queries
        if any(kw in q_lower for kw in self.COMPARISON_KEYWORDS):
            return AgentRoute.COMPARISON, True

        # 3. Character & Narrative Queries
        if any(kw in q_lower for kw in self.CHARACTER_KEYWORDS):
            return AgentRoute.CHARACTER_NARRATIVE, True

        # 4. Multi-step Investigation Queries
        if any(kw in q_lower for kw in self.MULTI_STEP_KEYWORDS) or len(q_lower.split()) > 12:
            return AgentRoute.MULTI_STEP_INVESTIGATION, True

        # Default fast path
        return AgentRoute.SIMPLE_FACTUAL, False

