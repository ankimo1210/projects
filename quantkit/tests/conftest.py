"""Test fixtures. Network is never required: connectors are tested by feeding raw
fixtures to ``normalize``/``to_observations`` or by subclassing with a fake
``_download``. The data cache is redirected to a tmp dir.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _tmp_data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("quantkit_data")
    os.environ["QUANTKIT_DATA_DIR"] = str(d)
    yield
