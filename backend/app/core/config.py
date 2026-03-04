from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Local 3D Agent", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        alias="CORS_ORIGINS",
    )

    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    upload_dir: Path = Field(default=Path("./data/uploads"), alias="UPLOAD_DIR")
    output_dir: Path = Field(default=Path("./data/outputs"), alias="OUTPUT_DIR")

    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="mistral:7b", alias="OLLAMA_MODEL")
    ollama_timeout_seconds: int = Field(default=120, alias="OLLAMA_TIMEOUT_SECONDS")
    agent_max_steps: int = Field(default=6, alias="AGENT_MAX_STEPS")

    instantmesh_python: str = Field(default="", alias="INSTANTMESH_PYTHON")
    instantmesh_script: str = Field(default="", alias="INSTANTMESH_SCRIPT")
    instantmesh_extra_args: str = Field(default="", alias="INSTANTMESH_EXTRA_ARGS")

    blender_mcp_command: str = Field(default="", alias="BLENDER_MCP_COMMAND")
    blender_mcp_args: str = Field(default="", alias="BLENDER_MCP_ARGS")
    blender_mcp_env: str = Field(default="", alias="BLENDER_MCP_ENV")
    blender_mcp_allowed_tools: str = Field(
        default="get_scene_info,execute_blender_code,get_viewport_screenshot",
        alias="BLENDER_MCP_ALLOWED_TOOLS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def blender_mcp_args_list(self) -> list[str]:
        return [item.strip() for item in self.blender_mcp_args.split(",") if item.strip()]

    @property
    def blender_allowed_tools(self) -> set[str]:
        return {item.strip() for item in self.blender_mcp_allowed_tools.split(",") if item.strip()}

    @property
    def instantmesh_extra_args_list(self) -> list[str]:
        return [item.strip() for item in self.instantmesh_extra_args.split(",") if item.strip()]

    @property
    def blender_mcp_env_map(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for item in self.blender_mcp_env.split(","):
            if not item.strip() or "=" not in item:
                continue
            key, value = item.split("=", 1)
            values[key.strip()] = value.strip()
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()
