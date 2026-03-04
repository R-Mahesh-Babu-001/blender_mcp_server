from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.core.config import Settings
from app.schemas import AgentToolCall
from app.services.ollama import OllamaClient
from app.services.tools import ToolExecutor

SYSTEM_PROMPT = """
You are a local-only 3D modeling agent.
Return JSON only with this schema:
{"tool":"generate_mesh"|"blender_modify"|"finish","args":{...}}

Rules:
- Use "generate_mesh" when an image needs to become a 3D model.
- Use "blender_modify" when the user wants Blender changes applied to an existing model.
- If no image_path is present, never use "generate_mesh". Use "blender_modify" for existing scene edits, model edits, and animation edits.
- Use "finish" only when the request is complete.
- For "blender_modify", always return structured args.
- Include args.action with the original requested edit in short snake_case or short text.
- Include args.operation when possible. Allowed operations:
  - "shape_convert"
  - "scale_axis"
  - "set_material"
  - "animate"
  - "transform"
- For shape conversion, include args.target_shape with one of:
  - "sphere"
  - "triangle"
  - "cylinder"
- For scaling, include args.axis with "x", "y", or "z" and args.factor as a number.
- For materials, include args.material with values like "metallic".
- For animation, include args.animation with values like "spin" or "bounce".
- Prefer precise structured args over vague action text.
- Never return plain text outside the JSON object.
"""


class AgentService:
    def __init__(self, settings: Settings, ollama: OllamaClient, tools: ToolExecutor) -> None:
        self._settings = settings
        self._ollama = ollama
        self._tools = tools

    async def run(
        self,
        *,
        prompt: str,
        image_path: Path | None,
        model_path: str | None,
        emit: Callable,
        create_output_path: Callable[[], Path],
    ) -> dict[str, Any]:
        context = {"model_path": model_path, "image_path": str(image_path) if image_path else None}
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"prompt": prompt, **context})},
        ]

        for step in range(1, self._settings.agent_max_steps + 1):
            await emit("agent_thinking", {"step": step, "prompt": prompt, "context": context})
            raw_response = await self._ollama.ask_for_tool_call(messages)
            tool_call = AgentToolCall.model_validate(raw_response)
            if tool_call.tool == "generate_mesh" and not image_path:
                tool_call = AgentToolCall(tool="blender_modify", args={"action": prompt, **tool_call.args})
            await emit("tool_selected", {"step": step, "tool": tool_call.tool, "args": tool_call.args})

            if tool_call.tool == "finish":
                return {"status": "completed", "result_path": context.get("model_path")}

            if tool_call.tool == "generate_mesh":
                if not image_path:
                    raise RuntimeError("The agent requested mesh generation but no image was provided.")
                output_path = create_output_path()
                result = await self._tools.generate_mesh(image_path=image_path, output_path=output_path)
                context["model_path"] = result["model_path"]
                messages.append({"role": "assistant", "content": json.dumps(tool_call.model_dump())})
                messages.append({"role": "tool", "content": json.dumps(result)})
                await emit("tool_completed", {"tool": tool_call.tool, "result": result})
                continue

            if tool_call.tool == "blender_modify":
                result = await self._tools.blender_modify(
                    action=str(tool_call.args.get("action", prompt)),
                    args=tool_call.args,
                    model_path=context.get("model_path"),
                )
                messages.append({"role": "assistant", "content": json.dumps(tool_call.model_dump())})
                messages.append({"role": "tool", "content": json.dumps(result)})
                await emit("tool_completed", {"tool": tool_call.tool, "result": result})
                return {"status": "completed", "result_path": context.get("model_path")}

        raise RuntimeError("Agent exceeded maximum number of steps without reaching finish.")
