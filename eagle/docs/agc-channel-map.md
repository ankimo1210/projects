# yaAGC Channel Map and Packet Protocol

## Packet Layout

4-byte packets, signature bits `00/01/10/11` in the top 2 bits of each byte:

```
byte0: 00 u t pppp   u=bitmask flag, t=counter flag, pppp = channel bits 6..3
byte1: 01 ppp ddd    ppp = channel bits 2..0, ddd = data bits 14..12
byte2: 10 dddddd     data bits 11..6
byte3: 11 dddddd     data bits 5..0
```

7-bit channel (octal 0–177), 15-bit data. Ping packet = `FF FF FF FF`.

## DSKY Keycodes

Input ch 015:
- `1..9 = 0o1..0o11`
- `0 = 0o20`
- `VERB = 0o21`
- `RSET = 0o22`
- `KEY REL = 0o31`
- `+ = 0o32`
- `- = 0o33`
- `ENTR = 0o34`
- `CLR = 0o36`
- `NOUN = 0o37`

PRO/STBY is **not** a keycode: input ch 032 bit 14, inverted (0 = pressed).

### PRO/STBY Wire Protocol (ch 032, bit 14)

Confirmed against `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp`, function
`MainFrame::OutputPro` (yaDSKY2.cpp:2174-2199), called with `OffOn=0` from
`on_ProButton_pressed` (yaDSKY2.cpp:762, `// Press.` at :797-798) and with
`OffOn=1` from `on_ProButton_released` (yaDSKY2.cpp:985-991). Unlike the
other DSKY keys (a single keycode byte on ch 015), PRO is a discrete bit on
input channel 032 and yaAGC requires two packets to update it:

