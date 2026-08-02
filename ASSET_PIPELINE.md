# Asset Pipeline (Phase 2)

Milestone 1 uses **only original temporary geometry and synthesized audio** —
nothing is imported yet, so `THIRD_PARTY_ASSETS.md` is an empty registry.
This document defines the pipeline that Phase 2 must follow when importing
FlightGear 737 cockpit assets.

## Pipeline

```
FlightGear aircraft package (AC3D .ac + textures + XML)
    → Blender import (io_scene_ac3d or converted via osgconv/assimp)
    → cleanup (see checklist)
    → glTF 2.0 / GLB export
    → Babylon.js loadAssetContainer
```

## Rules (spec §8)

- Preserve original license files and attribution; never strip copyright.
- Record EVERY imported asset in `THIRD_PARTY_ASSETS.md`
  (source URL, license, original path, conversion steps, modifications).
- GPL-licensed FlightGear assets stay acceptable because this project is
  local-only and not distributed; still record them.
- Private Boeing/airline materials live under `private/` (gitignored) and
  are never committed or converted into repo assets.
- Manual Blender exploration is fine, but the final conversion MUST be a
  scripted, reproducible process (`scripts/convert-cockpit.py`, to be written
  in Phase 2 as a Blender headless script: `blender -b -P scripts/convert-cockpit.py -- <in> <out>`).

## Conversion checklist (to encode in the script)

1. **Coordinate systems:** AC3D/FlightGear models are typically +X aft,
   +Y right? (verify per model; FG uses +X aft, +Y right, +Z up for aircraft
   models) → glTF is +Y up, -Z forward → Babylon default is left-handed
   +Z forward. Apply one explicit conversion matrix; never eyeball rotations.
2. **Scale:** meters everywhere; normalize any non-metric source scale.
3. **Origin/pivot:** re-origin so the captain eye reference point matches the
   camera rig defined in `apps/web/src/sim3d/scene.ts`.
4. **Materials:** convert to PBR-lite (baseColor + emissive for lit
   annunciators); repair texture paths to relative `assets/imported/...`.
5. **Mesh naming:** rename interactive meshes to the `meshNames` ids declared
   in `packages/cockpit-model` (e.g. `flap_lever`, `gear_lever`) so the
   control registry binds without code changes.
6. **Animation mapping:** export lever/switch animations as named glTF
   animations keyed 0..1 matching the control's normalized state.
7. **LODs:** optional; only if frame rate requires it.

## Directory contract

```
assets/imported/    converted, license-recorded assets (committed)
assets/generated/   outputs of scripts (rebuildable, committed if small)
assets/references/  free-license reference images only
private/            NEVER committed (gitignored) — personal materials
```
