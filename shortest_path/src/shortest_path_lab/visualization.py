"""HTML rendering helpers for pathfinding traces."""

from __future__ import annotations

import html
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .algorithms import SearchResult, SearchStep
from .examples import ALGORITHM_LABELS, make_demo_problem, solve_demo_problem
from .grid import GridNode, GridProblem


def demo_payload() -> dict[str, Any]:
    problem = make_demo_problem()
    return payload_from_results(problem, solve_demo_problem(problem))


def payload_from_results(
    problem: GridProblem,
    results: dict[str, SearchResult],
) -> dict[str, Any]:
    return {
        "problem": {
            "width": problem.width,
            "height": problem.height,
            "start": _node(problem.start),
            "goal": _node(problem.goal),
            "blocked": [_node(node) for node in sorted(problem.blocked, key=_grid_sort_key)],
            "weights": [
                {"node": _node(node), "cost": cost}
                for node, cost in sorted(
                    problem.weights.items(), key=lambda item: _grid_sort_key(item[0])
                )
            ],
        },
        "results": [_result_payload(result) for result in results.values()],
    }


def render_notebook_html(
    problem: GridProblem,
    results: dict[str, SearchResult],
    *,
    height: int = 720,
) -> str:
    page = render_standalone_html(payload_from_results(problem, results))
    return (
        f'<iframe srcdoc="{html.escape(page, quote=True)}" '
        f'width="100%" height="{height}" style="border:0; border-radius:8px;"></iframe>'
    )


