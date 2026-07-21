# EAGLE Phase 0–1: yaAGC Spike + Rust Bridge + Web DSKY — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The original Luminary099 runs in yaAGC, and a browser DSKY can key V35E (lamp test) and V16N36E (mission clock) through a Rust bridge, with golden-trace regression tests.

**Architecture:** Three processes: yaAGC child process (C, vendored VirtualAGC) speaking its 4-byte TCP packet protocol; `eagle-runtime` (Rust/tokio) that spawns it, decodes DSKY channels into state, and serves WebSocket JSON; and a Vite+React 2D DSKY in the browser. All AGC I/O is trace-logged as JSONL; golden tests compare event order, not timestamps.

**Tech Stack:** Rust (tokio, axum, serde, thiserror, clap), Vite + React + TypeScript (vitest), vendored VirtualAGC (yaYUL assembler + yaAGC emulator), GNU Make.

**Spec:** `/home/kazumasa/projects/eagle/docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md`

## Global Constraints

- Repo root for git commands: `/home/kazumasa/projects` (monorepo). All project files under `eagle/`. Work on branch `eagle/phase01`.
- `vendor/` is fetched by script, **git-ignored**, and never edited; pins live in `eagle/vendor/manifest.json` (committed).
- Build only CLI targets from VirtualAGC (`yaYUL`, `yaAGC`). Never build wxWidgets GUIs. VirtualAGC README: do **not** run `configure`, do **not** `make install`, do **not** parallelize make.
- AGC channels are written in octal everywhere (docs, Rust literals `0o...`, JSONL traces).
- Every channel/keycode/lamp semantic learned goes into `eagle/docs/agc-channel-map.md` with a source citation, in the same task that uses it.
- yaAGC port: default `19797`; integration tests use `19897` to avoid clashes. WebSocket port default `8642`.
- Golden comparisons are event-order based; COMP ACTY (ch 011 bit 2) is excluded (timing-flaky). Golden capture flushes boot-time traffic before keying, and verifies the final DSKY state (displays + lamps) in addition to the milestone sequence.
- Rust integration tests that need a live yaAGC are `#[ignore]` and run via `make test-integration` **serially** (`--test-threads=1` — never run two yaAGC processes concurrently; timing contention destabilizes golden captures); plain `make test` must pass with no vendor build present. **Phase 1 DoD = `make test` AND `make test-integration` both pass.**
- Commit messages in English, conventional style (`feat:`, `test:`, `docs:`, `build:`).

## Reference: yaAGC packet protocol (source: ibiblio.org/apollo/developer.html)

4-byte packets, signature bits `00/01/10/11` in the top 2 bits of each byte:

```
byte0: 00 u t pppp   u=bitmask flag, t=counter flag, pppp = channel bits 6..3
byte1: 01 ppp ddd    ppp = channel bits 2..0, ddd = data bits 14..12
byte2: 10 dddddd     data bits 11..6
byte3: 11 dddddd     data bits 5..0
```

7-bit channel (octal 0–177), 15-bit data. Ping packet = `FF FF FF FF`.
DSKY keycodes (input ch 015): `1..9 = 0o1..0o11`, `0 = 0o20`, `VERB = 0o21`,
`RSET = 0o22`, `KEY REL = 0o31`, `+ = 0o32`, `- = 0o33`, `ENTR = 0o34`,
`CLR = 0o36`, `NOUN = 0o37`. PRO/STBY is **not** a keycode: input ch 032
bit 14, inverted (0 = pressed).
Display relay word (output ch 010): `AAAA B CCCCC DDDDD` (row, sign bit,
left digit code, right digit code). Digit codes: blank=0, `0`=0b10101,
`1`=0b00011, `2`=0b11001, `3`=0b11011, `4`=0b01111, `5`=0b11110, `6`=0b11100,
`7`=0b10011, `8`=0b11101, `9`=0b11111.

---

### Task 1: Repo skeleton + vendor pinning

**Files:**
- Create: `eagle/.gitignore`, `eagle/Makefile`, `eagle/README.md`, `eagle/scripts/fetch-vendor.sh`
- Generated (not committed): `eagle/vendor/virtualagc/`, `eagle/vendor/Apollo-11/`
- Committed after first run: `eagle/vendor/manifest.json`

**Interfaces:**
- Produces: `make vendor` (idempotent fetch+verify), `eagle/vendor/manifest.json` with `{repo, url, sha}` entries. Later tasks rely on paths `eagle/vendor/virtualagc/yaYUL`, `eagle/vendor/virtualagc/yaAGC`, `eagle/vendor/Apollo-11/Luminary099/MAIN.agc`.

- [ ] **Step 1: Create branch**

```bash
cd /home/kazumasa/projects && git checkout -b eagle/phase01
```

- [ ] **Step 2: Write `.gitignore`, `Makefile`, `README.md`**

`eagle/.gitignore`:
```gitignore
vendor/virtualagc/
vendor/Apollo-11/
build/
traces/
client/node_modules/
client/dist/
runtime/target/
```

`eagle/Makefile`:
```make
.PHONY: vendor agc-tools agc test test-integration dev

vendor:
	bash scripts/fetch-vendor.sh

agc-tools: vendor
	bash scripts/build-agc-tools.sh

agc: agc-tools
	bash scripts/assemble-luminary.sh

test:
	cd runtime && cargo test

test-integration: agc
	cd runtime && cargo test -- --ignored --test-threads=1

dev:
	@echo "run 'make dev-runtime' and 'make dev-client' in two terminals"

dev-runtime: agc
	cd runtime && cargo run -p eagle-runtime -- \
	  --yaagc ../build/agc/yaAGC --core ../build/agc/Luminary099.bin

dev-client:
	cd client && npm run dev
```

`eagle/README.md`: title, one-paragraph description (original Luminary099 in
yaAGC + Rust bridge + web DSKY), quickstart (`make agc`, `make dev-runtime`,
`make dev-client`), link to spec and `docs/agc-channel-map.md`.

- [ ] **Step 3: Write `scripts/fetch-vendor.sh`**

```bash
#!/usr/bin/env bash
# Fetch and pin vendor repos. First run records SHAs into vendor/manifest.json;
# later runs verify the checkout matches the manifest.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor
MANIFEST=vendor/manifest.json

fetch() { # name url
  local name=$1 url=$2 dir=vendor/$1 sha
  if [[ ! -d $dir/.git ]]; then
    git clone --depth 1 "$url" "$dir"
  fi
  sha=$(git -C "$dir" rev-parse HEAD)
  if [[ -f $MANIFEST ]] && command -v jq >/dev/null; then
    want=$(jq -r ".\"$name\".sha // empty" "$MANIFEST")
    if [[ -n $want && $want != "$sha" ]]; then
      echo "ERROR: $name at $sha, manifest pins $want" >&2; exit 1
    fi
  fi
  echo "$name $sha"
}

A=$(fetch virtualagc https://github.com/virtualagc/virtualagc.git)
B=$(fetch Apollo-11 https://github.com/chrislgarry/Apollo-11.git)

if [[ ! -f $MANIFEST ]]; then
  jq -n --arg a "${A#* }" --arg b "${B#* }" '{
    "virtualagc": {url:"https://github.com/virtualagc/virtualagc.git", sha:$a},
    "Apollo-11":  {url:"https://github.com/chrislgarry/Apollo-11.git",  sha:$b}
  }' > "$MANIFEST"
  echo "wrote $MANIFEST"
fi
```

- [ ] **Step 4: Run and verify**

```bash
cd /home/kazumasa/projects/eagle && make vendor
```
Expected: both repos cloned; `vendor/manifest.json` exists with two SHA entries.
Verify pin check: run `make vendor` again — prints the same SHAs, exits 0.
Verify: `ls vendor/Apollo-11/Luminary099/MAIN.agc vendor/virtualagc/yaYUL vendor/virtualagc/yaAGC` — all exist.

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/.gitignore eagle/Makefile eagle/README.md eagle/scripts/fetch-vendor.sh eagle/vendor/manifest.json
git commit -m "build(eagle): repo skeleton and pinned vendor fetch for VirtualAGC and Apollo-11"
```

---

### Task 2: Build yaYUL + yaAGC CLI tools

**Files:**
- Create: `eagle/scripts/build-agc-tools.sh`
- Generated: `eagle/build/agc/yaYUL`, `eagle/build/agc/yaAGC`

**Interfaces:**
- Consumes: `vendor/` from Task 1.
- Produces: `make agc-tools` → executables `eagle/build/agc/yaYUL`, `eagle/build/agc/yaAGC`.

- [ ] **Step 1: Install build dependencies**

```bash
sudo apt-get install -y build-essential libncurses-dev libreadline-dev jq
```
(`jq` used by fetch-vendor.sh; ncurses/readline used by yaAGC's debugger build.)

- [ ] **Step 2: Write `scripts/build-agc-tools.sh`**

```bash
#!/usr/bin/env bash
# Build only the CLI tools we need: yaYUL (assembler) and yaAGC (emulator).
# Per VirtualAGC README: no configure, no make install, no parallel make.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/agc

make -C vendor/virtualagc/yaYUL
make -C vendor/virtualagc/yaAGC

cp vendor/virtualagc/yaYUL/yaYUL build/agc/yaYUL
cp vendor/virtualagc/yaAGC/yaAGC build/agc/yaAGC
echo "OK: $(build/agc/yaYUL --help 2>&1 | head -1 || true)"
```

- [ ] **Step 3: Run and verify (spike — expect to debug)**

```bash
cd /home/kazumasa/projects/eagle && make agc-tools
```
Expected: `build/agc/yaYUL` and `build/agc/yaAGC` exist and are executable
(`build/agc/yaAGC --version` or bare invocation prints usage, exit code != 139).

Known likely failures and exact fixes (apply only what's needed, keep the fix
in the script):
- Undefined version macro (`NVER`): pass it —
  `make -C vendor/virtualagc/yaAGC NVER='\"eagle\"'` (same for yaYUL).
- Old-C warnings promoted to errors on modern gcc: append
  `CFLAGS='-O2 -Wno-error -fcommon'` to the `make` line (`-fcommon` fixes
  "multiple definition" link errors typical of pre-gcc-10 C).
- If the subdirectory Makefile depends on top-level variables that cannot be
  satisfied, fall back to the top-level build of just those directories:
  `make -C vendor/virtualagc yaYUL yaAGC` — and if that also fails, use
  `make -C vendor/virtualagc -k` and confirm the two needed binaries were
  produced before it failed elsewhere (GUI targets are allowed to fail).

If it takes more than three distinct repair attempts, stop and report
(per user's global working rules).

- [ ] **Step 4: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/scripts/build-agc-tools.sh
git commit -m "build(eagle): compile yaYUL and yaAGC CLI tools from vendored VirtualAGC"
```

