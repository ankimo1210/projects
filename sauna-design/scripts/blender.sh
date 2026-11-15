#!/usr/bin/env bash
# Run the Windows Blender from WSL with WSL paths converted to Windows UNC paths.
#   scripts/blender.sh build [--rooms main,water,rest,other]
#   scripts/blender.sh render <view> [--res 2400] [--samples 1024] [--exposure 0] [--name suffix]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${SAUNA_DATA_ROOT:-$HERE/../_data/sauna-design/fable-v3}"
DATA="$(realpath "$DATA")"
BLENDER="${BLENDER:-/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
MODEL="$DATA/model/sauna_a_v3.blend"
w() { wslpath -w "$1"; }
cmd="$1"; shift
mkdir -p "$DATA/model" "$DATA/renders" "$DATA/logs"
case "$cmd" in
  build)
    "$BLENDER" -b --factory-startup --python "$(w "$HERE/blender/build.py")" -- \
      --data-root "$(w "$DATA")" --plan "$(w "$HERE/plan/plan_a.json")" "$@" 2>&1 | tee "$DATA/logs/build.log" | grep -E "BUILD_OK|Error|Traceback|error|^  File|Exception" || true
    ;;
  render)
    view="$1"; shift
    name="$view"
    args=()
    while [ $# -gt 0 ]; do
      if [ "$1" = "--name" ]; then name="$2"; shift 2; else args+=("$1"); shift; fi
    done
    "$BLENDER" -b "$(w "$MODEL")" --python "$(w "$HERE/blender/render.py")" -- \
      --view "$view" --out "$(w "$DATA/renders")\\$name.png" "${args[@]}" 2>&1 | tee "$DATA/logs/render_$name.log" | grep -E "RENDER_OK|Error|Traceback|^  File|Exception" || true
    ;;
  glb)
    "$BLENDER" -b "$(w "$MODEL")" --python "$(w "$HERE/blender/export_glb.py")" -- \
      --out "$(w "$DATA/model")\\sauna_a_v3.glb" "$@" 2>&1 | tee "$DATA/logs/export_glb.log" | grep -E "GLB_OK|Error|Traceback|^  File|Exception" || true
    ;;
  py)
    script="$1"; shift
    "$BLENDER" -b "$(w "$MODEL")" --python "$(w "$script")" -- "$@"
    ;;
  *) echo "usage: blender.sh build|render|glb|py ..."; exit 2 ;;
esac
