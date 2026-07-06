"""Shortest path algorithms with trace data for visualization."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from math import inf
from typing import Literal

type Node = Hashable
type Direction = Literal["forward", "backward"]


@dataclass(frozen=True, slots=True)
class Edge:
    """A positive-cost edge to a neighboring node."""

    target: Node
    cost: float = 1.0


type NeighborFn = Callable[[Node], Iterable[Edge]]
type HeuristicFn = Callable[[Node, Node], float]


@dataclass(frozen=True, slots=True)
class SearchStep:
    """One expansion step recorded by a search algorithm."""

    algorithm: str
    direction: Direction
    current: Node
    current_cost: float
    opened: tuple[Node, ...] = ()
    frontier_forward: tuple[Node, ...] = ()
    frontier_backward: tuple[Node, ...] = ()
    closed_forward: tuple[Node, ...] = ()
    closed_backward: tuple[Node, ...] = ()
    meeting: Node | None = None
    best_cost: float | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A shortest path result plus the trace needed for visualization."""

    algorithm: str
    start: Node
    goal: Node
    path: tuple[Node, ...]
    cost: float
    steps: tuple[SearchStep, ...]
    expanded_forward: tuple[Node, ...]
    expanded_backward: tuple[Node, ...] = ()
    meeting: Node | None = None
    distances_forward: dict[Node, float] = field(default_factory=dict)
    distances_backward: dict[Node, float] = field(default_factory=dict)


def dijkstra(neighbors: NeighborFn, start: Node, goal: Node) -> SearchResult:
    """Run unidirectional Dijkstra search."""

    return _single_source_best_first(
        algorithm="dijkstra",
        neighbors=neighbors,
        start=start,
        goal=goal,
        priority=lambda node, cost: cost,
    )


def a_star(
    neighbors: NeighborFn,
    start: Node,
    goal: Node,
    heuristic: HeuristicFn,
) -> SearchResult:
    """Run unidirectional A* search.

    The heuristic should be admissible and consistent for the usual A*
    optimality guarantee.
    """

    return _single_source_best_first(
        algorithm="a_star",
        neighbors=neighbors,
        start=start,
        goal=goal,
        priority=lambda node, cost: cost + heuristic(node, goal),
    )


def bidirectional_dijkstra(
    neighbors: NeighborFn,
    start: Node,
    goal: Node,
    *,
    reverse_neighbors: NeighborFn | None = None,
) -> SearchResult:
    """Run bidirectional Dijkstra search.

    If the graph is directed, pass ``reverse_neighbors`` for the backward
    search. For undirected graphs it can be omitted.
    """

    reverse = reverse_neighbors or neighbors
    return _bidirectional_best_first(
        algorithm="bidirectional_dijkstra",
        neighbors_forward=neighbors,
        neighbors_backward=reverse,
        start=start,
        goal=goal,
        priority_forward=lambda node, cost: cost,
        priority_backward=lambda node, cost: cost,
    )


def bidirectional_a_star(
    neighbors: NeighborFn,
    start: Node,
    goal: Node,
    heuristic: HeuristicFn,
    *,
    reverse_neighbors: NeighborFn | None = None,
) -> SearchResult:
    """Run bidirectional A* search with balanced potentials.

    The heuristic should be admissible, consistent, and symmetric enough for
    ``heuristic(a, b)`` and ``heuristic(b, a)`` to be used as a shared lower
    bound family. Grid Manhattan distance satisfies this condition.
    """

    reverse = reverse_neighbors or neighbors
    return _bidirectional_balanced_a_star(
        neighbors_forward=neighbors,
        neighbors_backward=reverse,
        start=start,
        goal=goal,
        heuristic=heuristic,
    )


