import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger


class FileStorage(ABC):
    """Abstract Object Storage Interface."""

    @abstractmethod
    async def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        """Upload raw file bytes and return storage location key."""
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download raw file bytes by storage key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete stored file by storage key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get file metadata (size, content type, created date)."""
        pass


class LocalStorageService(FileStorage):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.LOCAL_STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        # Prevent path traversal attacks
        safe_key = os.path.basename(key)
        return os.path.join(self.base_dir, safe_key)

    async def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        filepath = self._get_path(key)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info(f"LocalStorage uploaded {len(file_bytes)} bytes to {filepath}")
        return key

    async def download(self, key: str) -> bytes:
        filepath = self._get_path(key)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File with key {key} not found.")
        with open(filepath, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        filepath = self._get_path(key)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return os.path.exists(self._get_path(key))

    async def get_metadata(self, key: str) -> Dict[str, Any]:
        filepath = self._get_path(key)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File with key {key} not found.")
        stat = os.stat(filepath)
        return {
            "size_bytes": stat.st_size,
            "created_at": stat.st_ctime,
            "key": key
        }


class S3StorageService(FileStorage):
    """S3 / MinIO object storage implementation using boto3."""

    def __init__(self):
        import boto3
        self.bucket_name = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )

    async def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type
        )
        return key

    async def download(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)
        return True

    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    async def get_metadata(self, key: str) -> Dict[str, Any]:
        response = self.client.head_object(Bucket=self.bucket_name, Key=key)
        return {
            "size_bytes": response["ContentLength"],
            "content_type": response["ContentType"],
            "key": key
        }


def get_storage_service() -> FileStorage:
    """Factory function to get active storage backend."""
    if settings.STORAGE_BACKEND.lower() in ("s3", "minio"):
        return S3StorageService()
    return LocalStorageService()
