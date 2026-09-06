import pytest
from app.services.embedding_service import MockEmbeddingService, get_embedding_service
from app.core.config import settings
from app.core.errors import ValidationError


@pytest.mark.asyncio
async def test_mock_embedding_service_dimension_and_determinism():
    dim = settings.EMBEDDING_DIMENSION
    service = MockEmbeddingService(dimension=dim)
    texts = ["Context-aware chunking for AI PDF chatter", "Same string test"]

    embeddings = await service.generate_embeddings(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == dim
    assert len(embeddings[1]) == dim

    # Verify determinism
    repeat_embeddings = await service.generate_embeddings(["Context-aware chunking for AI PDF chatter"])
    assert embeddings[0] == repeat_embeddings[0]


@pytest.mark.asyncio
async def test_embedding_factory_dimension_validation(monkeypatch):
    # Test valid factory call
    service = get_embedding_service()
    assert service is not None

    # Test invalid dimension error
    monkeypatch.setattr(settings, "EMBEDDING_DIMENSION", -1)
    with pytest.raises(ValidationError) as exc:
        get_embedding_service()
    assert "EMBEDDING_DIMENSION" in str(exc.value)
