import pytest


def test_event_does_not_double_count_occupants():
    from basic_design.operations import rest_demand

    assert rest_demand(20, 17, 24, 40)["shortfall"] == 13
    assert rest_demand(20, 20, 24, 40)["shortfall"] == 16
    with pytest.raises(ValueError):
        rest_demand(20, 21, 24, 40)


def test_queue_retains_peak_that_average_rate_hides():
    from basic_design.operations import simulate_pool

    burst = simulate_pool([0] * 20, 5, 60)
    assert burst["max_wait_s"] == 180
    assert burst["queued_people"] == 15
    assert burst["max_waiting_count"] == 15
    spaced = simulate_pool(list(range(0, 20 * 15, 15)), 5, 60)
    assert spaced["max_wait_s"] == 0


def test_pool_exit_cannot_occur_before_entry():
    from basic_design.operations import simulate_pool

    with pytest.raises(ValueError):
        simulate_pool([0, -1], 5, 60)
