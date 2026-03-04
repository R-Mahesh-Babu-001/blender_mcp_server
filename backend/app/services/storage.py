from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4


class StorageService:
    def __init__(self, upload_dir: Path, output_dir: Path) -> None:
        self.upload_dir = upload_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, source_path: Path) -> Path:
        suffix = source_path.suffix.lower()
        target = self.upload_dir / f"{uuid4().hex}{suffix}"
        shutil.copy2(source_path, target)
        return target

    def create_output_path(self, suffix: str = ".glb") -> Path:
        return self.output_dir / f"{uuid4().hex}{suffix}"
