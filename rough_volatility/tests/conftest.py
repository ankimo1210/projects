"""Shared pytest configuration for the rough_volatility test suite.

The ``slow`` marker is registered here via ``pytest_configure`` so that it is
valid both in project-scoped runs (rootdir = rough_volatility, config from the
member pyproject) and in workspace-root runs (rootdir = the uv workspace,
whose ``--strict-markers`` addopts would otherwise reject unknown markers).
"""


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "slow: long stochastic integration tests")
