#!/usr/bin/env bash
# V9 building-integration prototype: run blender/architecture_v9.py with the Windows Blender from WSL.
# NOT RUN BY THE AUTHOR. Audit blender/architecture_v9.py first. Run from the worktree root; do not cd elsewhere.
#
# Reads : fable-v8/model/sauna_a_v8.blend (never saved; SHA256 checked before and after)
# Writes: /home/kazumasa/projects/_data/sauna-design/fable-v9 only (fixed; no override)
#
# Suggested order (each line is one Blender process):
#   bash scripts/blender_v9.sh estimate
#   bash scripts/blender_v9.sh build
#   bash scripts/blender_v9.sh verify
#   bash scripts/blender_v9.sh render --view v9_section_deep --tests --res 600 --samples 48     # light test first
#   bash scripts/blender_v9.sh render --view v9_plan         --tests --res 600 --samples 48
#   bash scripts/blender_v9.sh render --view water           --tests --res 600 --samples 48     # V8 camera, study off
#   bash scripts/blender_v9.sh glb
#   bash scripts/blender_v9.sh render --view v9_section_deep                                    # finals: 2400 px
#   bash scripts/blender_v9.sh render --view v9_section_long
#   bash scripts/blender_v9.sh render --view v9_plan
#   bash scripts/blender_v9.sh render --view v9_axo
#   bash scripts/blender_v9.sh render --view v9_under
#   bash scripts/blender_v9.sh render --view water
#   bash scripts/blender_v9.sh verify
# Existing outputs of this script are never replaced unless --replace is added.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="/home/kazumasa/projects/_data/sauna-design/fable-v9"
V8="/home/kazumasa/projects/_data/sauna-design/fable-v8/model/sauna_a_v8.blend"
BLENDER="${BLENDER:-/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
[ "$(realpath "$OUT")" = "$OUT" ] || { echo "refusing: $OUT is not the canonical V9 root" >&2; exit 2; }
[ "$(realpath "$V8")" = "$V8" ] || { echo "refusing: $V8 is not the canonical V8 model" >&2; exit 2; }
[ -d "$OUT" ] || { echo "refusing: $OUT does not exist" >&2; exit 2; }
w() { wslpath -w "$1"; }
step="${1:-}"; [ $# -gt 0 ] && shift
case "$step" in
  estimate|build|verify|render|glb) ;;
  *) echo "usage: blender_v9.sh estimate|build|verify|render --view <name> [...]|glb [--draco] [--no-textures]" >&2; exit 2 ;;
esac
mkdir -p "$OUT/logs"
"$BLENDER" -b --python-exit-code 1 --python "$(w "$HERE/blender/architecture_v9.py")" -- \
  --step "$step" --v8 "$(w "$V8")" --out-root "$(w "$OUT")" "$@" 2>&1 \
  | tee -a "$OUT/logs/v9_$step.log" | grep -E "^V9_|Error|Traceback|^  File|Exception"
