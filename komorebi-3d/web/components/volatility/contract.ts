import { nearestPoint, type PointIndex, type SurfaceGrid } from './model';

export type EngineName = 'plotly' | 'three' | 'babylon';
export type View = { yaw: number; pitch: number; distance: number };
export type Vec3 = [number, number, number];
export const initialView: View = { yaw: -0.82, pitch: 0.56, distance: 11.8 };
export const frame = {
  width: 6,
  depth: 4.6,
  height: 3.2,
  center: [0, 1.6, 0] as Vec3,
  fov: 45,
};
export type SurfaceProps = {
  grid: SurfaceGrid;
  selected: PointIndex;
  wireframe: boolean;
  view: View;
  onView: (view: View) => void;
  onHover: (point: PointIndex | null) => void;
  onSelect: (point: PointIndex) => void;
  onReady: (gridId: string) => void;
  onError: () => void;
};
export const engineLabels: Record<
  EngineName,
  { name: string; detail: string }
> = {
  plotly: { name: 'Plotly', detail: '分析チャートとして表示' },
  three: { name: 'Three.js', detail: 'React Three Fiberで描画' },
  babylon: { name: 'Babylon.js', detail: '3Dエンジンで描画' },
};
export const palette: [number, string][] = [
  [0, '#25465b'],
  [0.25, '#328c94'],
  [0.5, '#78c6b0'],
  [0.75, '#c8e38b'],
  [1, '#f8e7a1'],
];
export const ink = {
  grid: '#57635f',
  label: '#aabbb3',
  selected: '#ddffac',
  background: '#151b19',
};
export function colorAt(fraction: number): Vec3 {
  const t = Math.max(0, Math.min(1, fraction));
  const section = Math.min(
    palette.length - 2,
    Math.floor(t * (palette.length - 1)),
  );
  const [a, from] = palette[section];
  const [b, to] = palette[section + 1];
  const weight = (t - a) / (b - a);
  const rgb = (hex: string) =>
    [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255);
  const start = rgb(from);
  const end = rgb(to);
  return start.map(
    (value, channel) => value + (end[channel] - value) * weight,
  ) as Vec3;
}
export const fraction = (value: number, range: [number, number]) =>
  (value - range[0]) / (range[1] - range[0]);
