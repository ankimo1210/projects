"""Offline AGC-state forensics from a recorded packet trace.

Decodes the LM descent downlist (ch 034/035 pairs) out of
build/traces/pkt-descent-full.jsonl and compares the AGC's own state
against sim truth from the matching EAGLE_TELEM_OUT telemetry.

STATUS 2026-07-31: working notes, not a polished tool. The frame
alignment is fragile — the pair stream carries occasional drops, so
index-based slot extraction slips; the productive method has been
ANCHOR-BASED extraction (find a physically-signed value like LAND_X
= R_SITE at b=24, or truth-adjacent RGU triples, and read neighbors).
See docs/superpowers/notes/2026-07-31-m1b-rod-loop.md §9 for what this
instrument has measured so far and what remains open (the VN-jump
question). A robust Rust decoder with tests is the follow-up.

Slot map (counted from DOWNLINK_LISTS.agc, LMDSASDL; ID at 0, 100 pairs
per 2-s frame): TEVENT 13, TTF/8 20, DELTAH 21, RLS 22-24, TIME2 50,
RN+2 51, RN+4 52, VN 53-55, PIPTIME 56, RN+0 57, RGU 66-68, VGU 69-71,
LAND 72-74, TLAND 76, TIG 81.

Scalings (DP): RGU/LAND b=24 m; VGU b=10 m/cs; RN b=27 m; VN b=7 m/cs;
TIME2/PIPTIME b=28 cs. LAND magnitude = R_SITE exactly (validated);
LAND rotates with the moon in ref coords (~4.6 m/s in Y), so validate
on |LAND| and the pole component, never on X/Y constancy.
"""
import json
import math
import pickle
import sys
from itertools import pairwise

TRACE = sys.argv[1] if len(sys.argv) > 1 else 'build/traces/pkt-descent-full.jsonl'

def i15(w):
    """15-bit one's-complement to signed int."""
    return w if w < 0o40000 else -(w ^ 0o77777)

def dp(hi, lo):
    """AGC double-precision: hi*2^14 + lo (signs may disagree)."""
    return i15(hi) * 16384 + i15(lo)

def phys(hi, lo, b):
    """Physical value at b-scale: DP fraction * 2^b (DP = 28 bits)."""
    return dp(hi, lo) * (2.0 ** (b - 28))

# ---- 1. pair stream ------------------------------------------------------
pairs = []          # (t_ms, hi, lo)
pending = None      # (t_ms, hi)
for line in open(TRACE):
    v = json.loads(line)
    if v.get('dir') != 'out':
        continue
    ch = v.get('channel')
    if ch == '034':
        pending = (v['t_ms'], int(v['data'], 8))
    elif ch == '035' and pending is not None:
        pairs.append((pending[0], pending[1], int(v['data'], 8)))
        pending = None
print(f"pairs: {len(pairs)}")

# ---- 2. frame sync via TIME2 (increments ~200 cs per 2-s frame) ----------
best = None
for k in range(100):
    seq = pairs[k::100]
    if len(seq) < 50:
        continue
    good = 0
    for a, b_ in pairwise(seq[100:201]):
        d = dp(b_[1], b_[2]) - dp(a[1], a[2])
        if 190 <= d <= 210:
            good += 1
    if best is None or good > best[1]:
        best = (k, good)
t2_slot, score = best
print(f"TIME2 slot offset {t2_slot} (score {score}/99)")
id_off = (t2_slot - 50) % 100

def slot(idx):
    """All pairs at frame-index idx."""
    return pairs[(id_off + idx) % 100::100]

# ---- 3. sanity: LAND magnitude ------------------------------------------

lands = list(zip(slot(72), slot(73), slot(74), strict=False))
mid = lands[len(lands)//2]
for b_try in (24, 25, 26, 27):
    v = [phys(p[1], p[2], b_try) for p in mid]
    mag = math.sqrt(sum(x*x for x in v))
    print(f"  LAND b={b_try}: |v| = {mag:.0f} m")

# ---- 4. extract time series ---------------------------------------------
frames = min(len(slot(i)) for i in range(100))
print(f"frames: {frames}")

def series(idx0, n, b):
    cols = [slot(idx0 + j) for j in range(n)]
    out = []
    for f in range(frames):
        t_ms = cols[0][f][0]
        vals = [phys(cols[j][f][1], cols[j][f][2], b) for j in range(n)]
        out.append((t_ms, vals))
    return out

t2   = series(50, 1, 28)
rgu  = series(66, 3, 24)
vgu  = series(69, 3, 10)
land = series(72, 3, 24)

print("\nsample frames (RGU components, m; VGU m/s):")
print(f"{'t_s':>8} {'TIME2_s':>9} {'RGU_X':>12} {'RGU_Y':>12} {'RGU_Z':>12} {'VGU_X':>8} {'VGU_Z':>9}")
for f in range(0, frames, max(1, frames // 25)):
    t_s = t2[f][0] / 1000.0
    print(f"{t_s:8.1f} {t2[f][1][0]/100:9.1f} {rgu[f][1][0]:12.1f} {rgu[f][1][1]:12.1f} "
          f"{rgu[f][1][2]:12.1f} {vgu[f][1][0]*100:8.2f} {vgu[f][1][2]*100:9.2f}")

# persist for the analysis step

with open('/tmp/claude-1000/-home-kazumasa-projects/31fea53a-1dc3-4021-b79f-712a89c4f820/scratchpad/downlink9.pkl', 'wb') as fh:
    pickle.dump({'t2': t2, 'rgu': rgu, 'vgu': vgu, 'land': land}, fh)
print("saved downlink9.pkl")
