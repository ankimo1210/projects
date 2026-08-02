# Asset Pipeline

The Phase-2 pipeline is **fully scripted** (spec §8: no undocumented manual
steps, no Blender dependency) and runs with one command:

```bash
pnpm assets:build      # = assets:fetch + convert
```

```
GitHub YV3399/737-800YV @ pinned SHA           scripts/fetch-cockpit-assets.mjs
    → assets/imported/737-800YV/               (originals + LICENSE + manifest.json)
        → packages/asset-pipeline (AC3D parser → glTF writer,
                                   FG-XML animation/assembly extractor)
            → assets/generated/webroot/cockpit/   *.gltf / *.bin / textures/ / sounds/
                                                  + cockpit-bindings.json
                → served by Vite publicDir → Babylon.js at runtime
```

Both asset directories are **gitignored** (re-fetchable, provenance in
THIRD_PARTY_ASSETS.md + the manifest). The app falls back to the Milestone-1
temporary geometry when `assets/generated/webroot` is absent.

## Stage 1 — fetch (`scripts/fetch-cockpit-assets.mjs`)

- Pinned to one upstream commit; `--force` re-downloads.
- Skipping is earned, not assumed: an existing manifest is only trusted after
  every recorded sha256 is re-verified against the files on disk.
- Downloads into `assets/imported/737-800YV.staging` and swaps the directory in
  only when the run succeeds, so a failed or partial fetch leaves no residue.
- Fails (and discards the staging tree) when a required sound is unavailable
  upstream — a silent build is worse than a loud failure.
- Downloads models (.ac), the FG model XMLs, LICENSE and selected GPL sounds.
- Parses each `.ac` for `texture "…"` references and fetches them with
  fallback directories (`Models/`, `Models/Instruments/`, `Models/Overhead/`,
  `Models/OH-panel/`); genuinely missing upstream textures are recorded.
- Writes `manifest.json` (full per-file sha256, sizes, missing list). Files
  resolved through a fallback directory are not reported as missing.

## Stage 2 — convert (`packages/asset-pipeline`)

1. **Parse** AC3D (`src/ac3d.ts`): materials, object tree, `loc`/`rot`,
   per-surface UVs, SURF flags. Unit-tested against a golden mini model.
2. **Frame change** (`toFgFrame`): AC3D native (x aft, y up, z toward viewer)
   → FlightGear model frame (x aft, y lateral, z up) via the proper rotation
   `(x, y, z)_fg = (x, −z, y)_ac`. After this, vertex data and the XML
   offsets/animation axes share one frame. (Empirically verified against the
   in-sim geometry; a reflection here would mirror panel lettering.)
3. **glTF write** (`src/gltf.ts`): fan triangulation, Newell face normals,
   smooth normals for `shaded` surfaces / flat otherwise (crease angle is
   approximated by this split), UV v-flip + `texrep`, PBR-lite materials
   (baseColor/emissive/alpha from AC3D material, double-sided), object names
   preserved verbatim on nodes/meshes — the control registry binds by name.
   Textures are copied with a content-hash prefix (same basename can differ
   between directories upstream).
4. **Bindings extraction** (`src/extractBindings.ts`): walks
   `Models/cockpit.xml` includes (both file-relative and aircraft-root
   relative paths), collecting
   - assembly instances: which `.ac` renders where (offset chains), and
   - rotate/translate animation specs (objects, axis, center, factor,
     interpolation table, FG property) for the whitelisted properties
     (throttle, reversers, flaps, speed brake, gear lever, parking brake,
     autobrake, yoke elevator/aileron).
     Output: `cockpit-bindings.json`.
5. **Sounds**: fetched `.wav` files are flattened into `sounds/`.

Stage 2 removes its output directory first, and copies only the sounds the
audio engine actually loads (an allowlist), so the generated tree never depends
on leftovers from an earlier asset set.

## Stage 3 — runtime (apps/web)

- `src/sim3d/cockpitLoader.ts` loads each instance's glTF, builds the offset
  chains, and computes the wrapper transform at runtime as `W = L⁻¹·D`
  (L = the glTF importer's own root transform, D = FG→aircraft mapping), so
  the code does not depend on Babylon's internal handedness convention.
- Animation specs get pivot nodes inserted at the FG-declared centers;
  values come from **backend state** every frame (spec §7).
- Interactive meshes bind through `packages/cockpit-model` `meshNames`
  (hover outline + tooltip, click/drag → typed commands).
- Audio uses the real samples when present, synthesized fallback otherwise.

## Verifying / regenerating

```bash
pnpm --filter @b737/asset-pipeline test    # parser/writer/extractor units
pnpm assets:build                          # idempotent; --force via assets:fetch
pnpm test:e2e                              # includes a 3D pick round-trip test
```

## Directory contract

```
assets/imported/    fetched originals + LICENSE + manifest (gitignored, re-fetchable)
assets/generated/   converted outputs (gitignored, rebuildable)
assets/references/  free-license reference images only (committed)
private/            NEVER committed — personal materials
```
