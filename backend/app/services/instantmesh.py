from __future__ import annotations

import asyncio
import logging
import shlex
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class InstantMeshRunner:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, image_path: Path, output_path: Path) -> Path:
        if not self._settings.instantmesh_python or not self._settings.instantmesh_script:
            raise RuntimeError("InstantMesh is not configured. Set INSTANTMESH_PYTHON and INSTANTMESH_SCRIPT.")

        command = [
            self._settings.instantmesh_python,
            self._settings.instantmesh_script,
            "--image",
            str(image_path),
            "--output",
            str(output_path),
            *self._settings.instantmesh_extra_args_list,
        ]
        logger.info("Running InstantMesh command: %s", shlex.join(command))
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_text = stderr.decode("utf-8", errors="ignore").strip()
            output_text = stdout.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(
                "InstantMesh failed with exit code "
                f"{process.returncode}: {(error_text or output_text or 'Unknown error')}"
            )
        logger.info("InstantMesh output: %s", stdout.decode("utf-8", errors="ignore").strip())
        if not output_path.exists():
            raise RuntimeError(f"InstantMesh did not produce output file: {output_path}")
        return output_path
