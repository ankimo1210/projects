# Milestone 2 — Definition of Done verification

Verified 2026-08-02 (same environment as M1). Evidence: automated tests +
in-session screenshots + numeric probes recorded in the session log.
Re-verified after the review remediation (`docs/REVIEW_RESPONSE.md`); rows 1, 3
and 7 were corrected in that pass.

| #   | Requirement (MILESTONE_02.md)                                                                                     | Status | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | ----------------------------------------------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `pnpm assets:build` fetches + converts from a clean checkout, idempotently                                        | ✅     | 94 unique files / 22.7 MB @ pinned SHA `9d967d89`; a second run skips only after re-verifying every recorded sha256; fetch stages into a temp tree and swaps atomically; the converter regenerates its output directory from scratch (R-21)                                                                                                                                                                                                     |
| 2   | 3D view shows the imported 737 cockpit from the captain seat, improved lighting                                   | ✅     | Screenshot: glareshield, MIP with readable (non-mirrored) lettering, windshield frames, overhead, gear panel; interior point light added                                                                                                                                                                                                                                                                                                        |
| 3   | Throttle/flaps/speed brake/gear/parking brake/autobrake clickable-draggable in 3D, meshes move with backend state | ✅     | e2e: 3D gear-lever click → backend rejection round-trip, plus an assertion that every mesh in the control registry exists in the scene and is pickable (four registry entries pointed at names absent from the model until R-13/R-21 cleanup); probes: flap pivot 17°→33.5° (flaps 5→15), throttle pivot 42°→11° at 60 %, park-brake pivot 45°→0° on release. Only controls inside the default captain view can be pointer-tested by projection |
| 4   | MCP + throttle quadrant visible as real 3D geometry                                                               | ✅     | `autopilot-panel.gltf` (81 meshes) assembled via flightdesk offsets; quadrant levers in pedestal (`quadone`… pivots)                                                                                                                                                                                                                                                                                                                            |
| 5   | Real (GPL, attributed) sounds play when assets present; synth fallback otherwise                                  | ✅     | `/cockpit/sounds/*` served (HTTP 200); audio engine crossfades CFM56 loops by N1, GPWS altitude callouts wired to FO RA events; fallback path exercised by the no-assets e2e run                                                                                                                                                                                                                                                                |
| 6   | THIRD_PARTY_ASSETS.md lists every imported file group with SHA, license, path, modifications                      | ✅     | Registry rewritten; upstream LICENSE preserved; known upstream-missing textures documented                                                                                                                                                                                                                                                                                                                                                      |
| 7   | All tests green; new pipeline unit tests; e2e passes with AND without generated assets                            | ✅     | 136 unit/integration tests + e2e 3/3 with assets, 2 passed + 1 skipped without assets (the earlier "93" was never measured; `pnpm test` itself was red until R-02)                                                                                                                                                                                                                                                                              |

## Notable engineering facts (for future sessions)

- `.ac` vertex data is AC3D-native **y-up**; FG model XML offsets/animations
  are **z-up**. The converter normalizes with the proper rotation
  `(x,−z,y)` — using a y/z swap instead mirrors all panel lettering.
- The Babylon glTF importer's root transform is compensated at runtime
  (`W = L⁻¹·D` in `cockpitLoader.ts`) rather than assumed.
- A `ResizeObserver` keeps the engine backing store in sync with canvas CSS
  size — without it, pointer picking coordinates drift after layout changes.
- FG animation `<center>` values are model-local; rotation about a lateral
  axis is insensitive to the center's lateral component.
- Model `<offsets>` rotations are applied as roll (+x), then pitch (+y), then
  heading (+z) in the FG frame and conjugated into the loader's content frame
  (`L⁻¹ R L`) — see `apps/web/src/sim3d/fgFrame.ts`. Dropping them left the
  flightdesk and the overhead panel flat (R-11).