def write_demo_html(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.write_text(render_standalone_html(demo_payload()), encoding="utf-8")
    return output_path


def write_demo_payload(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.write_text(json.dumps(demo_payload(), indent=2), encoding="utf-8")
    return output_path


def _result_payload(result: SearchResult) -> dict[str, Any]:
    return {
        "id": result.algorithm,
        "label": ALGORITHM_LABELS.get(result.algorithm, result.algorithm),
        "cost": result.cost if isfinite(result.cost) else None,
        "path": [_node(node) for node in result.path],
        "expandedForward": [_node(node) for node in result.expanded_forward],
        "expandedBackward": [_node(node) for node in result.expanded_backward],
        "meeting": _optional_node(result.meeting),
        "steps": [_step_payload(step) for step in result.steps],
    }


def _step_payload(step: SearchStep) -> dict[str, Any]:
    return {
        "direction": step.direction,
        "current": _node(step.current),
        "currentCost": step.current_cost,
        "opened": [_node(node) for node in step.opened],
        "meeting": _optional_node(step.meeting),
        "bestCost": step.best_cost,
    }


def _node(node: Any) -> list[int]:
    x, y = node
    return [int(x), int(y)]


def _optional_node(node: Any | None) -> list[int] | None:
    return None if node is None else _node(node)


def _grid_sort_key(node: GridNode) -> tuple[int, int]:
    return (node[1], node[0])


def render_standalone_html(payload: dict[str, Any]) -> str:
    json_payload = json.dumps(payload, separators=(",", ":"))
    return _HTML_TEMPLATE.replace("__PATHFINDING_PAYLOAD__", json_payload)


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shortest Path Lab</title>
<style>
:root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #5c6b73;
  --line: #cfd8dc;
  --panel: #f7f9fa;
  --canvas: #ffffff;
  --block: #2d3436;
  --weight: #f2b84b;
  --start: #1f9d55;
  --goal: #d64545;
  --frontier-f: #79c2ff;
  --frontier-b: #c7a7ff;
  --closed-f: #2f80ed;
  --closed-b: #8b5cf6;
  --current: #f97316;
  --path: #ffe156;
  --meet: #00a896;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--canvas);
}
main {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
  background: #fbfcfd;
}
h1 {
  margin: 0;
  font-size: 22px;
  line-height: 1.2;
  letter-spacing: 0;
}
.subtitle {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) 1fr;
  min-height: 0;
}
.controls {
  border-right: 1px solid var(--line);
  background: var(--panel);
  padding: 18px;
  display: grid;
  align-content: start;
  gap: 18px;
}
.control-group {
  display: grid;
  gap: 8px;
}
label {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0;
}
select,
input[type="range"],
button {
  width: 100%;
}
select {
  appearance: none;
  border: 1px solid #b8c4ca;
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
}
.button-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
button {
  min-height: 38px;
  border: 1px solid #aebbc2;
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
}
button.primary {
  border-color: #185abc;
  background: #1a73e8;
  color: #fff;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.stat {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}
.stat span {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.stat strong {
  display: block;
  margin-top: 4px;
  font-size: 20px;
}
.legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
  font-size: 12px;
  color: #334155;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.18);
  flex: 0 0 auto;
}
.stage {
  min-width: 0;
  overflow: auto;
  padding: 22px;
  display: grid;
  align-content: start;
  gap: 14px;
}
.grid-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  background: #eef3f6;
  padding: 12px;
}
.grid {
  --cell-size: 34px;
  display: grid;
  grid-template-columns: repeat(var(--cols), var(--cell-size));
  grid-auto-rows: var(--cell-size);
  gap: 2px;
  width: max-content;
}
.cell {
  width: var(--cell-size);
  height: var(--cell-size);
  display: grid;
  place-items: center;
  border: 1px solid #d7e0e5;
  background: #fff;
  color: #111827;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
  transition: background-color 80ms linear, outline-color 80ms linear;
}
.cell.weight { background: color-mix(in srgb, var(--weight) 65%, white); }
.cell.blocked { background: var(--block); border-color: var(--block); color: #fff; }
.cell.frontier-forward { background: color-mix(in srgb, var(--frontier-f) 55%, white); }
.cell.frontier-backward { background: color-mix(in srgb, var(--frontier-b) 55%, white); }
.cell.closed-forward { background: color-mix(in srgb, var(--closed-f) 70%, white); color: #fff; }
.cell.closed-backward { background: color-mix(in srgb, var(--closed-b) 70%, white); color: #fff; }
.cell.path { background: var(--path); color: #1f2937; }
.cell.current { outline: 3px solid var(--current); outline-offset: -3px; }
.cell.meeting { outline: 3px solid var(--meet); outline-offset: -3px; }
.cell.start { background: var(--start); color: #fff; }
.cell.goal { background: var(--goal); color: #fff; }
.timeline {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}
#progress {
  width: 100%;
}
@media (max-width: 820px) {
  .topbar {
    display: block;
  }
  .layout {
    grid-template-columns: 1fr;
  }
  .controls {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .grid {
    --cell-size: 30px;
  }
}
</style>
</head>
<body>
<main>
  <header class="topbar">
    <div>
      <h1>Shortest Path Lab</h1>
      <p class="subtitle">Trace Dijkstra, A*, and bidirectional variants on one weighted grid.</p>
    </div>
  </header>
  <section class="layout">
    <aside class="controls">
      <div class="control-group">
        <label for="algorithm">Algorithm</label>
        <select id="algorithm"></select>
      </div>
      <div class="button-row">
        <button id="reset">Reset</button>
        <button id="step">Step</button>
        <button id="play" class="primary">Play</button>
      </div>
      <div class="control-group">
        <label for="speed">Speed</label>
        <input id="speed" type="range" min="40" max="900" value="180" step="20">
      </div>
      <div class="stats">
        <div class="stat"><span>Cost</span><strong id="cost">-</strong></div>
        <div class="stat"><span>Expanded</span><strong id="expanded">-</strong></div>
        <div class="stat"><span>Step</span><strong id="step-count">-</strong></div>
        <div class="stat"><span>Path</span><strong id="path-length">-</strong></div>
      </div>
      <div class="legend">
        <div class="legend-item"><i class="swatch" style="background: var(--start)"></i>Start</div>
        <div class="legend-item"><i class="swatch" style="background: var(--goal)"></i>Goal</div>
        <div class="legend-item"><i class="swatch" style="background: var(--block)"></i>Blocked</div>
        <div class="legend-item"><i class="swatch" style="background: var(--weight)"></i>Weighted</div>
        <div class="legend-item"><i class="swatch" style="background: var(--closed-f)"></i>Forward</div>
        <div class="legend-item"><i class="swatch" style="background: var(--closed-b)"></i>Backward</div>
        <div class="legend-item"><i class="swatch" style="background: var(--current)"></i>Current</div>
        <div class="legend-item"><i class="swatch" style="background: var(--path)"></i>Path</div>
      </div>
    </aside>
    <section class="stage">
      <div class="grid-wrap">
        <div id="grid" class="grid" aria-label="Pathfinding grid"></div>
      </div>
      <div class="timeline">
        <span id="status">Ready</span>
        <input id="progress" type="range" min="0" value="0" step="1">
        <span id="progress-label">0 / 0</span>
      </div>
    </section>
  </section>
</main>
<script>
const payload = __PATHFINDING_PAYLOAD__;
const problem = payload.problem;
const results = new Map(payload.results.map((result) => [result.id, result]));
const cellByKey = new Map();
const key = (node) => `${node[0]},${node[1]}`;
const nodeSet = (nodes) => new Set((nodes || []).map(key));
const algorithmSelect = document.getElementById("algorithm");
const grid = document.getElementById("grid");
const resetButton = document.getElementById("reset");
const stepButton = document.getElementById("step");
const playButton = document.getElementById("play");
const speedInput = document.getElementById("speed");
const progressInput = document.getElementById("progress");
const progressLabel = document.getElementById("progress-label");
const statusText = document.getElementById("status");
const costText = document.getElementById("cost");
const expandedText = document.getElementById("expanded");
const stepCountText = document.getElementById("step-count");
const pathLengthText = document.getElementById("path-length");
const blocked = nodeSet(problem.blocked);
const weights = new Map(
  problem.weights
    .filter((item) => item.cost >= 6)
    .map((item) => [key(item.node), item.cost])
);

let active = payload.results[0];
let stepIndex = -1;
let timer = null;

function setupControls() {
  for (const result of payload.results) {
    const option = document.createElement("option");
    option.value = result.id;
    option.textContent = result.label;
    algorithmSelect.appendChild(option);
  }
  algorithmSelect.addEventListener("change", () => {
    active = results.get(algorithmSelect.value);
    stop();
    stepIndex = -1;
    progressInput.max = Math.max(active.steps.length - 1, 0);
    paint();
  });
  resetButton.addEventListener("click", () => {
    stop();
    stepIndex = -1;
    paint();
  });
  stepButton.addEventListener("click", () => {
    stop();
    stepForward();
  });
  playButton.addEventListener("click", () => {
    if (timer) {
      stop();
    } else {
      play();
    }
  });
  progressInput.addEventListener("input", () => {
    stop();
    stepIndex = Number(progressInput.value);
    paint();
  });
}

function buildGrid() {
  grid.style.setProperty("--cols", problem.width);
  for (let y = 0; y < problem.height; y += 1) {
    for (let x = 0; x < problem.width; x += 1) {
      const node = [x, y];
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.key = key(node);
      cellByKey.set(key(node), cell);
      grid.appendChild(cell);
    }
  }
}

function resetCells() {
  const startKey = key(problem.start);
  const goalKey = key(problem.goal);
  for (const [cellKey, cell] of cellByKey.entries()) {
    cell.className = "cell";
    cell.textContent = "";
    if (weights.has(cellKey)) {
      cell.classList.add("weight");
      cell.textContent = weights.get(cellKey);
    }
    if (blocked.has(cellKey)) {
      cell.classList.add("blocked");
      cell.textContent = "";
    }
    if (cellKey === startKey) {
      cell.classList.add("start");
      cell.textContent = "S";
    }
    if (cellKey === goalKey) {
      cell.classList.add("goal");
      cell.textContent = "G";
    }
  }
}

function addClass(nodes, className) {
  for (const node of nodes || []) {
    const cell = cellByKey.get(key(node));
    if (cell && !cell.classList.contains("blocked")) {
      cell.classList.add(className);
    }
  }
}

function addClassKeys(keys, className) {
  for (const cellKey of keys) {
    const cell = cellByKey.get(cellKey);
    if (cell && !cell.classList.contains("blocked")) {
      cell.classList.add(className);
    }
  }
}

function stateAt(index) {
  const state = {
    frontierForward: new Set(),
    frontierBackward: new Set(),
    closedForward: new Set(),
    closedBackward: new Set(),
    meeting: null,
    currentStep: null
  };
  if (index < 0) {
    return state;
  }
  const last = Math.min(index, active.steps.length - 1);
  for (let i = 0; i <= last; i += 1) {
    const step = active.steps[i];
    const currentKey = key(step.current);
    const frontier = step.direction === "forward" ? state.frontierForward : state.frontierBackward;
    const closed = step.direction === "forward" ? state.closedForward : state.closedBackward;
    frontier.delete(currentKey);
    closed.add(currentKey);
    for (const opened of step.opened || []) {
      const openedKey = key(opened);
      if (!closed.has(openedKey)) {
        frontier.add(openedKey);
      }
    }
    if (step.meeting) {
      state.meeting = step.meeting;
    }
    state.currentStep = step;
  }
  return state;
}

function paint() {
  resetCells();
  const finalStepIndex = active.steps.length - 1;
  const trace = stateAt(stepIndex);
  const currentStep = trace.currentStep;
  if (currentStep) {
    addClassKeys(trace.frontierForward, "frontier-forward");
    addClassKeys(trace.frontierBackward, "frontier-backward");
    addClassKeys(trace.closedForward, "closed-forward");
    addClassKeys(trace.closedBackward, "closed-backward");
    addClass(currentStep.opened, currentStep.direction === "forward" ? "frontier-forward" : "frontier-backward");
    addClass([currentStep.current], "current");
    if (trace.meeting) {
      addClass([trace.meeting], "meeting");
    }
  }
  if (stepIndex >= finalStepIndex) {
    addClass(active.path, "path");
  }
  addClass([problem.start], "start");
  addClass([problem.goal], "goal");
  updateReadout(currentStep);
}

function updateReadout(currentStep) {
  const done = stepIndex >= active.steps.length - 1;
  costText.textContent = active.cost === null ? "inf" : active.cost.toFixed(1).replace(/\\.0$/, "");
  expandedText.textContent = String(active.expandedForward.length + active.expandedBackward.length);
  stepCountText.textContent = `${Math.max(stepIndex + 1, 0)}/${active.steps.length}`;
  pathLengthText.textContent = active.path.length ? String(active.path.length) : "-";
  progressInput.max = Math.max(active.steps.length - 1, 0);
  progressInput.value = Math.max(stepIndex, 0);
  progressLabel.textContent = `${Math.max(stepIndex + 1, 0)} / ${active.steps.length}`;
  stepButton.disabled = done;
  statusText.textContent = currentStep
    ? `${active.label}: ${currentStep.direction} expansion at (${currentStep.current[0]}, ${currentStep.current[1]})`
    : `${active.label}: ready`;
}

function stepForward() {
  if (stepIndex < active.steps.length - 1) {
    stepIndex += 1;
    paint();
  } else {
    stop();
  }
}

function play() {
  if (stepIndex >= active.steps.length - 1) {
    stepIndex = -1;
  }
  playButton.textContent = "Pause";
  stepForward();
  timer = window.setInterval(stepForward, Number(speedInput.value));
}

function stop() {
  if (timer) {
    window.clearInterval(timer);
    timer = null;
  }
  playButton.textContent = "Play";
}

setupControls();
buildGrid();
progressInput.max = Math.max(active.steps.length - 1, 0);
paint();
</script>
</body>
</html>
"""
