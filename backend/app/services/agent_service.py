from abc import ABC, abstractmethod
from typing import Dict, Any

class AgentService(ABC):
    """Abstract interface boundary for multi-step agentic analysis (Phase 11)."""

    @abstractmethod
    async def run_agent_task(self, prompt: str, document_id: str) -> Dict[str, Any]:
        """Execute multi-step reasoning agent workflow."""
        pass
