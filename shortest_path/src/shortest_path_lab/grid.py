"""Grid graph helpers used by the pathfinding examples."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .algorithms import Edge

type GridNode = tuple[int, int]


@dataclass(frozen=True, slots=True)
class GridProblem:
    """A rectangular weighted grid with blocked cells."""

    width: int
    height: int
    start: GridNode
    goal: GridNode
    blocked: frozenset[GridNode] = field(default_factory=frozenset)
    weights: Mapping[GridNode, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        blocked = frozenset(self.blocked)
        weights = dict(self.weights)
        object.__setattr__(self, "blocked", blocked)
        object.__setattr__(self, "weights", weights)

        if self.width <= 0 or self.height <= 0:
            raise ValueError("grid dimensions must be positive")
        for label, node in {"start": self.start, "goal": self.goal}.items():
            if not self.in_bounds(node):
                raise ValueError(f"{label} node {node!r} is outside the grid")
            if node in blocked:
                raise ValueError(f"{label} node {node!r} cannot be blocked")
        for node, cost in weights.items():
            if not self.in_bounds(node):
                raise ValueError(f"weighted node {node!r} is outside the grid")
            if cost <= 0:
                raise ValueError(f"cell weights must be positive; got {cost!r}")

    def cells(self) -> Iterable[GridNode]:
        for y in range(self.height):
            for x in range(self.width):
                yield (x, y)

    def in_bounds(self, node: GridNode) -> bool:
        x, y = node
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, node: GridNode) -> bool:
        return node not in self.blocked

    def cell_cost(self, node: GridNode) -> float:
        return float(self.weights.get(node, 1.0))

    def min_step_cost(self) -> float:
        return min((1.0, *self.weights.values()))

    def neighbors(self, node: GridNode) -> Iterable[Edge]:
        x, y = node
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if self.in_bounds(candidate) and self.passable(candidate):
                yield Edge(candidate, self.cell_cost(candidate))

    def reverse_neighbors(self, node: GridNode) -> Iterable[Edge]:
        x, y = node
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if self.in_bounds(candidate) and self.passable(candidate):
                yield Edge(candidate, self.cell_cost(node))

    def heuristic(self, node: GridNode, target: GridNode | None = None) -> float:
        target = self.goal if target is None else target
        return self.min_step_cost() * (abs(node[0] - target[0]) + abs(node[1] - target[1]))
