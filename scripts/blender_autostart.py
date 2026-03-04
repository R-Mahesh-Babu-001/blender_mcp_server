import bpy
import importlib.util
import subprocess
import traceback
from pathlib import Path


WORKSPACE = Path(r"C:\Users\gHOST\Downloads\New folder")
SOURCE_ADDON = WORKSPACE / "vendor" / "blender-mcp" / "addon.py"
MODULE_NAME = "blendermcp_autoload"
BACKEND_PYTHON = WORKSPACE / "backend_runtime" / "Scripts" / "python.exe"
WORKSPACE_BOOT = WORKSPACE / "scripts" / "workspace_boot.py"
DETACHED = 0x00000008 | 0x00000200
AUTOSTART_LOG = WORKSPACE / "blender-autostart.log"


def _log(message: str) -> None:
    AUTOSTART_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUTOSTART_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _boot():
    try:
        _log("autostart begin")
        spec = importlib.util.spec_from_file_location(MODULE_NAME, SOURCE_ADDON)
        if spec is None or spec.loader is None:
            _log(f"Unable to load Blender MCP addon from {SOURCE_ADDON}")
            return None

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
            _log("blender addon socket started")

        subprocess.Popen(
            [str(BACKEND_PYTHON), str(WORKSPACE_BOOT)],
            cwd=str(WORKSPACE),
            creationflags=DETACHED,
            close_fds=True,
        )
        _log("workspace boot spawned")

        print("BLENDER_MCP_AUTOSTART_READY")
        _log("autostart complete")
    except Exception:
        _log(traceback.format_exc())
    return None


bpy.app.timers.register(_boot, first_interval=1.0)
