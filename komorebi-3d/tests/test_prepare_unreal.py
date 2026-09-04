"""Exercise real filesystem boundaries; Unreal runtime is verified separately."""

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "prepare_unreal.py"


def valid_glb():
    payload = json.dumps({"asset": {"version": "2.0"}, "meshes": [{}]}).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<4sIIII", b"glTF", 2, 20 + len(payload), len(payload), 0x4E4F534A) + payload


class PrepareProjectTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "The safe project preparation command is missing")
        spec = importlib.util.spec_from_file_location("prepare_unreal", MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "unreal" / "Content" / "Python").mkdir(parents=True)
        (self.source / "unreal" / "Komorebi3D.uproject").write_text('{"FileVersion":3}')
        (self.source / "unreal" / "Content" / "Python" / "bootstrap_scene.py").write_text("pass\n")
        (self.source / "assets" / "export").mkdir(parents=True)
        (self.source / "assets" / "export" / "komorebi.glb").write_bytes(valid_glb())
        self.destination = self.root / "Unreal Projects" / "喫茶店"

    def test_new_copy_includes_scene_bytes_and_editor_script(self):
        self.module.prepare_project(self.source, self.destination)
        self.assertEqual(
            (self.destination / "SourceAssets" / "komorebi.glb").read_bytes(), valid_glb()
        )
        self.assertEqual(
            (self.destination / "Content" / "Python" / "bootstrap_scene.py").read_text(), "pass\n"
        )
        self.assertTrue((self.source / "assets" / "export" / "komorebi.glb").is_file())

    def test_existing_destination_is_preserved(self):
        self.destination.mkdir(parents=True)
        saved = self.destination / "user-edited.umap"
        saved.write_bytes(b"user work")
        with self.assertRaises(FileExistsError):
            self.module.prepare_project(self.source, self.destination)
        self.assertEqual(saved.read_bytes(), b"user work")
        self.assertEqual(list(self.destination.iterdir()), [saved])

    def test_missing_scene_creates_no_partial_destination(self):
        (self.source / "assets" / "export" / "komorebi.glb").unlink()
        with self.assertRaises(FileNotFoundError):
            self.module.prepare_project(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_corrupt_glb_creates_no_partial_destination(self):
        (self.source / "assets" / "export" / "komorebi.glb").write_bytes(b"truncated")
        with self.assertRaises(ValueError):
            self.module.prepare_project(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_refuses_destination_inside_source(self):
        with self.assertRaises(ValueError):
            self.module.prepare_project(self.source, self.source / "unreal" / "nested")
        self.assertFalse((self.source / "unreal" / "nested").exists())


if __name__ == "__main__":
    unittest.main()
