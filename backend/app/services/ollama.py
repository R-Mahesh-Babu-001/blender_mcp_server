from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ask_for_tool_call(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self._settings.ollama_model,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "enum": ["generate_mesh", "blender_modify", "finish"],
                    },
                    "args": {"type": "object"},
                },
                "required": ["tool", "args"],
            },
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=self._settings.ollama_timeout_seconds) as client:
            response = await client.post(f"{self._settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
        body = response.json()
        content = body["message"]["content"]
        if isinstance(content, dict):
            return content
        return json.loads(content)