export function positionOf(
  grid: SurfaceGrid,
  row: number,
  column: number,
): Vec3 {
  return [
    (fraction(grid.moneyness[column], grid.domain.moneyness) - 0.5) *
      frame.width,
    fraction(grid.iv[row][column], grid.domain.iv) * frame.height,
    (0.5 - fraction(grid.tenors[row], grid.domain.tenor)) * frame.depth,
  ];
}
export function pointAtWorld(grid: SurfaceGrid, x: number, z: number) {
  const m =
    grid.domain.moneyness[0] +
    (x / frame.width + 0.5) *
      (grid.domain.moneyness[1] - grid.domain.moneyness[0]);
  const t =
    grid.domain.tenor[0] +
    (0.5 - z / frame.depth) * (grid.domain.tenor[1] - grid.domain.tenor[0]);
  return nearestPoint(grid, m, t);
}
export function cameraPosition(view: View): Vec3 {
  return [
    view.distance * Math.sin(view.yaw) * Math.cos(view.pitch),
    frame.center[1] + view.distance * Math.sin(view.pitch),
    view.distance * Math.cos(view.yaw) * Math.cos(view.pitch),
  ];
}
export function viewFromPosition([x, y, z]: Vec3): View {
  const height = y - frame.center[1];
  const distance = Math.hypot(x, height, z);
  return {
    yaw: Math.atan2(x, z),
    pitch: Math.asin(height / distance),
    distance,
  };
}
export function constrainView(view: View): View {
  return {
    yaw: view.yaw,
    pitch: Math.max(0.12, Math.min(1.4, view.pitch)),
    distance: Math.max(7, Math.min(22, view.distance)),
  };
}
export function sameView(a: View, b: View) {
  return (
    Math.abs(a.yaw - b.yaw) < 0.0001 &&
    Math.abs(a.pitch - b.pitch) < 0.0001 &&
    Math.abs(a.distance - b.distance) < 0.0001
  );
}
export function meshData(grid: SurfaceGrid) {
  const positions: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  for (let row = 0; row < grid.tenors.length; row++)
    for (let column = 0; column < grid.moneyness.length; column++) {
      positions.push(...positionOf(grid, row, column));
      colors.push(...colorAt(fraction(grid.iv[row][column], grid.domain.iv)));
      if (row < grid.tenors.length - 1 && column < grid.moneyness.length - 1) {
        const a = row * grid.moneyness.length + column;
        const b = a + grid.moneyness.length;
        indices.push(a, a + 1, b, a + 1, b + 1, b);
      }
    }
  return { positions, colors, indices };
}
export function meshLines(grid: SurfaceGrid): Vec3[][] {
  return [
    ...grid.tenors.map((_, row) =>
      grid.moneyness.map((_, column) => positionOf(grid, row, column)),
    ),
    ...grid.moneyness.map((_, column) =>
      grid.tenors.map((_, row) => positionOf(grid, row, column)),
    ),
  ].map((line) => line.map(([x, y, z]) => [x, y + 0.006, z] as Vec3));
}
export function selectedLines(
  grid: SurfaceGrid,
  selected: PointIndex,
): Vec3[][] {
  return [
    grid.moneyness.map((_, column) => positionOf(grid, selected.row, column)),
    grid.tenors.map((_, row) => positionOf(grid, row, selected.column)),
  ].map((line) => line.map(([x, y, z]) => [x, y + 0.015, z] as Vec3));
}
export function axes(grid: SurfaceGrid) {
  const lines: Vec3[][] = [];
  const labels: { position: Vec3; text: string; title?: boolean }[] = [];
  const { width: w, depth: d, height: h } = frame;
  for (let i = 0; i <= 4; i++) {
    const t = i / 4;
    const x = (t - 0.5) * w;
    const z = (0.5 - t) * d;
    lines.push(
      [
        [x, 0, -d / 2],
        [x, 0, d / 2],
      ],
      [
        [-w / 2, 0, z],
        [w / 2, 0, z],
      ],
    );
    labels.push({
      position: [x, -0.16, d / 2 + 0.22],
      text: `${((grid.domain.moneyness[0] + t * (grid.domain.moneyness[1] - grid.domain.moneyness[0])) * 100).toFixed(0)}%`,
    });
    if (i > 0 && i < 4)
      labels.push({
        position: [-w / 2 - 0.36, -0.08, z],
        text: (
          grid.domain.tenor[0] +
          t * (grid.domain.tenor[1] - grid.domain.tenor[0])
        ).toFixed(2),
      });
    const y = t * h;
    lines.push([
      [-w / 2, y, -d / 2],
      [-w / 2 + 0.08, y, -d / 2],
    ]);
    labels.push({
      position: [-w / 2 - 0.4, y, -d / 2 - 0.14],
      text: `${((grid.domain.iv[0] + t * (grid.domain.iv[1] - grid.domain.iv[0])) * 100).toFixed(1)}%`,
    });
  }
  lines.push(
    [
      [-w / 2, 0, -d / 2],
      [-w / 2, h, -d / 2],
    ],
    [
      [-w / 2, 0, d / 2],
      [w / 2, 0, d / 2],
    ],
    [
      [-w / 2, 0, d / 2],
      [-w / 2, 0, -d / 2],
    ],
  );
  labels.push(
    { position: [0, -0.52, d / 2 + 0.55], text: 'K / F', title: true },
    { position: [-w / 2 - 0.95, -0.3, 0], text: 'T（年）', title: true },
  );
  return { lines, labels };
}
