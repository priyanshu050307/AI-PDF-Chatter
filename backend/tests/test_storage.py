import pytest
import tempfile
import shutil
from app.services.storage_service import LocalStorageService

@pytest.mark.asyncio
async def test_local_storage_crud():
    temp_dir = tempfile.mkdtemp()
    try:
        storage = LocalStorageService(base_dir=temp_dir)
        test_key = "test_document.pdf"
        test_data = b"%PDF-1.4 Mock PDF Content"

        # 1. Upload
        uploaded_key = await storage.upload(test_data, test_key)
        assert uploaded_key == test_key
        assert await storage.exists(test_key) is True

        # 2. Download
        downloaded_bytes = await storage.download(test_key)
        assert downloaded_bytes == test_data

        # 3. Metadata
        meta = await storage.get_metadata(test_key)
        assert meta["size_bytes"] == len(test_data)

        # 4. Delete
        deleted = await storage.delete(test_key)
        assert deleted is True
        assert await storage.exists(test_key) is False
    finally:
        shutil.rmtree(temp_dir)
