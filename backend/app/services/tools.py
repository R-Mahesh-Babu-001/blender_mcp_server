from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.instantmesh import InstantMeshRunner
from app.services.mcp import StdioMcpClient


class ToolExecutor:
    def __init__(self, instantmesh: InstantMeshRunner, mcp_client: StdioMcpClient) -> None:
        self._instantmesh = instantmesh
        self._mcp = mcp_client

    async def _run_blender_code(self, code: str) -> dict[str, Any]:
        return await self._mcp.call_tool("execute_blender_code", {"code": code})

    async def generate_mesh(self, *, image_path: Path, output_path: Path) -> dict[str, Any]:
        mesh_path = await self._instantmesh.generate(image_path=image_path, output_path=output_path)
        code = f"""
import bpy
from mathutils import Vector

existing = set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath={json.dumps(str(mesh_path))})
imported = [obj for obj in bpy.context.selected_objects if obj.name not in existing]
if not imported:
    imported = [obj for obj in bpy.context.selected_objects]

if not imported:
    raise RuntimeError("No objects were imported from the GLB file.")

for obj in imported:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

for obj in imported:
    obj.location = (0.0, 0.0, 0.0)

mesh_objects = [obj for obj in imported if obj.type == 'MESH']
if mesh_objects:
    max_dim = max(max(obj.dimensions) for obj in mesh_objects)
    if max_dim > 0:
        scale = 1.0 / max_dim
        for obj in mesh_objects:
            obj.scale = tuple(component * scale for component in obj.scale)
    for obj in mesh_objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True

bpy.ops.wm.save_mainfile()
print("Imported and normalized", [obj.name for obj in imported])
"""
        await self._run_blender_code(code)
        return {"model_path": str(mesh_path)}

    async def blender_modify(
        self,
        *,
        action: str,
        args: dict[str, Any] | None = None,
        model_path: str | None = None,
    ) -> dict[str, Any]:
        args = args or {}
        normalized_action = action.lower()
        normalized_action_spaced = normalized_action.replace("_", " ").replace("-", " ")
        combined_text = f"{normalized_action} {normalized_action_spaced} {json.dumps(args).lower().replace('_', ' ')}"
        results: list[dict[str, Any]] = []
        operation = str(args.get("operation", "")).strip().lower()
        target_shape = str(args.get("target_shape", "")).strip().lower()
        axis = str(args.get("axis", "")).strip().lower()
        material = str(args.get("material", "")).strip().lower()
        animation = str(args.get("animation", "")).strip().lower()
        scale_terms = [
            "taller",
            "tall",
            "height",
            "increase height",
            "increase the height",
            "make taller",
            "make it taller",
            "elongate",
            "stretch",
            "higher",
            "grow",
            "scale z",
            "scale up",
        ]
        shape_to_sphere_terms = [
            "circle",
            "round",
            "rounded",
            "sphere",
            "ball",
        ]
        shape_to_cylinder_terms = [
            "cylinder",
            "cylindrical",
            "tube",
        ]
        shape_to_triangle_terms = [
            "triangle",
            "triangular",
            "tri prism",
            "triangular prism",
        ]
        if model_path:
            import_code = f"""
import bpy
bpy.ops.import_scene.gltf(filepath={json.dumps(str(model_path))})
print("Imported model", {json.dumps(str(model_path))})
"""
            results.append(await self._run_blender_code(import_code))
        structured_scale = operation == "scale_axis" and axis in {"x", "y", "z"}
        should_scale_z = (
            structured_scale and axis == "z"
        ) or (
            any(term in combined_text for term in scale_terms)
            or ("increase" in combined_text and "z" in combined_text)
            or ("increase" in combined_text and "vertical" in combined_text)
            or normalized_action in {"scale", "scale_z", "resize", "increase_height"}
        )
        if should_scale_z or structured_scale:
            factor = 1.35
            scale_axis = axis if structured_scale else "z"
            if isinstance(args.get("factor"), (int, float)):
                factor = float(args["factor"])
            elif isinstance(args.get("value"), list) and len(args["value"]) >= 3:
                try:
                    factor = float(args["value"][2])
                except (TypeError, ValueError):
                    factor = 1.35
            elif "slightly" in combined_text:
                factor = 1.1
            elif "much" in combined_text or "significantly" in combined_text or "a lot" in combined_text:
                factor = 1.6
            scale_code = """
import bpy

targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
if not targets and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type == 'MESH']

for obj in targets:
    index = AXIS_INDEX
    obj.scale[index] *= FACTOR

print("Scaled objects on axis", AXIS_NAME, [obj.name for obj in targets])
""".replace("FACTOR", str(factor)).replace("AXIS_INDEX", str({"x": 0, "y": 1, "z": 2}[scale_axis])).replace("AXIS_NAME", json.dumps(scale_axis))
            results.append(await self._run_blender_code(scale_code))
        should_make_metallic = (
            operation == "set_material" and material == "metallic"
        ) or (
            "metal" in combined_text
            or normalized_action in {"material_set", "assign_material", "set_material"}
        )
        if should_make_metallic:
            material_code = """
import bpy

material = bpy.data.materials.get("AgentMetal")
if material is None:
    material = bpy.data.materials.new(name="AgentMetal")
material.use_nodes = True
principled = material.node_tree.nodes.get("Principled BSDF")
if principled is None:
    raise RuntimeError("Principled BSDF node not found.")
principled.inputs["Metallic"].default_value = 1.0
principled.inputs["Roughness"].default_value = 0.2
principled.inputs["Base Color"].default_value = (0.72, 0.74, 0.78, 1.0)

targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
if not targets and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type == 'MESH']

for obj in targets:
    if not obj.data.materials:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material

print("Assigned AgentMetal to", [obj.name for obj in targets])
"""
            results.append(await self._run_blender_code(material_code))
        should_animate = (
            operation == "animate" and animation in {"spin", "bounce"}
        ) or any(
            term in combined_text
            for term in ["animate", "animation", "spin", "rotate", "bounce", "jump", "keyframe"]
        )
        if should_animate:
            animation_code = """
import bpy
import math

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 48

targets = [obj for obj in bpy.context.selected_objects if obj.type in {'MESH', 'ARMATURE', 'EMPTY'}]
if not targets and bpy.context.active_object:
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type in {'MESH', 'ARMATURE', 'EMPTY'}][:1]

animated = []
for obj in targets:
    scene.frame_set(1)
    start_location = obj.location.copy()
    start_rotation = obj.rotation_euler.copy()

    obj.keyframe_insert(data_path='location', frame=1)
    obj.keyframe_insert(data_path='rotation_euler', frame=1)

    if BOUNCE:
        scene.frame_set(24)
        obj.location.z = start_location.z + 1.0
        obj.keyframe_insert(data_path='location', frame=24)
        scene.frame_set(48)
        obj.location = start_location
        obj.keyframe_insert(data_path='location', frame=48)

    if SPIN:
        scene.frame_set(48)
        obj.rotation_euler = start_rotation
        obj.rotation_euler.z += math.radians(360)
        obj.keyframe_insert(data_path='rotation_euler', frame=48)

    animated.append(obj.name)

scene.frame_set(1)
print("Animated objects", animated)
""".replace("BOUNCE", "True" if (animation == "bounce" or any(term in combined_text for term in ["bounce", "jump"])) else "False").replace(
                "SPIN", "True" if (animation == "spin" or any(term in combined_text for term in ["spin", "rotate", "animation", "animate"])) else "False"
            )
            results.append(await self._run_blender_code(animation_code))
        should_make_sphere = (
            (operation == "shape_convert" and target_shape == "sphere")
        ) or (
            any(term in combined_text for term in shape_to_sphere_terms)
            and any(term in combined_text for term in ["shape", "change", "convert", "turn", "make", "rectangle", "square", "cube"])
        )
        should_make_cylinder = (
            (operation == "shape_convert" and target_shape == "cylinder")
        ) or (
            any(term in combined_text for term in shape_to_cylinder_terms)
            and any(term in combined_text for term in ["shape", "change", "convert", "turn", "make"])
        )
        should_make_triangle = (
            (operation == "shape_convert" and target_shape == "triangle")
        ) or (
            any(term in combined_text for term in shape_to_triangle_terms)
            and any(term in combined_text for term in ["shape", "change", "convert", "turn", "make"])
        )
        if should_make_sphere:
            sphere_code = """
import bpy
import math

targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
if not targets and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type == 'MESH'][:1]

converted = []
for obj in targets:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    location = obj.location.copy()
    rotation = obj.rotation_euler.copy()
    max_dim = max(obj.dimensions) if max(obj.dimensions) > 0 else 1.0
    name = obj.name
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=max_dim / 2.0, location=location, rotation=rotation)
    new_obj = bpy.context.active_object
    new_obj.name = name
    for polygon in new_obj.data.polygons:
        polygon.use_smooth = True
    converted.append(new_obj.name)

print("Converted objects to sphere", converted)
"""
            results.append(await self._run_blender_code(sphere_code))
        elif should_make_triangle:
            triangle_code = """
import bpy

targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
if not targets and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type == 'MESH'][:1]

converted = []
for obj in targets:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    location = obj.location.copy()
    rotation = obj.rotation_euler.copy()
    radius = max(obj.dimensions.x, obj.dimensions.y) / 2.0 if max(obj.dimensions.x, obj.dimensions.y) > 0 else 1.0
    depth = obj.dimensions.z if obj.dimensions.z > 0 else 2.0
    name = obj.name
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=radius, depth=depth, location=location, rotation=rotation)
    new_obj = bpy.context.active_object
    new_obj.name = name
    converted.append(new_obj.name)

print("Converted objects to triangle prism", converted)
"""
            results.append(await self._run_blender_code(triangle_code))
        elif should_make_cylinder:
            cylinder_code = """
import bpy

targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
if not targets and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
    targets = [bpy.context.active_object]
if not targets:
    targets = [obj for obj in bpy.data.objects if obj.type == 'MESH'][:1]

converted = []
for obj in targets:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    location = obj.location.copy()
    rotation = obj.rotation_euler.copy()
    radius = max(obj.dimensions.x, obj.dimensions.y) / 2.0 if max(obj.dimensions.x, obj.dimensions.y) > 0 else 1.0
    depth = obj.dimensions.z if obj.dimensions.z > 0 else 2.0
    name = obj.name
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location, rotation=rotation)
    new_obj = bpy.context.active_object
    new_obj.name = name
    for polygon in new_obj.data.polygons:
        polygon.use_smooth = True
    converted.append(new_obj.name)

print("Converted objects to cylinder", converted)
"""
            results.append(await self._run_blender_code(cylinder_code))
        if not results:
            results.append(
                {
                    "result": (
                        "No supported Blender operation matched the request yet. "
                        "Try scale taller, make metallic, rotate, animate, triangle, sphere, or cylinder."
                    )
                }
            )
        return {"operations": results, "action": action, "args": args}
