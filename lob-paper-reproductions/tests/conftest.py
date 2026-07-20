from __future__ import annotations

import numpy as np
import pytest
import torch


@pytest.fixture(autouse=True)
def deterministic_test_state() -> None:
    """Keep CPU golden tests repeatable and inexpensive."""

    torch.manual_seed(7)
    np.random.seed(7)


@pytest.fixture(scope="session", autouse=True)
def single_cpu_thread() -> None:
    torch.set_num_threads(1)
