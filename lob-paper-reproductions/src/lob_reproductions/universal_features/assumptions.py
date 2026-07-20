ASSUMPTIONS = {
    "SC2019-A001": "reset hidden state at stock/day boundary",
    "SC2019-A002": "use the fixture's explicit eight-feature state vector",
    "SC2019-A003": "SGD learning rate 0.01 and L2 coefficient 1e-5",
    "SC2019-A004": "independent truncated windows by default; carry-detach is an alternate mode",
    "SC2019-A005": "current PyTorch default initialization",
    "SC2019-A006": "fixed smoke epochs rather than an undisclosed stopping rule",
    "SC2019-A007": "uniform pooled-asset sampling",
}


def serialized_assumptions() -> list[dict[str, str]]:
    return [{"id": key, "choice": value} for key, value in sorted(ASSUMPTIONS.items())]
