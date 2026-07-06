from __future__ import annotations

from itertools import pairwise
from math import isinf
from random import Random

import pytest
from shortest_path_lab.algorithms import (
    Edge,
    a_star,
    bidirectional_a_star,
    bidirectional_dijkstra,
    dijkstra,
)
from shortest_path_lab.examples import make_demo_problem, solve_demo_problem
from shortest_path_lab.grid import GridProblem
from shortest_path_lab.visualization import demo_payload


def path_cost(problem: GridProblem, path: tuple[tuple[int, int], ...]) -> float:
    return sum(problem.cell_cost(node) for node in path[1:])


def assert_valid_path(problem: GridProblem, path: tuple[tuple[int, int], ...]) -> None:
    assert path[0] == problem.start
    assert path[-1] == problem.goal
    for left, right in pairwise(path):
        assert abs(left[0] - right[0]) + abs(left[1] - right[1]) == 1
        assert problem.passable(right)


def passable_neighbors(problem: GridProblem, node: tuple[int, int]) -> set[tuple[int, int]]:
    x, y = node
    return {
        candidate
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))
        if problem.in_bounds(candidate) and problem.passable(candidate)
    }


def assert_road_continues_through(problem: GridProblem, node: tuple[int, int]) -> None:
    x, y = node
    neighbors = passable_neighbors(problem, node)
    assert len(neighbors) >= 3
    assert ((x - 1, y) in neighbors and (x + 1, y) in neighbors) or (
        (x, y - 1) in neighbors and (x, y + 1) in neighbors
    )


def assert_single_corridor(problem: GridProblem, path: tuple[tuple[int, int], ...]) -> None:
    path_nodes = set(path)
    assert {node for node in problem.cells() if problem.passable(node)} == path_nodes

    for index, node in enumerate(path):
        expected_degree = 1 if index in (0, len(path) - 1) else 2
        assert len(passable_neighbors(problem, node)) == expected_degree


def count_shortest_paths(problem: GridProblem, distances: dict[tuple[int, int], float]) -> int:
    counts = {problem.start: 1}
    reachable = [node for node in problem.cells() if node in distances]
    reachable.sort(key=lambda node: distances[node])

    for node in reachable:
        if node not in counts:
            continue
        for edge in problem.neighbors(node):
            if edge.target not in distances:
                continue
            if abs(distances[node] + edge.cost - distances[edge.target]) < 1e-9:
                counts[edge.target] = min(2, counts.get(edge.target, 0) + counts[node])

    return counts.get(problem.goal, 0)


def test_all_algorithms_find_same_demo_cost() -> None:
    problem = make_demo_problem()
    results = solve_demo_problem(problem)
    expected_cost = results["dijkstra"].cost
    expected_path = results["dijkstra"].path

    assert len(expected_path) >= 45
    assert count_shortest_paths(problem, results["dijkstra"].distances_forward) == 1
    assert sum(1 for node in problem.cells() if problem.passable(node)) >= 500
    assert (
        sum(
            1
            for node in problem.cells()
            if problem.passable(node) and len(passable_neighbors(problem, node)) >= 3
        )
        >= 60
    )
    assert_road_continues_through(problem, problem.start)
    assert_road_continues_through(problem, problem.goal)

    for result in results.values():
        assert result.path == expected_path
        assert result.cost == pytest.approx(expected_cost)
        assert_valid_path(problem, result.path)
        assert path_cost(problem, result.path) == pytest.approx(result.cost)
        assert result.steps


def test_a_star_expands_no_more_than_dijkstra_on_demo_grid() -> None:
    problem = make_demo_problem()
    results = solve_demo_problem(problem)

    assert len(results["a_star"].expanded_forward) <= len(results["dijkstra"].expanded_forward)


def test_bidirectional_a_star_balanced_potentials_reduce_demo_search() -> None:
    problem = make_demo_problem()
    results = solve_demo_problem(problem)

    assert len(results["bidirectional_a_star"].steps) < len(results["a_star"].steps)
    assert len(results["bidirectional_a_star"].steps) < len(results["bidirectional_dijkstra"].steps)


def test_weighted_random_grids_match_dijkstra() -> None:
    rng = Random(20260707)

    for width in range(2, 7):
        for height in range(2, 7):
            cells = [(x, y) for y in range(height) for x in range(width)]
            for _ in range(12):
                start, goal = rng.sample(cells, 2)
                blocked = {
                    cell for cell in cells if cell not in (start, goal) and rng.random() < 0.22
                }
                weights = {
                    cell: rng.choice((1.5, 2.0, 3.0, 5.0, 8.0))
                    for cell in cells
                    if cell not in blocked and cell not in (start, goal) and rng.random() < 0.20
                }
                problem = GridProblem(width, height, start, goal, frozenset(blocked), weights)
                reference = dijkstra(problem.neighbors, problem.start, problem.goal)

                for result in (
                    a_star(problem.neighbors, problem.start, problem.goal, problem.heuristic),
                    bidirectional_dijkstra(
                        problem.neighbors,
                        problem.start,
                        problem.goal,
                        reverse_neighbors=problem.reverse_neighbors,
                    ),
                    bidirectional_a_star(
                        problem.neighbors,
                        problem.start,
                        problem.goal,
                        problem.heuristic,
                        reverse_neighbors=problem.reverse_neighbors,
                    ),
                ):
                    if isinf(reference.cost):
                        assert result.path == ()
                        assert isinf(result.cost)
                    else:
                        assert result.cost == pytest.approx(reference.cost)
                        assert_valid_path(problem, result.path)
                        assert path_cost(problem, result.path) == pytest.approx(result.cost)


