"""Create a new Unreal working copy without replacing existing user work."""

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path


def inspect_glb(path: Path) -> dict:
    """Reject truncated GLBs and exports requiring files outside the package."""
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f"Truncated GLB: {path}")
    magic, version, total = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError(f"Invalid GLB header: {path}")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A or length % 4 or 20 + length > len(data):
        raise ValueError(f"Invalid GLB JSON chunk: {path}")
    document = json.loads(data[20 : 20 + length])
    if document.get("asset", {}).get("version") != "2.0" or not document.get("meshes"):
        raise ValueError(f"GLB contains no glTF 2.0 meshes: {path}")
    for entry in document.get("buffers", []) + document.get("images", []):
        uri = entry.get("uri", "")
        if uri and not uri.startswith("data:"):
            raise ValueError(f"GLB requires an external file: {uri}")
    offset = 20 + length
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated GLB chunk header")
        chunk_length = struct.unpack_from("<I", data, offset)[0]
        offset += 8 + chunk_length
        if chunk_length % 4 or offset > len(data):
            raise ValueError("Truncated or unaligned GLB chunk")
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mesh_count": len(document["meshes"]),
        "material_count": len(document.get("materials", [])),
    }


def prepare_project(source_root: Path, destination: Path) -> Path:
    source_root = source_root.resolve()
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to replace an existing working copy: {destination}")
    if destination.resolve().is_relative_to(source_root):
        raise ValueError("The working copy must be outside the source project")
    template = source_root / "unreal"
    scene = source_root / "assets" / "export" / "komorebi.glb"
    for required in (
        template / "Komorebi3D.uproject",
        template / "Content" / "Python" / "bootstrap_scene.py",
        scene,
    ):
        if not required.is_file():
            raise FileNotFoundError(f"Required project input is missing: {required}")
    json.loads((template / "Komorebi3D.uproject").read_text(encoding="utf-8"))
    metadata = inspect_glb(scene)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        template,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "Saved", "Intermediate", "DerivedDataCache"),
    )
    asset_dir = destination / "SourceAssets"
    asset_dir.mkdir(exist_ok=True)
    shutil.copy2(scene, asset_dir / "komorebi.glb")
    (destination / "source_manifest.json").write_text(
        json.dumps({"project": "Komorebi 3D", "glb": metadata}, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination / "Komorebi3D.uproject"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        project = prepare_project(Path(__file__).resolve().parents[1], args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot prepare project: {exc}\n")
    print(f"Prepared: {project}")
    print("Open Open.cmd on Windows after installing Unreal Engine 5.8.")
    print("Unreal import and rendering have not been run by this command.")


if __name__ == "__main__":
    main()
