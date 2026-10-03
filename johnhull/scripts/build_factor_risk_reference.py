"""Independent factor arithmetic and local portfolios, with no hullkit imports."""

import argparse
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-2/reference.json"


def dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b, strict=True))


def build():
    lam = [0.2, -0.1, 0.4]
    loading = [0.05, 0.1, 0.15]
    pins = dict(
        example_28_3_excess=dot(lam, loading),
        contributions=[a * b for a, b in zip(lam, loading, strict=True)],
    )
    cases = []
    for r in (-0.02, 0.04):
        for price_scale in (-1, 0, 1):
            for loading_scale in (-1, 1):
                prices = [price_scale * x for x in lam]
                signed = [loading_scale * x for x in loading]
                excess = dot(prices, signed)
                cases.append(
                    dict(
                        r=r,
                        risk_prices=prices,
                        loadings=signed,
                        contributions=[a * b for a, b in zip(prices, signed, strict=True)],
                        excess=excess,
                        mu=r + excess,
                    )
                )
    weights = [0.25, 0.25, 0.5]
    matrix = [[0.2, 0], [0, 0.2], [-0.1, -0.1]]
    h_lam = [0.3, -0.2]
    rate = 0.04
    means = [rate + dot(h_lam, row) for row in matrix]
    hedge = dict(
        weights=weights,
        loadings=matrix,
        risk_prices=h_lam,
        r=rate,
        mu=means,
        portfolio_loading=[dot(weights, [row[i] for row in matrix]) for i in range(2)],
        portfolio_return=dot(weights, means),
        risk=[[w * row[i] for w, row in zip(weights, matrix, strict=True)] for i in range(2)],
        returns=[w * mu for w, mu in zip(weights, means, strict=True)],
    )
    rotations = []
    for angle in (0, math.pi / 6, math.pi / 2, math.pi):
        c, s = math.cos(angle), math.sin(angle)
        q = [[c, -s], [s, c]]
        lp = [dot(row, h_lam) for row in q]
        sp = [dot(row, [0.2, 0.1]) for row in q]
        rotations.append(
            dict(
                angle=angle,
                matrix=q,
                risk_prices=lp,
                loadings=sp,
                excess=dot(lp, sp),
                volatility=math.sqrt(dot(sp, sp)),
            )
        )
    xs = [-0.3 + i * 0.01 for i in range(61)]
    loading_figure = dict(
        loading=xs,
        r=0.04,
        risk_prices=[-0.1, 0.1],
        returns=[[0.04 + 0.2 * 0.05 + 0.4 * 0.15 + price * x for x in xs] for price in (-0.1, 0.1)],
    )
    correlations = [-1 + i * 0.1 for i in range(21)]
    capm = dict(
        correlation=correlations,
        market_vol=0.2,
        market_risk_price=0.3,
        loadings=[[0.2 * rho, 0.2 * math.sqrt(max(0, 1 - rho * rho))] for rho in correlations],
        excess=[0.06 * rho for rho in correlations],
        assumption="CAPM holds; orthogonal market and unpriced idiosyncratic Brownian factors",
    )
    return dict(
        section="28.2",
        source="Hull 11e GE pp.674–675",
        assumptions="Signed loadings and risk prices use the same risk basis; linear-algebra demos use independent Brownian factors",
        printed_pins=pins,
        synthetic_r=0.04,
        synthetic_total_return=0.04 + pins["example_28_3_excess"],
        zero_price_extension=dict(
            risk_prices=[*lam, 0],
            loadings=[*loading, 0.8],
            excess=dot([*lam, 0], [*loading, 0.8]),
            with_priced_extra=dot([*lam, 0.3], [*loading, 0.8]),
        ),
        cases=cases,
        hedge=hedge,
        rotations=rotations,
        capm=capm,
        figure=dict(
            contributions=dict(
                labels=["石油", "金", "株価指数", "合計"],
                values=[*pins["contributions"], pins["example_28_3_excess"]],
            ),
            loading=loading_figure,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("factor risk reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload)
    print("PASS: §28.2 independent excess-return pins, twelve markets, local hedge and four bases")


if __name__ == "__main__":
    main()
