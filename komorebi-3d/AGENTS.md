# Komorebi 3D agent guide

Read README.md first. Keep changes within this project.

- Blender authors geometry; Unreal Editor imports and renders a local working copy.
- The source Blender script is executed by Blender's embedded Python, not workspace Python.
- Unreal Python is editor-only. Do not claim gameplay functionality from editor scripts.
- Never replace a user's existing Windows working copy or imported Unreal assets.
- Generated Blender/GLB/PNG and Unreal binaries are ignored by Git; retain them locally.
- Run the stdlib tests and syntax checks. Actual Unreal validation requires Unreal Editor.
- A Blender render or mocked unreal module is not evidence of Unreal compatibility.
- Do not install paid plugins, download marketplace assets, publish, or commit without approval.
