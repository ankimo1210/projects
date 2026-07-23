#!/usr/bin/env bash
# Build only the CLI tools we need: yaYUL (assembler) and yaAGC (emulator).
# Per VirtualAGC README: no configure, no make install, no parallel make.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/agc

# The socket API updates NAVKEYIN for channel 016 but, unlike channel 015,
# does not request the matching KEYRUPT2 interrupt. Apply the tracked patch
# that lets Luminary's MARKRUPT/DESCBITS observe LM rate-of-descent clicks.
# Accept an already-patched checkout so repeated builds stay idempotent.
AGC_PATCH_PATH="$(pwd)/scripts/patches/virtualagc-ch016-keyrupt2.patch"
if git -C vendor/virtualagc apply --check "$AGC_PATCH_PATH" >/dev/null 2>&1; then
  git -C vendor/virtualagc apply "$AGC_PATCH_PATH"
elif git -C vendor/virtualagc apply --reverse --check "$AGC_PATCH_PATH" >/dev/null 2>&1; then
  echo "virtualagc ch016 KEYRUPT2 patch already applied"
else
  echo "ERROR: virtualagc ch016 KEYRUPT2 patch does not match pinned source" >&2
  exit 1
fi

# --- Deviations from the brief's literal script (documented per the brief's
#     own escape hatch: "keep the fix in the script") ---
#
# 1. (Brief's 3rd documented fallback, needed) `make -C
#    vendor/virtualagc/yaYUL` / `.../yaAGC` fails outright: those
#    subdirectory Makefiles reference ${cc}, ${CFLAGS}, ${NVER} etc. that are
#    only defined in the top-level vendor/virtualagc/Makefile and exported
#    down through its `$(BUILD)` helper. Building the two phony top-level
#    targets instead (as the brief's fallback #3 prescribes) picks up those
#    definitions and only builds yaYUL/yaAGC, not the GUI SUBDIRS.
# 2. (Not in the brief, minimal addition) yaAGC/Makefile unconditionally
#    links -lcurses on non-Win32 builds via a misnamed ${CURSES} var, even
#    though NOREADLINE=yes -- this Makefile's own default -- means no
#    curses/readline symbol is ever referenced by the compiled sources
#    (verified: no curses.h include or curses/readline call anywhere under
#    yaAGC/*.c when NOREADLINE is set). This host has no libncurses-dev
#    installed (`sudo apt-get install` in Step 1 can't run: no passwordless
#    sudo), only the runtime libncursesw6 .so, so the final link failed with
#    "/usr/bin/ld: cannot find -lcurses". Fix: override CURSES= on the make
#    command line so the unused -lcurses is dropped from the link. This
#    touches no vendor file and needs no system package install.
# The brief's other two documented fallbacks were NOT needed: the top-level
# Makefile already defines NVER (so no explicit NVER=... pass-through is
# required), and the default CFLAGS here has no -Werror, so no old-C
# warnings-as-errors surfaced (CFLAGS='-O2 -Wno-error -fcommon' was not
# applied).
make -C vendor/virtualagc CURSES= yaYUL yaAGC

cp vendor/virtualagc/yaYUL/yaYUL build/agc/yaYUL
cp vendor/virtualagc/yaAGC/yaAGC build/agc/yaAGC
echo "OK: $(build/agc/yaYUL --help 2>&1 | head -1 || true)"
