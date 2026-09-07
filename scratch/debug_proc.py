import sys
sys.path.insert(0, "c:/G.E.N.I.U.S/Workinseet/AI-pdfchatter/backend")
import asyncio
import uuid
import fitz
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.services.processing_service import DocumentProcessingService
from app.core.security import get_password_hash

async def debug_proc():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email='test_debug@example.com',
            password_hash=get_password_hash('Password123!'),
            full_name='Debug User'
        )
        session.add(user)
        await session.commit()

        doc_fitz = fitz.open()
        page = doc_fitz.new_page(width=595, height=842)
        page.insert_text((50, 50), "Debug Multimodal Page")
        pdf_bytes = doc_fitz.tobytes()
        doc_fitz.close()

        doc = Document(
            id=uuid.uuid4(),
            user_id=user.id,
            title="debug.pdf",
            original_filename="debug.pdf",
            storage_key="debug_key",
            file_size_bytes=len(pdf_bytes),
            processing_status=DocumentStatus.PENDING,
            page_count=1
        )
        session.add(doc)
        await session.commit()

        ps = DocumentProcessingService(session)
        await ps.storage.upload("debug_key", pdf_bytes, "application/pdf")

        try:
            res = await ps.process_document(doc.id)
            print("RESULT:", res)
        except Exception as exc:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_proc())