def test_weighted_grid_prefers_lower_total_cost_over_fewer_steps() -> None:
    problem = GridProblem(
        width=5,
        height=3,
        start=(0, 1),
        goal=(4, 1),
        weights={(1, 1): 10.0, (2, 1): 10.0, (3, 1): 10.0},
    )

    result = dijkstra(problem.neighbors, problem.start, problem.goal)

    assert result.cost == pytest.approx(6.0)
    assert (1, 1) not in result.path
    assert_valid_path(problem, result.path)


def test_all_algorithms_return_same_path_when_shortest_path_is_unique() -> None:
    problem = GridProblem(
        width=4,
        height=3,
        start=(0, 1),
        goal=(3, 1),
        blocked=frozenset(
            {
                (0, 0),
                (1, 0),
                (2, 0),
                (3, 0),
                (0, 2),
                (1, 2),
                (2, 2),
                (3, 2),
            }
        ),
    )
    expected_path = ((0, 1), (1, 1), (2, 1), (3, 1))

    results = (
        dijkstra(problem.neighbors, problem.start, problem.goal),
        a_star(problem.neighbors, problem.start, problem.goal, problem.heuristic),
        bidirectional_dijkstra(
            problem.neighbors,
            problem.start,
            problem.goal,
            reverse_neighbors=problem.reverse_neighbors,
        ),
        bidirectional_a_star(
            problem.neighbors,
            problem.start,
            problem.goal,
            problem.heuristic,
            reverse_neighbors=problem.reverse_neighbors,
        ),
    )

    for result in results:
        assert result.path == expected_path
        assert result.cost == pytest.approx(3.0)


def test_all_algorithms_return_same_path_on_large_unique_corridor() -> None:
    expected_path = (
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (6, 1),
        (7, 1),
        (8, 1),
        (9, 1),
        (10, 1),
        (10, 2),
        (10, 3),
        (9, 3),
        (8, 3),
        (7, 3),
        (6, 3),
        (5, 3),
        (4, 3),
        (3, 3),
        (2, 3),
        (1, 3),
        (1, 4),
        (1, 5),
        (2, 5),
        (3, 5),
        (4, 5),
        (5, 5),
        (6, 5),
        (7, 5),
        (8, 5),
        (9, 5),
        (10, 5),
        (10, 6),
        (10, 7),
        (9, 7),
        (8, 7),
        (7, 7),
        (6, 7),
        (5, 7),
        (4, 7),
        (3, 7),
        (2, 7),
        (1, 7),
    )
    path_nodes = set(expected_path)
    blocked = {(x, y) for y in range(9) for x in range(12) if (x, y) not in path_nodes}
    problem = GridProblem(
        width=12,
        height=9,
        start=expected_path[0],
        goal=expected_path[-1],
        blocked=frozenset(blocked),
    )
    assert_single_corridor(problem, expected_path)

    results = (
        dijkstra(problem.neighbors, problem.start, problem.goal),
        a_star(problem.neighbors, problem.start, problem.goal, problem.heuristic),
        bidirectional_dijkstra(
            problem.neighbors,
            problem.start,
            problem.goal,
            reverse_neighbors=problem.reverse_neighbors,
        ),
        bidirectional_a_star(
            problem.neighbors,
            problem.start,
            problem.goal,
            problem.heuristic,
            reverse_neighbors=problem.reverse_neighbors,
        ),
    )

    for result in results:
        assert result.path == expected_path
        assert result.cost == pytest.approx(len(expected_path) - 1)


def test_unreachable_grid_returns_empty_path_and_infinite_cost() -> None:
    problem = GridProblem(
        width=3,
        height=3,
        start=(0, 1),
        goal=(2, 1),
        blocked=frozenset({(1, 0), (1, 1), (1, 2)}),
    )

    for search in (
        dijkstra(problem.neighbors, problem.start, problem.goal),
        a_star(problem.neighbors, problem.start, problem.goal, problem.heuristic),
        bidirectional_dijkstra(
            problem.neighbors,
            problem.start,
            problem.goal,
            reverse_neighbors=problem.reverse_neighbors,
        ),
        bidirectional_a_star(
            problem.neighbors,
            problem.start,
            problem.goal,
            problem.heuristic,
            reverse_neighbors=problem.reverse_neighbors,
        ),
    ):
        assert search.path == ()
        assert isinf(search.cost)


def test_bidirectional_grid_search_uses_reverse_cell_costs() -> None:
    problem = GridProblem(
        width=2,
        height=2,
        start=(0, 0),
        goal=(1, 1),
        blocked=frozenset({(1, 0)}),
        weights={(0, 1): 3.0},
    )

    for result in (
        bidirectional_dijkstra(
            problem.neighbors,
            problem.start,
            problem.goal,
            reverse_neighbors=problem.reverse_neighbors,
        ),
        bidirectional_a_star(
            problem.neighbors,
            problem.start,
            problem.goal,
            problem.heuristic,
            reverse_neighbors=problem.reverse_neighbors,
        ),
    ):
        assert result.path == ((0, 0), (0, 1), (1, 1))
        assert result.cost == pytest.approx(4.0)
        assert path_cost(problem, result.path) == pytest.approx(result.cost)


def test_rejects_non_positive_edge_costs() -> None:
    graph = {
        "start": [Edge("goal", 0.0)],
        "goal": [],
    }

    with pytest.raises(ValueError, match="positive"):
        dijkstra(lambda node: graph[node], "start", "goal")


def test_demo_payload_is_json_ready() -> None:
    payload = demo_payload()

    assert payload["problem"]["width"] == 49
    assert payload["problem"]["height"] == 31
    assert len(payload["problem"]["weights"]) >= 500
    assert {result["id"] for result in payload["results"]} == {
        "dijkstra",
        "a_star",
        "bidirectional_dijkstra",
        "bidirectional_a_star",
    }
