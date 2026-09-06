import fitz
import asyncio
import sys
import time

sys.path.insert(0, "backend")

from app.services.pdf_processor import PDFProcessor
from app.services.chunker import ContextAwareChunker
from app.services.embedding_service import OllamaEmbeddingService, MockEmbeddingService

async def test_performance():
    with open("test_300_pages.pdf", "rb") as f:
        file_bytes = f.read()

    start = time.time()
    processor = PDFProcessor(file_bytes)
    extracted_meta = processor.get_metadata()
    print(f"Metadata extracted in {time.time() - start:.3f}s: page_count={extracted_meta.page_count}")

    chunker = ContextAwareChunker()

    all_chunks = []
    chunk_time = 0
    t0 = time.time()
    for page_batch in processor.iter_extracted_pages(batch_size=50):
        batch_chunks = chunker.chunk_document(page_batch)
        all_chunks.extend(batch_chunks)
    chunk_time = time.time() - t0
    print(f"Extracted {len(all_chunks)} chunks from 300 pages in {chunk_time:.3f}s.")

    # Test batch embedding generation speed with sub-batches
    texts = [c.content for c in all_chunks[:50]] # first 50 chunks
    print(f"Testing embedding speed for 50 chunks...")
    ollama_embedder = OllamaEmbeddingService()
    t1 = time.time()
    try:
        res = await ollama_embedder.generate_embeddings(texts)
        print(f"Ollama embedded 50 chunks in {time.time() - t1:.3f}s (returned {len(res)} embeddings).")
    except Exception as e:
        print(f"Ollama embedding failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_performance())
