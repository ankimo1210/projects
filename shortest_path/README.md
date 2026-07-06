# Shortest Path Lab

Educational implementations and visualizations for shortest path search on a
weighted grid.

Implemented algorithms:

- Dijkstra
- A*
- Bidirectional Dijkstra
- Bidirectional A*

The Python implementation records each expansion step as trace data. The same
trace is used by the Jupyter notebook and the static HTML visualizer. The demo
visualizer uses a 49 x 31 weighted city-street map with intersections, loops,
closed segments, and roads extending beyond both the start and goal, while still
having a unique shortest path.

## Project Layout

```text
shortest_path/
├── notebooks/pathfinding_algorithms.ipynb
├── scripts/export_demo.py
├── site/index.html
├── src/shortest_path_lab/
└── tests/
```

## Run

From the workspace root:

```bash
PYTHONPATH=shortest_path/src python -m pytest shortest_path/tests
PYTHONPATH=shortest_path/src python shortest_path/scripts/export_demo.py
```

Open the static visualizer in a browser:

```text
shortest_path/site/index.html
```

Open the notebook:

```bash
PYTHONPATH=shortest_path/src jupyter notebook shortest_path/notebooks/pathfinding_algorithms.ipynb
```

## Notes

- Edge costs must be positive.
- Bidirectional search uses `reverse_neighbors` for directed graphs. Grid cell
  weights are modeled as "cost to enter the next cell", so the examples pass
  `GridProblem.reverse_neighbors` to keep backward distances consistent.
- A* and bidirectional A* expect an admissible, consistent heuristic. The grid
  helper provides a Manhattan heuristic scaled by the minimum step cost.
