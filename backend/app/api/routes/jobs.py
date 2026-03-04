from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.db.repository import JobRepository
from app.schemas import ChatRequest, JobCreateResponse, JobStatusResponse
from app.services.events import EventBus
from app.services.jobs import JobService
from app.services.storage import StorageService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


def get_storage(request: Request) -> StorageService:
    return request.app.state.storage_service


def get_repository(request: Request) -> JobRepository:
    return request.app.state.repository


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


@router.post("", response_model=JobCreateResponse)
async def create_job(
    request_json: str = Form(...),
    image: UploadFile | None = File(default=None),
    jobs: JobService = Depends(get_job_service),
    storage: StorageService = Depends(get_storage),
) -> JobCreateResponse:
    payload = ChatRequest.model_validate_json(request_json)
    stored_image_path = None
    if image:
        suffix = Path(image.filename or "upload.bin").suffix
        temp_path = storage.upload_dir / f"upload-{uuid4().hex}{suffix}"
        with temp_path.open("wb") as handle:
            while chunk := await image.read(1024 * 1024):
                handle.write(chunk)
        stored_image_path = storage.save_upload(temp_path)
        temp_path.unlink(missing_ok=True)
    job_id = await jobs.create_job(
        payload.prompt,
        str(stored_image_path) if stored_image_path else None,
        payload.model_path,
    )
    return JobCreateResponse(job_id=job_id, status="queued")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, repository: JobRepository = Depends(get_repository)) -> JobStatusResponse:
    record = repository.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**asdict(record))


@router.get("/{job_id}/events")
async def stream_events(
    job_id: str,
    request: Request,
    repository: JobRepository = Depends(get_repository),
    event_bus: EventBus = Depends(get_event_bus),
) -> StreamingResponse:
    if not repository.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        for event in repository.list_events(job_id):
            yield f"data: {json.dumps({'job_id': job_id, **event})}\n\n"
        queue = event_bus.subscribe(job_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            event_bus.unsubscribe(job_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
