import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.errors import ValidationError, AIProviderUnavailableError
from app.core.logging import logger


class BaseVisionProvider(ABC):
    """Abstract interface for Multimodal Vision model interaction."""

    @abstractmethod
    async def describe_image(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        """Generate a concise textual description of an image artifact or diagram."""
        pass

    @abstractmethod
    async def answer_visual_question(self, image_bytes: bytes, question: str) -> str:
        """Answer a targeted question about an image or visual element."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check reachability and health status of vision model provider."""
        pass


class MockVisionProvider(BaseVisionProvider):
    """Mock vision provider for unit tests and local CPU testing."""

    async def describe_image(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        if not image_bytes:
            return "Empty image payload."
        return "[Visual Description] Architectural diagram depicting data flow, system boundaries, and network connections."

    async def answer_visual_question(self, image_bytes: bytes, question: str) -> str:
        if not image_bytes:
            return "Empty image payload."
        return f"Based on the visual figure: The image illustrates '{question}' with clear structural components and annotated flow arrows."

    async def health_check(self) -> Dict[str, Any]:
        return {"available": True, "provider": "mock", "model": settings.VISION_MODEL, "status": "healthy"}


class DisabledVisionProvider(BaseVisionProvider):
    """Passthrough vision provider when vision processing is explicitly disabled."""

    async def describe_image(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        return "[Vision processing disabled]"

    async def answer_visual_question(self, image_bytes: bytes, question: str) -> str:
        return "[Vision processing disabled]"

    async def health_check(self) -> Dict[str, Any]:
        return {"available": False, "provider": "disabled", "status": "disabled"}


class OllamaVisionProvider(BaseVisionProvider):
    """
    Local Ollama Multimodal Vision model implementation (e.g. llava, qwen2-vl).
    Strictly raises AIProviderUnavailableError if Ollama vision service is unreachable. NO silent mock fallback.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, timeout: float = 60.0):
        self.base_url = (base_url or settings.OLLAMA_VISION_BASE_URL).rstrip("/")
        self.model = model or settings.VISION_MODEL
        self.timeout = timeout

    def _encode_image(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("utf-8")

    async def describe_image(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        if not image_bytes:
            return "Empty image payload."
        
        effective_prompt = prompt or "Describe the key visual elements, text, structure, and findings in this image in 2-3 sentences."
        b64_img = self._encode_image(image_bytes)

        payload = {
            "model": self.model,
            "prompt": effective_prompt,
            "images": [b64_img],
            "stream": False,
            "options": {"temperature": 0.2}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code != 200:
                    logger.error(f"Ollama vision error HTTP {res.status_code}: {res.text}")
                    raise AIProviderUnavailableError(
                        message=f"Ollama Vision provider error HTTP {res.status_code}: {res.text}"
                    )
                data = res.json()
                return data.get("response", "").strip()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Ollama Vision connection failed: {exc}")
            raise AIProviderUnavailableError(
                message=f"Ollama Vision provider is unavailable at {self.base_url}. Please ensure Ollama vision model '{self.model}' is installed."
            )

    async def answer_visual_question(self, image_bytes: bytes, question: str) -> str:
        prompt = f"Question about this image: {question}\nPlease answer accurately based on the visual contents."
        return await self.describe_image(image_bytes, prompt=prompt)

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    return {
                        "available": True,
                        "provider": "ollama",
                        "model": self.model,
                        "status": "healthy"
                    }
                return {"available": False, "provider": "ollama", "model": self.model, "status": "unhealthy"}
        except Exception as exc:
            return {"available": False, "provider": "ollama", "model": self.model, "status": "unavailable", "error": str(exc)}


def get_vision_provider(provider_name: Optional[str] = None) -> BaseVisionProvider:
    name = (provider_name or settings.VISION_PROVIDER).lower()
    if name == "mock":
        return MockVisionProvider()
    elif name == "ollama":
        return OllamaVisionProvider(base_url=settings.OLLAMA_VISION_BASE_URL, model=settings.VISION_MODEL)
    elif name == "disabled":
        return DisabledVisionProvider()
    return MockVisionProvider()
