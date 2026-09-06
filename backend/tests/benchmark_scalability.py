import io
import os
import sys
import time
import asyncio
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.processing_service import DocumentProcessingService


def generate_benchmark_pdf(num_pages: int = 100) -> bytes:
    """Generate a multi-page synthetic PDF containing text for ingestion benchmarking."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def run_benchmark():
    print("=" * 65)
    print(" AI PDF Chatter — Large Document Ingestion Scalability Benchmark ")
    print("=" * 65)

    async with AsyncSessionLocal() as db:
        # Create benchmark user
        user = User(
            id=uuid.uuid4(),
            email=f"bench_{int(time.time())}@example.com",
            password_hash="benchpass",
            full_name="Benchmark User"
        )
        db.add(user)
        await db.commit()

        for page_target in [50, 100, 250]:
            print(f"\n[+] Benchmarking {page_target}-page PDF Ingestion...")
            t0 = time.perf_counter()
            pdf_bytes = generate_benchmark_pdf(num_pages=page_target)
            t_gen = time.perf_counter() - t0

            # Upload phase
            t_upload_start = time.perf_counter()
            doc_service = DocumentService(db)
            doc_res = await doc_service.upload_document(
                user=user,
                file_bytes=pdf_bytes,
                filename=f"bench_{page_target}p.pdf"
            )
            t_upload = time.perf_counter() - t_upload_start

            # Metrics
            pages_per_sec = page_target / max(t_upload, 0.001)
            print(f"    * Document ID        : {doc_res.id}")
            print(f"    * PDF Payload Size   : {len(pdf_bytes) / 1024:.2f} KB")
            print(f"    * Total Pages        : {doc_res.page_count}")
            print(f"    * Status             : {doc_res.processing_status}")
            print(f"    * Ingestion Duration : {t_upload:.4f} s")
            print(f"    * Throughput         : {pages_per_sec:.2f} pages/sec")

    print("\n" + "=" * 65)
    print(" Benchmark Completed Successfully! ")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
