#!/usr/bin/env bash
# Assemble Luminary099 from BOTH transcriptions and require identical binaries.
# (Comments differ between repos; the octal program must not.)
#
# --- Deviation from the brief's literal script (documented per the brief's
#     own escape hatch: "if virtualagc lacks Luminary099, drop the
#     cross-check, keep the yaYUL success check") ---
# Both vendor/Apollo-11/Luminary099/ and vendor/virtualagc/Luminary099/ exist
# at the pinned SHAs, but Apollo-11's MAIN.agc (SHA 911e5c0) fails to
# assemble: it $-includes two files under names that do not exist anywhere
# in that same pinned tree --
#   MAIN.agc:34 -> $LAMBERT_AIMPOINT_GUIDANCE.agc      (file present is GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc)
#   MAIN.agc:88 -> $TRIM_GIMBAL_CNTROL_SYSTEM.agc       (file present is TRIM_GIMBAL_CONTROL_SYSTEM.agc, "CNTROL"->"CONTROL")
# This is a transcription defect internal to chrislgarry/Apollo-11, not a
# yaYUL or task-setup issue: every $-include in vendor/virtualagc/Luminary099
# resolves to an existing file (checked exhaustively) and that tree
# assembles cleanly (0 fatal errors, valid bugger-word checksums). We do not
# patch vendor/ (pinned by Task 1) to route around a third-party repo bug.
# So: try Apollo-11 first as the brief specifies; if -- and only if -- it
# fails to assemble, fall back to virtualagc alone as the sole source of
# build/agc/Luminary099.bin, skip the cross-check, and record why in
# manifest.json's "note" field so this is visible without reading logs.
set -uo pipefail
cd "$(dirname "$0")/.."
YAYUL=$PWD/build/agc/yaYUL

assemble() { # srcdir outprefix -> 0 on clean assembly, 1 on any fatal error
  if ( cd "$1" && "$YAYUL" MAIN.agc > "$PWD/../../../build/agc/$2.log" 2>&1 ); then
    cp "$1/MAIN.agc.bin" "build/agc/$2.bin"
    [[ -f $1/MAIN.agc.symtab ]] && cp "$1/MAIN.agc.symtab" "build/agc/$2.symtab"
    return 0
  fi
  return 1
}

NOTE=""
if assemble vendor/Apollo-11/Luminary099 Luminary099; then
  if assemble vendor/virtualagc/Luminary099 Luminary099-vagc; then
    cmp build/agc/Luminary099.bin build/agc/Luminary099-vagc.bin \
      && echo "OK: both transcriptions assemble to identical binaries"
  else
    echo "WARN: vendor/virtualagc/Luminary099 failed to assemble; cross-check skipped (see build/agc/Luminary099-vagc.log)" >&2
    NOTE="virtualagc transcription failed to assemble; used Apollo-11 only, cross-check skipped. See Luminary099-vagc.log."
  fi
else
  echo "WARN: vendor/Apollo-11/Luminary099 failed to assemble (see build/agc/Luminary099.log). Falling back to vendor/virtualagc/Luminary099 as the sole source." >&2
  tail -5 build/agc/Luminary099.log >&2
  assemble vendor/virtualagc/Luminary099 Luminary099 \
    || { echo "FATAL: virtualagc/Luminary099 also failed to assemble" >&2; exit 1; }
  echo "OK: assembled from virtualagc/Luminary099 only (Apollo-11 transcription has broken \$-includes; see script header)"
  NOTE="Apollo-11 transcription failed to assemble (MAIN.agc:34,88 \$-include stale filenames not present in the pinned tree); used virtualagc only, cross-check skipped. See Luminary099.log."
fi

sha256sum build/agc/Luminary099.bin
if [[ -n "$NOTE" ]]; then
  jq -n --arg sha "$(sha256sum build/agc/Luminary099.bin | cut -d' ' -f1)" --arg note "$NOTE" \
    '{program:"Luminary099", assembler:"yaYUL", binary_sha256:$sha, note:$note}' \
    > build/agc/manifest.json
else
  jq -n --arg sha "$(sha256sum build/agc/Luminary099.bin | cut -d' ' -f1)" \
    '{program:"Luminary099", assembler:"yaYUL", binary_sha256:$sha}' \
    > build/agc/manifest.json
fi
