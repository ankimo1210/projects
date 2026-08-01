"""The scaffold is wired: the package imports and declares a version."""

import stats_textbook


def test_package_imports_and_has_version():
    assert isinstance(stats_textbook.__version__, str)
    assert stats_textbook.__version__.count(".") == 2
