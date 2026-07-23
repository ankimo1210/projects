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

## Sources

- https://www.ibiblio.org/apollo/developer.html
- vendor/virtualagc/yaAGC/SocketAPI.c
- vendor/virtualagc/yaAGC/agc_engine.h (DSKY_* channel-0163 bit `#define`s)
- vendor/virtualagc/yaAGC/agc_engine.c (`UpdateDSKY`, channel-0163 synthesis; `CounterDINC` thrust pulses; `BurstOutput` coarse-align)
- vendor/virtualagc/yaDSKY2/yaDSKY2.h (`Ind_t` struct definition)
- vendor/virtualagc/yaDSKY2/yaDSKY2.cpp (`Inds[]` table, `ActOnIncomingIO` relay-row and channel-011 decode logic)
- vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc (engine, trim, jets, rod switch)
- vendor/virtualagc/Contributed/LM_Simulator/lm_simulator.tcl (RCS jet bit mapping)
