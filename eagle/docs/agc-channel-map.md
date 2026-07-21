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

## Sources

- https://www.ibiblio.org/apollo/developer.html
- vendor/virtualagc/yaAGC/SocketAPI.c