1. A **bitmask** packet on ch 032 claiming only bit 14 (`020000` octal =
   `1 << 13`, yaDSKY2.cpp:2186, `FormIoPacket(0432, 020000, Packet)` — the
   `0400` added to the channel number is this build's own on-the-wire
   bitmask-flag convention, decoded here instead via `Packet::bitmask`'s
   `u` bit per `docs/agc-channel-map.md`'s Packet Layout section).
2. A **value** packet on ch 032: data `0` while pressed, data `020000`
   (bit 14 set) once released (yaDSKY2.cpp:2181,2188-2190,
   `record (032, OffOn ? 020000 : 0)`). I.e. bit 14 is *inverted*: low = PRO
   held down, high = idle/released.

This matches `keys::pro_key_packets(pressed: bool) -> [Packet; 2]`, which
emits `[Packet::bitmask(0o32, 1 << 13), Packet::io(0o32, if pressed {0} else {1 << 13})]`.

**Result: no correction needed** — matches the plan's Reference block.

## Display Relay Word

Output ch 010: `AAAA B CCCCC DDDDD` (row, sign bit, left digit code, right digit code).

### Digit Codes

- blank=0
- `0`=0b10101
- `1`=0b00011
- `2`=0b11001
- `3`=0b11011
- `4`=0b01111
- `5`=0b11110
- `6`=0b11100
- `7`=0b10011
- `8`=0b11101
- `9`=0b11111

### Relay Word Row Assignments (ch 010, `AAAA` field)

Confirmed against `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp`, function
`ActOnIncomingIO`, `switch (Value & 0x7800)` (yaDSKY2.cpp:1959). `b` =
bit 10 (the relay word's sign/flag bit); `c`/`d` = digit codes at bits 5-9 /
0-4 respectively; `+` has priority over `-` when both rows are set.

| Row (AAAA) | Field | `b` meaning | `c` (left digit) | `d` (right digit) |
|---|---|---|---|---|
| 11 | PROG (M1/M2) | unused | M1 | M2 |
| 10 | VERB | unused | V1 | V2 |
| 9  | NOUN | unused | N1 | N2 |
| 8  | R1D1 | unused | *(unused)* | R1D1 |
| 7  | R1 sign(+)/D2/D3 | R1 `+` | R1D2 | R1D3 |
| 6  | R1 sign(−)/D4/D5 | R1 `−` | R1D4 | R1D5 |
| 5  | R2 sign(+)/D1/D2 | R2 `+` | R2D1 | R2D2 |
| 4  | R2 sign(−)/D3/D4 | R2 `−` | R2D3 | R2D4 |
| 3  | R2D5/R3D1 | unused | R2D5 | R3D1 |
| 2  | R3 sign(+)/D2/D3 | R3 `+` | R3D2 | R3D3 |
| 1  | R3 sign(−)/D4/D5 | R3 `−` | R3D4 | R3D5 |
| 12 | lamps (see below) | — | — | — |

Citations: yaDSKY2.cpp:1961 (`case 0x5800: // AAAA=11D`) through
yaDSKY2.cpp:2030 (`case 0x0800: // AAAA=1`); sign priority logic at
yaDSKY2.cpp:2047,2049 (`0 != (RSign & 2)` checked before `0 != (RSign & 1)`).
Row 8 has no left-digit widget in vendor source (`case 0x4000: // AAAA=8`,
yaDSKY2.cpp:1973-1975, sets only `Right = R1D1Digit`) — matched as-is (C
left undecoded for that row only). Row 3 is not like row 8: it drives both
digits, spanning two registers (`case 0x1800: // AAAA=3`, yaDSKY2.cpp:2016-
2019, sets `Left = R2D5Digit` and `Right = R3D1Digit`, with no sign), also
matched as-is (`self.r2.digits[4] = c; self.r3.digits[0] = d;`).

**Result: no correction needed** — matches the plan's Reference block
row-by-row.

### Row 12 Lamps (ch 010, row = 12)

Confirmed against `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp:181-207`, the
`Inds[14]` indicator table (`Ind_t { GraphicOn, GraphicOff, Channel, Bitmask,
Polarity, State, Widget, Latched, RowMask, Row }`, struct defined at
`yaDSKY2.h:71-83`). Entries with `Channel=010, Latched=1, RowMask=074000,
Row=060000` (`060000` octal = `12 << 11`, confirming row 12) give the
low-word bitmask for each lamp:

| Lamp | Vendor `Bitmask` (octal) | Bit (0-idx) | `DskyState.lamps` field |
|---|---|---|---|
| PRIO DISP | `01` | 0 | `prio_disp` |
| NO DAP | `02` | 1 | `no_dap` |
| VEL | `04` | 2 | `vel` |
| NO ATT | `010` | 3 | `no_att` |
| ALT | `020` | 4 | `alt` |
| GIMBAL LOCK | `040` | 5 | `gimbal_lock` |
| *(bit 6 unused — no vendor lamp defined)* | — | 6 | — |
| TRACKER | `0200` | 7 | `tracker` |
| PROG (alarm light) | `0400` | 8 | `prog_alarm` |

Citations: yaDSKY2.cpp:186 (NoAtt), 194 (PrioDisp), 196 (NoDap), 200
(GimbalLock), 203 (Prog), 207 (Tracker), 209 (Alt), 211 (Vel). Note "PROG"
here is the row-12 program-alarm *lamp*, distinct from the PROG *digits* on
relay row 11.

**Result: no correction needed** — matches the plan's Reference block.

### Channel 011 (lamp/discrete channel)

Confirmed against two independent vendor sites that agree:
- `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp:2085-2096`
  (`ActOnIncomingIO`, `else if (Channel == 011)`): `if ((Value & 2) != ...)`
  toggles COMP ACTY — i.e. bit 1 (0-idx, value 2).
- `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp:184` (Inds[] table): UPLINK ACTY
  = `Channel=011, Bitmask=04` (octal) = bit 2 (0-idx, value 4).
- `vendor/virtualagc/yaDSKY2/yaDSKY2.cpp:198`: TEMP = `Channel=011,
  Bitmask=010` (octal) = bit 3, matching `agc_engine.c:1707-1708`'s
  "Light TEMP if channel 11 bit 4 is set" (1-indexed bit 4 = 0-indexed bit 3).

| Bit (1-idx, as used by `apply`'s `b(n)` helper) | Bit (0-idx value) | Meaning |
|---|---|---|
| `b(2)` | 1 (value 2) | COMP ACTY |
| `b(3)` | 2 (value 4) | UPLINK ACTY |
| `b(4)` | 3 (value 8) | TEMP (also echoed to ch 0163, decoded there instead) |

**Result: no correction needed** — matches the plan's Reference block
(`comp_acty = b(2)`, `uplink_acty = b(3)`).

### Channel 013 (not decoded — only STBY-related bits, already folded into ch 0163)

Channel 013 is an AGC-internal discrete-input channel; `DskyState::apply`
(`runtime/crates/eagle-agc-protocol/src/dsky.rs`) only matches
`0o10`/`0o11`/`0o163`, so ch013 traffic falls through its `_ => {}` arm
un-decoded. Confirmed against `vendor/virtualagc/yaAGC/agc_engine.c`,
function `UpdateDSKY` and its callers: the only bits of ch013 consumed
anywhere in the engine are STBY-related, and both are already re-emitted
on ch0163's `DSKY_STBY`/`DSKY_RESTART` bits (decoded below), so no direct
ch013 decode is needed:

- Bit `01000` (octal): "the light test is active" — set during the V35E
  lamp test; immediately re-emitted as `DSKY_RESTART | DSKY_STBY` on
  ch0163 (agc_engine.c:1695-1697, `if (State->InputChannel[013] & 01000)
  ... State->DskyChannel163 |= DSKY_RESTART | DSKY_STBY`).
- Bit `02000` (octal), combined with `State->SbyPressed`: the PRO-held-down
  standby-enable timing check, 180° out of phase with the Night Watchman
  (agc_engine.c:2030-2032, `if (State->SbyPressed && ((State->InputChannel[013]
  & 002000) || State->Standby))`).

**Result:** no ch013 decode added — its only externally-relevant state
(STBY) is already covered via ch0163 below.

### Channel 0163 (yaAGC's synthesized DSKY flash/lamp channel)

Confirmed against `vendor/virtualagc/yaAGC/agc_engine.h:283-290` (`DSKY_*`
bitmask `#define`s, octal) and their use in
`vendor/virtualagc/yaAGC/agc_engine.c:1691-1747` (`UpdateDSKY`, which
synthesizes ch 0163 from internal state + ch 011 + ch 013 + ch 030 and emits
it via `ChannelOutput(State, 0163, ...)` at line 1747).

| Macro | agc_engine.h octal value | Decimal | Bit (0-idx) | `DskyState` field |
|---|---|---|---|---|
| `DSKY_AGC_WARN` | `000001` | 1 | 0 | *(not modeled — no field in scope)* |
| `DSKY_TEMP` | `000010` | 8 | 3 | `temp` |
| `DSKY_KEY_REL` | `000020` | 16 | 4 | `key_rel` |
| `DSKY_VN_FLASH` | `000040` | 32 | 5 | `verb_noun_flash` |
| `DSKY_OPER_ERR` | `000100` | 64 | 6 | `opr_err` |
| `DSKY_RESTART` | `000200` | 128 | 7 | `restart` |
| `DSKY_STBY` | `000400` | 256 | 8 | `standby` |
| `DSKY_EL_OFF` | `001000` | 512 | 9 | *(not modeled — no field in scope)* |

Citations: agc_engine.h:283-290 for the bit definitions; agc_engine.c:1693
(`DskyChannel163 &= ~(DSKY_KEY_REL | DSKY_VN_FLASH | DSKY_OPER_ERR |
DSKY_RESTART | DSKY_STBY | DSKY_AGC_WARN | DSKY_TEMP)`) confirms these are
the only bits yaAGC round-trips through this channel per update cycle.

**Result: no correction needed** — the plan's test comment ("bit 6 =
VERB/NOUN flash, bit 8 = RESTART", 1-indexed) and the implementation's
`b(6)`/`b(8)` helper both land on `DSKY_VN_FLASH` (32 = bit 5, 0-idx) and
`DSKY_RESTART` (128 = bit 7, 0-idx) exactly.

## Idle-Traffic Behavior (Test-Harness Note)

yaAGC's simulated environment does **not** go quiet at idle. Confirmed via a
throwaway diagnostic test against the live AGC (no keys sent, 8 s observed):

- Ch `034` (CDUZ) and ch `035` (OPTY) emit continuously, roughly every
  16 ms each, indefinitely — not just during boot.
- Ch `010` itself carries a periodic no-op packet (`AAAA`=0, i.e. row 0,
  which matches no row in the Relay Word table above and is a no-op for
  `DskyState`) roughly every 112-123 ms, indefinitely.

Consequence: a "drain until N ms of total silence across every channel"
loop never terminates, since something arrives on some channel every
~8-17 ms forever. `tests/golden_v35e.rs`'s `settle_dsky` helper instead
scopes its quiet check to the DSKY-relevant channels (`010`/`011`/`0163`)
— the only ones the golden comparison reads — while still draining and
discarding everything else. Their idle period (~120 ms) is comfortably
above the 100 ms quiet threshold used, so this terminates reliably
(observed ~120-200 ms per call across repeated runs, capped with a 5 s
safety assertion as defense in depth).

### Golden Milestone Flakiness: Pre-ENTR Keystroke Echo

A second, related source of flakiness surfaced once boot-flush hangs were
fixed: `milestones()` occasionally captured an extra leading entry, e.g.
ch `010` data `51540` decoding to VERB row `"3 "` — the transient echo of
typing `3` (verb digit 1 of "35") before `5` completes it. This packet is
generated *before* ENTR is sent (during the `VERB`/`3`/`5` keystrokes), so
it is typing noise unrelated to the V35E lamp-test signal proper (which
starts once ENTR is processed). It was captured intermittently because
packets generated while the key-send loop sleeps between keystrokes
accumulate, undrained, in the events channel — whether one is still
sitting there when the capture loop starts reading is a race against the
AGC's own redraw-cycle timing.

Fix: `run_v35e()` now calls `settle_dsky` after each of the `VERB`/`3`/`5`
keystrokes (draining their echoes) but deliberately *not* after `ENTR` —
settling right after ENTR would race the AGC's immediate response to it,
per the boot-flush note above. This is the permitted "loosen milestones"
step from the golden-test plan; the final-state check (all-8s) was not
loosened.

### Golden Final-State Semantics

A third flake source, found once milestones and boot-flush were stable:
the final-state comparison itself raced yaAGC's ch0163 flash modulation.
`verb_noun_flash`, `key_rel`, and `opr_err` are driven together by the
lamp-test blink (vendor `agc_engine.c:1727-1744`, `DSKY_FLASH_PERIOD`: a
1.28 s cycle, 75% duty), oscillating phase-coherently between
`(false, true, true)` (75% of the cycle) and `(true, false, false)`
(25%). Whichever phase the 3 s capture happened to end in decided the
value of all 3 bits, producing a ~1/10 flake in the final-state
`assert_eq!`.

Fix (user-approved "option (b) strengthened", decided 2026-07-22): those 3
bits are excluded from the final-state equality check, but the exclusion
is paired with *stronger* assertions that pin the AGC's real blink
behavior instead of ignoring it — `tests/golden_v35e.rs` now asserts (in
both record and verify modes) that every observed
`(verb_noun_flash, key_rel, opr_err)` triple after the first ch0163
packet is one of the two phase-coherent states above (phase coherence),
and that both states are observed at least once within the 3 s capture
(deterministic, since 3 s covers ≥2 full 1.28 s cycles). Every other
field — digits, signs, all other lamps (including `temp`, `restart`,
`standby`), `comp_acty` — remains in strict equality. `comp_acty` (ch011)
is also environment-modulated in principle but has been stable (`false`)
across ~15 recorded runs; it is the first suspect if this golden ever
flakes again.

## Counters and Autopilot Outputs (Phase 2)

### Counter Registers and Increment Types

Confirmed against `vendor/virtualagc/yaAGC/agc_engine.c:1570-1623`
(`UnprogrammedIncrement` function) and `vendor/virtualagc/yaAGC/SocketAPI.c:219-231`,
`vendor/virtualagc/yaAGC/agc_utilities.c:144-147` (counter channel = 0x80 | address,
data field = IncType). Counter packets encode
the AGC's erasable-memory increments with address in the channel field (bits
0-6) and increment type in the data field.

| IncType | Name | Semantics | Channels |
|---------|------|-----------|----------|
| 0 | `INC_PINC` | Positive increment (PIPA) | 0o37, 0o40, 0o41 (X, Y, Z) |
| 1 | `INC_PCDU` | Positive CDU command | 0o32, 0o33, 0o34 (X, Y, Z) |
| 2 | `INC_MINC` | Negative increment (PIPA) | 0o37, 0o40, 0o41 (X, Y, Z) |
| 3 | `INC_MCDU` | Negative CDU command | 0o32, 0o33, 0o34 (X, Y, Z) |
| 4 | `INC_DINC` | Thrust drive increment (DINC) | 0o55 |
| 0o21 | `INC_PCDU_FAST` | Fast positive CDU | 0o32, 0o33, 0o34 (X, Y, Z) |
| 0o23 | `INC_MCDU_FAST` | Fast negative CDU | 0o32, 0o33, 0o34 (X, Y, Z) |

PIPA registers (0o37=PIPAX, 0o40=PIPAY, 0o41=PIPAZ) accumulate accelerometer
pulses; CDU registers (0o32=CDUX, 0o33=CDUY, 0o34=CDUZ) track gyro-derived
gimbal angles; thrust register (0o55=THRUST) drives descent-engine throttle.

#### PIPA Pulse Scale: 1 cm/s (the rope decides, not the vehicle model)

**One PIPA pulse = 0.01 m/s in Luminary099.** This is not a modelling
choice: it is the constant the rope multiplies the counters by, so a
sim that emits pulses in any other unit hands the AGC a silently wrong ΔV.

- `vendor/virtualagc/Luminary099/SERVICER.agc:570-580` (PIPASR, REPIP1 /
  REPIP3): the raw PIPAX/PIPAY/PIPAZ counter readings go straight into the
  **high** words of `DELVX/DELVY/DELVZ`, so `DELV` as a DP fraction is
  `count · 2⁻¹⁴`. `IMU_COMPENSATION_PACKAGE.agc:58,65` states the same
  scaling in words ("(PP) X 2(+14)", "FRACTIONAL PIPA PULSES SCALED
  2(+14)").
- `vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:178-180`:
  `KPIP = .0512` ("SCALES DELV TO UNITS OF 2(5) M/CS"),
  `KPIP1 = .0128` (2(7) M/CS), `KPIP2 = .0064` (2(8) M/CS). All three
  reduce to the same physical value:
  `count · 2⁻¹⁴ · 0.0128 · 2⁷ = count · 1.0e-4 m/cs = count · 0.01 m/s`.

`vendor/virtualagc/Contributed/LM_Simulator/lm_simulator.tcl:145` sets
`PIPA_INCR 0.0585` (metres — `modules/AGC_IMU.tcl:293-297` displays the
integrated velocity both raw and × `MeterToFeet`), and that was this
repo's original provenance for `eagle_dynamics::constants::PIPA_INCR`. It
is **5.85× too coarse for this rope**: LM_Simulator drives a DSKY, never a
closed navigation loop, so nothing there ever noticed. Measured live in M1
flight 1 (2026-07-26): over a 198 s powered descent the AGC's own V06N63
R2 rate matched a model in which it integrated k = 0.159 of the ΔV we
delivered (rms 0.46 m/s; k = 1 gives rms 92.9 m/s), against the predicted
0.01/0.0585 = 0.171. See
`docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.

### Thrust Pulse Emissions

Confirmed against `vendor/virtualagc/yaAGC/agc_engine.c:1278-1305`
(`CounterDINC` function). When the thrust counter's sign changes, the AGC
emits a pulse on counter address 0o55 with data = IncType:

| IncType (data) | Emission | Semantics |
|--|--|--|
| 0o15 | POUT (Positive Out) | Positive value → decrement by 1 |
| 0o16 | MOUT (Minus Out) | Negative value → increment by 1 |
| 0o17 | ZOUT (Zero Out) | Counter crossed zero |

These are received as counter packets on ch 0o55 and decoded as `ThrustPulse`
enum variants to synchronize throttle setpoint with the autopilot.

**Verified live (Spike B).** The strobe protocol closes a real vertical
channel: after P66 entry the accumulated command ran 0 → 1808 → 3430 within
three seconds and held around 2400, i.e. 29-41 kN against a 15 t vehicle
whose weight is 24.6 kN, and the vertical truth stopped falling. Two
properties of the real actuator had to be modelled to get there:

- **The command is a bounded position, not a signed accumulator.** P63
  deliberately drives MOUT 4096 while the engine is off to seek the zero
  stop, then FLATOUT drives POUT 4096 (`P40-P47.agc:490-494`). Pulses past
  either end leave the position at that stop; an unbounded accumulator
  reads −4096 and never recovers.
- **Outstanding DINC strobes must be credit-limited.** Requesting a fresh
  burst every tick before the previous burst's POUT/MOUT/ZOUT have arrived
  queues thousands of strobes and drowns the loop in ZOUT chatter. Cap the
  in-flight count at `DINC_MAX_PER_TICK`.

The engine's idle stop is ~10 % thrust, not zero: Luminary leaves the
throttle parked there for the whole ZOOMTIME trim phase (~26 s) after
ignition, so a model that maps command 0 to zero thrust free-falls through
the burn-in.

### P66 Vertical Displays and Erasables (Spike B)

P66's display is `VERTDISP` → **V06N60** (`LUNAR_LANDING_GUIDANCE_EQUATIONS
.agc:898`); the braking/approach phases show N63. N60's registers are
VHORIZ, HDOTDISP, HCALC (`PINBALL_NOUN_TABLES.agc:724-726`), N63's R2 is
also HDOTDISP.

| Symbol | ECADR | Form | Role |
|--|--|--|--|
| HDOTDISP | 0o3473 | DP b=7 m/cs | altitude rate; seeds VDGVERT at STARTP66 |
| VDGVERT | 0o3644 | DP b=7 m/cs | desired altitude rate; only RODCOMP writes it in P66 |
| RODSCAL1 | 0o3756 | SP | working copy of the RODSCALE pad word |
| RODCOUNT | 0o3746 | SP | ROD click accumulator |

**Scale, measured live:** HDOTDISP read back as hi = 0o36 (491520 DP
pulses) while N63 R2 displayed `+00756` = 75.6 ft/s. 491520 × 2⁻²¹ m/cs =
0.2344 m/cs = 76.9 ft/s, a 1.7 % match — so the DP LSB is 2⁻²¹ m/cs
(4.77e-5 m/s) and these words are b=7 in m/cs. Since RODCOMP adds
`RODCOUNT × RODSCAL1` straight into VDGVERT's pulses, one ft/s per click is
0.003048 m/cs = **6392 pulses**, positive (a down-click loads RODCOUNT −1).

**The flight display owns the DSKY.** VERTDISP repaints every guidance
pass, so an in-flight V01N01/V21N01 entry has to be preceded by KEY REL and
retried (RSET + KEY REL) when it is swallowed — and a read must confirm the
frame really is V01N01 showing the requested address before trusting R1.
P66's N63 R1 (`+56077`) is five octal-legal digits and was silently
returned as erasable data before that check existed.

### Landing-Radar Bypass (FLGWRD11 / LRBYPASS, Wave 2 M1)

We model no landing radar, so R12 must never try to incorporate one. The
switch is a single erasable flag bit, and **fresh start already sets it** —
`run_scenario` therefore READS IT BACK and aborts if it is clear, rather
than writing it (`runner::run_scenario`, gated on `[agc] lrbypass`).

| Symbol | ECADR | Bit | Meaning when SET |
|--|--|--|--|
| FLGWRD11 | 0o107 | — | flag word 11 (`STATE +11D`, `STATE` = 0o74) |
| LRBYPASS | 0o107 | BIT15 = 0o40000 | bypass ALL landing-radar updates |

Citations, all verified against the shipped tree (`vendor/virtualagc/`, the
assembly the binary is built from):

- `vendor/virtualagc/Luminary099/FLAGWORD_ASSIGNMENTS.agc:1035` —
  `FLGWRD11 = STATE +11D`; `:1040-1041` — `LRBYPASS = 165D` /
  `LRBYBIT = BIT15`, commented *"BYPASS ALL LANDING RADAR UPDATES"* vs
  *"DO NOT BYPASS LR UPDATES"*.
- `build/agc/Luminary099.log:3262` — `26,2022  0107  FLGWRD11 = STATE +11D`,
  which is where the octal ECADR 0o107 comes from.
- `vendor/virtualagc/Luminary099/FRESH_START_AND_RESTART.agc:623` —
  `OCT 40000  # BIT 15 = LRBYPASS.`, the 12th word (index 11) of the
  `SWINIT` fresh-start flag-word table that begins at `:611`. Note the blank
  line at `:619`: the 12 words occupy `:611-618` and `:620-623`, so the
  index-11 word is at `:623` and not at `:622`.

**Confirmed live**, 2026-07-26 M1 flight 1: the read-back of 0o107 after
`dap_init` on a fresh `--no-resume` boot returned BIT15 set, and every M1
descent since has flown with the radar bypassed in-rope — the descent is
purely inertial. See `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.

### Coarse-Align CDU Outputs

Confirmed against `vendor/virtualagc/yaAGC/agc_engine.c:1630-1681` (`BurstOutput`
function), the direction-flag encoding at lines 1652–1663, and the channel
assignments at `agc_engine.c:2405-2422` (BurstOutput call sites). Coarse-alignment
(gimbal alignment) outputs are emitted as IO packets on channels 0o174 (X),
0o175 (Y), 0o176 (Z) with data = direction flag | pulse count:

| Channel | Axis | Register | Bits for Pulse Count |
|---------|------|----------|---------------------|
| 0o174 | X (CDUXCMD) | RegCDUXCMD | bits 0-13 (14 bits, 0o37777 mask) |
| 0o175 | Y (CDUYCMD) | RegCDUYCMD | bits 0-13 (14 bits, 0o37777 mask) |
| 0o176 | Z (CDUZCMD) | RegCDUZCMD | bits 0-13 (14 bits, 0o37777 mask) |

The direction flag (bit 0o40000, i.e. bit 15) is set (=1) for *negative*
direction (slew negative) and clear (=0) for *positive* direction per
agc_engine.c:1652-1663: `Direction = (040000 & DriveCount)` at line 1652,
then when `DriveCountSaved < 0` (negative demand), `Direction = 040000` at
line 1663, else `Direction = 0`. The pulse count remains in the lower 12 bits.

### Autopilot Discrete Outputs

Confirmed against `vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:59-94`
and `vendor/virtualagc/Contributed/LM_Simulator/lm_simulator.tcl:814-818`.

#### RCS Jets (Channels 5 and 6)

| Channel | Subsystem | Bits | Jet Assignments |
|---------|-----------|------|-----------------|
| 0o5 | Pitch RCS jets | 1-8 | Q4U, Q4D, Q3U, Q3D, Q2U, Q2D, Q1U, Q1D |
| 0o6 | Roll RCS jets | 1-8 | Q3A, Q4F, Q1F, Q2A, Q2L, Q3R, Q4R, Q1L |

Each bit (1-8) drives one jet on-off; bit masks are extracted directly from
the lower 8 bits of the IO packet data.

#### Descent Engine (Channel 11, 0o11)

- Bit 13 (1-indexed, = 1 << 12): Engine ON command
- Bit 14 (1-indexed, = 1 << 13): Engine OFF command

Both bits can be set simultaneously; the AGC uses them for cross-coupled
command logic.

#### Gimbal Trim (Channel 12, 0o12)

- Bit 9 (1-indexed, = 1 << 8): −Pitch gimbal trim (bell motion)
- Bit 10 (1-indexed, = 1 << 9): +Pitch gimbal trim (bell motion)
- Bit 11 (1-indexed, = 1 << 10): −Roll gimbal trim (bell motion)
- Bit 12 (1-indexed, = 1 << 11): +Roll gimbal trim (bell motion)

Each bit drives a trim solenoid; multiple bits can be active simultaneously.

#### Thrust Drive Enable (Channel 14, 0o14)

Confirmed against `vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:115-120`.

- Bit 4 (1-indexed, = 1 << 3): Thrust drive enable (1 = drive active)

#### Rod Switch Click (Channel 16, 0o16)

Confirmed against `vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:137-143`.

- Bit 6 (1-indexed, = 1 << 5): +1 click (slow descent)
- Bit 7 (1-indexed, = 1 << 6): −1 click

Emitted as discrete (IO) packets. Caller must send a press packet followed
by a release packet (data = 0) at least one tick later to allow the AGC's
MARKRUPT interrupt to latch the descent-rate change.

**yaAGC never raises that interrupt — use RODCOUNT instead (Spike B).**
`SocketAPI.c:239-249` sets `InterruptRequests[5]` (KEYRUPT1) for a
channel-015 write, but `InterruptRequests[6]` is not assigned anywhere in
the emulator. A socket write to channel 016 therefore updates NAVKEYIN and
stops there: KEYRUPT2 → MARKRUPT (`INTERRUPT_LEAD_INS.agc:65,68`) never
runs, so `DESCBITS` never runs and RODCOUNT never moves. GUILDENSTERN
enters P66 only on "ATT HOLD *and* RODCOUNT ≠ 0"
(`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217`), which the switch discrete
alone can never satisfy in this emulator.

We click the switch by loading RODCOUNT directly instead — V21N01 at ECADR
`0o3746` (`E7,1746`, `Luminary099.log:6033`), see `runner::rod_load`. This
is equivalent rather than an approximation: `DESCBITS`' entire body is
`ADS RODCOUNT` with ±1 (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1233-1238`),
and `RODCOMP` consumes the accumulator with `CAF ZERO / XCH RODCOUNT` once
per P66 pass (`:958-963`). Verified live: MM66 reached against an unpatched
yaAGC. No vendor source is patched.

The load is deliberately *not* read-back verified — RODCOMP zeroes the word
within one P66 pass, so a V01N01 verify would race the rope.

#### Gyro Torque Output (Channel 0o177)

Confirmed against `vendor/virtualagc/yaAGC/agc_engine.c:2354-2390` (`Gyro`
section of `ExecuteCycle`). The raw gyro torque count is emitted directly
as an IO packet on ch 0o177, data bits 0-11 carrying the pulse count and
bits 12-14 (shifted 6 places from input channel 014 bits 6-8) carrying
the axis-select bits. In Wave 1, this is decoded as a raw `u16` value
(see `AgcOutput::Gyro { raw: u16 }`); full interpretation of the axis and
rate-gyro feedback loop is deferred to Phase 3.

#### Downlink (Channels 34 and 35, 0o34 and 0o35)

These channels are synthesized uplink/downlink registers. They are identified
by the decoder as the `AgcOutput::Downlink` variant (no data extraction needed
for Phase 2).

## Symbol Table / ECADR Notation (Pad-Load, Task 5)

### Where the listing lives

`scripts/assemble-luminary.sh` already redirects yaYUL's stdout (which is
the full assembly listing, symbol table included — "The assembly listing,
including symbol table and any error messages appear on the standard
output", `yaYUL --help`) to `build/agc/Luminary099.log` /
`build/agc/Luminary099-apollo11.log`. No script change was needed to
preserve the listing; it was already captured, just not under a `.lst`
name. `build/agc/*.symtab` is a *different*, binary (non-text) yaYUL
artifact — not human-readable, not the listing.

### Line format

Every listing line (data, comment, or blank) is prefixed
`%06d,%06d: ` — **these two numbers are a running line counter and a
per-file line counter, not addresses** (confirmed at
`vendor/virtualagc/yaYUL/Pass.c:1744` and `:2577`:
`printf("%06d,%06d: %s", CurrentLineAll, CurrentLineInFile, s);`). Do not
parse them as ECADRs.

A symbol-table *definition* line (from an `ERASE` or `EQUALS` pseudo-op)
carries the address immediately before the symbol name, one column for
`ERASE`, two for `EQUALS` (the first of the two is just the current,
unrelated erasable location counter — see `RODSCALE`/`TAUROD` below,
which share an identical first column because no `ERASE` has advanced the
counter since):

```
004605,001043: E4,1422                        RLS                ERASE    +5                            	# I(6) LANDING SITE VECTOR -MOON REF
004969,001407: E5,1642  E5,1537               RODSCALE           EQUALS   LRWVFF     +1                 	# I(1) CLICK SCALE FACTOR FOR ROD
    0366                        RESTREG            ERASE                                  	# B(1)PRM FOR DISPLAY RESTARTS
```

yaYUL's own address-formatting code (`vendor/virtualagc/yaYUL/Pass.c:1362-1382`)
prints exactly three address shapes:

- Switched erasable (banks E0–E7): `printf("E%1o,%04o  ", Address->EB, Address->SReg)` → `E<bank>,<offset>`, offset always in `1400`–`1777` (octal), the shared bank-switched CPU address window (`Pass.c:1372`).
- Unswitched erasable (banks E0–E2, address 0000–1377 octal, always directly addressable): `printf("   %04o  ", Address->SReg)` → plain 4-digit octal, no `E` prefix, no comma (`Pass.c:1364`).
- Fixed-bank references print `%02o,%04o` (bank,offset) and numeric constants print `%07o` — neither is a pad-loadable erasable address and both are ignored by the symtab parser.

### ECADR conversion rule

```
switched (E0-E7, offset 1400-1777 octal): ecadr = bank*0o400 + (offset - 0o1400)
unswitched (plain octal 0000-1377):        ecadr = offset            (as-is)
```

**Hand-verified against `vendor/virtualagc/Luminary099/ERASABLE_ASSIGNMENTS.agc`**
(the shipped/virtualagc source — `build/agc/manifest.json`'s recorded
binary is built from this tree): `EBANK-4 ASSIGNMENTS` opens with
`SETLOC 2000` (`ERASABLE_ASSIGNMENTS.agc:1008`) — i.e. yaYUL's *own*
internal erasable location counter for bank E4 starts at octal `2000`,
which is exactly `4 * 0o400`, confirming the bank-base term of the
formula independently of the listing's `E4,nnnn` notation. Counting
`ERASE` words forward from `WRENDPOS` (`:1016`, at `2000`) through
`WRENDVEL, WSHAFT, WTRUN, RMAX, VMAX` (`:1017-1021`, 1 word each →
`2001`–`2005`), `WSURFPOS, WSURFVEL` (`:1025-1026` → `2006`-`2007`),
`SHAFTVAR, TRUNVAR` (`:1030-1031` → `2010`-`2011`), `504LM ERASE +5`
(`:1035`, 6 words → `2012`-`2017`), `AGSK ERASE +1` (`:1039`, 2 words →
`2020`-`2021`) lands exactly on `RLS ERASE +5` (`:1043`) at **`2022`**
octal — matching the formula applied to the listing's own
`RLS ... E4,1422` entry (`build/agc/Luminary099.log:4504`):
`ecadr = 4*0o400 + (0o1422 - 0o1400) = 0o2000 + 0o22 = 0o2022`. Two
independent derivations agree; this is the value asserted by hand in
`padload.rs`'s `symtab_parses_fixture` test.

### Sources (this section)

- `vendor/virtualagc/yaYUL/Pass.c:1362-1382` (address-format `printf`s: unbanked, banked-erasable, banked-fixed)
- `vendor/virtualagc/yaYUL/Pass.c:1744`, `:2577` (`%06d,%06d:` line-counter prefix, not an address)
- `vendor/virtualagc/Luminary099/ERASABLE_ASSIGNMENTS.agc:1006-1043` (`EBANK-4 ASSIGNMENTS`, `SETLOC 2000`, manual word count to `RLS`)
- `build/agc/Luminary099.log` (yaYUL listing stdout, preserved by the existing `scripts/assemble-luminary.sh` redirect — regenerate via `make agc`)

## Sources

- https://www.ibiblio.org/apollo/developer.html
- vendor/virtualagc/yaAGC/SocketAPI.c
- vendor/virtualagc/yaAGC/agc_engine.h (DSKY_* channel-0163 bit `#define`s)
- vendor/virtualagc/yaAGC/agc_engine.c (`UpdateDSKY`, channel-0163 synthesis; `CounterDINC` thrust pulses; `BurstOutput` coarse-align)
- vendor/virtualagc/yaDSKY2/yaDSKY2.h (`Ind_t` struct definition)
- vendor/virtualagc/yaDSKY2/yaDSKY2.cpp (`Inds[]` table, `ActOnIncomingIO` relay-row and channel-011 decode logic)
- vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc (engine, trim, jets, rod switch)
- vendor/virtualagc/Contributed/LM_Simulator/lm_simulator.tcl (RCS jet bit mapping)
