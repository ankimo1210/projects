#!/usr/bin/env python3
"""Fetch the CC0 Poly Haven assets used by the sauna model.

Source: https://polyhaven.com (official API https://api.polyhaven.com), license CC0 1.0.
Writes files under <data-root>/assets/polyhaven/<asset_id>/ and a manifest
(assets/polyhaven/manifest.json) with source URL, size and md5 for every file.
A file already present in --cache with the md5 published by the API is copied instead of downloaded
(the cache is only read, never modified).

Usage:  python3 scripts/fetch_assets.py [--data-root <fable-v6>] [--cache <fable-v5>/assets/polyhaven]
"""

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import urllib.request

UA = "blender-asset-fetch/1.0"
API = "https://api.polyhaven.com"
CANONICAL = pathlib.Path("/home/kazumasa/projects/_data/sauna-design")

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


def md5_of(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def obtain(url, dest, md5=None, cached=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and md5_of(dest) == md5:
        return "present"
    if cached is not None and cached.is_file() and md5 and md5_of(cached) == md5:
        shutil.copyfile(cached, dest)
        return "copied from cache"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise RuntimeError(f"md5 mismatch for {url}")
    dest.write_bytes(data)
    return "downloaded"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(CANONICAL / "fable-v8"))
    ap.add_argument("--cache", default=str(CANONICAL / "fable-v7" / "assets" / "polyhaven"))
    args = ap.parse_args()
    root = pathlib.Path(args.data_root) / "assets" / "polyhaven"
    cache = pathlib.Path(args.cache)
    manifest = {
        "source": "https://polyhaven.com",
        "license": "CC0 1.0 (https://polyhaven.com/license)",
        "assets": {},
    }

    def take(aid, rel, info, entry):
        rel_path = pathlib.PurePosixPath(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise RuntimeError(f"unsafe path {rel}")
        state = obtain(info["url"], root / aid / rel_path, info.get("md5"), cache / aid / rel_path)
        entry["files"].append(
            {
                "file": f"{aid}/{rel}",
                "url": info["url"],
                "size": info["size"],
                "md5": info.get("md5"),
            }
        )
        print(aid, rel, state)

    for aid, (res, maps) in TEXTURES.items():
        files = get_json(f"{API}/files/{aid}")
        entry = {"type": "texture", "page": f"https://polyhaven.com/a/{aid}", "files": []}
        for m in maps:
            info = files[m][res]["jpg"]
            take(aid, info["url"].rsplit("/", 1)[1], info, entry)
        manifest["assets"][aid] = entry

    for aid, res in MODELS.items():
        files = get_json(f"{API}/files/{aid}")
        info = files["gltf"][res]["gltf"]
        entry = {"type": "model", "page": f"https://polyhaven.com/a/{aid}", "files": []}
        take(aid, info["url"].rsplit("/", 1)[1], info, entry)
        for rel, inc in info.get("include", {}).items():
            take(aid, rel, inc, entry)
        manifest["assets"][aid] = entry

    (root / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("manifest", root / "manifest.json")


if __name__ == "__main__":
    sys.exit(main())
