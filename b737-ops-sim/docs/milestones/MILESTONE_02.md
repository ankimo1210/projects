# Milestone 2 — Asset Integration (spec §22 Phase 2)

> **Goal:** replace the temporary cockpit geometry with a real open-source
> 737 cockpit model through a fully scripted, reproducible pipeline; map
> interactive cockpit meshes to the control registry; improve lighting; add
> legally reusable real cockpit sounds.

**Status:** Complete (2026-08-02) — see MILESTONE_02_DOD.md

## Spike findings (P2-T0, verified 2026-08-02)

| Question               | Answer                                                                                                                                                                                                                                                           |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source aircraft        | **`YV3399/737-800YV`** (GitHub, GPL-2.0, FlightGear 737-800)                                                                                                                                                                                                     |
| Cockpit assets         | `Models/cockpit.ac` (914 objects), `Models/flightdesk.*` (main panel), `Models/pedestal.ac` (203 objects incl. throttle quadrant), `Models/yoke/yoke.ac`, `Models/OH-panel/OH-panel.ac`, `Models/Instruments/autopilot-panel.ac` (MCP) + referenced PNG textures |
| Interactive mesh names | From `cockpit.xml` (110 animation blocks): throttle `quadone/boxone/no1thrarm` (+2), reversers `no*revarm`, flaps `flaparm/handle`, speed brake `sbhandle/sbarm`, gear lever `lghandle`, `autobrake`, `parkbrake_*`                                              |
| Animation authority    | FG model XMLs define rotate/pick with exact axis+center per object → extract to JSON instead of hand-tuning                                                                                                                                                      |
| Sounds                 | Repo `Sounds/*.wav` (GPL): CFM56 loops (`FL2070/cfm1*.wav`), callouts etc.                                                                                                                                                                                       |
| Conversion tool        | **Custom Node AC3D→glTF converter** (AC3D is a simple text format). No Blender dependency ⇒ fully scripted + unit-testable, satisfying spec §8 "no undocumented manual steps"                                                                                    |

## Key decisions

| #   | Decision                                                                                                                                           | Rationale                                                                         |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| D1  | Pin the source to a specific commit SHA in the fetch script                                                                                        | Reproducibility + provenance in THIRD_PARTY_ASSETS.md                             |
| D2  | Originals under `assets/imported/737-800YV/` (with LICENSE); converted output under `assets/generated/webroot/cockpit/` served by Vite `publicDir` | Spec §8 directory contract; regeneration never touches originals                  |
| D3  | Emit `.gltf` + `.bin` + copied textures (not GLB)                                                                                                  | Simpler writer; textures stay inspectable files                                   |
| D4  | The web app keeps the M1 temporary shell as **fallback** when converted assets are absent                                                          | Tests/e2e stay green offline; graceful degradation                                |
| D5  | GPL-2.0 assets are recorded, licenses preserved; acceptable because the app is local-only and not distributed                                      | Spec §8                                                                           |
| D6  | 3D display units (DU screens) remain textured (non-live) in M2                                                                                     | Live 3D PFD texture is Phase 3+ polish; 2D instruments remain the primary display |

## Tasks

- [x] P2-T0 Spike: locate assets, verify licenses, choose conversion route
- [x] P2-T1 `scripts/fetch-cockpit-assets.mjs`: pinned-SHA downloads (models, textures, XMLs, LICENSE, selected sounds) + THIRD_PARTY_ASSETS.md entries
- [x] P2-T2 `packages/asset-pipeline`: AC3D parser (materials/hierarchy/UV/`loc`), triangulation, normal generation, glTF writer preserving object names + unit tests
- [x] P2-T3 Animation/pick extractor: FG XML → `cockpit-bindings.json` (mesh, type, axis, center, factor/interpolation, FG property) + FG-property→AircraftState mapping table
- [x] P2-T4 Babylon: load converted cockpit, align captain camera, improved lighting, mesh picking → registry commands (hover cursor/tooltip/guided pulse), levers/handles follow backend state
- [x] P2-T5 Sample-based audio (engine loops + switch clicks where available) with synth fallback
- [x] P2-T6 Full verification (tests with/without assets, screenshots) + docs updates + DoD record

## Definition of Done (M2)

1. `pnpm assets:build` (documented) fetches + converts everything from a clean checkout, idempotently.
2. The 3D view shows the imported 737 cockpit from the captain seat (screenshot evidence), with improved lighting.
3. At least throttle, flaps, speed brake, gear lever, parking brake and autobrake are clickable/draggable **in the 3D cockpit** and their meshes move with backend state (no independent UI state).
4. MCP + throttle quadrant visible as real 3D geometry.
5. Real (GPL, attributed) engine sound loops play when assets are present; synth fallback otherwise.
6. THIRD_PARTY_ASSETS.md lists every imported file group with source SHA, license, path and modifications.
7. All existing tests remain green; new pipeline units tests pass; e2e passes both with and without generated assets.
