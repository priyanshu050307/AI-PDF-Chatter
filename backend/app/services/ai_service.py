import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
import httpx

from app.core.config import settings
from app.core.errors import ValidationError, AIProviderUnavailableError
from app.core.logging import logger


class AIService(ABC):
    """Abstract interface boundary for LLM completion, streaming, and health checks."""

    @abstractmethod
    async def generate_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate a complete AI answer given system prompt and conversation history."""
        pass

    @abstractmethod
    async def stream_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Yield token strings in real-time as SSE stream."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify provider reachability and report status without generating tokens."""
        pass


class MockAIService(AIService):
    """
    Mock AI Provider for local testing and CI.
    Generates intelligent grounded responses using supplied document context.
    """

    async def generate_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        user_query = messages[-1]["content"] if messages else ""
        
        # Check if context states no relevant information
        if "NO_RELEVANT_CONTEXT_FOUND" in system_prompt or "No document information available" in system_prompt:
            content = "I could not find information addressing your question in the provided document."
        else:
            content = f"Based on the provided document context, regarding '{user_query}': The document details key findings and structural sections as outlined in the text."

        return {
            "content": content,
            "token_usage": {"prompt_tokens": 150, "completion_tokens": 40, "total_tokens": 190}
        }

    async def stream_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        ans = await self.generate_answer(system_prompt, messages)
        words = ans["content"].split(" ")
        for word in words:
            yield word + " "
            await asyncio.sleep(0.02)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": "mock",
            "model": settings.LLM_MODEL,
            "status": "healthy"
        }


class OpenAIAIService(AIService):
    """OpenAI API implementation using httpx."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValidationError(message="OPENAI_API_KEY is required for OpenAI AI provider.")
        self.api_key = api_key
        self.model = model

    async def generate_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        payload_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": payload_messages,
                        "temperature": 0.2
                    }
                )
                if res.status_code != 200:
                    logger.error(f"OpenAI completion error: {res.text}")
                    raise ValidationError(message=f"LLM provider error: {res.status_code}")

                data = res.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "token_usage": usage
                }
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.error(f"OpenAI connection error: {exc}")
            raise AIProviderUnavailableError(message="OpenAI API endpoint is unreachable.")

    async def stream_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        payload_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": payload_messages,
                        "temperature": 0.2,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                continue
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.error(f"OpenAI stream connection error: {exc}")
            raise AIProviderUnavailableError(message="OpenAI API streaming endpoint is unreachable.")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": bool(self.api_key),
            "provider": "openai",
            "model": self.model,
            "status": "healthy" if self.api_key else "missing_api_key"
        }


class OllamaAIService(AIService):
    """
    Local Ollama REST API implementation slot.
    Communicates with Ollama instance at base_url (default http://localhost:11434).
    Strictly raises AIProviderUnavailableError if Ollama is unreachable. NO silent mock fallback.
    """

    def __init__(self, base_url: str = None, model: str = None, timeout: float = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    async def generate_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        payload_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": payload_messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2
                        }
                    }
                )
                if res.status_code != 200:
                    logger.error(f"Ollama chat error HTTP {res.status_code}: {res.text}")
                    raise AIProviderUnavailableError(
                        message=f"Ollama AI provider error HTTP {res.status_code}: {res.text}"
                    )

                data = res.json()
                content = data.get("message", {}).get("content", "")
                eval_count = data.get("eval_count", 0)
                prompt_eval_count = data.get("prompt_eval_count", 0)

                return {
                    "content": content,
                    "token_usage": {
                        "prompt_tokens": prompt_eval_count,
                        "completion_tokens": eval_count,
                        "total_tokens": prompt_eval_count + eval_count,
                    }
                }
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Ollama provider connection failed: {exc}")
            raise AIProviderUnavailableError(
                message=f"Ollama AI provider is unavailable at {self.base_url}. Please ensure Ollama is installed and running."
            )

    async def stream_answer(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        payload_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": payload_messages,
                        "stream": True,
                        "options": {
                            "temperature": 0.2
                        }
                    }
                ) as response:
                    if response.status_code != 200:
                        raise AIProviderUnavailableError(
                            message=f"Ollama streaming failed with HTTP {response.status_code}"
                        )
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            delta = data.get("message", {}).get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Ollama streaming connection failed: {exc}")
            raise AIProviderUnavailableError(
                message=f"Ollama AI provider is unavailable at {self.base_url}. Please ensure Ollama is installed and running."
            )

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    version_data = res.json()
                    return {
                        "available": True,
                        "provider": "ollama",
                        "model": self.model,
                        "status": "healthy",
                        "version": version_data.get("version", "unknown")
                    }
                return {
                    "available": False,
                    "provider": "ollama",
                    "model": self.model,
                    "status": "unhealthy",
                    "error": f"HTTP status {res.status_code}"
                }
        except Exception as exc:
            return {
                "available": False,
                "provider": "ollama",
                "model": self.model,
                "status": "unavailable",
                "error": str(exc)
            }


def get_ai_service() -> AIService:
    """Factory function to get configured AI service provider."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIAIService(api_key=settings.OPENAI_API_KEY, model=settings.LLM_MODEL)
    elif provider == "ollama":
        return OllamaAIService(base_url=settings.OLLAMA_BASE_URL, model=settings.LLM_MODEL)
    return MockAIService()


get_llm_service = get_ai_service

