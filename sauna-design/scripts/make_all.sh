#!/usr/bin/env bash
# Regenerate v8: model, mesh check, figure, the views of the changed rooms, .glb, viewer, manifest.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="v8"
DATA="$(realpath -m "${SAUNA_DATA_ROOT:-/home/kazumasa/projects/_data/sauna-design/fable-$V}")"
case "$DATA" in "$HERE"/*) echo "refusing source-tree output" >&2; exit 2 ;; esac
case "$DATA" in */fable-v3|*/fable-v4|*/fable-v5|*/fable-v6|*/fable-v7|*/reference-v2) echo "refusing frozen output" >&2; exit 2 ;; esac
mkdir -p "$DATA"
export SAUNA_DATA_ROOT="$DATA"
B="$HERE/scripts/blender.sh"
python3 -B "$HERE/scripts/fetch_assets.py" --data-root "$DATA"
"$B" build
# mesh check; also compares the untouched stages with the frozen v7 model (opened read-only)
"$B" py "$HERE/blender/verify_v8.py" "$(wslpath -w "$DATA")" | grep -E "V8_OK|Error|Traceback|^  File|Exception"
python3 -B "$HERE/scripts/v8_diagram.py" "$DATA"
for view in self self_seat dry water annex annex_pool; do
  "$B" render "$view" --res 2400 --samples 1500 --threshold 0.01 --name "sauna_${view}_$V"
done
# the two postures of the dry room with the assumed bodies shown (the two standing ones in front of the camera hidden)
"$B" render dry_seats --res 2400 --samples 1500 --threshold 0.01 --show Check_people --hide-objects Body_DT --name "sauna_dry_people_$V"
"$B" render bath_top --res 2400 --samples 400 --hide Ceilings --world 0.35 --name "sauna_bath_top_$V"
"$B" glb --draco
mkdir -p "$DATA/viewer"
cp "$HERE/viewer/index.html" "$DATA/viewer/index.html"
# Only this run's regenerable native backup; frozen versions are refused above.
rm -f -- "$DATA/model/sauna_a_$V.blend1"
python3 -B "$HERE/scripts/write_manifest.py" "$DATA"
