from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

from app.core.config import Settings


class StdioMcpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._host = settings.blender_mcp_env_map.get("BLENDER_HOST", "127.0.0.1")
        self._port = int(settings.blender_mcp_env_map.get("BLENDER_PORT", "9876"))

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._settings.blender_allowed_tools:
            raise RuntimeError(f"Tool is not in allowlist: {name}")
        return await asyncio.to_thread(self._call_tool_sync, name, arguments)

    def _call_tool_sync(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "execute_blender_code":
            payload = {"type": "execute_code", "params": {"code": arguments["code"]}}
        elif name == "get_scene_info":
            payload = {"type": "get_scene_info", "params": {}}
        elif name == "get_viewport_screenshot":
            payload = {"type": "get_viewport_screenshot", "params": arguments}
        else:
            raise RuntimeError(f"Unsupported tool for direct Blender transport: {name}")

        with socket.create_connection((self._host, self._port), timeout=10) as sock:
            sock.settimeout(10)
            sock.sendall(json.dumps(payload).encode("utf-8"))

            chunks: list[bytes] = []
            while True:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout as exc:
                    raise RuntimeError(
                        f"Timed out waiting for Blender response on {self._host}:{self._port}"
                    ) from exc
                if not chunk:
                    break
                chunks.append(chunk)
                raw = b"".join(chunks).decode("utf-8", errors="ignore")
                try:
                    response = json.loads(raw)
                    break
                except json.JSONDecodeError:
                    continue
            else:
                response = {}

        if not chunks:
            raise RuntimeError(f"No response received from Blender on {self._host}:{self._port}")

        if response.get("status") != "success":
            raise RuntimeError(response.get("message", "Unknown Blender error"))

        result = response.get("result")
        if isinstance(result, dict):
            return result
        return {"result": result}
