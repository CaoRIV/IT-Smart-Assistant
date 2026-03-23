"""Storage abstraction for filesystem and S3-compatible backends."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FILESYSTEM_STORAGE_DIR = BACKEND_ROOT / "uploads" / "storage"


@dataclass(frozen=True)
class StoredObject:
    """Result returned after persisting a file/object."""

    key: str
    backend: str
    bucket: str | None = None
    content_type: str | None = None


class StorageService:
    """Simple storage adapter supporting filesystem and S3-compatible backends."""

    def __init__(self) -> None:
        self.backend = settings.STORAGE_BACKEND
        self.bucket = settings.S3_BUCKET if self.backend == "s3" else None
        self._client = None

    def _normalize_key(self, key: str) -> str:
        return str(Path(key)).replace("\\", "/").lstrip("/")

    def _filesystem_path(self, key: str) -> Path:
        return FILESYSTEM_STORAGE_DIR / self._normalize_key(key)

    @property
    def client(self):
        if self.backend != "s3":
            return None

        if self._client is None:
            session = boto3.session.Session()
            self._client = session.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                use_ssl=settings.S3_SECURE,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._client

    def upload_bytes(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> StoredObject:
        """Persist raw bytes to the configured storage backend."""
        normalized_key = self._normalize_key(key)
        resolved_content_type = content_type or mimetypes.guess_type(normalized_key)[0]

        if self.backend == "s3":
            self.client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=normalized_key,
                Body=content,
                ContentType=resolved_content_type or "application/octet-stream",
            )
            return StoredObject(
                key=normalized_key,
                backend=self.backend,
                bucket=settings.S3_BUCKET,
                content_type=resolved_content_type,
            )

        path = self._filesystem_path(normalized_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(
            key=str(path),
            backend=self.backend,
            content_type=resolved_content_type,
        )

    def download_bytes(self, key: str) -> bytes:
        """Fetch bytes from the configured storage backend."""
        if self.backend == "s3":
            response = self.client.get_object(Bucket=settings.S3_BUCKET, Key=self._normalize_key(key))
            return response["Body"].read()

        return Path(key).read_bytes()

    def delete_object(self, key: str) -> None:
        """Delete an object from storage if it exists."""
        if self.backend == "s3":
            self.client.delete_object(Bucket=settings.S3_BUCKET, Key=self._normalize_key(key))
            return

        path = Path(key)
        if path.exists():
            path.unlink()


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Return a cached storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
