from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from app.db.repository import JobRepository
from app.services.agent import AgentService
from app.services.events import EventBus

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        event_bus: EventBus,
        agent: AgentService,
        create_output_path,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._agent = agent
        self._create_output_path = create_output_path

    async def create_job(self, prompt: str, image_path: str | None, model_path: str | None) -> str:
        job_id = uuid4().hex
        self._repository.create_job(job_id, prompt, image_path)
        asyncio.create_task(self._run_job(job_id, prompt, image_path, model_path))
        return job_id

    async def _run_job(self, job_id: str, prompt: str, image_path: str | None, model_path: str | None) -> None:
        async def emit(event_type: str, payload: dict) -> None:
            self._repository.add_event(job_id, event_type, payload)
            await self._event_bus.publish(self._event_bus.build(job_id, event_type, payload))

        try:
            self._repository.update_job(job_id, status="running")
            await emit("job_started", {"status": "running"})
            result = await self._agent.run(
                prompt=prompt,
                image_path=Path(image_path) if image_path else None,
                model_path=model_path,
                emit=emit,
                create_output_path=self._create_output_path,
            )
            self._repository.update_job(job_id, status="completed", result_path=result.get("result_path"))
            await emit("job_completed", result)
        except Exception as exc:
            logger.exception("Job failed: %s", job_id)
            self._repository.update_job(job_id, status="failed", error=str(exc))
            await emit("job_failed", {"error": str(exc)})
