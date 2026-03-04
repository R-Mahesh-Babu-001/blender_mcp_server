from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.jobs import router as jobs_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.repository import JobRepository
from app.services.agent import AgentService
from app.services.events import EventBus
from app.services.instantmesh import InstantMeshRunner
from app.services.jobs import JobService
from app.services.mcp import StdioMcpClient
from app.services.ollama import OllamaClient
from app.services.storage import StorageService
from app.services.tools import ToolExecutor

configure_logging()
settings = get_settings()

storage = StorageService(upload_dir=settings.upload_dir, output_dir=settings.output_dir)
repository = JobRepository(settings.data_dir / "agent.db")
event_bus = EventBus()
ollama = OllamaClient(settings)
instantmesh = InstantMeshRunner(settings)
mcp_client = StdioMcpClient(settings)
tool_executor = ToolExecutor(instantmesh=instantmesh, mcp_client=mcp_client)
agent = AgentService(settings=settings, ollama=ollama, tools=tool_executor)
job_service = JobService(
    repository=repository,
    event_bus=event_bus,
    agent=agent,
    create_output_path=lambda: storage.create_output_path(".glb"),
)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.storage_service = storage
app.state.repository = repository
app.state.event_bus = event_bus
app.state.job_service = job_service

app.include_router(jobs_router)
app.mount("/files", StaticFiles(directory=Path(settings.data_dir).resolve()), name="files")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
