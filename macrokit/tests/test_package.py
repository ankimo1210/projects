"""The package must be importable under its own name.

The workspace runs one pytest over every member. Because this project's
directory name equals its package name, pytest 9 will synthesize a namespace
module for `macrokit` and shadow the real package unless the root conftest
imports it first. This test fails loudly if that regresses.
"""

import macrokit


def test_package_exposes_a_version():
    assert isinstance(macrokit.__version__, str)
    assert macrokit.__version__


def test_package_is_the_real_one_not_a_namespace_shadow():
    # A namespace shadow has no __file__; the installed package does.
    assert macrokit.__file__ is not None
    assert macrokit.__file__.endswith("src/macrokit/__init__.py")
