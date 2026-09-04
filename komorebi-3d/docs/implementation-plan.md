# Komorebi 3D Implementation Plan

**Goal:** Promote the existing cafe scene into a local Blender and Unreal project.

**Architecture:** Keep Blender source and exports together. Prepare a separate,
non-overwriting Windows copy of a content-only Unreal project. Import the GLB
through the editor's Interchange API and save a new inspection map.

**Tech Stack:** Blender 5.2.1, Python standard library, Unreal Engine 5.8 (target).

**Spec:** design.md

## Constraints

- No new production packages, remote writes, commits, or asset downloads.
- Preserve the original conversation assets and all existing working copies.
- No claim of Unreal validation without executing Unreal Editor.

## Execution in this task

- [x] Adopt existing Blender assets and make output paths project-relative.
- [x] Test copying to a new path and refusing existing or incomplete destinations.
- [x] Implement the copy helper, UE descriptor, import script and Windows launcher.
- [x] Prepare the actual Windows working copy and validate copied data.
- [x] Run tests, Python/PowerShell syntax checks and Blender data inspection.
- [x] Document the engine installation and remaining runtime verification.

Unreal import and visual verification remain pending engine installation, as
recorded in validation.md. No Unreal runtime success is claimed.
