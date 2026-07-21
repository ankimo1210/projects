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

## Sources

- https://www.ibiblio.org/apollo/developer.html
- vendor/virtualagc/yaAGC/SocketAPI.c
- vendor/virtualagc/yaAGC/agc_engine.h (DSKY_* channel-0163 bit `#define`s)
- vendor/virtualagc/yaAGC/agc_engine.c (`UpdateDSKY`, channel-0163 synthesis)
- vendor/virtualagc/yaDSKY2/yaDSKY2.h (`Ind_t` struct definition)
- vendor/virtualagc/yaDSKY2/yaDSKY2.cpp (`Inds[]` table, `ActOnIncomingIO`
  relay-row and channel-011 decode logic)
