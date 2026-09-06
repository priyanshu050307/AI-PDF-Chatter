import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np
import httpx

from app.core.config import settings
from app.core.errors import ValidationError, AIProviderUnavailableError
from app.core.logging import logger


class EmbeddingService(ABC):
    """Abstract interface boundary for vector embedding generation and health checking."""

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate numerical embedding vectors for a list of text strings."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify embedding provider reachability and status."""
        pass


class MockEmbeddingService(EmbeddingService):
    """
    Deterministic zero-dependency mock embedding provider.
    Produces 1536-dimensional normalized unit vectors based on text hash.
    Enables 100% offline development and automated test execution.
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        embeddings = []
        for text in texts:
            # Create seed from text SHA256 hash
            seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
            seed_int = int.from_bytes(seed_hash[:4], "big")
            rng = np.random.RandomState(seed_int)

            # Generate random vector and normalize to unit length
            vec = rng.randn(self.dimension)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec.tolist())

        return embeddings

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": "mock",
            "model": settings.EMBEDDING_MODEL,
            "dimension": self.dimension,
            "status": "healthy"
        }


class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI API Embedding Service implementation using httpx."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536):
        if not api_key:
            raise ValidationError(message="OPENAI_API_KEY is required for OpenAI embedding provider.")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        batch_size = 50
        all_embeddings = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "input": batch,
                            "model": self.model,
                            "dimensions": self.dimension
                        }
                    )
                    if response.status_code != 200:
                        logger.error(f"OpenAI embedding error: {response.text}")
                        raise ValidationError(message=f"Embedding provider error: {response.status_code}")

                    data = response.json()
                    sorted_data = sorted(data["data"], key=lambda x: x["index"])
                    all_embeddings.extend([item["embedding"] for item in sorted_data])
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.error(f"OpenAI embedding connection error: {exc}")
            raise AIProviderUnavailableError(message="OpenAI Embedding API endpoint is unreachable.")

        return all_embeddings

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": bool(self.api_key),
            "provider": "openai",
            "model": self.model,
            "dimension": self.dimension,
            "status": "healthy" if self.api_key else "missing_api_key"
        }


class OllamaEmbeddingService(EmbeddingService):
    """
    Local Ollama REST API embedding service slot.
    Communicates with Ollama instance at base_url (default http://localhost:11434).
    Strictly raises AIProviderUnavailableError if Ollama is unreachable. NO silent mock fallback.
    """

    def __init__(self, base_url: str = None, model: str = None, dimension: int = 1536, timeout: float = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings = []
        sub_batch_size = 10  # Mini-batching for CPU stability and timeout prevention

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for i in range(0, len(texts), sub_batch_size):
                    batch = texts[i:i + sub_batch_size]
                    res = await client.post(
                        f"{self.base_url}/api/embed",
                        json={
                            "model": self.model,
                            "input": batch
                        }
                    )
                    if res.status_code == 200:
                        data = res.json()
                        batch_embeddings = data.get("embeddings", [])
                        all_embeddings.extend(batch_embeddings)
                    elif res.status_code == 404:
                        # Fallback to single text /api/embeddings legacy endpoint per item
                        for text in batch:
                            single_res = await client.post(
                                f"{self.base_url}/api/embeddings",
                                json={
                                    "model": self.model,
                                    "prompt": text
                                }
                            )
                            if single_res.status_code != 200:
                                raise AIProviderUnavailableError(
                                    message=f"Ollama legacy embedding error HTTP {single_res.status_code}: {single_res.text}"
                                )
                            all_embeddings.append(single_res.json().get("embedding", []))
                    else:
                        logger.error(f"Ollama embedding error HTTP {res.status_code}: {res.text}")
                        raise AIProviderUnavailableError(
                            message=f"Ollama embedding provider error HTTP {res.status_code}: {res.text}"
                        )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Ollama embedding provider connection failed: {exc}")
            raise AIProviderUnavailableError(
                message=f"Ollama Embedding provider is unavailable at {self.base_url}. Please ensure Ollama is installed and running."
            )

        return all_embeddings

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    return {
                        "available": True,
                        "provider": "ollama",
                        "model": self.model,
                        "dimension": self.dimension,
                        "status": "healthy"
                    }
                return {
                    "available": False,
                    "provider": "ollama",
                    "model": self.model,
                    "dimension": self.dimension,
                    "status": "unhealthy",
                    "error": f"HTTP status {res.status_code}"
                }
        except Exception as exc:
            return {
                "available": False,
                "provider": "ollama",
                "model": self.model,
                "dimension": self.dimension,
                "status": "unavailable",
                "error": str(exc)
            }


def get_embedding_service() -> EmbeddingService:
    """Factory function to get configured embedding provider."""
    if settings.EMBEDDING_DIMENSION <= 0:
        raise ValidationError(message=f"Invalid EMBEDDING_DIMENSION configuration: {settings.EMBEDDING_DIMENSION}")

    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        return OpenAIEmbeddingService(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION
        )
    elif provider == "ollama":
        return OllamaEmbeddingService(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION
        )
    return MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)