---

### Task 3: Assemble Luminary099, verify, smoke-test yaAGC

**Files:**
- Create: `eagle/scripts/assemble-luminary.sh`, `eagle/tests/golden-agc/smoke_yaagc.py`
- Generated: `eagle/build/agc/Luminary099.bin`, `eagle/build/agc/Luminary099.symtab`, `eagle/build/agc/manifest.json`

**Interfaces:**
- Consumes: `build/agc/yaYUL`, `build/agc/yaAGC` from Task 2.
- Produces: `make agc` → assembled+verified `build/agc/Luminary099.bin`; smoke test proving yaAGC boots it and answers on TCP. Later tasks launch `build/agc/yaAGC --core=build/agc/Luminary099.bin --port=<port>`.

- [ ] **Step 1: Write `scripts/assemble-luminary.sh`**

```bash
#!/usr/bin/env bash
# Assemble Luminary099 from BOTH transcriptions and require identical binaries.
# (Comments differ between repos; the octal program must not.)
set -euo pipefail
cd "$(dirname "$0")/.."
YAYUL=$PWD/build/agc/yaYUL

assemble() { # srcdir outprefix
  ( cd "$1" && "$YAYUL" MAIN.agc > "$PWD/../../../build/agc/$2.log" 2>&1 )
  cp "$1/MAIN.agc.bin" "build/agc/$2.bin"
  [[ -f $1/MAIN.agc.symtab ]] && cp "$1/MAIN.agc.symtab" "build/agc/$2.symtab"
}

assemble vendor/Apollo-11/Luminary099   Luminary099
assemble vendor/virtualagc/Luminary099  Luminary099-vagc

cmp build/agc/Luminary099.bin build/agc/Luminary099-vagc.bin \
  && echo "OK: both transcriptions assemble to identical binaries"

sha256sum build/agc/Luminary099.bin
jq -n --arg sha "$(sha256sum build/agc/Luminary099.bin | cut -d' ' -f1)" \
  '{program:"Luminary099", assembler:"yaYUL", binary_sha256:$sha}' \
  > build/agc/manifest.json
```
Note: if `vendor/virtualagc/Luminary099/` does not exist in the pinned
revision, drop the cross-check, keep the yaYUL success check (yaYUL validates
embedded bank checksums — "Bugger" words — so a clean assembly is itself a
strong integrity check), and record that in the script comment.

- [ ] **Step 2: Run and verify**

```bash
cd /home/kazumasa/projects/eagle && make agc
```
Expected: "OK: both transcriptions assemble to identical binaries" (or the
documented fallback), a SHA-256 line, and `build/agc/manifest.json` written.
Check the yaYUL log tail: `tail -5 build/agc/Luminary099.log` shows an
error/warning summary with **0 fatal errors**.

- [ ] **Step 3: Write the smoke test `tests/golden-agc/smoke_yaagc.py`**

```python
#!/usr/bin/env python3
"""Boot yaAGC with Luminary099, press RSET, expect packet traffic back."""
import socket, subprocess, sys, time

PORT = 19897
AGC = ["build/agc/yaAGC", "--core=build/agc/Luminary099.bin", f"--port={PORT}"]

def key_packet(code: int) -> bytes:  # DSKY keycode -> ch 015 packet
    ch, d = 0o15, code & 0x7FFF
    return bytes([ch >> 3, 0x40 | ((ch & 7) << 3) | (d >> 12),
                  0x80 | ((d >> 6) & 0x3F), 0xC0 | (d & 0x3F)])

proc = subprocess.Popen(AGC, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    s = None
    for _ in range(50):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=0.2); break
        except OSError:
            time.sleep(0.1)
    assert s, "could not connect to yaAGC"
    s.sendall(key_packet(0o22))  # RSET
    s.settimeout(5.0)
    data = s.recv(4096)
    assert len(data) >= 4, "no packet traffic from yaAGC"
    print(f"OK: received {len(data)} bytes from yaAGC")
finally:
    proc.terminate(); proc.wait(timeout=5)
```

- [ ] **Step 4: Run smoke test**

```bash
cd /home/kazumasa/projects/eagle && python3 tests/golden-agc/smoke_yaagc.py
```
Expected: `OK: received N bytes from yaAGC` (N ≥ 4). This is the Phase 0
definition of done.

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/scripts/assemble-luminary.sh eagle/tests/golden-agc/smoke_yaagc.py
git commit -m "feat(eagle): assemble and verify Luminary099; yaAGC boot smoke test"
```

---

### Task 4: Rust workspace skeleton

**Files:**
- Create: `eagle/runtime/Cargo.toml`, `eagle/runtime/crates/eagle-agc-protocol/Cargo.toml`, `eagle/runtime/crates/eagle-agc-protocol/src/lib.rs`, `eagle/runtime/crates/eagle-schema/Cargo.toml`, `eagle/runtime/crates/eagle-schema/src/lib.rs`, `eagle/runtime/apps/eagle-runtime/Cargo.toml`, `eagle/runtime/apps/eagle-runtime/src/main.rs`

**Interfaces:**
- Produces: cargo workspace `eagle/runtime` with member crates `eagle-agc-protocol` (lib), `eagle-schema` (lib), `eagle-runtime` (bin). `cargo test` runs from `eagle/runtime`.

- [ ] **Step 1: Write workspace files**

`eagle/runtime/Cargo.toml`:
```toml
[workspace]
resolver = "2"
members = ["crates/eagle-agc-protocol", "crates/eagle-schema", "apps/eagle-runtime"]

[workspace.dependencies]
thiserror = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
```

`crates/eagle-agc-protocol/Cargo.toml`:
```toml
[package]
name = "eagle-agc-protocol"
version = "0.1.0"
edition = "2021"

[dependencies]
thiserror = { workspace = true }
```
`src/lib.rs`: `pub mod packet;` placeholder module with `pub fn crate_ok() -> bool { true }` and a test asserting it (removed in Task 5).

`crates/eagle-schema/Cargo.toml`: same shape, deps `serde`, `serde_json`; `src/lib.rs` with the same trivial test.

`apps/eagle-runtime/Cargo.toml`:
```toml
[package]
name = "eagle-runtime"
version = "0.1.0"
edition = "2021"

[dependencies]
eagle-agc-protocol = { path = "../../crates/eagle-agc-protocol" }
eagle-schema = { path = "../../crates/eagle-schema" }
tokio = { workspace = true }
serde_json = { workspace = true }
anyhow = "1"
clap = { version = "4", features = ["derive"] }
axum = { version = "0.8", features = ["ws"] }
futures-util = "0.3"

[dev-dependencies]
tokio-tungstenite = "0.26"
```
`src/main.rs`: `fn main() { println!("eagle-runtime"); }`

- [ ] **Step 2: Verify build and tests**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test
```
Expected: PASS (2 trivial tests), workspace compiles.

- [ ] **Step 3: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime
git commit -m "build(eagle): rust workspace skeleton (protocol, schema, runtime)"
```

---

### Task 5: Packet codec in `eagle-agc-protocol` (TDD)

**Files:**
- Create: `eagle/runtime/crates/eagle-agc-protocol/src/packet.rs`, `eagle/docs/agc-channel-map.md`
- Modify: `eagle/runtime/crates/eagle-agc-protocol/src/lib.rs`

**Interfaces:**
- Produces (used by Tasks 6–10):
  - `PacketKind { Io, Counter, Bitmask }`
  - `Packet { kind: PacketKind, channel: u8, data: u16 }`
  - `Packet::io(channel: u8, data: u16) -> Result<Packet, PacketError>` (also `counter`, `bitmask` constructors)
  - `Packet::encode(&self) -> [u8; 4]`, `Packet::decode([u8; 4]) -> Result<Packet, PacketError>`
  - `pub const PING: [u8; 4]`
  - `StreamDecoder::new()`, `StreamDecoder::push(&mut self, bytes: &[u8]) -> Vec<Packet>` (byte-shift resync on bad signature, silently skips pings)

- [ ] **Step 1: Write failing tests in `src/packet.rs`**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_io_packet() {
        let p = Packet::io(0o15, 0o31).unwrap();
        assert_eq!(Packet::decode(p.encode()).unwrap(), p);
    }

    #[test]
    fn known_vector_ch015_data031() {
        // hand-computed from the 00utpppp 01pppddd 10dddddd 11dddddd layout
        let p = Packet::io(0o15, 0o31).unwrap();
        assert_eq!(p.encode(), [0x01, 0x68, 0x80, 0xD9]);
    }

    #[test]
    fn rejects_bad_signature() {
        assert!(matches!(
            Packet::decode([0xFF, 0x00, 0x80, 0xC0]),
            Err(PacketError::BadSignature(_))
        ));
    }

    #[test]
    fn rejects_out_of_range() {
        assert!(Packet::io(0x80, 0).is_err());
        assert!(Packet::io(0o15, 0x8000).is_err());
    }

    #[test]
    fn stream_decoder_resyncs_and_skips_pings() {
        let good = Packet::io(0o10, 0o12345).unwrap();
        let mut bytes = vec![0xC0, 0x81]; // garbage tail of a torn packet
        bytes.extend_from_slice(&PING);
        bytes.extend_from_slice(&good.encode());
        let mut dec = StreamDecoder::new();
        assert_eq!(dec.push(&bytes), vec![good]);
    }

    #[test]
    fn stream_decoder_handles_split_packets() {
        let good = Packet::io(0o11, 0o4).unwrap();
        let enc = good.encode();
        let mut dec = StreamDecoder::new();
        assert_eq!(dec.push(&enc[..2]), vec![]);
        assert_eq!(dec.push(&enc[2..]), vec![good]);
    }
}
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-agc-protocol
```
Expected: COMPILE ERROR (Packet not defined) — that counts as the failing state.

