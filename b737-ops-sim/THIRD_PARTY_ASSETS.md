# Third-Party Asset Registry

Every imported asset MUST be recorded here **before** use (spec §8).
Originals are NOT committed to git — they are re-fetched reproducibly by
`pnpm assets:fetch` from a pinned upstream commit; this registry plus the
fetch script and the downloaded `assets/imported/737-800YV/manifest.json`
(per-file SHA-256) are the provenance record. The upstream LICENSE file is
downloaded alongside the assets and preserved.

## 737-800YV (FlightGear aircraft)

| Field | Value |
|---|---|
| Source | https://github.com/YV3399/737-800YV |
| Pinned commit | `9d967d89dd2ee0ae1bf01d00c49839a574aa9da5` (master @ 2026-08-02) |
| License | **GPL-2.0** (upstream `LICENSE` fetched to `assets/imported/737-800YV/LICENSE`) |
| Fetch tool | `scripts/fetch-cockpit-assets.mjs` (pinned SHA, per-file sha256 manifest) |
| Usage basis | Local personal use, not distributed; GPL obligations respected by preserving license/attribution and recording provenance |

### Imported file groups

| Group | Original paths | Conversion | Modifications |
|---|---|---|---|
| Cockpit models | `Models/cockpit.ac`, `Models/flightdesk.ac`, `Models/pedestal.ac`, `Models/pedals.ac`, `Models/yoke/yoke.ac`, `Models/Overhead/Overhead.ac`, `Models/OH-panel/OH-panel.ac`, `Models/Instruments/autopilot-panel.ac`, `Models/seats/cockpitseat*.ac` | AC3D → glTF 2.0 via `packages/asset-pipeline` (`pnpm assets:build`) into `assets/generated/webroot/cockpit/` | Frame change AC3D→FG `(x,−z,y)`; triangulation; smooth/flat normal generation; materials → PBR-lite; mesh/object names preserved verbatim |
| Model XMLs | `Models/*.xml` (cockpit, flightdesk, pedestal, pedals, yoke, Overhead, autopilot-panel, seats) | Parsed by the pipeline into `cockpit-bindings.json` (assembly offsets + rotate/translate animation specs) | Extraction only; not redistributed as XML |
| Textures | PNGs referenced by the above `.ac` files (resolved from `Models/`, `Models/Instruments/`, `Models/Overhead/`, `Models/OH-panel/`) | Copied with content-hash prefixes to `assets/generated/webroot/cockpit/textures/` | None (byte-identical copies) |
| Sounds | `Sounds/click.wav`, `flaps.wav`, `gear.wav`, `Wind.wav`, `altAlert.wav`, `Apdisco.wav`, `approaching-minimums.wav`, `Sounds/FL2070/cfm1[1-4][ab].wav` (CFM56 loops), `Sounds/gpws/altitude-*.wav` | Copied to `assets/generated/webroot/cockpit/sounds/` | None (byte-identical copies) |

### Known upstream defects (tolerated)

`OH-PANEL.png`, `apugen*.png`, `genbus*.png` are referenced by
`OH-panel.ac` but do not exist anywhere in the upstream repository — the
affected overhead sub-panels render untextured (FlightGear silently does the
same). Recorded in the fetch manifest under `missingOptional`.

## Not imported

Instrument display models (`Models/Instruments/PFD`, `ND`, `EICAS`, …) are
intentionally not imported in Phase 2 — the 2D instrument row remains the
live display (see docs/milestones/MILESTONE_02.md D6).
