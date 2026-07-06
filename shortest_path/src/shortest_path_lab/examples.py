"""Reusable example grids for notebooks and the static HTML demo."""

from __future__ import annotations

from .algorithms import (
    SearchResult,
    a_star,
    bidirectional_a_star,
    bidirectional_dijkstra,
    dijkstra,
)
from .grid import GridNode, GridProblem

ALGORITHM_LABELS = {
    "dijkstra": "Dijkstra",
    "a_star": "A*",
    "bidirectional_dijkstra": "Bidirectional Dijkstra",
    "bidirectional_a_star": "Bidirectional A*",
}


def make_demo_problem() -> GridProblem:
    return _make_city_map_problem()


def _make_city_map_problem() -> GridProblem:
    width = 49
    height = 31
    start = (10, 23)
    goal = (40, 7)
    open_nodes: set[GridNode] = set()

    for y in (3, 7, 11, 15, 19, 23, 27):
        open_nodes.update((x, y) for x in range(1, width - 1))
    for x in (4, 10, 16, 22, 28, 34, 40, 46):
        open_nodes.update((x, y) for y in range(1, height - 1))

    open_nodes.update((x, 5) for x in range(10, 41))
    open_nodes.update((x, 13) for x in range(4, 29))
    open_nodes.update((x, 21) for x in range(22, 47))
    open_nodes.update((13, y) for y in range(7, 24))
    open_nodes.update((19, y) for y in range(3, 16))
    open_nodes.update((31, y) for y in range(15, 28))
    open_nodes.update((37, y) for y in range(5, 22))

    closures: set[GridNode] = set()
    closures.update((x, 15) for x in range(5, 10))
    closures.update((x, 11) for x in range(29, 34))
    closures.update((22, y) for y in range(4, 7))
    closures.update((34, y) for y in range(24, 27))
    closures.update((x, 23) for x in range(41, 46))
    closures.update((16, y) for y in range(20, 23))
    closures.update((28, y) for y in range(8, 11))
    open_nodes.difference_update(closures)

    blocked = {(x, y) for y in range(height) for x in range(width) if (x, y) not in open_nodes}

    weights: dict[GridNode, float] = {}
    for node in open_nodes:
        if node not in (start, goal):
            weights[node] = 2.0 + ((node[0] * 17 + node[1] * 31) % 4)

    preferred_route = [
        *((10, y) for y in range(23, 12, -1)),
        *((x, 13) for x in range(10, 20)),
        *((19, y) for y in range(13, 4, -1)),
        *((x, 5) for x in range(19, 38)),
        *((37, y) for y in range(5, 8)),
        *((x, 7) for x in range(37, 41)),
    ]
    for node in preferred_route:
        if node in weights:
            weights[node] = 1.0

    for x in range(22, 41):
        if (x, 11) in weights:
            weights[(x, 11)] = 7.0
    for y in range(7, 24):
        if (22, y) in weights:
            weights[(22, y)] = 8.0
    for x in range(4, 35):
        if (x, 19) in weights:
            weights[(x, 19)] = 6.0
    for y in range(7, 28):
        if (28, y) in weights:
            weights[(28, y)] = 6.0

    return GridProblem(
        width=width,
        height=height,
        start=start,
        goal=goal,
        blocked=frozenset(blocked),
        weights=weights,
    )


def solve_demo_problem(problem: GridProblem | None = None) -> dict[str, SearchResult]:
    problem = make_demo_problem() if problem is None else problem
    return {
        "dijkstra": dijkstra(problem.neighbors, problem.start, problem.goal),
        "a_star": a_star(problem.neighbors, problem.start, problem.goal, problem.heuristic),
        "bidirectional_dijkstra": bidirectional_dijkstra(
            problem.neighbors,
            problem.start,
            problem.goal,
            reverse_neighbors=problem.reverse_neighbors,
        ),
        "bidirectional_a_star": bidirectional_a_star(
            problem.neighbors,
            problem.start,
            problem.goal,
            problem.heuristic,
            reverse_neighbors=problem.reverse_neighbors,
        ),
    }
