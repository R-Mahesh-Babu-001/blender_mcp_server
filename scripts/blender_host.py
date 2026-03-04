import bpy
import importlib.util
import time
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_ADDON = WORKSPACE / "vendor" / "blender-mcp" / "addon.py"
MODULE_NAME = "blendermcp_runtime_host"

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

print("BLENDER_MCP_HOST_READY")

while True:
    time.sleep(1)
