from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def check_runtime() -> int:
    missing: list[str] = []
    try:
        import numpy  # noqa: F401
    except ModuleNotFoundError:
        missing.append("numpy")
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        missing.append("torch")
        torch = None  # type: ignore
    try:
        import rembg  # noqa: F401
    except ModuleNotFoundError:
        missing.append("rembg")
    try:
        import trimesh  # noqa: F401
    except ModuleNotFoundError:
        missing.append("trimesh")

    if missing:
        return fail(
            "InstantMesh runtime is incomplete. Missing packages: "
            + ", ".join(missing)
            + ". Rebuild vendor/InstantMesh/.venv with the project setup."
        )

    if torch is not None and not torch.cuda.is_available():
        return fail(
            "InstantMesh requires CUDA but torch.cuda.is_available() is false. "
            "Install the CUDA-enabled PyTorch build and required Windows CUDA toolchain."
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="")
    args = parser.parse_args()

    runtime_status = check_runtime()
    if runtime_status != 0:
        return runtime_status

    workspace = Path(__file__).resolve().parents[1]
    instantmesh_dir = workspace / "vendor" / "InstantMesh"
    config_path = Path(args.config) if args.config else instantmesh_dir / "configs" / "instant-mesh-large.yaml"
    input_path = Path(args.image).resolve()
    output_path = Path(args.output).resolve()

    if not config_path.exists():
        return fail(f"InstantMesh config not found: {config_path}")
    if not input_path.exists():
        return fail(f"Input image not found: {input_path}")

    with tempfile.TemporaryDirectory(prefix="instantmesh-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        command = [
            sys.executable,
            "run.py",
            str(config_path),
            str(input_path),
            "--output_path",
            str(temp_dir),
        ]
        process = subprocess.run(
            command,
            cwd=str(instantmesh_dir),
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            return fail(
                f"InstantMesh command failed with exit code {process.returncode}.\n"
                f"STDERR:\n{process.stderr.strip()}\nSTDOUT:\n{process.stdout.strip()}"
            )

        mesh_dir = temp_dir / config_path.stem / "meshes"
        mesh_candidates = sorted(mesh_dir.glob("*.obj"))
        if not mesh_candidates:
            return fail(f"InstantMesh completed but no OBJ mesh was produced in {mesh_dir}")

        mesh_path = mesh_candidates[0]
        if output_path.suffix.lower() == ".obj":
            shutil.copyfile(mesh_path, output_path)
            print(str(output_path))
            return 0

        try:
            import trimesh  # type: ignore
        except ModuleNotFoundError:
            return fail("trimesh is required to convert InstantMesh OBJ output into GLB.")

        scene_or_mesh = trimesh.load(mesh_path, force="scene")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scene_or_mesh.export(output_path)
        print(str(output_path))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
