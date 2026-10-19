from sector_leadlag.g1 import run_g1


def test_rotated_worlds_lose_the_lead_and_a_planted_one_is_found(decayed_world):
    prior = {"g0": {"selected": "lagged", "variants": {"lagged": {"fit_a": {"beta_1e4": 20.0}}}}}
    out = run_g1(decayed_world, prior, count=3)
    assert out["count"] == 3 and len(out["worlds"]) == 3
    assert out["significant"] <= 1 and out["pass"]
    assert out["detected"] == 3 and out["planted_beta_1e4"] == 10.0
    assert all(world["shift"] >= 60 for world in out["worlds"])
