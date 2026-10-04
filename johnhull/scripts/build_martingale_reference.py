"""Independent finite-GBM martingale arithmetic, no hullkit import."""

import argparse
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-3/reference.json"


def mean(x, mf, mg, sf, sg, h):
    a = math.fsum([mf, -mg, sg * sg, -sf * sg])
    return x * math.exp(a * h)


def build():
    cases = []
    for sf, sg in ((0.3, 0.15), (-0.3, 0.15), (0.3, -0.2), (-0.3, -0.2), (-0.3, 0), (0.2, 0.2)):
        mf, mg = 0.04 + sg * sf, 0.04 + sg * sg
        a = math.fsum([mf, -mg, sg * sg, -sf * sg])
        b = sf - sg
        cases.append(
            dict(
                r=0.04,
                s_f=sf,
                s_g=sg,
                mu_f=mf,
                mu_g=mg,
                drift=a,
                log_drift=a - 0.5 * b * b,
                mean=mean(1.5, mf, mg, sf, sg, 1.75),
                wrong_drift=sg * sg - sf * sg,
                wrong_mean=mean(1.5, 0.04, 0.04, sf, sg, 1.75),
                second_moment=2.25 * math.exp((2 * a + b * b) * 1.75),
            )
        )
    conditional = []
    for t in (0, 0.3, 0.7):
        for x in (0.5, 1.25, 2):
            h = 1.5 - t
            conditional.append(
                dict(
                    t=t,
                    T=1.5,
                    value=x,
                    horizon=h,
                    mean=x,
                    second_moment=x * x * math.exp(0.15**2 * h),
                    mu_f=0.085,
                    mu_g=0.0625,
                    s_f=0.3,
                    s_g=0.15,
                )
            )
    S, K, G, r, sf, T = 100, 100, 80, 0.04, 0.3, 1.5
    d1 = (math.log(S / K) + (r + 0.5 * sf * sf) * T) / (sf * math.sqrt(T))
    d2 = d1 - sf * math.sqrt(T)

    def cdf(x):
        return 0.5 * math.erfc(-x / math.sqrt(2))

    price = S * cdf(d1) - K * math.exp(-r * T) * cdf(d2)
    pricing = [dict(S=S, K=K, G=G, r=r, s_f=sf, s_g=sg, T=T, price=price) for sg in (0.15, -0.15)]
    horizons = [0, 0.25, 0.5, 0.75, 1, 1.5, 2]
    curves = []
    for lam in (-0.2, 0, -0.4):
        curves.append(
            dict(
                risk_price=lam,
                mean=[
                    mean(1.25, 0.04 + lam * 0.3, 0.04 + lam * (-0.2), 0.3, -0.2, h)
                    for h in horizons
                ],
            )
        )
    return dict(
        section="28.3",
        synthetic=True,
        printed_pins=[],
        cases=cases,
        conditional=conditional,
        conditional_note="t=0 values .5 and2 are separate initial markets; one fixed S0=100/G0=80 has only1.25",
        pricing=pricing,
        integrability="Finite horizon constant GBM moments finite; positive G and no income. H/G<=S/G, not necessarily<=1.",
        figure=dict(
            ito=dict(labels=["μf−μg", "s_g²", "−s_f s_g", "a"], values=[-0.1, 0.04, 0.06, 0]),
            conditional=dict(horizons=horizons, curves=curves),
            conditional_mc=dict(
                labels=[f"t={v['t']}, x={v['value']}" for v in conditional],
                values=[v["mean"] for v in conditional],
            ),
            pricing=dict(
                labels=[
                    f"{measure}, sg={sg:+.2f}" for sg in (0.15, -0.15) for measure in ("Q", "G")
                ],
                reference=[price] * 4,
            ),
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("martingale reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload)
    print("PASS: §28.3 independent signed GBM, nine conditional states and same call payoff")


if __name__ == "__main__":
    main()
