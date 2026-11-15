"""Read-only structural checks for Fable's delivery; visual review remains manual."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from pathlib import Path

from dispatch_fable import DATA


def png_info(path: Path) -> dict:
    result: dict = {}
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            return {"valid_png": False}
        while True:
            header = stream.read(8)
            if len(header) != 8:
                break
            size, kind = struct.unpack(">I4s", header)
            if kind == b"IHDR":
                payload = stream.read(size)
                result.update(
                    width=struct.unpack(">I", payload[:4])[0],
                    height=struct.unpack(">I", payload[4:8])[0],
                )
            elif kind == b"tEXt" and size < 100000:
                key, _, value = stream.read(size).partition(b"\0")
                if key in {b"Software", b"RenderTime", b"Blender", b"Cycles"}:
                    result[key.decode("latin1")] = value.decode("latin1", errors="replace")[:200]
            else:
                stream.seek(size, 1)
            stream.seek(4, 1)
            if kind == b"IEND":
                break
    result["valid_png"] = bool(result.get("width") and result.get("height"))
    return result


def glb_info(path: Path) -> dict:
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            return {"valid_glb": False}
        chunk_size, chunk_kind = struct.unpack("<II", stream.read(8))
        if chunk_kind != 0x4E4F534A:
            return {"valid_glb": False}
        document = json.loads(stream.read(chunk_size))
    position_accessors = {
        primitive["attributes"]["POSITION"]
        for mesh in document.get("meshes", [])
        for primitive in mesh.get("primitives", [])
        if "POSITION" in primitive.get("attributes", {})
    }
    return {
        "valid_glb": True,
        "meshes": len(document.get("meshes", [])),
        "nodes": len(document.get("nodes", [])),
        "materials": len(document.get("materials", [])),
        "position_vertices": sum(
            document["accessors"][index]["count"] for index in position_accessors
        ),
    }


def main() -> None:
    output = DATA / "fable-v3"
    files = [path for path in sorted(output.rglob("*")) if path.is_file()]
    records = []
    for path in files:
        suffix = path.suffix.lower()
        if suffix not in {".png", ".blend", ".glb"}:
            continue
        item = {
            "path": subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
        }
        if suffix == ".png":
            item.update(png_info(path))
        elif suffix == ".glb":
            item.update(glb_info(path))
        else:
            with path.open("rb") as stream:
                header = stream.read(12)
            if header.startswith(b"BLENDER"):
                item["native_encoding"] = "Blender"
            elif header[:4] == bytes.fromhex("28b52ffd"):
                item["native_encoding"] = "zstd-compressed Blender file"
            elif header[:2] == bytes.fromhex("1f8b"):
                item["native_encoding"] = "gzip-compressed Blender file"
            else:
                item["native_encoding"] = "unknown; requires application-level validation"
        records.append(item)
    report = {
        "file_count": len(files),
        "output_bytes": sum(path.stat().st_size for path in files),
        "artifacts": records,
        "limits": "Structural checks only; appearance, engineering and budget require separate review.",
    }
    saved = output / "verification" / "parent_delivery_check.json"
    saved.parent.mkdir(exist_ok=True)
    saved.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
