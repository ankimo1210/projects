#!/usr/bin/env python3
"""Fetch the CC0 Poly Haven assets used by the sauna model.

Source: https://polyhaven.com (official API https://api.polyhaven.com), license CC0 1.0.
Writes files under <data-root>/assets/polyhaven/<asset_id>/ and a manifest
(assets/polyhaven/manifest.json) with source URL, size and md5 for every file.

Usage:  python3 scripts/fetch_assets.py [--data-root ../_data/sauna-design/fable-v3]
"""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

UA = "blender-asset-fetch/1.0"
API = "https://api.polyhaven.com"

# asset id -> (resolution, wanted maps)
TEXTURES = {
    "cherry_veneer": ("2k", ["Diffuse", "Rough", "nor_gl"]),
}
MODELS = {
    "moon_rock_02": "1k",
    "moon_rock_03": "1k",
    "moon_rock_04": "1k",
    "moon_rock_06": "1k",
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and hashlib.md5(dest.read_bytes()).hexdigest() == md5:
        return "cached"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise RuntimeError(f"md5 mismatch for {url}")
    dest.write_bytes(data)
    return "downloaded"


def main():
    here = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(here.parent / "_data" / "sauna-design" / "fable-v3"))
    args = ap.parse_args()
    root = pathlib.Path(args.data_root) / "assets" / "polyhaven"
    manifest = {
        "source": "https://polyhaven.com",
        "license": "CC0 1.0 (https://polyhaven.com/license)",
        "assets": {},
    }

    for aid, (res, maps) in TEXTURES.items():
        files = get_json(f"{API}/files/{aid}")
        entry = {"type": "texture", "page": f"https://polyhaven.com/a/{aid}", "files": []}
        for m in maps:
            info = files[m][res]["jpg"]
            name = info["url"].rsplit("/", 1)[1]
            state = download(info["url"], root / aid / name, info.get("md5"))
            entry["files"].append(
                {
                    "file": f"{aid}/{name}",
                    "url": info["url"],
                    "size": info["size"],
                    "md5": info.get("md5"),
                }
            )
            print(aid, name, state)
        manifest["assets"][aid] = entry

    for aid, res in MODELS.items():
        files = get_json(f"{API}/files/{aid}")
        info = files["gltf"][res]["gltf"]
        name = info["url"].rsplit("/", 1)[1]
        entry = {"type": "model", "page": f"https://polyhaven.com/a/{aid}", "files": []}
        state = download(info["url"], root / aid / name, info.get("md5"))
        entry["files"].append(
            {
                "file": f"{aid}/{name}",
                "url": info["url"],
                "size": info["size"],
                "md5": info.get("md5"),
            }
        )
        print(aid, name, state)
        for rel, inc in info.get("include", {}).items():
            rel_path = pathlib.PurePosixPath(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                raise RuntimeError(f"unsafe include path {rel}")
            state = download(inc["url"], root / aid / rel_path, inc.get("md5"))
            entry["files"].append(
                {
                    "file": f"{aid}/{rel}",
                    "url": inc["url"],
                    "size": inc["size"],
                    "md5": inc.get("md5"),
                }
            )
            print(aid, rel, state)
        manifest["assets"][aid] = entry

    (root / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("manifest", root / "manifest.json")


if __name__ == "__main__":
    sys.exit(main())
