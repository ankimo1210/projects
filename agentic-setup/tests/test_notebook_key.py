"""Only execute notebook key configuration and the offline API probe."""

import ast
import contextlib
import io
import json
import os
import types
import unittest
from pathlib import Path
from unittest.mock import patch

NOTEBOOK = (
    Path(__file__).resolve().parents[2] / "notebooks/real_estate/real_estate_data_collection.ipynb"
)


class NotebookKeyTests(unittest.TestCase):
    def assignment(self):
        data = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        for cell in data["cells"]:
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "REINFOLIB_API_KEY"
                    for target in node.targets
                ):
                    return node
        self.fail("API-key configuration assignment not found")

    def evaluate_key(self, environment):
        node = self.assignment()
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        namespace = {"os": os}
        with patch.dict(os.environ, environment, clear=True):
            exec(compile(module, "<key-configuration>", "exec"), namespace)
        return namespace["REINFOLIB_API_KEY"]

    def test_key_comes_from_environment_without_exposing_old_literal(self):
        key = self.evaluate_key({"REINFOLIB_API_KEY": "unit-test-reinfolib"})
        self.assertTrue(
            key == "unit-test-reinfolib",
            "Notebook must read the environment; old value is redacted",
        )

    def test_missing_key_is_empty_instead_of_falling_back_to_old_literal(self):
        key = self.evaluate_key({})
        self.assertTrue(key == "", "Missing key must not reuse the old value")

    def test_probe_does_not_make_a_request_without_a_key(self):
        data = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        probe = next(
            "".join(cell["source"])
            for cell in data["cells"]
            if cell.get("cell_type") == "code" and "_resp_test" in "".join(cell.get("source", []))
        )
        calls = []
        response = types.SimpleNamespace(
            status_code=200, text="unit test", json=lambda: {"data": []}
        )

        def get(*args, **kwargs):
            calls.append(True)
            return response

        namespace = {
            "REINFOLIB_API_KEY": "",
            "LAND_PRICE_API_URL": "https://example.invalid",
            "LAND_PRICE_AREA_CODE": "test",
            "requests": types.SimpleNamespace(get=get),
        }
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(probe, "<api-probe>", "exec"), namespace)
        self.assertEqual(calls, [], "Unset credentials must not trigger a request")


if __name__ == "__main__":
    unittest.main()
