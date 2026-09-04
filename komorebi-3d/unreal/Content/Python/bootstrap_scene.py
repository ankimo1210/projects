"""Build a NEW inspection map inside Unreal Editor; never replace user assets.

Target: UE 5.8. This script must be validated in an installed Unreal Editor.
Python is used only for editor setup, not runtime gameplay.
"""

import hashlib
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "SourceAssets" / "komorebi.glb"
MAP = "/Game/Maps/Komorebi_Dusk"
DESTINATION = "/Game/Komorebi/Imported"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def inspect_bounds(actors):
    """Measure imported mesh bounds in Unreal centimetres, without helper actors."""
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    count = 0
    for actor in actors:
        if not actor.get_components_by_class(unreal.StaticMeshComponent):
            continue
        origin, extent = actor.get_actor_bounds(False)
        for i, axis in enumerate(("x", "y", "z")):
            minimum[i] = min(minimum[i], getattr(origin, axis) - getattr(extent, axis))
            maximum[i] = max(maximum[i], getattr(origin, axis) + getattr(extent, axis))
        count += 1
    require(count > 0, "Interchange created no actors containing static meshes")
    span = max(high - low for high, low in zip(maximum, minimum, strict=True))
    require(200 < span < 2000, f"Unexpected scene size: {span:.1f} cm; inspect import units")
    center = unreal.Vector(*[(low + high) / 2 for low, high in zip(minimum, maximum, strict=True)])
    return center, span, count


def main():
    require(SOURCE.is_file(), f"Missing GLB source: {SOURCE}")
    require(
        not unreal.EditorAssetLibrary.does_asset_exist(MAP),
        "Map already exists; refusing to overwrite it",
    )
    require(
        not unreal.EditorAssetLibrary.does_directory_exist(DESTINATION),
        "Imported content already exists; use a fresh working copy",
    )
    require(
        not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
        "Save your currently edited maps before running this script",
    )
    require(
        not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
        "Save your currently edited assets before running this script",
    )
    require(hasattr(unreal, "InterchangeManager"), "Enable the built-in Interchange plugins first")

    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    source_data = unreal.InterchangeManager.create_source_data(str(SOURCE))
    require(
        manager.can_translate_source_data(source_data, True),
        "The installed Interchange translator cannot import this GLB as a scene",
    )

    # The map stays unsaved until imports and unit checks have succeeded.
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    require(world is not None, "Could not create a blank editor world")
    parameters = unreal.ImportAssetParameters()
    parameters.is_automated = True
    parameters.replace_existing = False
    require(
        manager.import_scene(DESTINATION, source_data, parameters),
        "Interchange scene import failed",
    )

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    center, span, mesh_actor_count = inspect_bounds(actor_subsystem.get_all_level_actors())

    def spawn(actor_class, label, position, rotation=unreal.Rotator()):
        actor = actor_subsystem.spawn_actor_from_class(actor_class, position, rotation)
        require(actor is not None, f"Could not create {label}")
        actor.set_actor_label(label)
        return actor

    spawn(unreal.SkyAtmosphere, "Komorebi atmosphere", unreal.Vector())
    sun = spawn(unreal.DirectionalLight, "Komorebi dusk sun", center, unreal.Rotator(-25, -40, 0))
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3.0)
    sun.light_component.set_light_color(unreal.LinearColor(1.0, 0.68, 0.4, 1.0))
    sun.light_component.set_editor_property("atmosphere_sun_light", True)
    sky = spawn(unreal.SkyLight, "Komorebi skylight", center)
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)

    # glTF does not carry Blender AREA lights. Add an Unreal-native fill light.
    fill_position = center + unreal.Vector(span * 0.45, -span * 0.6, span * 0.9)
    fill_rotation = unreal.MathLibrary.find_look_at_rotation(fill_position, center)
    fill = spawn(unreal.RectLight, "Komorebi soft fill", fill_position, fill_rotation)
    fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill.light_component.set_intensity(2500.0)
    fill.light_component.set_editor_property("source_width", span * 0.6)
    fill.light_component.set_editor_property("source_height", span * 0.6)
    fill.light_component.set_light_color(unreal.LinearColor(0.65, 0.78, 1.0, 1.0))

    camera_position = center + unreal.Vector(span * 1.0, -span * 1.45, span * 0.9)
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_position, center)
    camera = spawn(
        unreal.CameraActor, "Komorebi inspection camera", camera_position, camera_rotation
    )
    camera.camera_component.set_field_of_view(40.0)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        camera_position, camera_rotation
    )

    require(
        unreal.EditorAssetLibrary.save_directory(
            DESTINATION, only_if_is_dirty=False, recursive=True
        ),
        "Could not save imported assets",
    )
    require(
        unreal.EditorLoadingAndSavingUtils.save_map(world, MAP), "Could not save the inspection map"
    )
    result = {
        "engine": unreal.SystemLibrary.get_engine_version(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "map": MAP,
        "mesh_actors": mesh_actor_count,
        "scene_span_cm": span,
        "status": "imported_and_saved",
        "visual_check": "pending",
    }
    saved = ROOT / "Saved"
    saved.mkdir(exist_ok=True)
    (saved / "komorebi_import.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    unreal.log("KOMOREBI_IMPORT_COMPLETE " + json.dumps(result))


if __name__ == "__main__":
    main()
