'use client';

import { useEffect, useRef } from 'react';
import type { Data, Layout, PlotlyHTMLElement } from 'plotly.js';
import {
  cameraPosition,
  constrainView,
  frame,
  ink,
  palette,
  sameView,
  viewFromPosition,
  type SurfaceProps,
  type View,
} from './contract';
import { nearestPoint } from './model';

type PlotlyApi = typeof import('plotly.js');
type Camera = {
  eye: { x: number; y: number; z: number };
  center: { x: number; y: number; z: number };
  up: { x: number; y: number; z: number };
};
type SurfaceEvent = {
  points?: { x: number; y: number; z?: number; curveNumber: number }[];
};
const cameraFor = (props: SurfaceProps): Camera => {
  const [x, y, z] = cameraPosition(props.view);
  return {
    eye: { x, y: -z, z: y - frame.center[1] },
    center: { x: 0, y: 0, z: 0 },
    up: { x: 0, y: 0, z: 1 },
  };
};

function chart(props: SurfaceProps) {
  const { grid, selected, wireframe } = props;
  const z = grid.iv.map((row) => row.map((iv) => iv * 100));
  const lineTrace = (
    paths: [number, number][][],
    color: string,
    width: number,
    hover = false,
  ) => {
    const x: (number | null)[] = [],
      y: (number | null)[] = [],
      values: (number | null)[] = [];
    paths.forEach((path) => {
      path.forEach(([row, column]) => {
        x.push(grid.moneyness[column] * 100);
        y.push(grid.tenors[row]);
        values.push(
          z[row][column] +
            (grid.domain.iv[1] - grid.domain.iv[0]) * 100 * 0.0047,
        );
      });
      x.push(null);
      y.push(null);
      values.push(null);
    });
    return {
      type: 'scatter3d',
      mode: 'lines',
      x,
      y,
      z: values,
      line: { color, width },
      connectgaps: false,
      hoverinfo: hover ? 'none' : 'skip',
      showlegend: false,
    } as Data;
  };
  const rows = grid.tenors.map((_, row) =>
    grid.moneyness.map((_, column) => [row, column] as [number, number]),
  );
  const columns = grid.moneyness.map((_, column) =>
    grid.tenors.map((_, row) => [row, column] as [number, number]),
  );
  const surface = {
    type: 'surface',
    x: grid.moneyness.map((m) => m * 100),
    y: grid.tenors,
    z,
    colorscale: palette,
    cmin: grid.domain.iv[0] * 100,
    cmax: grid.domain.iv[1] * 100,
    showscale: false,
    hidesurface: wireframe,
    lighting: { ambient: 1, diffuse: 0, specular: 0, roughness: 1, fresnel: 0 },
    hovertemplate:
      'K/F %{x:.1f}%<br>T %{y:.3f}年<br>IV %{z:.2f}%<extra></extra>',
    contours: {
      x: { highlight: false },
      y: { highlight: false },
      z: { highlight: false },
    },
  } as Data;
  const data: Data[] = [
    surface,
    {
      ...lineTrace([...rows, ...columns], '#91c5b4', 1.5, wireframe),
      visible: wireframe,
    },
    lineTrace([rows[selected.row], columns[selected.column]], ink.selected, 3),
    {
      type: 'scatter3d',
      mode: 'markers',
      x: [grid.moneyness[selected.column] * 100],
      y: [grid.tenors[selected.row]],
      z: [z[selected.row][selected.column]],
      marker: { size: 4, color: ink.selected },
      hoverinfo: 'skip',
      showlegend: false,
    },
  ];
  const axis = {
    showbackground: false,
    showline: true,
    linecolor: ink.grid,
    gridcolor: '#34433e',
    zeroline: false,
    tickfont: { size: 12, color: ink.label },
    ticks: '' as const,
    showspikes: false,
  };
  const layout: Partial<Layout> = {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { l: 0, r: 0, t: 0, b: 0 },
    font: { family: 'Geist, sans-serif', color: ink.label, size: 12 },
    showlegend: false,
    scene: {
      aspectmode: 'manual',
      aspectratio: { x: frame.width, y: frame.depth, z: frame.height },
      camera: cameraFor(props),
      dragmode: 'turntable',
      xaxis: {
        ...axis,
        title: { text: 'K / F' },
        range: grid.domain.moneyness.map((m) => m * 100),
        ticksuffix: '%',
        nticks: 5,
      },
      yaxis: {
        ...axis,
        title: { text: 'T（年）' },
        range: grid.domain.tenor,
        nticks: 5,
      },
      zaxis: {
        ...axis,
        title: { text: '' },
        range: grid.domain.iv.map((iv) => iv * 100),
        ticksuffix: '%',
        nticks: 5,
      },
    },
  };
  return { data, layout };
}

