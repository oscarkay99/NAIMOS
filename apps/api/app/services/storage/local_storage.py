"""Local-filesystem StorageProvider. Swap for an S3-compatible implementation
in production by adding a class with the same interface and switching
STORAGE_PROVIDER (section 55 — provider abstraction, no premature integration)."""

import hashlib
import uuid
from pathlib import Path

from app.core.config import get_settings


class LocalStorageProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_local_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, subdir: str, filename: str, content: bytes) -> tuple[str, str, int]:
        """Returns (relative_path, sha256_hash, size_bytes). Never overwrites:
        every save gets a fresh UUID-prefixed name."""
        target_dir = self.root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(filename).name
        stored_name = f"{uuid.uuid4()}_{safe_name}"
        target_path = target_dir / stored_name
        target_path.write_bytes(content)

        file_hash = hashlib.sha256(content).hexdigest()
        relative_path = str(target_path.relative_to(self.root))
        return relative_path, file_hash, len(content)

    def read(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()

    def absolute_path(self, relative_path: str) -> Path:
        return self.root / relative_path


def get_storage_provider() -> LocalStorageProvider:
    return LocalStorageProvider()
