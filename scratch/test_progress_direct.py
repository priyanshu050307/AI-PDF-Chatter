import sys
sys.path.insert(0, r"c:\G.E.N.I.U.S\Workinseet\AI-pdfchatter\backend")
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.annotation import ReadingProgress
from app.repositories.reading_progress_repository import ReadingProgressRepository
from app.services.reading_progress_service import ReadingProgressService
from app.schemas.reading_progress import ReadingProgressCreate, ReadingProgressResponse
from sqlalchemy import select
import uuid

async def test_direct():
    async with AsyncSessionLocal() as db:
        service = ReadingProgressService(db)
        
        # Test unit logic
        print("Testing ReadingProgressRepository & Service direct instantiation...")
        
        # Fetch or mock a doc ID
        res = await db.execute(select(Document).limit(1))
        doc = res.scalars().first()
        if not doc:
            print("No documents found in DB to test against.")
            return
            
        print(f"Testing against document ID: {doc.id}, page_count: {doc.page_count}")
        
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalars().first()
        if not user:
            print("No users found in DB.")
            return

        # Save progress
        prog_in = ReadingProgressCreate(
            document_id=doc.id,
            current_page=1,
            scroll_position_pct=15.5
        )
        saved = await service.save_progress(user, doc.id, prog_in)
        print(f"Saved progress successfully: page={saved.current_page}, scroll={saved.scroll_position_pct}")
        
        # Retrieve progress
        retrieved = await service.get_progress(user, doc.id)
        print(f"Retrieved progress successfully: page={retrieved.current_page}, scroll={retrieved.scroll_position_pct}")
        assert retrieved.current_page == 1
        assert retrieved.scroll_position_pct == 15.5
        print("Reading Progress Direct Test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_direct())