def _single_source_best_first(
    *,
    algorithm: str,
    neighbors: NeighborFn,
    start: Node,
    goal: Node,
    priority: Callable[[Node, float], float],
) -> SearchResult:
    ticket = count()
    heap: list[tuple[float, int, Node, float]] = []
    distances: dict[Node, float] = {start: 0.0}
    previous: dict[Node, Node] = {}
    closed: set[Node] = set()
    closed_order: list[Node] = []
    steps: list[SearchStep] = []

    _push(heap, ticket, priority(start, 0.0), start, 0.0)

    while heap:
        item = _pop_valid(heap, closed, distances)
        if item is None:
            break

        current, current_cost = item
        closed.add(current)
        closed_order.append(current)
        opened: list[Node] = []

        if current != goal:
            for edge in neighbors(current):
                _validate_edge(edge)
                next_cost = current_cost + edge.cost
                if edge.target in closed:
                    continue
                if next_cost < distances.get(edge.target, inf):
                    distances[edge.target] = next_cost
                    previous[edge.target] = current
                    _push(heap, ticket, priority(edge.target, next_cost), edge.target, next_cost)
                    opened.append(edge.target)

        steps.append(
            SearchStep(
                algorithm=algorithm,
                direction="forward",
                current=current,
                current_cost=current_cost,
                opened=tuple(opened),
                frontier_forward=_open_nodes(distances, closed),
                closed_forward=tuple(closed_order),
                meeting=current if current == goal else None,
                best_cost=current_cost if current == goal else None,
            )
        )

        if current == goal:
            break

    found = goal in closed
    path = _path_from_previous(previous, start, goal) if found else ()
    return SearchResult(
        algorithm=algorithm,
        start=start,
        goal=goal,
        path=path,
        cost=distances[goal] if found else inf,
        steps=tuple(steps),
        expanded_forward=tuple(closed_order),
        distances_forward=dict(distances),
    )


def _bidirectional_best_first(
    *,
    algorithm: str,
    neighbors_forward: NeighborFn,
    neighbors_backward: NeighborFn,
    start: Node,
    goal: Node,
    priority_forward: Callable[[Node, float], float],
    priority_backward: Callable[[Node, float], float],
) -> SearchResult:
    if start == goal:
        return SearchResult(
            algorithm=algorithm,
            start=start,
            goal=goal,
            path=(start,),
            cost=0.0,
            steps=(
                SearchStep(
                    algorithm=algorithm,
                    direction="forward",
                    current=start,
                    current_cost=0.0,
                    closed_forward=(start,),
                    meeting=start,
                    best_cost=0.0,
                ),
            ),
            expanded_forward=(start,),
            meeting=start,
            distances_forward={start: 0.0},
            distances_backward={goal: 0.0},
        )

    ticket = count()
    heap_forward: list[tuple[float, int, Node, float]] = []
    heap_backward: list[tuple[float, int, Node, float]] = []
    dist_forward: dict[Node, float] = {start: 0.0}
    dist_backward: dict[Node, float] = {goal: 0.0}
    prev_forward: dict[Node, Node] = {}
    prev_backward: dict[Node, Node] = {}
    closed_forward: set[Node] = set()
    closed_backward: set[Node] = set()
    order_forward: list[Node] = []
    order_backward: list[Node] = []
    steps: list[SearchStep] = []
    best_cost = inf
    meeting: Node | None = None

    _push(heap_forward, ticket, priority_forward(start, 0.0), start, 0.0)
    _push(heap_backward, ticket, priority_backward(goal, 0.0), goal, 0.0)

    while heap_forward and heap_backward:
        if (
            _min_open_cost(dist_forward, closed_forward)
            + _min_open_cost(dist_backward, closed_backward)
            >= best_cost
        ):
            break

        top_forward = _peek_priority(heap_forward, closed_forward, dist_forward)
        top_backward = _peek_priority(heap_backward, closed_backward, dist_backward)
        if top_forward is None or top_backward is None:
            break

        if top_forward <= top_backward:
            expanded = _expand_direction(
                direction="forward",
                algorithm=algorithm,
                heap=heap_forward,
                ticket=ticket,
                neighbors=neighbors_forward,
                priority=priority_forward,
                own_dist=dist_forward,
                other_dist=dist_backward,
                own_prev=prev_forward,
                closed_own=closed_forward,
                closed_other=closed_backward,
                order_own=order_forward,
                order_other=order_backward,
                current_best=best_cost,
                current_meeting=meeting,
            )
        else:
            expanded = _expand_direction(
                direction="backward",
                algorithm=algorithm,
                heap=heap_backward,
                ticket=ticket,
                neighbors=neighbors_backward,
                priority=priority_backward,
                own_dist=dist_backward,
                other_dist=dist_forward,
                own_prev=prev_backward,
                closed_own=closed_backward,
                closed_other=closed_forward,
                order_own=order_backward,
                order_other=order_forward,
                current_best=best_cost,
                current_meeting=meeting,
            )

        if expanded is None:
            break

        best_cost, meeting, step = expanded
        steps.append(
            SearchStep(
                algorithm=step.algorithm,
                direction=step.direction,
                current=step.current,
                current_cost=step.current_cost,
                opened=step.opened,
                frontier_forward=_open_nodes(dist_forward, closed_forward),
                frontier_backward=_open_nodes(dist_backward, closed_backward),
                closed_forward=tuple(order_forward),
                closed_backward=tuple(order_backward),
                meeting=meeting,
                best_cost=best_cost if best_cost < inf else None,
            )
        )

    path = _stitch_path(meeting, prev_forward, prev_backward, start, goal) if meeting else ()
    return SearchResult(
        algorithm=algorithm,
        start=start,
        goal=goal,
        path=path,
        cost=best_cost if path else inf,
        steps=tuple(steps),
        expanded_forward=tuple(order_forward),
        expanded_backward=tuple(order_backward),
        meeting=meeting if path else None,
        distances_forward=dict(dist_forward),
        distances_backward=dict(dist_backward),
    )