- [ ] **Step 3: Implement**

```rust
//! yaAGC 4-byte socket packet codec.
//! Layout (developer.html): 00utpppp 01pppddd 10dddddd 11dddddd
//! u = bitmask flag, t = counter flag, p = 7-bit channel, d = 15-bit data.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PacketKind { Io, Counter, Bitmask }

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Packet {
    pub kind: PacketKind,
    pub channel: u8,
    pub data: u16,
}

pub const PING: [u8; 4] = [0xFF, 0xFF, 0xFF, 0xFF];

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum PacketError {
    #[error("bad packet signature: {0:02x?}")]
    BadSignature([u8; 4]),
    #[error("channel out of range: {0:#o}")]
    ChannelRange(u8),
    #[error("data out of range: {0:#o}")]
    DataRange(u16),
}

impl Packet {
    fn new(kind: PacketKind, channel: u8, data: u16) -> Result<Self, PacketError> {
        if channel > 0x7F { return Err(PacketError::ChannelRange(channel)); }
        if data > 0x7FFF { return Err(PacketError::DataRange(data)); }
        Ok(Self { kind, channel, data })
    }
    pub fn io(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Io, channel, data)
    }
    pub fn counter(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Counter, channel, data)
    }
    pub fn bitmask(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Bitmask, channel, data)
    }

    pub fn encode(&self) -> [u8; 4] {
        let u = matches!(self.kind, PacketKind::Bitmask) as u8;
        let t = matches!(self.kind, PacketKind::Counter) as u8;
        let (ch, d) = (self.channel, self.data);
        [
            (u << 5) | (t << 4) | (ch >> 3),
            0x40 | ((ch & 0b111) << 3) | ((d >> 12) as u8),
            0x80 | (((d >> 6) & 0x3F) as u8),
            0xC0 | ((d & 0x3F) as u8),
        ]
    }

    pub fn decode(b: [u8; 4]) -> Result<Self, PacketError> {
        if b[0] >> 6 != 0b00 || b[1] >> 6 != 0b01
            || b[2] >> 6 != 0b10 || b[3] >> 6 != 0b11 {
            return Err(PacketError::BadSignature(b));
        }
        let kind = match ((b[0] >> 5) & 1, (b[0] >> 4) & 1) {
            (1, _) => PacketKind::Bitmask,
            (0, 1) => PacketKind::Counter,
            _ => PacketKind::Io,
        };
        let channel = ((b[0] & 0x0F) << 3) | ((b[1] >> 3) & 0b111);
        let data = (((b[1] & 0b111) as u16) << 12)
            | (((b[2] & 0x3F) as u16) << 6)
            | ((b[3] & 0x3F) as u16);
        Ok(Self { kind, channel, data })
    }
}

/// Incremental decoder over a TCP byte stream: aligns on signature bits,
/// resyncs by shifting one byte on mismatch, drops ping packets.
#[derive(Default)]
pub struct StreamDecoder { buf: Vec<u8> }

impl StreamDecoder {
    pub fn new() -> Self { Self::default() }

    pub fn push(&mut self, bytes: &[u8]) -> Vec<Packet> {
        self.buf.extend_from_slice(bytes);
        let mut out = Vec::new();
        while self.buf.len() >= 4 {
            let head: [u8; 4] = self.buf[..4].try_into().unwrap();
            if head == PING {
                self.buf.drain(..4);
            } else if let Ok(p) = Packet::decode(head) {
                self.buf.drain(..4);
                out.push(p);
            } else {
                self.buf.remove(0); // resync one byte at a time
            }
        }
        out
    }
}
```
Update `src/lib.rs`: `pub mod packet;` and re-export
`pub use packet::{Packet, PacketKind, PacketError, StreamDecoder, PING};`
Remove the Task 4 placeholder test.

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-agc-protocol
```
Expected: PASS, 6 tests.

- [ ] **Step 5: Start `eagle/docs/agc-channel-map.md`**

Create the doc with the packet-layout section (the Reference block at the top
of this plan, verbatim) plus a Sources section citing
`https://www.ibiblio.org/apollo/developer.html` and
`vendor/virtualagc/yaAGC/SocketAPI.c`.

- [ ] **Step 6: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime/crates/eagle-agc-protocol eagle/docs/agc-channel-map.md
git commit -m "feat(eagle): yaAGC 4-byte packet codec with stream resync"
```

---

### Task 6: yaAGC session (spawn + TCP + packet channels)

**Files:**
- Create: `eagle/runtime/apps/eagle-runtime/src/agc_session.rs`
- Modify: `eagle/runtime/apps/eagle-runtime/src/main.rs` (add `mod agc_session;`)
- Test: `eagle/runtime/apps/eagle-runtime/tests/live_agc.rs`

**Interfaces:**
- Consumes: `Packet`, `StreamDecoder` from Task 5.
- Produces (used by Tasks 8–10):
  - `AgcConfig { yaagc_bin: PathBuf, core_bin: PathBuf, port: u16 }`
  - `AgcSession::start(cfg: AgcConfig) -> anyhow::Result<AgcSession>`
  - `AgcSession::events(&mut self) -> &mut tokio::sync::mpsc::Receiver<Packet>` (AGC → us)
  - `AgcSession::send(&self, p: Packet) -> anyhow::Result<()>` (us → AGC)
  - `AgcSession::shutdown(self)` (kills the child)

- [ ] **Step 1: Write the failing integration test** (`tests/live_agc.rs`)

```rust
use eagle_agc_protocol::Packet;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use std::path::PathBuf;

