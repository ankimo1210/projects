"""Illustrative queue and rest demand; times are not bathing recommendations."""

import heapq


def rest_demand(event, others, seats, total_limit):
    if min(event, others, seats, total_limit) < 0 or event + others > total_limit:
        raise ValueError("Occupants must be nonnegative and not double counted")
    return {"demand": event + others, "seats": seats, "shortfall": max(0, event + others - seats)}


def simulate_pool(arrivals_s, positions, occupancy_s):
    if positions < 1 or occupancy_s <= 0 or any(t < 0 for t in arrivals_s):
        raise ValueError("Positive capacity/time and nonnegative arrivals required")
    servers = [0.0] * positions
    heapq.heapify(servers)
    customers = []
    for arrival in sorted(arrivals_s):
        start = max(arrival, heapq.heappop(servers))
        finish = start + occupancy_s
        customers.append(
            {"arrival_s": arrival, "start_s": start, "finish_s": finish, "wait_s": start - arrival}
        )
        heapq.heappush(servers, finish)
    events = []
    for c in customers:
        if c["wait_s"] > 1e-9:
            events.extend([(c["arrival_s"], 1), (c["start_s"], -1)])
    waiting = peak = 0
    for _, delta in sorted(events):
        waiting += delta
        peak = max(peak, waiting)
    waits = [c["wait_s"] for c in customers]
    return {
        "positions": positions,
        "occupancy_s": occupancy_s,
        "queued_people": sum(w > 1e-9 for w in waits),
        "max_wait_s": max(waits, default=0),
        "max_waiting_count": peak,
        "customers": customers,
    }


def normal_cycle():
    return [
        (3, 10),
        (6.4, 9.8),
        (12.23, 9.45),
        (12.23, 8.40),
        (12.23, 9.45),
        (6.532, 9.45),
        (6.532, 7.756),
        (6.0, 7.55),
        (5.36, 6.55),
    ]