def _bidirectional_balanced_a_star(
    *,
    neighbors_forward: NeighborFn,
    neighbors_backward: NeighborFn,
    start: Node,
    goal: Node,
    heuristic: HeuristicFn,
) -> SearchResult:
    if start == goal:
        return SearchResult(
            algorithm="bidirectional_a_star",
            start=start,
            goal=goal,
            path=(start,),
            cost=0.0,
            steps=(
                SearchStep(
                    algorithm="bidirectional_a_star",
                    direction="forward",
                    current=start,
                    current_cost=0.0,
                    closed_forward=(start,),
                    meeting=start,
                    best_cost=0.0,
                ),
            ),
            expanded_forward=(start,),
            meeting=start,
            distances_forward={start: 0.0},
            distances_backward={goal: 0.0},
        )

    def potential(node: Node) -> float:
        return 0.5 * (heuristic(node, goal) - heuristic(node, start))

    ticket = count()
    heap_forward: list[tuple[float, int, Node, float]] = []
    heap_backward: list[tuple[float, int, Node, float]] = []
    dist_forward: dict[Node, float] = {start: 0.0}
    dist_backward: dict[Node, float] = {goal: 0.0}
    prev_forward: dict[Node, Node] = {}
    prev_backward: dict[Node, Node] = {}
    closed_forward: set[Node] = set()
    closed_backward: set[Node] = set()
    order_forward: list[Node] = []
    order_backward: list[Node] = []
    steps: list[SearchStep] = []
    best_cost = inf
    meeting: Node | None = None

    def priority_forward(node: Node, cost: float) -> float:
        return cost + potential(node)

    def priority_backward(node: Node, cost: float) -> float:
        return cost - potential(node)

    _push(heap_forward, ticket, priority_forward(start, 0.0), start, 0.0)
    _push(heap_backward, ticket, priority_backward(goal, 0.0), goal, 0.0)

    while heap_forward and heap_backward:
        top_forward = _peek_priority(heap_forward, closed_forward, dist_forward)
        top_backward = _peek_priority(heap_backward, closed_backward, dist_backward)
        if top_forward is None or top_backward is None:
            break
        if top_forward + top_backward >= best_cost:
            break

        if top_forward <= top_backward:
            expanded = _expand_direction(
                direction="forward",
                algorithm="bidirectional_a_star",
                heap=heap_forward,
                ticket=ticket,
                neighbors=neighbors_forward,
                priority=priority_forward,
                own_dist=dist_forward,
                other_dist=dist_backward,
                own_prev=prev_forward,
                closed_own=closed_forward,
                closed_other=closed_backward,
                order_own=order_forward,
                order_other=order_backward,
                current_best=best_cost,
                current_meeting=meeting,
            )
        else:
            expanded = _expand_direction(
                direction="backward",
                algorithm="bidirectional_a_star",
                heap=heap_backward,
                ticket=ticket,
                neighbors=neighbors_backward,
                priority=priority_backward,
                own_dist=dist_backward,
                other_dist=dist_forward,
                own_prev=prev_backward,
                closed_own=closed_backward,
                closed_other=closed_forward,
                order_own=order_backward,
                order_other=order_forward,
                current_best=best_cost,
                current_meeting=meeting,
            )

        if expanded is None:
            break

        best_cost, meeting, step = expanded
        steps.append(
            SearchStep(
                algorithm=step.algorithm,
                direction=step.direction,
                current=step.current,
                current_cost=step.current_cost,
                opened=step.opened,
                frontier_forward=_open_nodes(dist_forward, closed_forward),
                frontier_backward=_open_nodes(dist_backward, closed_backward),
                closed_forward=tuple(order_forward),
                closed_backward=tuple(order_backward),
                meeting=meeting,
                best_cost=best_cost if best_cost < inf else None,
            )
        )

    path = _stitch_path(meeting, prev_forward, prev_backward, start, goal) if meeting else ()
    return SearchResult(
        algorithm="bidirectional_a_star",
        start=start,
        goal=goal,
        path=path,
        cost=best_cost if path else inf,
        steps=tuple(steps),
        expanded_forward=tuple(order_forward),
        expanded_backward=tuple(order_backward),
        meeting=meeting if path else None,
        distances_forward=dict(dist_forward),
        distances_backward=dict(dist_backward),
    )