fn cfg(port: u16) -> AgcConfig {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
    AgcConfig {
        yaagc_bin: root.join("build/agc/yaAGC"),
        core_bin: root.join("build/agc/Luminary099.bin"),
        port,
    }
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn boots_and_produces_packets_after_rset() {
    let mut s = AgcSession::start(cfg(19897)).await.unwrap();
    s.send(Packet::io(0o15, 0o22).unwrap()).unwrap(); // RSET
    let p = tokio::time::timeout(std::time::Duration::from_secs(5), s.events().recv())
        .await.expect("timed out").expect("channel closed");
    assert!(p.channel <= 0o177);
    s.shutdown();
}
```
Note: this requires exposing modules to integration tests. In
`apps/eagle-runtime/Cargo.toml` add a lib target:
```toml
[lib]
name = "eagle_runtime"
path = "src/lib.rs"
```
Create `src/lib.rs` with `pub mod agc_session;` and keep `main.rs` as the bin
(`use eagle_runtime::agc_session;`).

- [ ] **Step 2: Verify failure**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-runtime -- --ignored --test-threads=1
```
Expected: COMPILE ERROR (agc_session not defined).

- [ ] **Step 3: Implement `agc_session.rs`**

```rust
use anyhow::{Context, Result};
use eagle_agc_protocol::{Packet, StreamDecoder};
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::process::{Child, Command};
use tokio::sync::mpsc;

pub struct AgcConfig {
    pub yaagc_bin: PathBuf,
    pub core_bin: PathBuf,
    pub port: u16,
}

pub struct AgcSession {
    child: Child,
    events_rx: mpsc::Receiver<Packet>,
    cmd_tx: mpsc::UnboundedSender<Packet>,
}

impl AgcSession {
    pub async fn start(cfg: AgcConfig) -> Result<Self> {
        let child = Command::new(&cfg.yaagc_bin)
            .arg(format!("--core={}", cfg.core_bin.display()))
            .arg(format!("--port={}", cfg.port))
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| format!("spawning {:?}", cfg.yaagc_bin))?;

        let mut stream = None;
        for _ in 0..50 {
            match TcpStream::connect(("127.0.0.1", cfg.port)).await {
                Ok(s) => { stream = Some(s); break; }
                Err(_) => tokio::time::sleep(std::time::Duration::from_millis(100)).await,
            }
        }
        let stream = stream.context("could not connect to yaAGC")?;
        let (mut rd, mut wr) = stream.into_split();

        let (events_tx, events_rx) = mpsc::channel::<Packet>(1024);
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<Packet>();

        tokio::spawn(async move {
            let mut dec = StreamDecoder::new();
            let mut buf = [0u8; 4096];
            loop {
                match rd.read(&mut buf).await {
                    Ok(0) | Err(_) => break,
                    Ok(n) => {
                        for p in dec.push(&buf[..n]) {
                            if events_tx.send(p).await.is_err() { return; }
                        }
                    }
                }
            }
        });
        tokio::spawn(async move {
            while let Some(p) = cmd_rx.recv().await {
                if wr.write_all(&p.encode()).await.is_err() { break; }
            }
        });

        Ok(Self { child, events_rx, cmd_tx })
    }

    pub fn events(&mut self) -> &mut mpsc::Receiver<Packet> { &mut self.events_rx }

    pub fn send(&self, p: Packet) -> Result<()> {
        self.cmd_tx.send(p).map_err(|_| anyhow::anyhow!("agc writer gone"))
    }

    pub fn shutdown(mut self) {
        let _ = self.child.start_kill();
    }
}
```

- [ ] **Step 4: Verify pass (needs `make agc` done once)**

```bash
cd /home/kazumasa/projects/eagle && make agc   # if not already built
cd runtime && cargo test -p eagle-runtime -- --ignored --test-threads=1
```
Expected: PASS `boots_and_produces_packets_after_rset`.
Also verify `cargo test` (without --ignored) still passes and skips it.

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime/apps/eagle-runtime
git commit -m "feat(eagle): yaAGC child-process session with packet event stream"
```

---

### Task 7: DSKY state decoder (TDD, pure)

**Files:**
- Create: `eagle/runtime/crates/eagle-agc-protocol/src/dsky.rs`
- Modify: `eagle/runtime/crates/eagle-agc-protocol/src/lib.rs`, `eagle/docs/agc-channel-map.md`

**Interfaces:**
- Consumes: `Packet` from Task 5.
- Produces (used by Tasks 9–10):
  - `DskyState` (all fields `pub`): `prog: [char; 2]`, `verb: [char; 2]`, `noun: [char; 2]`, `r1: RegisterDisplay`, `r2`, `r3`, `lamps: Lamps`, plus `verb_noun_flash: bool`, `restart: bool`, `standby: bool`, `key_rel: bool`, `opr_err: bool`, `temp: bool`
  - `RegisterDisplay { sign: char /* ' ', '+', '-' */, digits: [char; 5] }`
  - `Lamps { comp_acty: bool, uplink_acty: bool, no_att: bool, gimbal_lock: bool, prog_alarm: bool, tracker: bool, alt: bool, vel: bool, no_dap: bool, prio_disp: bool }`
  - `DskyState::default()`, `DskyState::apply(&mut self, p: &Packet) -> bool` (true if visible state changed)

- [ ] **Step 0: Confirm channel semantics from vendored sources**

The relay-row table and digit codes are in the plan Reference block. Confirm
the row-12 lamp bit positions and ch 0163 bit meanings against the local
vendor checkout before writing tests:

```bash
grep -rn "163" /home/kazumasa/projects/eagle/vendor/virtualagc/yaAGC/agc_engine.c | head -20
grep -rni "gimbal\|no att\|tracker\|prio" /home/kazumasa/projects/eagle/vendor/virtualagc/yaDSKY2/*.cpp* 2>/dev/null | head -30
```
Record the confirmed tables (rows 1–12 of ch 010, ch 011 bits, ch 0163 bits)
in `eagle/docs/agc-channel-map.md` with file/line citations. Use those
confirmed values in the tests below (the values shown are the expected ones
from the developer docs; correct them if vendor source disagrees — vendor
source wins).

- [ ] **Step 1: Write failing tests in `src/dsky.rs`**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use crate::Packet;

    // relay word helper: AAAA B CCCCC DDDDD
    fn relay(row: u16, b: u16, c: u16, d: u16) -> Packet {
        Packet::io(0o10, (row << 11) | (b << 10) | (c << 5) | d).unwrap()
    }

    #[test]
    fn decodes_prog_63() {
        let mut s = DskyState::default();
        // row 11 drives M1/M2 (PROG). '6' = 0b11100, '3' = 0b11011
        s.apply(&relay(11, 0, 0b11100, 0b11011));
        assert_eq!(s.prog, ['6', '3']);
    }

    #[test]
    fn decodes_verb_noun() {
        let mut s = DskyState::default();
        s.apply(&relay(10, 0, 0b00011, 0b11100)); // VERB 16
        s.apply(&relay(9, 0, 0b11011, 0b11100)); // NOUN 36
        assert_eq!(s.verb, ['1', '6']);
        assert_eq!(s.noun, ['3', '6']);
    }

    #[test]
    fn decodes_r1_with_sign() {
        let mut s = DskyState::default();
        s.apply(&relay(8, 0, 0, 0b10101));       // R1D1 = '0'
        s.apply(&relay(7, 1, 0b10101, 0b10101)); // +sign, R1D2, R1D3
        s.apply(&relay(6, 0, 0b11011, 0b00011)); // no -sign, R1D4='3', R1D5='1'
        assert_eq!(s.r1.sign, '+');
        assert_eq!(s.r1.digits, ['0', '0', '0', '3', '1']);
    }

    #[test]
    fn blank_code_blanks_digit() {
        let mut s = DskyState::default();
        s.apply(&relay(11, 0, 0b11101, 0b11101)); // "88"
        s.apply(&relay(11, 0, 0, 0));             // blank both
        assert_eq!(s.prog, [' ', ' ']);
    }

    #[test]
    fn lamp_channel_011() {
        let mut s = DskyState::default();
        assert!(s.apply(&Packet::io(0o11, 1 << 1).unwrap())); // bit 2: COMP ACTY
        assert!(s.lamps.comp_acty);
        s.apply(&Packet::io(0o11, 0).unwrap());
        assert!(!s.lamps.comp_acty);
    }

    #[test]
    fn flash_and_restart_on_0163() {
        let mut s = DskyState::default();
        // bit 6 = VERB/NOUN flash, bit 8 = RESTART (verify in Step 0)
        s.apply(&Packet::io(0o163, (1 << 5) | (1 << 7)).unwrap());
        assert!(s.verb_noun_flash);
        assert!(s.restart);
    }

    #[test]
    fn apply_reports_change() {
        let mut s = DskyState::default();
        let p = relay(10, 0, 0b00011, 0b11100);
        assert!(s.apply(&p));
        assert!(!s.apply(&p)); // same word again: no visible change
    }
}
```

- [ ] **Step 2: Verify failure**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-agc-protocol dsky
```
Expected: COMPILE ERROR (DskyState not defined).

- [ ] **Step 3: Implement `dsky.rs`**

```rust
//! DSKY display-state decoder for output channels 010/011/013/0163.
//! Sources: docs/agc-channel-map.md (row/bit tables with citations).

use crate::Packet;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RegisterDisplay {
    pub sign: char,
    pub digits: [char; 5],
}

impl Default for RegisterDisplay {
    fn default() -> Self { Self { sign: ' ', digits: [' '; 5] } }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Lamps {
    pub comp_acty: bool,
    pub uplink_acty: bool,
    pub no_att: bool,
    pub gimbal_lock: bool,
    pub prog_alarm: bool,
    pub tracker: bool,
    pub alt: bool,
    pub vel: bool,
    pub no_dap: bool,
    pub prio_disp: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DskyState {
    pub prog: [char; 2],
    pub verb: [char; 2],
    pub noun: [char; 2],
    pub r1: RegisterDisplay,
    pub r2: RegisterDisplay,
    pub r3: RegisterDisplay,
    pub lamps: Lamps,
    pub verb_noun_flash: bool,
    pub restart: bool,
    pub standby: bool,
    pub key_rel: bool,
    pub opr_err: bool,
    pub temp: bool,
    // internal: sign is driven by two rows (plus-row and minus-row)
    plus: [bool; 3],
    minus: [bool; 3],
}

impl Default for DskyState {
    fn default() -> Self {
        Self {
            prog: [' '; 2], verb: [' '; 2], noun: [' '; 2],
            r1: Default::default(), r2: Default::default(), r3: Default::default(),
            lamps: Default::default(),
            verb_noun_flash: false, restart: false, standby: false,
            key_rel: false, opr_err: false, temp: false,
            plus: [false; 3], minus: [false; 3],
        }
    }
}

fn digit(code: u16) -> char {
    match code {
        0 => ' ',
        0b10101 => '0', 0b00011 => '1', 0b11001 => '2', 0b11011 => '3',
        0b01111 => '4', 0b11110 => '5', 0b11100 => '6', 0b10011 => '7',
        0b11101 => '8', 0b11111 => '9',
        _ => '?',
    }
}

impl DskyState {
    pub fn apply(&mut self, p: &Packet) -> bool {
        let before = *self;
        match p.channel {
            0o10 => self.apply_relay(p.data),
            0o11 => {
                let b = |n: u16| p.data & (1 << (n - 1)) != 0;
                self.lamps.comp_acty = b(2);
                self.lamps.uplink_acty = b(3);
            }
            0o163 => {
                let b = |n: u16| p.data & (1 << (n - 1)) != 0;
                self.temp = b(4);
                self.key_rel = b(5);
                self.verb_noun_flash = b(6);
                self.opr_err = b(7);
                self.restart = b(8);
                self.standby = b(9);
            }
            _ => {}
        }
        for i in 0..3 {
            let sign = match (self.plus[i], self.minus[i]) {
                (true, _) => '+',
                (false, true) => '-',
                _ => ' ',
            };
            match i { 0 => self.r1.sign = sign, 1 => self.r2.sign = sign, _ => self.r3.sign = sign }
        }
        *self != before
    }

    fn apply_relay(&mut self, data: u16) {
        let row = (data >> 11) & 0xF;
        let b = (data >> 10) & 1 != 0;
        let c = digit((data >> 5) & 0x1F);
        let d = digit(data & 0x1F);
        match row {
            11 => { self.prog = [c, d]; }
            10 => { self.verb = [c, d]; }
            9 => { self.noun = [c, d]; }
            8 => { self.r1.digits[0] = d; }
            7 => { self.plus[0] = b; self.r1.digits[1] = c; self.r1.digits[2] = d; }
            6 => { self.minus[0] = b; self.r1.digits[3] = c; self.r1.digits[4] = d; }
            5 => { self.plus[1] = b; self.r2.digits[0] = c; self.r2.digits[1] = d; }
            4 => { self.minus[1] = b; self.r2.digits[2] = c; self.r2.digits[3] = d; }
            3 => { self.r2.digits[4] = c; self.r3.digits[0] = d; }
            2 => { self.plus[2] = b; self.r3.digits[1] = c; self.r3.digits[2] = d; }
            1 => { self.minus[2] = b; self.r3.digits[3] = c; self.r3.digits[4] = d; }
            12 => {
                let l = |n: u16| data & (1 << n) != 0; // confirm positions in Step 0
                self.lamps.prio_disp = l(0);
                self.lamps.no_dap = l(1);
                self.lamps.vel = l(2);
                self.lamps.no_att = l(3);
                self.lamps.alt = l(4);
                self.lamps.gimbal_lock = l(5);
                self.lamps.tracker = l(7);
                self.lamps.prog_alarm = l(8);
            }
            _ => {}
        }
    }
}
```
Add `pub mod dsky;` + re-exports to `lib.rs`. Adjust bit positions to match
what Step 0 confirmed (tests and impl together).

- [ ] **Step 4: Verify pass**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-agc-protocol
```
Expected: PASS (codec + dsky tests).

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime/crates/eagle-agc-protocol eagle/docs/agc-channel-map.md
git commit -m "feat(eagle): DSKY display-state decoder for ch 010/011/0163"
```

---

### Task 8: Key input + live V35E lamp-test integration

**Files:**
- Create: `eagle/runtime/crates/eagle-agc-protocol/src/keys.rs`
- Modify: `eagle/runtime/crates/eagle-agc-protocol/src/lib.rs`, `eagle/docs/agc-channel-map.md`
- Test: `eagle/runtime/apps/eagle-runtime/tests/live_agc.rs` (extend)

**Interfaces:**
- Consumes: `Packet`, `AgcSession`, `DskyState`.
- Produces (used by Tasks 9–11):
  - `DskyKey` enum: `Zero..=Nine` (as `D0..D9`), `Verb`, `Noun`, `Rset`, `KeyRel`, `Plus`, `Minus`, `Entr`, `Clr`
  - `DskyKey::code(self) -> u16` (octal codes from the Reference block)
  - `DskyKey::packet(self) -> Packet` (ch `0o15`)
  - `DskyKey::from_name(&str) -> Option<DskyKey>` (names: `"0".."9"`, `"VERB"`, `"NOUN"`, `"RSET"`, `"KEY_REL"`, `"PLUS"`, `"MINUS"`, `"ENTR"`, `"CLR"`)
  - `pro_key_packets(pressed: bool) -> [Packet; 2]` (bitmask for ch `0o32` bit 14, then value with bit 14 = !pressed)

- [ ] **Step 1: Write failing unit tests in `keys.rs`**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keycodes_match_channel_map() {
        assert_eq!(DskyKey::D0.code(), 0o20);
        assert_eq!(DskyKey::D9.code(), 0o11);
        assert_eq!(DskyKey::Verb.code(), 0o21);
        assert_eq!(DskyKey::Noun.code(), 0o37);
        assert_eq!(DskyKey::Entr.code(), 0o34);
        assert_eq!(DskyKey::Rset.code(), 0o22);
        assert_eq!(DskyKey::Clr.code(), 0o36);
        assert_eq!(DskyKey::KeyRel.code(), 0o31);
        assert_eq!(DskyKey::Plus.code(), 0o32);
        assert_eq!(DskyKey::Minus.code(), 0o33);
    }

    #[test]
    fn key_packet_targets_ch015() {
        let p = DskyKey::Verb.packet();
        assert_eq!((p.channel, p.data), (0o15, 0o21));
    }

    #[test]
    fn from_name_roundtrip() {
        assert_eq!(DskyKey::from_name("VERB"), Some(DskyKey::Verb));
        assert_eq!(DskyKey::from_name("5"), Some(DskyKey::D5));
        assert_eq!(DskyKey::from_name("bogus"), None);
    }

    #[test]
    fn pro_key_uses_ch032_bit14_inverted() {
        use crate::PacketKind;
        let [mask, val] = pro_key_packets(true);
        assert_eq!(mask.kind, PacketKind::Bitmask);
        assert_eq!((mask.channel, mask.data), (0o32, 1 << 13));
        assert_eq!(val.kind, PacketKind::Io);
        assert_eq!((val.channel, val.data), (0o32, 0)); // pressed => bit low
        let [_, released] = pro_key_packets(false);
        assert_eq!(released.data, 1 << 13);
    }
}
```

- [ ] **Step 2: Verify failure, then implement**

Run: `cargo test -p eagle-agc-protocol keys` → COMPILE ERROR. Implement:

```rust
use crate::{Packet, PacketError};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DskyKey {
    D0, D1, D2, D3, D4, D5, D6, D7, D8, D9,
    Verb, Noun, Rset, KeyRel, Plus, Minus, Entr, Clr,
}

impl DskyKey {
    pub fn code(self) -> u16 {
        use DskyKey::*;
        match self {
            D1 => 0o1, D2 => 0o2, D3 => 0o3, D4 => 0o4, D5 => 0o5,
            D6 => 0o6, D7 => 0o7, D8 => 0o10, D9 => 0o11, D0 => 0o20,
            Verb => 0o21, Rset => 0o22, KeyRel => 0o31, Plus => 0o32,
            Minus => 0o33, Entr => 0o34, Clr => 0o36, Noun => 0o37,
        }
    }
    pub fn packet(self) -> Packet {
        Packet::io(0o15, self.code()).expect("static keycodes are in range")
    }
    pub fn from_name(name: &str) -> Option<Self> {
        use DskyKey::*;
        Some(match name {
            "0" => D0, "1" => D1, "2" => D2, "3" => D3, "4" => D4,
            "5" => D5, "6" => D6, "7" => D7, "8" => D8, "9" => D9,
            "VERB" => Verb, "NOUN" => Noun, "RSET" => Rset, "KEY_REL" => KeyRel,
            "PLUS" => Plus, "MINUS" => Minus, "ENTR" => Entr, "CLR" => Clr,
            _ => return None,
        })
    }
}

/// PRO/STBY is not a keycode: it is input channel 032 bit 14, inverted
/// (0 = pressed). Send a bitmask packet claiming bit 14, then the value.
pub fn pro_key_packets(pressed: bool) -> [Packet; 2] {
    let bit = 1u16 << 13; // bit 14, 1-indexed
    let value = if pressed { 0 } else { bit };
    [
        Packet::bitmask(0o32, bit).expect("static"),
        Packet::io(0o32, value).expect("static"),
    ]
}

#[allow(unused)]
fn _err_ty(_: PacketError) {}
```
Add `pub mod keys;` + re-exports. Run: `cargo test -p eagle-agc-protocol` → PASS.
Append the keycode table and PRO semantics to `docs/agc-channel-map.md`.

- [ ] **Step 3: Add the live V35E test to `tests/live_agc.rs`**

```rust
use eagle_agc_protocol::{dsky::DskyState, keys::DskyKey};

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn v35e_lights_all_eights() {
    let mut s = AgcSession::start(cfg(19898)).await.unwrap();
    // let Luminary boot before keying
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    for k in [DskyKey::Verb, DskyKey::D3, DskyKey::D5, DskyKey::Entr] {
        s.send(k.packet()).unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    }
    let mut state = DskyState::default();
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(5);
    loop {
        let timeout = deadline - tokio::time::Instant::now();
        match tokio::time::timeout(timeout, s.events().recv()).await {
            Ok(Some(p)) => {
                state.apply(&p);
                if state.verb == ['8', '8'] && state.noun == ['8', '8']
                    && state.prog == ['8', '8'] {
                    s.shutdown();
                    return; // lamp test confirmed
                }
            }
            _ => break,
        }
    }
    panic!("V35E did not produce the 88 lamp-test display; last state: {state:?}");
}
```

- [ ] **Step 4: Run live test**

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-runtime -- --ignored --test-threads=1
```
Expected: PASS both live tests. If `v35e_lights_all_eights` fails, debug with
the JSONL trace from Task 10 stage or by printing packets (octal) — most
likely causes: keycode table wrong (fix `keys.rs` + channel map doc) or
Luminary not yet accepting input (increase boot sleep to 5 s).

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime eagle/docs/agc-channel-map.md
git commit -m "feat(eagle): DSKY key encoding and live V35E lamp-test integration"
```

---

### Task 9: WebSocket schema + server

**Files:**
- Create: `eagle/runtime/crates/eagle-schema/src/lib.rs` (replace placeholder), `eagle/runtime/apps/eagle-runtime/src/server.rs`
- Modify: `eagle/runtime/apps/eagle-runtime/src/lib.rs`, `src/main.rs`
- Test: schema unit tests inline; `eagle/runtime/apps/eagle-runtime/tests/live_ws.rs`

**Interfaces:**
- Consumes: `AgcSession`, `DskyState`, `DskyKey`, `pro_key_packets`.
- Produces (used by Tasks 10–11):
  - `eagle-schema`: `ServerMsg::DskyState { schema_version: u32, prog: String, verb: String, noun: String, r1: String, r2: String, r3: String, lamps: BTreeMap<String, bool>, verb_noun_flash: bool, restart: bool, standby: bool, key_rel: bool, opr_err: bool, temp: bool }` and `ClientMsg::Key { key: String } | ClientMsg::Pro { pressed: bool }`, serde-tagged `{"type": "dsky_state" | "key" | "pro"}`; `impl From<&DskyState> for ServerMsg` lives in eagle-runtime (`server.rs`) to keep eagle-schema dependency-free of the protocol crate. Register strings are 6 chars: sign then 5 digits (e.g. `"+00031"`, blanks as spaces).
  - Runtime binary: `eagle-runtime --yaagc <path> --core <path> [--agc-port 19797] [--ws-port 8642] [--trace-out traces/session.jsonl]`; serves `GET /ws` WebSocket: pushes a full `dsky_state` JSON on connect and on every visible change; applies incoming `key`/`pro` messages to the AGC.

- [ ] **Step 1: Write failing schema tests** (in `eagle-schema/src/lib.rs`)

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn server_msg_json_shape() {
        let msg = ServerMsg::DskyState(DskyStateMsg {
            schema_version: 1,
            prog: "63".into(), verb: "16".into(), noun: "36".into(),
            r1: "+00031".into(), r2: "      ".into(), r3: "      ".into(),
            lamps: Default::default(),
            verb_noun_flash: false, restart: false, standby: false,
            key_rel: false, opr_err: false, temp: false,
        });
        let j: serde_json::Value = serde_json::to_value(&msg).unwrap();
        assert_eq!(j["type"], "dsky_state");
        assert_eq!(j["verb"], "16");
    }

    #[test]
    fn client_msg_parses() {
        let m: ClientMsg = serde_json::from_str(r#"{"type":"key","key":"VERB"}"#).unwrap();
        assert!(matches!(m, ClientMsg::Key { ref key } if key == "VERB"));
        let m: ClientMsg = serde_json::from_str(r#"{"type":"pro","pressed":true}"#).unwrap();
        assert!(matches!(m, ClientMsg::Pro { pressed: true }));
    }
}
```

- [ ] **Step 2: Verify failure, implement schema**

Run `cargo test -p eagle-schema` → COMPILE ERROR. Implement:

```rust
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct DskyStateMsg {
    pub schema_version: u32,
    pub prog: String,
    pub verb: String,
    pub noun: String,
    pub r1: String,
    pub r2: String,
    pub r3: String,
    pub lamps: BTreeMap<String, bool>,
    pub verb_noun_flash: bool,
    pub restart: bool,
    pub standby: bool,
    pub key_rel: bool,
    pub opr_err: bool,
    pub temp: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMsg {
    DskyState(DskyStateMsg),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMsg {
    Key { key: String },
    Pro { pressed: bool },
}
```
Run `cargo test -p eagle-schema` → PASS.

- [ ] **Step 3: Implement `server.rs` + `main.rs`**

`server.rs`:
```rust
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::Router;
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::keys::{pro_key_packets, DskyKey};
use eagle_agc_protocol::Packet;
use eagle_schema::{ClientMsg, DskyStateMsg, ServerMsg, SCHEMA_VERSION};
use futures_util::{SinkExt, StreamExt};
use tokio::sync::{broadcast, mpsc};

pub fn to_msg(s: &DskyState) -> ServerMsg {
    let reg = |r: &eagle_agc_protocol::dsky::RegisterDisplay| {
        std::iter::once(r.sign).chain(r.digits).collect::<String>()
    };
    let mut lamps = std::collections::BTreeMap::new();
    for (name, v) in [
        ("comp_acty", s.lamps.comp_acty), ("uplink_acty", s.lamps.uplink_acty),
        ("no_att", s.lamps.no_att), ("gimbal_lock", s.lamps.gimbal_lock),
        ("prog", s.lamps.prog_alarm), ("tracker", s.lamps.tracker),
        ("alt", s.lamps.alt), ("vel", s.lamps.vel),
        ("no_dap", s.lamps.no_dap), ("prio_disp", s.lamps.prio_disp),
    ] { lamps.insert(name.to_string(), v); }
    ServerMsg::DskyState(DskyStateMsg {
        schema_version: SCHEMA_VERSION,
        prog: s.prog.iter().collect(), verb: s.verb.iter().collect(),
        noun: s.noun.iter().collect(),
        r1: reg(&s.r1), r2: reg(&s.r2), r3: reg(&s.r3),
        lamps,
        verb_noun_flash: s.verb_noun_flash, restart: s.restart,
        standby: s.standby, key_rel: s.key_rel, opr_err: s.opr_err,
        temp: s.temp,
    })
}

#[derive(Clone)]
pub struct AppState {
    pub state_rx: broadcast::Sender<String>, // serialized ServerMsg JSON
    pub agc_tx: mpsc::UnboundedSender<Packet>,
    pub latest: std::sync::Arc<std::sync::Mutex<String>>,
}

pub fn router(app: AppState) -> Router {
    Router::new().route("/ws", get(ws_handler)).with_state(app)
}

async fn ws_handler(ws: WebSocketUpgrade, State(app): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(move |sock| client_loop(sock, app))
}

async fn client_loop(sock: WebSocket, app: AppState) {
    let (mut tx, mut rx) = sock.split();
    let snapshot = app.latest.lock().unwrap().clone();
    if !snapshot.is_empty() {
        let _ = tx.send(Message::Text(snapshot.into())).await;
    }
    let mut updates = app.state_rx.subscribe();
    loop {
        tokio::select! {
            u = updates.recv() => match u {
                Ok(json) => { if tx.send(Message::Text(json.into())).await.is_err() { break } }
                Err(broadcast::error::RecvError::Lagged(_)) => continue,
                Err(_) => break,
            },
            m = rx.next() => match m {
                Some(Ok(Message::Text(text))) => {
                    if let Ok(msg) = serde_json::from_str::<ClientMsg>(&text) {
                        match msg {
                            ClientMsg::Key { key } => {
                                if let Some(k) = DskyKey::from_name(&key) {
                                    let _ = app.agc_tx.send(k.packet());
                                }
                            }
                            ClientMsg::Pro { pressed } => {
                                for p in pro_key_packets(pressed) {
                                    let _ = app.agc_tx.send(p);
                                }
                            }
                        }
                    }
                }
                Some(Ok(_)) => continue,
                _ => break,
            },
        }
    }
}
```

`main.rs`:
```rust
use clap::Parser;
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::{router, to_msg, AppState};
use eagle_runtime::trace::TraceWriter;
use std::path::PathBuf;
use tokio::sync::{broadcast, mpsc};

#[derive(Parser)]
struct Args {
    #[arg(long)]
    yaagc: PathBuf,
    #[arg(long)]
    core: PathBuf,
    #[arg(long, default_value_t = 19797)]
    agc_port: u16,
    #[arg(long, default_value_t = 8642)]
    ws_port: u16,
    #[arg(long)]
    trace_out: Option<PathBuf>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    let mut session = AgcSession::start(AgcConfig {
        yaagc_bin: args.yaagc, core_bin: args.core, port: args.agc_port,
    }).await?;

    let (state_tx, _) = broadcast::channel::<String>(256);
    let (agc_tx, mut agc_rx) = mpsc::unbounded_channel();
    let latest = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let mut trace = TraceWriter::open(args.trace_out)?;

    let app = AppState { state_rx: state_tx.clone(), agc_tx, latest: latest.clone() };
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", args.ws_port)).await?;
    tokio::spawn(async move {
        axum::serve(listener, router(app)).await.unwrap();
    });
    eprintln!("eagle-runtime: ws://127.0.0.1:{}/ws", args.ws_port);

    let mut dsky = DskyState::default();
    loop {
        tokio::select! {
            Some(pkt) = session.events().recv() => {
                trace.log("out", &pkt);
                if dsky.apply(&pkt) {
                    let json = serde_json::to_string(&to_msg(&dsky))?;
                    *latest.lock().unwrap() = json.clone();
                    let _ = state_tx.send(json);
                }
            }
            Some(pkt) = agc_rx.recv() => {
                trace.log("in", &pkt);
                session.send(pkt)?;
            }
            else => break,
        }
    }
    Ok(())
}
```
(`trace::TraceWriter` is defined in Task 10 — to keep this task compiling,
create `src/trace.rs` now with the real implementation from Task 10 Step 2,
or stub `TraceWriter::open(None) -> no-op`; the plan orders Task 10 next, so
implement the no-op stub with the exact signature:
`pub struct TraceWriter(Option<std::fs::File>);`
`pub fn open(path: Option<PathBuf>) -> anyhow::Result<Self>`,
`pub fn log(&mut self, dir: &str, p: &Packet)` — bodies may be `Ok(Self(None))`
and `{}` for now.)
Add `pub mod server; pub mod trace;` to `lib.rs`.

- [ ] **Step 4: Write and run the live WS end-to-end test** (`tests/live_ws.rs`)

This is the headless Phase 1 DoD test: V16N36E over WebSocket shows a running clock.

```rust
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::tungstenite::Message;

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn v16n36_shows_running_clock_over_ws() {
    let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let mut child = tokio::process::Command::new(env!("CARGO_BIN_EXE_eagle-runtime"))
        .arg("--yaagc").arg(root.join("build/agc/yaAGC"))
        .arg("--core").arg(root.join("build/agc/Luminary099.bin"))
        .arg("--agc-port").arg("19899")
        .arg("--ws-port").arg("8899")
        .kill_on_drop(true)
        .spawn().unwrap();

    tokio::time::sleep(std::time::Duration::from_secs(3)).await; // AGC boot
    let (mut ws, _) = tokio_tungstenite::connect_async("ws://127.0.0.1:8899/ws")
        .await.expect("ws connect");

    for key in ["VERB", "1", "6", "NOUN", "3", "6", "ENTR"] {
        ws.send(Message::Text(format!(r#"{{"type":"key","key":"{key}"}}"#).into()))
            .await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(300)).await;
    }

    // Collect r1 (hours), r2 (minutes), r3 (seconds*100) readings for ~4 s;
    // the centiseconds register must change => the clock is running.
    let mut r3_values = std::collections::HashSet::new();
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(4);
    while tokio::time::Instant::now() < deadline {
        let Ok(Some(Ok(Message::Text(t)))) = tokio::time::timeout(
            std::time::Duration::from_millis(500), ws.next()).await else { continue };
        let v: serde_json::Value = serde_json::from_str(&t).unwrap();
        if v["type"] == "dsky_state" && v["verb"] == "16" && v["noun"] == "36" {
            r3_values.insert(v["r3"].as_str().unwrap().to_string());
        }
    }
    child.kill().await.ok();
    assert!(r3_values.len() >= 2,
        "expected V16N36 R3 (seconds) to tick, got {r3_values:?}");
}
```

```bash
cd /home/kazumasa/projects/eagle/runtime && cargo test -p eagle-runtime -- --ignored --test-threads=1 v16n36
```
Expected: PASS. (`cargo test` without `--ignored` must also still pass.)

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime
git commit -m "feat(eagle): WebSocket server streaming DSKY state; V16N36 clock e2e test"
```

---

### Task 10: JSONL trace + golden V35E regression

**Files:**
- Create: `eagle/runtime/apps/eagle-runtime/src/trace.rs` (replace stub), `eagle/runtime/apps/eagle-runtime/tests/golden_v35e.rs`
- Modify: `eagle/runtime/apps/eagle-runtime/Cargo.toml` (add `serde = { workspace = true }` to `[dev-dependencies]`)
- Committed after recording: `eagle/tests/golden-agc/v35e.golden.json`

**Interfaces:**
- Consumes: `AgcSession`, `DskyKey`, `Packet`, `DskyState`, `to_msg`, `DskyStateMsg`.
- Produces:
  - `TraceWriter::open(path: Option<PathBuf>) -> anyhow::Result<TraceWriter>`, `TraceWriter::log(&mut self, dir: &str, p: &Packet)` — JSONL lines `{"t_ms": <u128 since open>, "dir": "in"|"out", "kind": "io"|"counter"|"bitmask", "channel": "015", "data": "00031"}` (octal, zero-padded).
  - `milestones(packets: &[Packet]) -> Vec<(String, String)>` — filter to ch `0o10` words whose decoded digits are non-blank, dedupe consecutive duplicates, return `(channel, data)` octal strings.
  - Golden file `v35e.golden.json` = `{ "milestones": [...], "final_state": <DskyStateMsg JSON> }`; the capture flushes boot traffic **before** keying (flushing after keying would race the AGC's immediate response to ENTR) and verifies both the milestone sequence and the final DSKY state (displays + lamps).

- [ ] **Step 1: Write failing unit test for milestone filtering** (in `trace.rs`)

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use eagle_agc_protocol::Packet;

    #[test]
    fn milestones_filters_and_dedupes() {
        let blank = Packet::io(0o10, 11 << 11).unwrap();
        let v88 = Packet::io(0o10, (10 << 11) | (0b11101 << 5) | 0b11101).unwrap();
        let lamp = Packet::io(0o11, 0b10).unwrap();
        let got = milestones(&[blank, v88, v88, lamp]);
        assert_eq!(got, vec![("010".to_string(), format!("{:05o}", v88.data))]);
    }
}
```

- [ ] **Step 2: Verify failure, implement `trace.rs`**

Run `cargo test -p eagle-runtime milestones` → COMPILE ERROR. Implement:

```rust
use anyhow::Result;
use eagle_agc_protocol::{dsky, Packet, PacketKind};
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

pub struct TraceWriter {
    file: Option<std::fs::File>,
    t0: Instant,
}

impl TraceWriter {
    pub fn open(path: Option<PathBuf>) -> Result<Self> {
        let file = match path {
            Some(p) => {
                if let Some(dir) = p.parent() { std::fs::create_dir_all(dir)?; }
                Some(std::fs::File::create(p)?)
            }
            None => None,
        };
        Ok(Self { file, t0: Instant::now() })
    }

    pub fn log(&mut self, dir: &str, p: &Packet) {
        let Some(f) = self.file.as_mut() else { return };
        let kind = match p.kind {
            PacketKind::Io => "io", PacketKind::Counter => "counter",
            PacketKind::Bitmask => "bitmask",
        };
        let _ = writeln!(
            f,
            r#"{{"t_ms":{},"dir":"{}","kind":"{}","channel":"{:03o}","data":"{:05o}"}}"#,
            self.t0.elapsed().as_millis(), dir, kind, p.channel, p.data
        );
    }
}

/// Golden-comparison view of an output stream: ch 010 relay words that carry
/// at least one non-blank digit, deduped consecutively. Event-order only —
/// no timestamps (the process backend is not bit-exact).
pub fn milestones(packets: &[Packet]) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut state = dsky::DskyState::default();
    for p in packets {
        if p.channel != 0o10 { continue; }
        let visible = state.apply(p);
        let c = (p.data >> 5) & 0x1F;
        let d = p.data & 0x1F;
        if !visible || (c == 0 && d == 0) { continue; }
        let entry = (format!("{:03o}", p.channel), format!("{:05o}", p.data));
        if out.last() != Some(&entry) { out.push(entry); }
    }
    out
}
```
Run `cargo test -p eagle-runtime milestones` → PASS. Then wire the real
`TraceWriter` into `main.rs` (remove the Task 9 stub if it was stubbed) and
confirm `cargo build` succeeds.

- [ ] **Step 3: Write the golden test with record mode** (`tests/golden_v35e.rs`)

```rust
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::{keys::DskyKey, Packet};
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::to_msg;
use eagle_runtime::trace::milestones;
use eagle_schema::{DskyStateMsg, ServerMsg};
use std::path::PathBuf;

fn root() -> PathBuf { PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..") }

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Debug)]
struct GoldenV35e {
    milestones: Vec<(String, String)>,
    final_state: DskyStateMsg,
}

async fn run_v35e() -> GoldenV35e {
    let mut s = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19900,
    }).await.unwrap();
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;

    // Flush boot-time traffic so the capture starts at the keying point.
    // (Flushing AFTER keying would race the AGC's immediate response to ENTR.)
    while let Ok(Some(_)) = tokio::time::timeout(
        std::time::Duration::from_millis(100), s.events().recv()).await {}

    let mut packets: Vec<Packet> = Vec::new();
    for k in [DskyKey::Verb, DskyKey::D3, DskyKey::D5, DskyKey::Entr] {
        s.send(k.packet()).unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    }
    // Capture 3 s only: the V35 lamp test auto-reverts after ~5 s, and the
    // final-state check must land inside the all-8s window deterministically.
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(3);
    while tokio::time::Instant::now() < deadline {
        if let Ok(Some(p)) = tokio::time::timeout(
            std::time::Duration::from_millis(500), s.events().recv()).await {
            packets.push(p);
        }
    }
    s.shutdown();

    let mut state = DskyState::default();
    for p in &packets { state.apply(p); }
    let ServerMsg::DskyState(final_state) = to_msg(&state);
    GoldenV35e { milestones: milestones(&packets), final_state }
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn golden_v35e_milestones_and_final_state() {
    let golden_path = root().join("tests/golden-agc/v35e.golden.json");
    let got = run_v35e().await;
    assert!(!got.milestones.is_empty(), "no display milestones captured");
    // Sanity even in record mode: mid-lamp-test the displays must be all 8s.
    assert_eq!(got.final_state.verb, "88");
    assert_eq!(got.final_state.noun, "88");
    assert_eq!(got.final_state.prog, "88");
    if std::env::var("GOLDEN_RECORD").is_ok() {
        std::fs::write(&golden_path,
            serde_json::to_string_pretty(&got).unwrap()).unwrap();
        eprintln!("recorded golden to {golden_path:?}");
        return;
    }
    let want: GoldenV35e = serde_json::from_str(
        &std::fs::read_to_string(&golden_path)
            .expect("golden file missing — run with GOLDEN_RECORD=1 first"),
    ).unwrap();
    assert_eq!(got.milestones, want.milestones, "V35E display sequence diverged");
    assert_eq!(got.final_state, want.final_state,
        "final DSKY state (displays/lamps) diverged from golden");
}
```

- [ ] **Step 4: Record golden, then verify replay determinism**

```bash
cd /home/kazumasa/projects/eagle/runtime
GOLDEN_RECORD=1 cargo test -p eagle-runtime -- --ignored --test-threads=1 golden_v35e
cargo test -p eagle-runtime -- --ignored --test-threads=1 golden_v35e
cargo test -p eagle-runtime -- --ignored --test-threads=1 golden_v35e
```
Expected: record run writes the file; two verify runs PASS (stable
event-order and identical final state). If flaky, loosen `milestones` (e.g.
also dedupe non-consecutive repeats) — do **not** loosen the final-state
check — and document the decision in the test comment and channel map doc.

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/runtime eagle/tests/golden-agc/v35e.golden.json
git commit -m "test(eagle): JSONL AGC trace and golden V35E regression (event order + final state)"
```

---

### Task 11: Web DSKY client (Vite + React + TS)

**Files:**
- Create: `eagle/client/` (Vite scaffold), `eagle/client/src/dsky/types.ts`, `eagle/client/src/dsky/reducer.ts`, `eagle/client/src/dsky/useDskySocket.ts`, `eagle/client/src/dsky/Dsky.tsx`, `eagle/client/src/dsky/dsky.css`, `eagle/client/src/dsky/reducer.test.ts`
- Modify: `eagle/client/src/App.tsx`

**Interfaces:**
- Consumes: WebSocket JSON from Task 9 (`dsky_state` / `key` / `pro` messages), `ws://127.0.0.1:8642/ws`.
- Produces: browser DSKY at `http://localhost:5173` (vite default).

- [ ] **Step 1: Scaffold**

```bash
cd /home/kazumasa/projects/eagle
npm create vite@latest client -- --template react-ts
cd client && npm install && npm install -D vitest
```
Add to `client/package.json` scripts: `"test": "vitest run"`.

- [ ] **Step 2: Write failing reducer test** (`src/dsky/reducer.test.ts`)

```ts
import { describe, expect, it } from "vitest";
import { initialDsky, reduceServerMsg } from "./reducer";

describe("reduceServerMsg", () => {
  it("applies a dsky_state message", () => {
    const msg = {
      type: "dsky_state", schema_version: 1,
      prog: "63", verb: "16", noun: "36",
      r1: "+00031", r2: "      ", r3: "      ",
      lamps: { comp_acty: true },
      verb_noun_flash: true, restart: false, standby: false,
      key_rel: false, opr_err: false, temp: false,
    };
    const s = reduceServerMsg(initialDsky, msg as never);
    expect(s.verb).toBe("16");
    expect(s.r1).toBe("+00031");
    expect(s.lamps.comp_acty).toBe(true);
    expect(s.verbNounFlash).toBe(true);
  });

  it("ignores unknown message types", () => {
    const s = reduceServerMsg(initialDsky, { type: "bogus" } as never);
    expect(s).toBe(initialDsky);
  });
});
```
Run: `cd client && npm test` → FAIL (module missing).

- [ ] **Step 3: Implement types + reducer**

`src/dsky/types.ts`:
```ts
export interface DskyStateMsg {
  type: "dsky_state";
  schema_version: number;
  prog: string; verb: string; noun: string;
  r1: string; r2: string; r3: string;
  lamps: Record<string, boolean>;
  verb_noun_flash: boolean; restart: boolean; standby: boolean;
  key_rel: boolean; opr_err: boolean; temp: boolean;
}
export type ServerMsg = DskyStateMsg | { type: string };

export interface DskyView {
  prog: string; verb: string; noun: string;
  r1: string; r2: string; r3: string;
  lamps: Record<string, boolean>;
  verbNounFlash: boolean; restart: boolean; standby: boolean;
  keyRel: boolean; oprErr: boolean; temp: boolean;
  connected: boolean;
}
```

`src/dsky/reducer.ts`:
```ts
import type { DskyView, ServerMsg, DskyStateMsg } from "./types";

export const initialDsky: DskyView = {
  prog: "  ", verb: "  ", noun: "  ",
  r1: "      ", r2: "      ", r3: "      ",
  lamps: {}, verbNounFlash: false, restart: false, standby: false,
  keyRel: false, oprErr: false, temp: false, connected: false,
};

export function reduceServerMsg(state: DskyView, msg: ServerMsg): DskyView {
  if (msg.type !== "dsky_state") return state;
  const m = msg as DskyStateMsg;
  return {
    ...state,
    prog: m.prog, verb: m.verb, noun: m.noun,
    r1: m.r1, r2: m.r2, r3: m.r3,
    lamps: m.lamps,
    verbNounFlash: m.verb_noun_flash, restart: m.restart, standby: m.standby,
    keyRel: m.key_rel, oprErr: m.opr_err, temp: m.temp,
  };
}
```
Run: `npm test` → PASS.

- [ ] **Step 4: Implement socket hook and component**

`src/dsky/useDskySocket.ts`:
```ts
import { useEffect, useRef, useState } from "react";
import { initialDsky, reduceServerMsg } from "./reducer";
import type { DskyView } from "./types";

const WS_URL = "ws://127.0.0.1:8642/ws";

export function useDskySocket(): [DskyView, (key: string) => void, (pressed: boolean) => void] {
  const [state, setState] = useState<DskyView>(initialDsky);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    const connect = () => {
      const sock = new WebSocket(WS_URL);
      ws.current = sock;
      sock.onopen = () => setState((s) => ({ ...s, connected: true }));
      sock.onmessage = (ev) =>
        setState((s) => reduceServerMsg(s, JSON.parse(ev.data)));
      sock.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (!closed) setTimeout(connect, 1000);
      };
    };
    connect();
    return () => { closed = true; ws.current?.close(); };
  }, []);

  const sendKey = (key: string) =>
    ws.current?.send(JSON.stringify({ type: "key", key }));
  const sendPro = (pressed: boolean) =>
    ws.current?.send(JSON.stringify({ type: "pro", pressed }));
  return [state, sendKey, sendPro];
}
```

`src/dsky/Dsky.tsx`:
```tsx
import { useDskySocket } from "./useDskySocket";
import "./dsky.css";

const KEYS: [label: string, name: string][] = [
  ["VERB", "VERB"], ["NOUN", "NOUN"], ["+", "PLUS"], ["-", "MINUS"],
  ["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"],
  ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"], ["9", "9"],
  ["CLR", "CLR"], ["PRO", "PRO"], ["KEY REL", "KEY_REL"],
  ["ENTR", "ENTR"], ["RSET", "RSET"],
];

const LAMPS: [label: string, key: string][] = [
  ["UPLINK ACTY", "uplink_acty"], ["NO ATT", "no_att"], ["TEMP", "__temp"],
  ["GIMBAL LOCK", "gimbal_lock"], ["PROG", "prog"], ["TRACKER", "tracker"],
  ["ALT", "alt"], ["VEL", "vel"], ["STBY", "__standby"],
  ["KEY REL", "__key_rel"], ["OPR ERR", "__opr_err"], ["RESTART", "__restart"],
];

export function Dsky() {
  const [s, sendKey, sendPro] = useDskySocket();
  const lampOn = (key: string) =>
    key === "__temp" ? s.temp : key === "__standby" ? s.standby :
    key === "__key_rel" ? s.keyRel : key === "__opr_err" ? s.oprErr :
    key === "__restart" ? s.restart : !!s.lamps[key];

  return (
    <div className="dsky">
      <div className="dsky-status">{s.connected ? "CONNECTED" : "NO LINK"}</div>
      <div className="dsky-lamps">
        {LAMPS.map(([label, key]) => (
          <div key={label} className={`lamp ${lampOn(key) ? "on" : ""}`}>{label}</div>
        ))}
      </div>
      <div className="dsky-display">
        <div className="disp-cell"><label>PROG</label><span>{s.prog}</span></div>
        <div className={`disp-cell ${s.verbNounFlash ? "flash" : ""}`}>
          <label>VERB</label><span>{s.verb}</span>
        </div>
        <div className={`disp-cell ${s.verbNounFlash ? "flash" : ""}`}>
          <label>NOUN</label><span>{s.noun}</span>
        </div>
        <div className="disp-reg">{s.r1}</div>
        <div className="disp-reg">{s.r2}</div>
        <div className="disp-reg">{s.r3}</div>
      </div>
      <div className="dsky-keys">
        {KEYS.map(([label, name]) =>
          name === "PRO" ? (
            <button key={name} className="key"
              onMouseDown={() => sendPro(true)} onMouseUp={() => sendPro(false)}>
              {label}
            </button>
          ) : (
            <button key={name} className="key" onClick={() => sendKey(name)}>
              {label}
            </button>
          ))}
      </div>
    </div>
  );
}
```

`src/dsky/dsky.css` (documentary style: dark panel, green EL digits — keep
to ~60 lines):
```css
.dsky { background: #1a1a1c; color: #ddd; padding: 1.5rem; width: 420px;
  font-family: "Segoe UI", sans-serif; border-radius: 8px; }
.dsky-status { font-size: 0.7rem; color: #888; margin-bottom: 0.5rem; }
.dsky-lamps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;
  margin-bottom: 1rem; }
.lamp { background: #2a2a2c; color: #555; font-size: 0.6rem; padding: 6px 4px;
  text-align: center; border-radius: 2px; }
.lamp.on { background: #c9a227; color: #111; }
.dsky-display { background: #0a0f0a; padding: 0.8rem; border-radius: 4px;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  font-family: "Courier New", monospace; }
.disp-cell label { display: block; font-size: 0.55rem; color: #4a7; }
.disp-cell span, .disp-reg { color: #39ff6a; font-size: 1.6rem;
  letter-spacing: 0.2em; white-space: pre; }
.disp-reg { grid-column: 1 / -1; text-align: right; }
.disp-cell.flash span { animation: dsky-flash 1.28s step-start infinite; }
@keyframes dsky-flash { 50% { opacity: 0; } }
.dsky-keys { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px;
  margin-top: 1rem; }
.key { background: #333; color: #eee; border: 1px solid #555; padding: 10px 4px;
  font-size: 0.7rem; border-radius: 4px; cursor: pointer; }
.key:active { background: #555; }
```

`src/App.tsx`: render `<Dsky />` centered on a dark page; remove Vite demo
content.

- [ ] **Step 5: Verify tests and build**

```bash
cd /home/kazumasa/projects/eagle/client && npm test && npm run build
```
Expected: vitest PASS, `tsc`/vite build clean.

- [ ] **Step 6: Commit**

```bash
cd /home/kazumasa/projects
git add eagle/client
git commit -m "feat(eagle): web DSKY client (display, lamps, keypad, ws hook)"
```

---

### Task 12: Wire-up, docs, and Phase 1 acceptance

**Files:**
- Modify: `eagle/Makefile` (test targets), `eagle/README.md`, `eagle/docs/agc-channel-map.md`
- Create: `eagle/CLAUDE.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `make test` (cargo unit + vitest), `make test-integration`, documented dev workflow.

- [ ] **Step 1: Extend Makefile**

Replace the `test` target and add client test:
```make
test:
	cd runtime && cargo test
	cd client && npm test
```

- [ ] **Step 2: Write `eagle/CLAUDE.md`**

```markdown
# eagle — Apollo 11 lunar descent simulator (Phase 1)

Original Luminary099 running in vendored yaAGC, bridged to a web DSKY.

- Spec: docs/superpowers/specs/2026-07-21-eagle-roadmap-design.md
- Channel semantics: docs/agc-channel-map.md (octal; update with citations)
- Build AGC artifacts once: `make agc` (fetches vendor, builds yaYUL/yaAGC,
  assembles Luminary099, verifies hashes)
- Fast tests: `make test` (no AGC needed)
- Live AGC tests: `make test-integration`
- Run: `make dev-runtime` + `make dev-client`, open http://localhost:5173
- vendor/ is read-only and git-ignored; pins in vendor/manifest.json
```

- [ ] **Step 3: Update README quickstart + channel-map completeness pass**

README: quickstart with the three commands and a screenshot placeholder
removed (no screenshot yet — text only). Channel map doc: confirm it now
covers packet layout, ch 010 rows + digit codes, ch 011, ch 013 (note: only
STBY-related bits used so far), ch 015 keycodes, ch 032 bit 14, ch 0163, each
with a source citation (developer.html URL or vendor file path).

- [ ] **Step 4: Full acceptance run (Phase 1 definition of done)**

```bash
cd /home/kazumasa/projects/eagle
make test               # cargo unit + vitest: PASS
make test-integration   # live AGC (serial): boots, V35E, V16N36 clock, golden: PASS
```
**Both commands passing together is the Phase 1 DoD** (spec §7); neither
alone is sufficient.
Manual check (two terminals): `make dev-runtime`, `make dev-client`, open
`http://localhost:5173`:
1. Key **V35E** → all displays show `88`, lamps light for ~5 s.
2. Key **V16N36E** → R1/R2/R3 show mission time, R3 counting.
3. Kill and restart `make dev-client` (browser reload) → state reappears
   (server pushes snapshot on connect).
Record the result of each check in the final report.

- [ ] **Step 5: Final commit**

```bash
cd /home/kazumasa/projects
git add eagle/Makefile eagle/README.md eagle/CLAUDE.md eagle/docs/agc-channel-map.md
git commit -m "docs(eagle): phase 1 wiring, acceptance checklist, channel map"
```

---

## Self-review notes

- **Spec coverage:** Phase 0 DoD (Task 3), Phase 1 DoD (Tasks 8–9, acceptance
  in Task 12), golden traces (Task 10), channel-map doc (Tasks 5/7/8/12),
  octal convention + event-order comparison (Global Constraints) — all spec
  requirements for Phase 0–1 are covered. Phase 2+ items (dynamics, sensors,
  scenario) are intentionally absent per the roadmap.
- **Known uncertainty, by design:** ch 010 row-12 lamp bit positions and
  ch 0163 bit numbering are verified against vendored sources in Task 7
  Step 0 before the tests lock them in; vendor source wins over this plan's
  tables. Task 2 is a build spike with documented fallbacks and the
  three-attempt stop rule.
- **Type consistency check:** `Packet`/`StreamDecoder` (T5) used by T6/T8/T10;
  `DskyState::apply` (T7) used by T8/T9/T10; `DskyKey::from_name`/`packet`
  (T8) used by T9; `ServerMsg`/`ClientMsg` JSON shapes (T9) match the client
  reducer/test fixtures (T11). `TraceWriter` signature stubbed in T9 matches
  the real T10 implementation.
