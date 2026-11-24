import os
import shutil
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Union, Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import FileValidationException


class BaseStorageService(ABC):
    """Abstract storage interface allowing local filesystem or cloud object storage."""

    @abstractmethod
    async def save_file(
        self,
        file_source: Union[bytes, UploadFile],
        destination_key: str,
    ) -> str:
        """Saves file content to destination key and returns the internal storage path."""
        pass

    @abstractmethod
    async def read_file(self, storage_path: str) -> bytes:
        """Reads and returns the complete binary content of the file."""
        pass

    @abstractmethod
    async def stream_file(
        self,
        storage_path: str,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        """Streams binary file chunks asynchronously without loading entire file in memory."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Deletes file from storage. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """Checks if file exists at specified storage path."""
        pass

    @abstractmethod
    async def get_file_size(self, storage_path: str) -> int:
        """Returns file size in bytes."""
        pass


class LocalStorageService(BaseStorageService):
    """Enterprise local disk storage implementation with path traversal protection."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"Initialized LocalStorageService at base directory: {self.base_dir}")

    def _resolve_and_validate_path(self, destination_key: str) -> str:
        """Resolves target file path and rigorously enforces sandboxing against path traversal."""
        # Strip leading slashes to prevent root-relative path escaping
        sanitized_key = destination_key.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.base_dir, sanitized_key))

        # Check for path traversal escaping base directory
        if not target_path.startswith(self.base_dir + os.sep) and target_path != self.base_dir:
            logger.error(f"Path traversal security breach attempt blocked: key={destination_key}")
            raise FileValidationException("Path traversal attempt detected. Access denied.")

        return target_path

    async def save_file(
        self,
        file_source: Union[bytes, UploadFile],
        destination_key: str,
    ) -> str:
        target_path = self._resolve_and_validate_path(destination_key)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        def _write_bytes(data: bytes):
            with open(target_path, "wb") as f:
                f.write(data)

        def _write_upload_file(src: UploadFile):
            with open(target_path, "wb") as dst:
                shutil.copyfileobj(src.file, dst)

        if isinstance(file_source, bytes):
            await asyncio.to_thread(_write_bytes, file_source)
        elif isinstance(file_source, UploadFile):
            await asyncio.to_thread(_write_upload_file, file_source)
        else:
            raise ValueError("Unsupported file source type.")

        logger.debug(f"Saved document to secure storage: {destination_key}")
        # Return relative storage path relative to workspace or normalized
        return target_path

    async def read_file(self, storage_path: str) -> bytes:
        target_path = os.path.abspath(storage_path)
        if not target_path.startswith(self.base_dir):
            raise FileValidationException("Access denied: File outside storage root.")

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Storage object not found: {storage_path}")

        def _read():
            with open(target_path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def stream_file(
        self,
        storage_path: str,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        target_path = os.path.abspath(storage_path)
        if not target_path.startswith(self.base_dir):
            raise FileValidationException("Access denied: File outside storage root.")

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Storage object not found: {storage_path}")

        # Stream chunks asynchronously using thread executor
        offset = 0
        file_size = os.path.getsize(target_path)

        while offset < file_size:
            def _read_chunk(off: int, length: int) -> bytes:
                with open(target_path, "rb") as f:
                    f.seek(off)
                    return f.read(length)

            chunk = await asyncio.to_thread(_read_chunk, offset, chunk_size)
            if not chunk:
                break
            offset += len(chunk)
            yield chunk

    async def delete_file(self, storage_path: str) -> bool:
        target_path = os.path.abspath(storage_path)
        if not target_path.startswith(self.base_dir):
            raise FileValidationException("Access denied: File outside storage root.")

        if not os.path.exists(target_path):
            return False

        def _delete():
            os.remove(target_path)

        await asyncio.to_thread(_delete)
        logger.info(f"Permanently purged storage file: {storage_path}")
        return True

    async def file_exists(self, storage_path: str) -> bool:
        target_path = os.path.abspath(storage_path)
        if not target_path.startswith(self.base_dir):
            return False
        return await asyncio.to_thread(os.path.exists, target_path)

    async def get_file_size(self, storage_path: str) -> int:
        target_path = os.path.abspath(storage_path)
        if not target_path.startswith(self.base_dir):
            raise FileValidationException("Access denied: File outside storage root.")
        return await asyncio.to_thread(os.path.getsize, target_path)


# Singleton factory
_storage_service: Optional[BaseStorageService] = None


def get_storage_service() -> BaseStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = LocalStorageService(settings.STORAGE_DIR)
    return _storage_service
