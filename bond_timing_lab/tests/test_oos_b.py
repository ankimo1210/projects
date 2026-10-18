from bond_timing import evaluate as ev
from bond_timing.oos_b import build_evidence

NAMES = ["P1", "P2", "P3", "P4", "P5"]


def inputs():
    oos_a = {
        "instruments": {
            "tlt": {
                "tests": {
                    "vs_hold": {k: {"p_holm": 0.01 if k == "P4" else 0.5} for k in NAMES},
                    "vs_p1": {k: {"p_holm": 0.02} for k in ("P4", "P5")},
                },
                "robust": {
                    k: {
                        "vs_hold_4bp": 0.01,
                        "vs_hold_delay": 0.01,
                        "vs_p1_4bp": 0.01,
                        "vs_p1_delay": 0.01,
                    }
                    for k in NAMES
                },
            }
        }
    }
    g3 = {"p": {"P4": 0.01, "P5": 0.5}}
    oos_b = {k: {"vs_hold": 0.001, "vs_p1": 0.001} for k in NAMES}
    return oos_a, g3, oos_b


def test_build_evidence_feeds_the_verdict():
    oos_a, g3, oos_b = inputs()
    evidence = build_evidence(oos_a, g3, oos_b)
    assert evidence["P4"].g3_p == 0.01 and evidence["P1"].p_vs_p1 is None
    assert ev.verdict(evidence) == "ml_signal_usable"
    oos_b["P4"]["vs_p1"] = -0.001
    assert ev.verdict(build_evidence(oos_a, g3, oos_b)) == "no_usable_signal"


def test_a_delay_loss_breaks_robustness():
    oos_a, g3, oos_b = inputs()
    oos_a["instruments"]["tlt"]["robust"]["P4"]["vs_hold_delay"] = -0.001
    assert not build_evidence(oos_a, g3, oos_b)["P4"].robust_vs_hold
