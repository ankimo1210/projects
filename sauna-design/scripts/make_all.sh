#!/usr/bin/env bash
# Regenerate everything from source: assets -> .blend -> 5 renders -> labelled plan -> .glb -> viewer copy -> manifest.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$(realpath "${SAUNA_DATA_ROOT:-$HERE/../_data/sauna-design/fable-v3}")"
cd "$HERE"
python3 scripts/fetch_assets.py --data-root "$DATA"
scripts/blender.sh build
for v in main water rest; do
  scripts/blender.sh render "$v" --res 2400 --samples 1500 --threshold 0.01 --name "sauna_${v}_v3"
done
for v in overview plan; do
  scripts/blender.sh render "$v" --res 2400 --samples 400 --hide Ceilings --world 0.35 --name "sauna_${v}_v3"
done
python3 scripts/label_plan.py "$DATA"
scripts/blender.sh glb --draco
rm -f "$DATA/model/sauna_a_v3.blend1"
mkdir -p "$DATA/viewer" && cp viewer/index.html "$DATA/viewer/index.html"
python3 scripts/write_manifest.py "$DATA"
