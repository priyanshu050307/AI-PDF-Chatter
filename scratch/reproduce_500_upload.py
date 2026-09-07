import fitz
import asyncio
import httpx
import sys

sys.path.insert(0, "backend")

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.services.document_service import DocumentService
from sqlalchemy import select

async def test_reproduce():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 1. Generate a large PDF (~9MB or many pages with text)
    doc = fitz.open()
    for i in range(100):
        page = doc.new_page(width=612, height=792)
        # Put 500 words per page to simulate realistic textbook payload
        text = f"Digital Electronics by Anil K Maini Chapter {i+1}\n\n" + ("Logic gates, flip flops, sequential circuits, digital design principles. " * 50)
        page.insert_text((50, 50), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    print(f"Generated PDF bytes: {len(pdf_bytes)} bytes (~{len(pdf_bytes)/(1024*1024):.2f} MB)")

    async with AsyncSessionLocal() as session:
        # Get or create first user
        user_res = await session.execute(select(User))
        user = user_res.scalars().first()
        if not user:
            from app.core.security import get_password_hash
            user = User(email="test_user@example.com", password_hash=get_password_hash("Password123!"), full_name="Test User")
            session.add(user)
            await session.commit()
            await session.refresh(user)

        print(f"Testing upload for user: {user.email}")
        doc_service = DocumentService(session)
        try:
            doc_res = await doc_service.upload_document(user, pdf_bytes, "Digital_electronics_by_Anil_K_Maini.pdf", run_inline_processing=False)
            print(f"Upload successful: doc_id={doc_res.id}, title={doc_res.title}")
            
            # Now test get_user_document
            get_res = await doc_service.get_user_document(user, doc_res.id)
            print(f"Get document successful: doc_id={get_res.id}")
        except Exception as e:
            print(f"EXCEPTIONS CAUGHT: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reproduce())
