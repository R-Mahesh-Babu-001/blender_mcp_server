import bpy
import importlib.util
import traceback
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_ADDON = WORKSPACE / "vendor" / "blender-mcp" / "addon.py"
MODULE_NAME = "blendermcp_runtime"
STARTUP_LOG = WORKSPACE / "blender-startup.log"


def log(message: str) -> None:
    STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with STARTUP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def bootstrap():
    try:
        log("startup begin")
        spec = importlib.util.spec_from_file_location(MODULE_NAME, SOURCE_ADDON)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load Blender MCP addon from {SOURCE_ADDON}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "register"):
            module.register()

        bpy.context.scene.blendermcp_port = 9876
        bpy.context.scene.blendermcp_use_polyhaven = False
        bpy.context.scene.blendermcp_use_hyper3d = False
        bpy.context.scene.blendermcp_use_hunyuan3d = False

        if not bpy.context.scene.blendermcp_server_running:
            bpy.ops.blendermcp.start_server()
            log("socket started")

        log("startup complete")
        print("BLENDER_MCP_READY")
    except Exception:
        log(traceback.format_exc())
    return None


bpy.app.timers.register(bootstrap, first_interval=1.5)
