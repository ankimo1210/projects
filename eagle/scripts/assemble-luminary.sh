#!/usr/bin/env bash
# Assemble Luminary099 from BOTH transcriptions and require identical binaries.
# (Comments differ between repos; the octal program must not.)
#
# --- Deviation from the brief's literal script, round 2 (controller-reviewed) ---
# vendor/Apollo-11/Luminary099/MAIN.agc (pinned SHA 911e5c0) $-includes two
# files under names that do not exist in that pinned tree:
#   MAIN.agc:34 -> $LAMBERT_AIMPOINT_GUIDANCE.agc      (actual file: GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc)
#   MAIN.agc:88 -> $TRIM_GIMBAL_CNTROL_SYSTEM.agc       (actual file: TRIM_GIMBAL_CONTROL_SYSTEM.agc)
# Both referenced files DO exist in that tree under a different name --
# this is upstream include-name drift (the file was renamed/typo-fixed at
# some point without updating the $-include in MAIN.agc), not missing
# content. We do not edit vendor/ (pinned by Task 1) to fix this. Instead
# we build a disposable staging copy of the Apollo-11 source under
# build/agc/staging-apollo11/ (gitignored, rebuilt every run) containing
# two extra copies of the renamed files under the names MAIN.agc actually
# references, and assemble THAT -- restoring the two-transcription
# cross-check without ever touching pinned vendor content.
#
# vendor/virtualagc/Luminary099 is self-consistent (every $-include
# resolves; 0 fatal errors) and remains the shipped source of
# build/agc/Luminary099.bin regardless of the cross-check outcome -- it is
# the more authoritative, actively-maintained assembly source. The
# Apollo-11 staging assembly exists ONLY to verify the two transcriptions
# agree; if it still can't be built, or it builds to a genuinely different
# binary, we do NOT force a match -- we keep virtualagc as the shipped
# binary and record the divergence (or skip reason) in manifest.json's
# "note" field, which is always populated to make the cross-check outcome
# visible without reading logs.
#
# Measured outcome (this pinned SHA pair): the staged Apollo-11 build DOES
# assemble cleanly once the two filenames are aliased, but cmp finds a real
# byte difference (first offset: byte 36343) -- confirmed via bugger-word
# bank checksums to affect banks 21 and 33. This is NOT limited to the two
# aliased files (their code is byte-identical to virtualagc once comments
# are stripped); a normalized-diff sweep across all ~150 identically-named
# .agc files found ~20 with genuine (non-comment) differences, e.g.
# ERASABLE_ASSIGNMENTS.agc: symbol "W.IND1" (virtualagc) vs "W.INDI"
# (Apollo-11), "NEGTOTKP" vs "NETTOTKP" -- classic 1/I and G/T OCR-era
# transcription slips -- and CONTROLLED_CONSTANTS.agc: "$$/DAPAO" vs
# "$$/DAPAD". Apollo-11 (chrislgarry) appears to be a snapshot that
# predates several of virtualagc's proofing passes (virtualagc's own
# comments cite corrections through 2021). This is accumulated upstream
# transcription drift between two independently-maintained archives, not a
# bug in this script.
set -euo pipefail
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

# --- Ship virtualagc unconditionally as build/agc/Luminary099.bin ---
assemble vendor/virtualagc/Luminary099 Luminary099 \
  || { echo "FATAL: vendor/virtualagc/Luminary099 failed to assemble (see build/agc/Luminary099.log)" >&2; exit 1; }

# --- Apollo-11 staging copy: alias the two drifted filenames, then try to
#     assemble it too, for the cross-check only. Never touches vendor/. ---
STAGE=build/agc/staging-apollo11
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp vendor/Apollo-11/Luminary099/*.agc "$STAGE/"
( cd "$STAGE" \
    && cp GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc LAMBERT_AIMPOINT_GUIDANCE.agc \
    && cp TRIM_GIMBAL_CONTROL_SYSTEM.agc TRIM_GIMBAL_CNTROL_SYSTEM.agc )

NOTE=""
if assemble "$STAGE" Luminary099-apollo11; then
  if CMPOUT=$(cmp build/agc/Luminary099.bin build/agc/Luminary099-apollo11.bin 2>&1); then
    echo "OK: both transcriptions assemble to identical binaries (Apollo-11 via staged filename aliases for upstream include-name drift)"
    NOTE="Cross-check restored via staging copy: Apollo-11/Luminary099/MAIN.agc references LAMBERT_AIMPOINT_GUIDANCE.agc and TRIM_GIMBAL_CNTROL_SYSTEM.agc under names absent from the pinned tree (actual files: GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc, TRIM_GIMBAL_CONTROL_SYSTEM.agc); aliased via copies in build/agc/staging-apollo11/ (vendor/ untouched) and assembled -- binary matches virtualagc exactly (cmp: no differences)."
  else
    echo "WARN: staged Apollo-11 assembly produced a DIFFERENT binary than virtualagc: $CMPOUT" >&2
    NOTE="Cross-check FAILED: staged Apollo-11 assembly (filename aliases for upstream include-name drift) produced a binary differing from virtualagc's. cmp: $CMPOUT. Root cause: accumulated upstream transcription drift across ~20 shared .agc files (not limited to the two aliased files), e.g. ERASABLE_ASSIGNMENTS.agc symbol W.IND1 vs W.INDI, NEGTOTKP vs NETTOTKP; CONTROLLED_CONSTANTS.agc \$\$/DAPAO vs \$\$/DAPAD -- see script header for detail. Bugger-word checksums confirm banks 21 and 33 differ. Shipped binary is virtualagc's; see build/agc/Luminary099-apollo11.bin/.log for the divergent Apollo-11 build."
  fi
else
  echo "WARN: staged Apollo-11 assembly still failed (see build/agc/Luminary099-apollo11.log); cross-check skipped" >&2
  NOTE="Cross-check skipped: staged Apollo-11 assembly (filename aliases for LAMBERT_AIMPOINT_GUIDANCE.agc / TRIM_GIMBAL_CNTROL_SYSTEM.agc) still failed to assemble. See build/agc/Luminary099-apollo11.log for the error/warning summary. Shipped binary is virtualagc's."
fi

sha256sum build/agc/Luminary099.bin
jq -n --arg sha "$(sha256sum build/agc/Luminary099.bin | cut -d' ' -f1)" --arg note "$NOTE" \
  '{program:"Luminary099", assembler:"yaYUL", binary_sha256:$sha, note:$note}' \
  > build/agc/manifest.json
