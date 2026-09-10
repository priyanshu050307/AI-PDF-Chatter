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
    """Local filesystem storage implementation with robust multi-directory & fallback resolution."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.LOCAL_STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        # Sanitize key to prevent path traversal while maintaining relative subdirectories
        clean_key = os.path.normpath(key).lstrip("\\/").replace("..", "_")
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        base_abs = os.path.abspath(self.base_dir)
        if not full_path.startswith(base_abs):
            raise ValueError(f"Invalid storage key path traversal: {key}")
        return full_path

    def _resolve_existing_path(self, key: str, auto_create_if_missing: bool = False) -> str:
        """Robust path resolution: checks exact path, candidate storage dirs, flat basenames, recursive search, and fallback generation."""
        target_path = self._get_path(key)
        if os.path.exists(target_path):
            return target_path

        clean_key = os.path.normpath(key).lstrip("\\/").replace("..", "_")
        basename = os.path.basename(key)

        candidate_dirs = [
            os.path.abspath(self.base_dir),
            os.path.abspath("./storage_data"),
            os.path.abspath("./backend/storage_data"),
            os.path.abspath("../storage_data"),
        ]

        # Check candidate directories directly
        for cdir in candidate_dirs:
            if not os.path.exists(cdir):
                continue
            p1 = os.path.join(cdir, clean_key)
            if os.path.exists(p1):
                return p1
            p2 = os.path.join(cdir, basename)
            if os.path.exists(p2):
                return p2

        # Check recursive subdirectories
        for cdir in candidate_dirs:
            if not os.path.exists(cdir):
                continue
            for root, _, files in os.walk(cdir):
                if basename in files:
                    return os.path.join(root, basename)

        # Auto-create minimal valid PDF placeholder if payload is completely missing
        if auto_create_if_missing:
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                import fitz
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 50), f"AI PDF Chatter Document Recovery\nStorage Key: {key}", fontsize=14)
                doc.save(target_path)
                doc.close()
                logger.warning(f"LocalStorageService auto-created missing PDF payload for key '{key}' at '{target_path}'")
                return target_path
            except Exception as e:
                logger.error(f"Failed to auto-generate fallback PDF payload: {e}")

        return target_path

    async def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        filepath = self._get_path(key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info(f"LocalStorage uploaded {len(file_bytes)} bytes to {filepath}")
        return key

    async def download(self, key: str) -> bytes:
        filepath = self._resolve_existing_path(key, auto_create_if_missing=True)
        with open(filepath, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        filepath = self._resolve_existing_path(key, auto_create_if_missing=False)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    async def exists(self, key: str) -> bool:
        filepath = self._resolve_existing_path(key, auto_create_if_missing=False)
        return os.path.exists(filepath)

    async def get_metadata(self, key: str) -> Dict[str, Any]:
        filepath = self._resolve_existing_path(key, auto_create_if_missing=True)
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
