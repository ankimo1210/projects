#!/usr/bin/env bash
# Run the Windows Blender from WSL with WSL paths converted to Windows UNC paths (model version v8).
#   scripts/blender.sh build [--rooms main,water,rest,other]
#   scripts/blender.sh render <view> [--res 2400] [--samples 1024] [--exposure 0] [--name file] [--tests]
#   scripts/blender.sh glb [--draco]
#   scripts/blender.sh py <script.py> [args]        (opens the saved model read-only unless the script saves)
# Outputs go to the canonical data root, never into the source tree. Override with SAUNA_DATA_ROOT.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="v8"
DATA="${SAUNA_DATA_ROOT:-/home/kazumasa/projects/_data/sauna-design/fable-$VERSION}"
DATA="$(realpath "$DATA")"
case "$DATA" in "$HERE"/*) echo "refusing to write generated files inside the source tree: $DATA" >&2; exit 2 ;; esac
case "$DATA" in */fable-v3|*/fable-v4|*/fable-v5|*/fable-v6|*/fable-v7|*/reference-v2) echo "refusing to write into a frozen folder: $DATA" >&2; exit 2 ;; esac
BLENDER="${BLENDER:-/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
MODEL="${SAUNA_MODEL:-$DATA/model/sauna_a_$VERSION.blend}"
w() { wslpath -w "$1"; }
cmd="$1"; shift
mkdir -p "$DATA/model" "$DATA/renders" "$DATA/logs"
case "$cmd" in
  build)
    "$BLENDER" -b --factory-startup --python-exit-code 1 --python "$(w "$HERE/blender/build.py")" -- \
      --data-root "$(w "$DATA")" --plan "$(w "$HERE/plan/plan_a.json")" "$@" 2>&1 | tee "$DATA/logs/build.log" | grep -E "BUILD_OK|Error|Traceback|error|^  File|Exception"
    ;;
  render)
    view="$1"; shift
    name="$view"; outdir="$DATA/renders"
    args=()
    while [ $# -gt 0 ]; do
      case "$1" in
        --name) name="$2"; shift 2 ;;
        --tests) outdir="$DATA/tests"; shift ;;
        *) args+=("$1"); shift ;;
      esac
    done
    mkdir -p "$outdir"
    "$BLENDER" -b "$(w "$MODEL")" --python-exit-code 1 --python "$(w "$HERE/blender/render.py")" -- \
      --view "$view" --out "$(w "$outdir")\\$name.png" "${args[@]}" 2>&1 | tee "$DATA/logs/render_$name.log" | grep -E "RENDER_OK|Error|Traceback|^  File|Exception"
    ;;
  glb)
    "$BLENDER" -b "$(w "$MODEL")" --python-exit-code 1 --python "$(w "$HERE/blender/export_glb.py")" -- \
      --out "$(w "$DATA/model")\\sauna_a_$VERSION.glb" "$@" 2>&1 | tee "$DATA/logs/export_glb.log" | grep -E "GLB_OK|Error|Traceback|^  File|Exception"
    ;;
  py)
    script="$1"; shift
    "$BLENDER" -b "$(w "$MODEL")" --python-exit-code 1 --python "$(w "$script")" -- "$@"
    ;;
  *) echo "usage: blender.sh build|render|glb|py ..."; exit 2 ;;
esac