def _expand_direction(
    *,
    direction: Direction,
    algorithm: str,
    heap: list[tuple[float, int, Node, float]],
    ticket: count,
    neighbors: NeighborFn,
    priority: Callable[[Node, float], float],
    own_dist: dict[Node, float],
    other_dist: dict[Node, float],
    own_prev: dict[Node, Node],
    closed_own: set[Node],
    closed_other: set[Node],
    order_own: list[Node],
    order_other: list[Node],
    current_best: float,
    current_meeting: Node | None,
) -> tuple[float, Node | None, SearchStep] | None:
    item = _pop_valid(heap, closed_own, own_dist)
    if item is None:
        return None

    current, current_cost = item
    closed_own.add(current)
    order_own.append(current)
    opened: list[Node] = []
    best_cost = current_best
    meeting = current_meeting

    if current in other_dist:
        candidate = current_cost + other_dist[current]
        if candidate < best_cost:
            best_cost = candidate
            meeting = current

    for edge in neighbors(current):
        _validate_edge(edge)
        if edge.target in closed_own:
            continue
        next_cost = current_cost + edge.cost
        if next_cost < own_dist.get(edge.target, inf):
            own_dist[edge.target] = next_cost
            own_prev[edge.target] = current
            _push(heap, ticket, priority(edge.target, next_cost), edge.target, next_cost)
            opened.append(edge.target)

        if edge.target in other_dist:
            candidate = next_cost + other_dist[edge.target]
            if candidate < best_cost:
                best_cost = candidate
                meeting = edge.target

    if direction == "forward":
        closed_forward = tuple(order_own)
        closed_backward = tuple(order_other)
    else:
        closed_forward = tuple(order_other)
        closed_backward = tuple(order_own)

    step = SearchStep(
        algorithm=algorithm,
        direction=direction,
        current=current,
        current_cost=current_cost,
        opened=tuple(opened),
        closed_forward=closed_forward,
        closed_backward=closed_backward,
        meeting=meeting,
        best_cost=best_cost if best_cost < inf else None,
    )
    return best_cost, meeting, step


def _push(
    heap: list[tuple[float, int, Node, float]],
    ticket: count,
    priority: float,
    node: Node,
    cost: float,
) -> None:
    heappush(heap, (float(priority), next(ticket), node, float(cost)))


def _pop_valid(
    heap: list[tuple[float, int, Node, float]],
    closed: set[Node],
    distances: dict[Node, float],
) -> tuple[Node, float] | None:
    while heap:
        _, _, node, cost_at_push = heappop(heap)
        if node in closed:
            continue
        if cost_at_push != distances.get(node):
            continue
        return node, cost_at_push
    return None


def _peek_priority(
    heap: list[tuple[float, int, Node, float]],
    closed: set[Node],
    distances: dict[Node, float],
) -> float | None:
    while heap:
        priority, _, node, cost_at_push = heap[0]
        if node not in closed and cost_at_push == distances.get(node):
            return priority
        heappop(heap)
    return None


def _open_nodes(distances: dict[Node, float], closed: set[Node]) -> tuple[Node, ...]:
    return tuple(node for node in distances if node not in closed)


def _min_open_cost(distances: dict[Node, float], closed: set[Node]) -> float:
    return min((cost for node, cost in distances.items() if node not in closed), default=inf)


def _validate_edge(edge: Edge) -> None:
    if edge.cost <= 0:
        raise ValueError(f"edge costs must be positive; got {edge.cost!r}")


def _path_from_previous(previous: dict[Node, Node], start: Node, goal: Node) -> tuple[Node, ...]:
    if start == goal:
        return (start,)
    if goal not in previous:
        return ()

    path = [goal]
    current = goal
    while current != start:
        current = previous.get(current)
        if current is None:
            return ()
        path.append(current)
    path.reverse()
    return tuple(path)


def _stitch_path(
    meeting: Node | None,
    previous_forward: dict[Node, Node],
    previous_backward: dict[Node, Node],
    start: Node,
    goal: Node,
) -> tuple[Node, ...]:
    if meeting is None:
        return ()

    left = _path_from_previous(previous_forward, start, meeting)
    if not left:
        return ()

    right: list[Node] = []
    current = meeting
    while current != goal:
        next_node = previous_backward.get(current)
        if next_node is None:
            return ()
        right.append(next_node)
        current = next_node

    return (*left, *right)
