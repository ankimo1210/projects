#!/usr/bin/env bash
# Parent-run native Blender stages for the compact comparison, never frozen versions.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="/home/kazumasa/projects/_data/sauna-design/fable-v10"
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
[ -d "$OUT" ] && [ "$(realpath "$OUT")" = "$OUT" ] || exit 2
step="${1:-}"; [ $# -gt 0 ] && shift
case "$step" in estimate|build|verify|render|glb) ;; *) echo "usage: blender_v10.sh estimate|build|verify|render|glb" >&2; exit 2 ;; esac
mkdir -p "$OUT/logs"
"$BLENDER" -b --python-exit-code 1 --python "$(wslpath -w "$HERE/blender/compact_v10.py")" -- \
  --step "$step" --out-root "$(wslpath -w "$OUT")" "$@" 2>&1 \
  | tee "$OUT/logs/parent_${step}_latest.log" \
  | grep -E "COMPACT|V10|BUILD|VERIFY|RENDER|GLB|Error|Traceback|^  File|Exception|Saved:|Time:"