export default function PlotlySurface(props: SurfaceProps) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef(props);
  const update = useRef<(() => void) | null>(null);
  useEffect(() => {
    latest.current = props;
    update.current?.();
  });
  useEffect(() => {
    if (!host.current) return;
    // Each effect owns its node, including during React StrictMode remounts.
    const element = document.createElement('div');
    element.className = 'vol-plotly-scene';
    host.current.appendChild(element);
    let alive = true;
    let api: PlotlyApi | undefined;
    let graph: PlotlyHTMLElement | undefined;
    let queue = Promise.resolve();
    let applying = false;
    let pointer: { x: number; y: number; moved: boolean } | null = null;
    let pendingPoint: ReturnType<typeof nearestPoint> | null = null;
    let pendingGrid = '';
    const beginPointer = (event: PointerEvent) => {
      if (pointer) {
        pointer.moved = true;
        return;
      }
      pointer = { x: event.clientX, y: event.clientY, moved: false };
      pendingPoint = null;
      pendingGrid = latest.current.grid.id;
    };
    const movePointer = (event: PointerEvent) => {
      if (
        pointer &&
        Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) >= 4
      )
        pointer.moved = true;
    };
    const finishPointer = () => {
      const point = pointer && !pointer.moved ? pendingPoint : null;
      const gridId = pendingGrid;
      pointer = null;
      pendingPoint = null;
      // Native Plotly clicks occur while pressed. Rebuilding then interrupts a drag.
      if (point)
        requestAnimationFrame(() => {
          if (alive && latest.current.grid.id === gridId)
            latest.current.onSelect(point);
        });
    };
    const cancelPointer = () => {
      pointer = null;
      pendingPoint = null;
    };
    const zoom = (event: WheelEvent) => {
      // Plotly emits its wheel camera event before applying the zoom. Drive the
      // shared distance directly so all renderers see the same bounded value.
      event.preventDefault();
      event.stopPropagation();
      const pixels =
        event.deltaY *
        (event.deltaMode === 1
          ? 16
          : event.deltaMode === 2
            ? element.clientHeight
            : 1);
      const view = latest.current.view;
      latest.current.onView(
        constrainView({
          ...view,
          distance:
            view.distance *
            Math.exp(Math.max(-1000, Math.min(1000, pixels)) * 0.001),
        }),
      );
    };
    element.addEventListener('pointerdown', beginPointer);
    element.addEventListener('wheel', zoom, { passive: false, capture: true });
    window.addEventListener('pointermove', movePointer);
    window.addEventListener('pointerup', finishPointer);
    window.addEventListener('pointercancel', cancelPointer);
    let revision = '';
    let previousView: View | undefined;
    const fail = () => {
      if (alive) latest.current.onError();
    };
    const draw = () => {
      queue = queue
        .then(async () => {
          if (!api || !alive) return;
          const value = latest.current;
          const nextRevision = `${value.grid.id}:${value.selected.row}:${value.selected.column}:${value.wireframe}`;
          const camera = cameraFor(value);
          applying = true;
          try {
            if (revision !== nextRevision) {
              const { data, layout } = chart(value);
              graph = await api.react(element, data, layout, {
                displayModeBar: false,
                responsive: false,
                scrollZoom: false,
                plotGlPixelRatio: 1,
              });
              revision = nextRevision;
              if (alive) value.onReady(value.grid.id);
            } else if (!previousView || !sameView(value.view, previousView)) {
              const cameraUpdate: Partial<Layout> & { 'scene.camera': Camera } =
                { 'scene.camera': camera };
              await api.relayout(element, cameraUpdate);
            }
            previousView = value.view;
          } finally {
            applying = false;
          }
        })
        .catch(fail);
    };
    const observer = new ResizeObserver(() => {
      queue = queue
        .then(async () => {
          if (api && graph && alive)
            await Promise.resolve(api.Plots.resize(graph));
        })
        .catch(fail);
    });
    observer.observe(element);
    void import('plotly.js-gl3d-dist-min')
      .then(async (module) => {
        if (!alive) return;
        api = module.default;
        update.current = draw;
        draw();
        await queue;
        if (!alive || !graph) return;
        const reportCamera = (event: { 'scene.camera'?: Camera }) => {
          if (applying || !event['scene.camera']) return;
          const camera = event['scene.camera'];
          const raw = viewFromPosition([
            camera.eye.x - camera.center.x,
            frame.center[1] + camera.eye.z - camera.center.z,
            -(camera.eye.y - camera.center.y),
          ]);
          const bounded = constrainView(raw);
          previousView = raw;
          latest.current.onView(bounded);
          if (!sameView(raw, bounded)) {
            // A clamped React state can be unchanged; still correct Plotly itself.
            const corrected = cameraFor({ ...latest.current, view: bounded });
            queue = queue
              .then(async () => {
                if (!alive || !api) return;
                applying = true;
                try {
                  const change: Partial<Layout> & { 'scene.camera': Camera } = {
                    'scene.camera': corrected,
                  };
                  await api.relayout(element, change);
                  previousView = bounded;
                } finally {
                  applying = false;
                }
              })
              .catch(fail);
          }
        };
        // Plotly's current event typings omit relayouting and the 3D z value.
        const events = graph as unknown as {
          on: (event: string, listener: (...args: never[]) => void) => void;
        };
        events.on('plotly_relayout', reportCamera);
        events.on('plotly_relayouting', reportCamera);
        const getPoint = (event: SurfaceEvent) => {
          const point = event.points?.[0];
          return point && point.curveNumber <= 1
            ? nearestPoint(latest.current.grid, point.x / 100, point.y)
            : null;
        };
        events.on('plotly_hover', (event: SurfaceEvent) =>
          latest.current.onHover(getPoint(event)),
        );
        events.on('plotly_unhover', () => latest.current.onHover(null));
        events.on('plotly_click', (event: SurfaceEvent) => {
          const point = getPoint(event);
          if (pointer && point) pendingPoint = point;
        });
        element
          .querySelectorAll('canvas')
          .forEach((canvas) =>
            canvas.addEventListener('webglcontextlost', fail),
          );
      })
      .catch(fail);
    return () => {
      alive = false;
      update.current = null;
      observer.disconnect();
      element.removeEventListener('pointerdown', beginPointer);
      element.removeEventListener('wheel', zoom, true);
      window.removeEventListener('pointermove', movePointer);
      window.removeEventListener('pointerup', finishPointer);
      window.removeEventListener('pointercancel', cancelPointer);
      void queue.finally(() => {
        api?.purge(element);
        element.remove();
      });
    };
  }, []);
  return (
    <div
      ref={host}
      className="vol-native-scene"
      aria-label="Plotly ボラティリティーサーフェス"
    />
  );
}
