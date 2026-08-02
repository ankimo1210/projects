"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { chapters, glossary, type LabKind } from "../content/chapters";
import { drawExtendedLab, extendedMetrics } from "./extended-labs";

type Settings = {
  seed: number;
  steps: number;
  paths: number;
  mu: number;
  sigma: number;
  horizon: number;
  kappa: number;
  theta: number;
  time: number;
  rate: number;
  functionChoice: number;
  zoom: number;
  rho: number;
  sigma2: number;
  x0: number;
  strike: number;
  lowerBarrier: number;
  upperBarrier: number;
  selectedPath: number;
  localDt: number;
};

type Point = [number, number];
type Rect = { x: number; y: number; w: number; h: number };

const baseSettings: Settings = {
  seed: 20260802,
  steps: 128,
  paths: 32,
  mu: 0.08,
  sigma: 0.3,
  horizon: 1,
  kappa: 1.4,
  theta: 0,
  time: 0.65,
  rate: 0.03,
  functionChoice: 1,
  zoom: 3,
  rho: 0.65,
  sigma2: 0.45,
  x0: 0,
  strike: 0.3,
  lowerBarrier: -1,
  upperBarrier: 1,
  selectedPath: 2,
  localDt: 0.08,
};

const labDefaults: Partial<Record<LabKind, Partial<Settings>>> = {
  "sde-overview": { paths: 24, mu: 0.25, sigma: 0.45, sigma2: 0.35, time: 0.65, x0: 0 },
  "random-walk": { steps: 128, paths: 12, mu: 0.08, sigma: 0.3 },
  brownian: { steps: 256, paths: 8, mu: 0, sigma: 0.55 },
  "path-distribution": { steps: 160, paths: 48, sigma: 0.7, time: 0.55, selectedPath: 2 },
  roughness: { steps: 256, sigma: 1, time: 0.62, zoom: 3 },
  "quadratic-variation": { steps: 256, paths: 8, mu: 0, sigma: 1 },
  "stochastic-integral": { steps: 128, sigma: 1 },
  "ito-correction": { steps: 128, paths: 64, mu: 0, sigma: 0.7, functionChoice: 1 },
  "drift-diffusion": { steps: 160, paths: 24, mu: 0.2, sigma: 0.5, kappa: 1.2, theta: 0, functionChoice: 0, x0: 0.4 },
  "arithmetic-brownian": { steps: 160, paths: 40, x0: 0, mu: 0.3, sigma: 0.7, time: 0.65 },
  gbm: { steps: 160, paths: 40, mu: 0.08, sigma: 0.3 },
  ou: { steps: 160, paths: 24, sigma: 0.45, kappa: 1.4, theta: 0 },
  cir: { steps: 256, paths: 24, x0: 0.6, kappa: 1.4, theta: 0.6, sigma: 0.55 },
  "correlated-brownian": { steps: 160, paths: 64, mu: 0, sigma: 0.7, sigma2: 0.45, rho: 0.65 },
  generator: { paths: 64, x0: 0.4, mu: 0.2, sigma: 0.6, localDt: 0.08, functionChoice: 1 },
  "backward-equation": { x0: 0, mu: 0.15, sigma: 0.7, time: 0.35, strike: 0.3, functionChoice: 0 },
  "fokker-planck": { paths: 72, mu: 0.2, sigma: 0.5, time: 0.65 },
  "feynman-kac": { paths: 32, x0: 0.4, mu: 0.15, rate: 0.08, sigma: 0.55, horizon: 1 },
  "first-passage": { paths: 64, steps: 256, x0: 0, mu: 0.05, sigma: 0.65, lowerBarrier: -1, upperBarrier: 1 },
  euler: { steps: 24, paths: 16, mu: 0.08, sigma: 0.45 },
  "measure-change": { paths: 56, mu: 0.09, sigma: 0.2, rate: 0.03 },
  "brownian-default": { steps: 128, sigma: 0.6, horizon: 1 },
  "poisson-jumps": { kappa: 3, horizon: 2 },
  "levy-tails": { sigma: 0.6, sigma2: 0.7, kappa: 1.5, horizon: 2 },
  "colored-noise": { kappa: 3, sigma: 0.3, horizon: 2 },
  "fractional-brownian": { rho: 0.72, sigma: 0.7, horizon: 1 },
  hawkes: { rate: 0.5, sigma: 0.55, kappa: 1.4, horizon: 4 },
  milstein: { x0: 100, mu: 0.08, sigma: 0.35, steps: 32 },
  "monte-carlo": { strike: 1, paths: 32, functionChoice: 0 },
  "parameter-inference": {
    x0: -0.5,
    kappa: 1.2,
    theta: 0.5,
    sigma: 0.45,
    sigma2: 0.12,
    steps: 256,
    horizon: 8,
  },
  predictability: { mu: 0.08, sigma: 0.35, horizon: 3 },
  martingale: { x0: 100, strike: 100, mu: 0.08, rate: 0.03, sigma: 0.25, paths: 64 },
  "delta-hedging": { x0: 100, strike: 100, rate: 0.03, sigma: 0.25, steps: 32 },
  "volatility-models": { x0: 100, sigma: 0.25, sigma2: 0.5, rho: -0.6, kappa: 2 },
  "short-rate": { x0: 0.03, theta: 0.05, kappa: 1.2, sigma: 0.08, horizon: 5 },
  "forward-curve": { rate: 0.03, sigma: 0.02, kappa: 0.5 },
  "credit-default": { kappa: 0.25, rho: 0.4, horizon: 5 },
  langevin: { x0: 1, sigma: 0.6, kappa: 1.1, theta: 0.7, horizon: 6 },
  "chemical-reaction": { x0: 36, rate: 5, kappa: 0.25, sigma: 0.5, horizon: 8 },
  population: { x0: 12, theta: 80, rate: 0.8, sigma: 0.35, sigma2: 0.12, horizon: 8 },
  epidemic: { x0: 4, theta: 120, rate: 1.6, kappa: 0.65, horizon: 10 },
  neuroscience: { x0: -0.4, theta: 0.2, kappa: 2, sigma: 0.55, rho: 0.35, upperBarrier: 1, horizon: 6 },
  filtering: { x0: 0, kappa: 0.8, sigma: 0.45, sigma2: 0.7, horizon: 6 },
  "model-selection": { functionChoice: 0, kappa: 1.4, sigma: 0.45, sigma2: 0.35, horizon: 4 },
  "model-criticism": { functionChoice: 1, kappa: 1.4, sigma: 0.45, sigma2: 0.3, horizon: 4 },
  "sde-synthesis": { x0: 0.3, mu: 0.15, sigma: 0.5, kappa: 1.4, zoom: 3, horizon: 1 },
};

const chapterGroups = Array.from(new Set(chapters.map((chapter) => chapter.part)));

function mulberry32(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let x = value;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(random: () => number) {
  const u = Math.max(random(), Number.EPSILON);
  const v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function normalPdf(x: number, mean: number, sd: number) {
  const safeSd = Math.max(sd, 1e-6);
  const z = (x - mean) / safeSd;
  return Math.exp(-0.5 * z * z) / (safeSd * Math.sqrt(2 * Math.PI));
}

function normalCdf(value: number) {
  const sign = value < 0 ? -1 : 1;
  const x = Math.abs(value) / Math.sqrt(2);
  const t = 1 / (1 + 0.3275911 * x);
  const polynomial =
    (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
    t;
  const erf = sign * (1 - polynomial * Math.exp(-x * x));
  return 0.5 * (1 + erf);
}

function lognormalPdf(x: number, logMean: number, logSd: number) {
  if (x <= 0) return 0;
  return normalPdf(Math.log(x), logMean, logSd) / x;
}

function clamp(value: number, low: number, high: number) {
  return Math.min(Math.max(value, low), high);
}

function formatNumber(value: number, digits = 2) {
  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function formatPercent(value: number) {
  return `${formatNumber(value * 100, 0)}%`;
}

function chartColors(canvas: HTMLCanvasElement, dark = false) {
  if (dark) {
    return {
      ink: "#e8f0ed",
      muted: "#95aaa5",
      grid: "#34484b",
      paper: "#1a292d",
      teal: "#58c6b9",
      amber: "#efa85f",
      coral: "#ec8179",
      violet: "#a89fe8",
      white: "#142226",
    };
  }
  const style = getComputedStyle(canvas);
  return {
    ink: style.getPropertyValue("--plot-ink").trim() || "#142b33",
    muted: style.getPropertyValue("--plot-muted").trim() || "#60747a",
    grid: style.getPropertyValue("--plot-grid").trim() || "#dce3df",
    paper: style.getPropertyValue("--plot-paper").trim() || "#f8faf7",
    teal: style.getPropertyValue("--plot-teal").trim() || "#007f78",
    amber: style.getPropertyValue("--plot-amber").trim() || "#d77a25",
    coral: style.getPropertyValue("--plot-coral").trim() || "#d85f58",
    violet: style.getPropertyValue("--plot-violet").trim() || "#6f66b3",
    white: style.getPropertyValue("--plot-white").trim() || "#ffffff",
  };
}

function prepareCanvas(canvas: HTMLCanvasElement) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(canvas.clientWidth, 320);
  const height = Math.max(canvas.clientHeight, 360);
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function drawRoundedRect(
  context: CanvasRenderingContext2D,
  rect: Rect,
  radius: number,
  fill: string,
) {
  context.beginPath();
  context.roundRect(rect.x, rect.y, rect.w, rect.h, radius);
  context.fillStyle = fill;
  context.fill();
}

function drawChart(
  context: CanvasRenderingContext2D,
  rect: Rect,
  series: Array<{
    points: Point[];
    color: string;
    width?: number;
    dashed?: boolean;
    alpha?: number;
  }>,
  domain: { x: [number, number]; y: [number, number] },
  colors: ReturnType<typeof chartColors>,
  options?: { xLabel?: string; yLabel?: string; zeroLine?: boolean },
) {
  const padding = { left: 42, right: 12, top: 14, bottom: 32 };
  const plot = {
    x: rect.x + padding.left,
    y: rect.y + padding.top,
    w: rect.w - padding.left - padding.right,
    h: rect.h - padding.top - padding.bottom,
  };
  const xSpan = Math.max(domain.x[1] - domain.x[0], 1e-9);
  const ySpan = Math.max(domain.y[1] - domain.y[0], 1e-9);
  const xMap = (value: number) => plot.x + ((value - domain.x[0]) / xSpan) * plot.w;
  const yMap = (value: number) => plot.y + plot.h - ((value - domain.y[0]) / ySpan) * plot.h;

  context.save();
  context.strokeStyle = colors.grid;
  context.lineWidth = 1;
  context.fillStyle = colors.muted;
  context.font = "11px ui-monospace, SFMono-Regular, Consolas, monospace";
  for (let index = 0; index <= 4; index += 1) {
    const x = plot.x + (plot.w * index) / 4;
    const y = plot.y + (plot.h * index) / 4;
    context.beginPath();
    context.moveTo(x, plot.y);
    context.lineTo(x, plot.y + plot.h);
    context.stroke();
    context.beginPath();
    context.moveTo(plot.x, y);
    context.lineTo(plot.x + plot.w, y);
    context.stroke();
  }
  if (options?.zeroLine && domain.y[0] < 0 && domain.y[1] > 0) {
    context.strokeStyle = colors.muted;
    context.setLineDash([4, 4]);
    context.beginPath();
    context.moveTo(plot.x, yMap(0));
    context.lineTo(plot.x + plot.w, yMap(0));
    context.stroke();
    context.setLineDash([]);
  }

  context.fillText(formatNumber(domain.y[1], 1), rect.x + 2, plot.y + 4);
  context.fillText(formatNumber(domain.y[0], 1), rect.x + 2, plot.y + plot.h);
  context.fillText(formatNumber(domain.x[0], 1), plot.x, rect.y + rect.h - 8);
  const maxX = formatNumber(domain.x[1], 1);
  context.fillText(maxX, plot.x + plot.w - context.measureText(maxX).width, rect.y + rect.h - 8);
  if (options?.xLabel) {
    const labelWidth = context.measureText(options.xLabel).width;
    context.fillText(options.xLabel, plot.x + (plot.w - labelWidth) / 2, rect.y + rect.h - 8);
  }

  context.beginPath();
  context.rect(plot.x, plot.y, plot.w, plot.h);
  context.clip();
  for (const item of series) {
    if (!item.points.length) continue;
    context.beginPath();
    item.points.forEach(([x, y], index) => {
      if (index === 0) context.moveTo(xMap(x), yMap(y));
      else context.lineTo(xMap(x), yMap(y));
    });
    context.strokeStyle = item.color;
    context.globalAlpha = item.alpha ?? 1;
    context.lineWidth = item.width ?? 2;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.setLineDash(item.dashed ? [6, 5] : []);
    context.stroke();
  }
  context.restore();
}

function yDomain(series: Point[][], padding = 0.12): [number, number] {
  const values = series.flatMap((points) => points.map((point) => point[1]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 0.5);
  return [min - span * padding, max + span * padding];
}

function drawLabel(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  color: string,
  align: CanvasTextAlign = "left",
) {
  context.save();
  context.fillStyle = color;
  context.font = "600 12px ui-sans-serif, system-ui, sans-serif";
  context.textAlign = align;
  context.fillText(text, x, y);
  context.restore();
}

function drawSdeOverview(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const random = mulberry32(settings.seed + 11);
  const steps = 120;
  const dt = settings.horizon / steps;
  const count = Math.min(settings.paths, 18);
  const fixed: Point[][] = [];
  const uncertain: Point[][] = [];
  const stochastic: Point[][] = [];
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    const uncertainInitial = settings.x0 + settings.sigma2 * normal(random);
    let stochasticValue = settings.x0;
    const fixedPath: Point[] = [[0, settings.x0]];
    const uncertainPath: Point[] = [[0, uncertainInitial]];
    const stochasticPath: Point[] = [[0, stochasticValue]];
    for (let index = 0; index < steps; index += 1) {
      const time = (index + 1) * dt;
      fixedPath.push([time, settings.x0 + settings.mu * time]);
      uncertainPath.push([time, uncertainInitial + settings.mu * time]);
      stochasticValue += settings.mu * dt + settings.sigma * Math.sqrt(dt) * normal(random);
      stochasticPath.push([time, stochasticValue]);
    }
    fixed.push(fixedPath);
    uncertain.push(uncertainPath);
    stochastic.push(stochasticPath);
  }

  const selectedTime = settings.time * settings.horizon;
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.67 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const panelGap = 8;
  const panelHeight = (left.h - panelGap * 2) / 3;
  const definitions = [
    { label: "固定初期値の ODE", paths: fixed, color: colors.muted },
    { label: "初期値だけ不確実", paths: uncertain, color: colors.amber },
    { label: "連続ショックの SDE", paths: stochastic, color: colors.teal },
  ];
  const sharedDomain = yDomain([...fixed, ...uncertain, ...stochastic], 0.08);
  definitions.forEach((definition, panelIndex) => {
    const panel = {
      x: left.x,
      y: left.y + panelIndex * (panelHeight + panelGap),
      w: left.w,
      h: panelHeight,
    };
    drawRoundedRect(context, panel, 12, colors.paper);
    drawChart(
      context,
      panel,
      [
        ...definition.paths.map((points, index) => ({
          points,
          color: definition.color,
          width: index === 0 ? 2 : 1,
          alpha: index === 0 ? 1 : 0.28,
        })),
        {
          points: [[selectedTime, sharedDomain[0]], [selectedTime, sharedDomain[1]]] as Point[],
          color: colors.coral,
          width: 1.2,
          dashed: true,
        },
      ],
      { x: [0, settings.horizon], y: sharedDomain },
      colors,
      { xLabel: panelIndex === 2 ? "時間 t" : undefined, zeroLine: true },
    );
    drawLabel(context, definition.label, panel.x + 52, panel.y + 18, definition.color);
  });

  const mean = settings.x0 + settings.mu * selectedTime;
  const initialSd = Math.max(settings.sigma2, 1e-3);
  const processSd = Math.max(settings.sigma * Math.sqrt(selectedTime), 1e-3);
  const span = Math.max(initialSd, processSd, 0.1);
  const densityDomain: [number, number] = [mean - 3.8 * span, mean + 3.8 * span];
  const density = (sd: number): Point[] => Array.from({ length: 121 }, (_, index) => {
    const x = densityDomain[0] + (index / 120) * (densityDomain[1] - densityDomain[0]);
    return [x, normalPdf(x, mean, sd)];
  });
  const initialDensity = density(initialSd);
  const processDensity = density(processSd);
  const densityUpper =
    Math.max(
      ...initialDensity.map((point) => point[1]),
      ...processDensity.map((point) => point[1]),
    ) * 1.12;
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: [[mean, 0], [mean, densityUpper]], color: colors.muted, width: 1.7, dashed: true },
      { points: initialDensity, color: colors.amber, width: 2.2 },
      { points: processDensity, color: colors.teal, width: 2.2 },
    ],
    {
      x: densityDomain,
      y: [0, densityUpper],
    },
    colors,
    { xLabel: `時刻 ${formatNumber(selectedTime, 2)} の状態` },
  );
  drawLabel(context, "横断分布", right.x + 52, right.y + 18, colors.ink);
  drawLabel(context, "初期値", right.x + 126, right.y + 18, colors.amber);
  drawLabel(context, "SDE", right.x + right.w - 14, right.y + 18, colors.teal, "right");
}

function drawRandomWalk(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const random = mulberry32(settings.seed);
  const steps = Math.max(settings.steps, 16);
  const dt = settings.horizon / steps;
  const shocks = Array.from({ length: steps }, () => normal(random));
  const definitions = [
    { label: "Δt — 揺らぎが消える", scale: dt, color: colors.violet },
    { label: "√Δt — 揺らぎが残る", scale: Math.sqrt(dt), color: colors.teal },
    { label: "無尺度 — 揺らぎが爆発", scale: 1, color: colors.coral },
  ];
  const gap = 14;
  const height = (area.h - gap * 2) / 3;
  const expectedEnd = settings.mu * settings.horizon;
  const referenceSpan = Math.max(3.5 * settings.sigma * Math.sqrt(settings.horizon), 0.6);
  const sharedDomain: [number, number] = [
    Math.min(0, expectedEnd) - referenceSpan,
    Math.max(0, expectedEnd) + referenceSpan,
  ];

  definitions.forEach((definition, panelIndex) => {
    let value = 0;
    const points: Point[] = [[0, value]];
    shocks.forEach((shock, index) => {
      value += settings.mu * dt + settings.sigma * definition.scale * shock;
      points.push([(index + 1) * dt, value]);
    });
    const panel = { x: area.x, y: area.y + panelIndex * (height + gap), w: area.w, h: height };
    drawRoundedRect(context, panel, 12, colors.paper);
    drawLabel(
      context,
      `${definition.label}   Xₜ=${formatNumber(value, 2)}`,
      panel.x + 14,
      panel.y + 18,
      definition.color,
    );
    drawChart(
      context,
      { x: panel.x + 2, y: panel.y + 20, w: panel.w - 4, h: panel.h - 20 },
      [{ points, color: definition.color, width: 1.8 }],
      { x: [0, settings.horizon], y: sharedDomain },
      colors,
      { zeroLine: true, xLabel: panelIndex === 2 ? "時間 t" : undefined },
    );
  });
}

function drawBrownian(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const fineSteps = 4096;
  const random = mulberry32(settings.seed);
  const dt = settings.horizon / fineSteps;
  const cumulative = [0];
  for (let index = 0; index < fineSteps; index += 1) {
    cumulative.push(cumulative[index] + Math.sqrt(dt) * normal(random));
  }
  const resolutions = Array.from(new Set([16, 64, settings.steps])).sort((a, b) => a - b);
  const allSeries = resolutions.map((resolution) => {
    const points: Point[] = [];
    for (let index = 0; index <= resolution; index += 1) {
      const fineIndex = Math.round((index / resolution) * fineSteps);
      points.push([(index / resolution) * settings.horizon, cumulative[fineIndex]]);
    }
    const isSelected = resolution === settings.steps;
    const color = isSelected ? colors.teal : resolution === 16 ? colors.amber : colors.violet;
    return { points, color, width: isSelected ? 2.4 : 1.5 };
  });
  drawRoundedRect(context, area, 16, colors.paper);
  drawChart(
    context,
    area,
    allSeries,
    { x: [0, settings.horizon], y: yDomain(allSeries.map((item) => item.points), 0.16) },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "16 分割", area.x + 54, area.y + 18, settings.steps === 16 ? colors.teal : colors.amber);
  drawLabel(context, "64 分割", area.x + 126, area.y + 18, settings.steps === 64 ? colors.teal : colors.violet);
  if (settings.steps !== 64) {
    drawLabel(context, `${settings.steps} 分割`, area.x + 200, area.y + 18, colors.teal);
  }
}

function pathDistributionDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 29);
  const steps = Math.max(settings.steps, 32);
  const count = Math.max(settings.paths, 16);
  const dt = settings.horizon / steps;
  const selectedIndex = clamp(Math.round(settings.time * steps), 1, steps);
  const paths: Point[][] = [];
  const crossSection: number[] = [];
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let value = 0;
    const points: Point[] = [[0, 0]];
    for (let index = 0; index < steps; index += 1) {
      value += settings.sigma * Math.sqrt(dt) * normal(random);
      points.push([(index + 1) * dt, value]);
      if (index + 1 === selectedIndex) crossSection.push(value);
    }
    paths.push(points);
  }
  const mean = crossSection.reduce((sum, value) => sum + value, 0) / crossSection.length;
  const variance = crossSection.reduce((sum, value) => sum + (value - mean) ** 2, 0) /
    Math.max(crossSection.length - 1, 1);
  return {
    paths,
    crossSection,
    selectedIndex,
    selectedTime: selectedIndex * dt,
    selectedPath: clamp(Math.round(settings.selectedPath), 0, paths.length - 1),
    mean,
    variance,
  };
}

function drawPathDistribution(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = pathDistributionDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.66 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const selected = diagnostics.paths[diagnostics.selectedPath];
  const history = selected.slice(0, diagnostics.selectedIndex + 1);
  const future = selected.slice(diagnostics.selectedIndex);
  const domain = yDomain(diagnostics.paths, 0.1);
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...diagnostics.paths.map((points, index) => ({
        points,
        color: colors.violet,
        width: 0.9,
        alpha: index === diagnostics.selectedPath ? 0 : 0.18,
      })),
      { points: history, color: colors.teal, width: 2.5 },
      { points: future, color: colors.amber, width: 1.8, dashed: true },
      {
        points: [[diagnostics.selectedTime, domain[0]], [diagnostics.selectedTime, domain[1]]],
        color: colors.coral,
        width: 1.3,
        dashed: true,
      },
    ],
    { x: [0, settings.horizon], y: domain },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, `経路 ${diagnostics.selectedPath + 1} · 既知`, left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "未来", left.x + 148, left.y + 18, colors.amber);

  const theoreticalSd = settings.sigma * Math.sqrt(diagnostics.selectedTime);
  const xMin = -3.8 * theoreticalSd;
  const xMax = 3.8 * theoreticalSd;
  const bins = 20;
  const counts = Array.from({ length: bins }, () => 0);
  diagnostics.crossSection.forEach((value) => {
    const index = clamp(Math.floor(((value - xMin) / (xMax - xMin)) * bins), 0, bins - 1);
    counts[index] += 1;
  });
  const histogram: Point[] = counts.flatMap((count, index) => {
    const leftEdge = xMin + (index / bins) * (xMax - xMin);
    const rightEdge = xMin + ((index + 1) / bins) * (xMax - xMin);
    const density = count / diagnostics.crossSection.length / ((xMax - xMin) / bins);
    return [[leftEdge, density], [rightEdge, density]] as Point[];
  });
  const exact: Point[] = Array.from({ length: 121 }, (_, index) => {
    const x = xMin + (index / 120) * (xMax - xMin);
    return [x, normalPdf(x, 0, theoreticalSd)];
  });
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: histogram, color: colors.violet, width: 1.5, alpha: 0.72 },
      { points: exact, color: colors.teal, width: 2.5 },
    ],
    { x: [xMin, xMax], y: [0, Math.max(...exact.map((point) => point[1])) * 1.2] },
    colors,
    { xLabel: `時刻 ${formatNumber(diagnostics.selectedTime, 2)} の Wₜ` },
  );
  drawLabel(context, "横断標本", right.x + 52, right.y + 18, colors.violet);
  drawLabel(context, "N(0, t)", right.x + right.w - 14, right.y + 18, colors.teal, "right");
}

function roughnessDiagnostics(settings: Settings) {
  const fineSteps = 4096;
  const random = mulberry32(settings.seed + 41);
  const dt = settings.horizon / fineSteps;
  const path: Point[] = [[0, 0]];
  let value = 0;
  for (let index = 0; index < fineSteps; index += 1) {
    value += settings.sigma * Math.sqrt(dt) * normal(random);
    path.push([(index + 1) * dt, value]);
  }

  const zoom = clamp(Math.round(settings.zoom), 0, 6);
  const window = settings.horizon / 2 ** zoom;
  const center = settings.time * settings.horizon;
  const requestedStart = clamp(center - window / 2, 0, settings.horizon - window);
  const startIndex = clamp(Math.round(requestedStart / dt), 0, fineSteps - 1);
  const endIndex = clamp(Math.round((requestedStart + window) / dt), startIndex + 1, fineSteps);
  const start = path[startIndex][0];
  const end = path[endIndex][0];
  const startValue = path[startIndex][1];
  const brownianSegment = path.slice(startIndex, endIndex + 1);
  const smoothAt = (time: number) => 0.8 * Math.sin((2 * Math.PI * time) / settings.horizon);
  const smoothStart = smoothAt(start);
  const smoothSegment: Point[] = brownianSegment.map(([time]) => [
    time,
    startValue + smoothAt(time) - smoothStart,
  ]);
  const duration = Math.max(end - start, dt);
  const brownianSlope = Math.abs((path[endIndex][1] - startValue) / duration);
  const smoothSlope = Math.abs((smoothAt(end) - smoothStart) / duration);
  return {
    path,
    start,
    end,
    window: duration,
    brownianSegment,
    smoothSegment,
    brownianSlope,
    smoothSlope,
  };
}

function drawRoughness(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = roughnessDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.43 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const overviewDomain = yDomain([diagnostics.path], 0.12);
  const selectionLines: Point[][] = [diagnostics.start, diagnostics.end].map((time) => [
    [time, overviewDomain[0]],
    [time, overviewDomain[1]],
  ]);

  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: diagnostics.path, color: colors.teal, width: 1.7 },
      ...selectionLines.map((points) => ({
        points,
        color: colors.amber,
        width: 1.4,
        dashed: true,
      })),
    ],
    { x: [0, settings.horizon], y: overviewDomain },
    colors,
    { xLabel: "全区間 t", zeroLine: true },
  );
  drawLabel(context, "元の経路", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "選択区間", left.x + left.w - 14, left.y + 18, colors.amber, "right");

  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: diagnostics.brownianSegment, color: colors.teal, width: 2.4 },
      { points: diagnostics.smoothSegment, color: colors.coral, width: 2, dashed: true },
    ],
    {
      x: [diagnostics.start, diagnostics.end],
      y: yDomain([diagnostics.brownianSegment, diagnostics.smoothSegment], 0.16),
    },
    colors,
    { xLabel: "拡大した時間 t", zeroLine: true },
  );
  drawLabel(context, `Brownian · ×${2 ** Math.round(settings.zoom)}`, right.x + 52, right.y + 18, colors.teal);
  drawLabel(context, "滑らかな正弦波", right.x + 172, right.y + 18, colors.coral);
}

function drawQuadraticVariation(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const random = mulberry32(settings.seed);
  const fineSteps = 4096;
  const fineDt = settings.horizon / fineSteps;
  const cumulative = [0];
  for (let index = 0; index < fineSteps; index += 1) {
    cumulative.push(cumulative[index] + Math.sqrt(fineDt) * normal(random));
  }
  let qv = 0;
  let smoothQv = 0;
  const brownian: Point[] = [[0, 0]];
  const smooth: Point[] = [[0, 0]];
  const target: Point[] = [[0, 0]];
  for (let index = 0; index < settings.steps; index += 1) {
    const fineStart = Math.round((index / settings.steps) * fineSteps);
    const fineEnd = Math.round(((index + 1) / settings.steps) * fineSteps);
    const t0 = fineStart * fineDt;
    const t1 = fineEnd * fineDt;
    const increment = cumulative[fineEnd] - cumulative[fineStart];
    qv += increment * increment;
    const smoothIncrement = Math.sin(2 * Math.PI * t1) - Math.sin(2 * Math.PI * t0);
    smoothQv += smoothIncrement * smoothIncrement;
    brownian.push([t1, qv]);
    smooth.push([t1, smoothQv]);
    target.push([t1, t1]);
  }
  drawRoundedRect(context, area, 16, colors.paper);
  const upper = Math.max(settings.horizon * 1.35, ...brownian.map((point) => point[1])) * 1.05;
  drawChart(
    context,
    area,
    [
      { points: target, color: colors.muted, width: 1.5, dashed: true },
      { points: brownian, color: colors.teal, width: 2.4 },
      { points: smooth, color: colors.coral, width: 1.7 },
    ],
    { x: [0, settings.horizon], y: [0, upper] },
    colors,
    { xLabel: "時間 t" },
  );
  drawLabel(context, "Brownian Σ(ΔW)²", area.x + 54, area.y + 18, colors.teal);
  drawLabel(context, "y=t", area.x + 192, area.y + 18, colors.muted);
  drawLabel(context, "smooth", area.x + 236, area.y + 18, colors.coral);
}

function stochasticIntegralDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 79);
  const steps = Math.max(settings.steps, 8);
  const dt = settings.horizon / steps;
  let w = 0;
  let left = 0;
  let midpoint = 0;
  let right = 0;
  let quadraticVariation = 0;
  const leftPoints: Point[] = [[0, 0]];
  const midpointPoints: Point[] = [[0, 0]];
  const rightPoints: Point[] = [[0, 0]];
  for (let index = 0; index < steps; index += 1) {
    const increment = Math.sqrt(dt) * normal(random);
    const next = w + increment;
    left += w * increment;
    midpoint += ((w + next) / 2) * increment;
    right += next * increment;
    quadraticVariation += increment * increment;
    w = next;
    const time = (index + 1) * dt;
    leftPoints.push([time, left]);
    midpointPoints.push([time, midpoint]);
    rightPoints.push([time, right]);
  }
  return {
    left,
    midpoint,
    right,
    quadraticVariation,
    leftPoints,
    midpointPoints,
    rightPoints,
    limits: [
      0.5 * (w * w - settings.horizon),
      0.5 * w * w,
      0.5 * (w * w + settings.horizon),
    ],
  };
}

function drawStochasticIntegral(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = stochasticIntegralDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.66 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: diagnostics.leftPoints, color: colors.teal, width: 2.2 },
      { points: diagnostics.midpointPoints, color: colors.amber, width: 2.2 },
      { points: diagnostics.rightPoints, color: colors.violet, width: 2.2 },
    ],
    {
      x: [0, settings.horizon],
      y: yDomain(
        [diagnostics.leftPoints, diagnostics.midpointPoints, diagnostics.rightPoints],
        0.14,
      ),
    },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "左端 · Itô", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "中点 · Stratonovich", left.x + 132, left.y + 18, colors.amber);
  drawLabel(context, "右端", left.x + 270, left.y + 18, colors.violet);

  const observed: Point[] = [
    [0, diagnostics.left],
    [1, diagnostics.midpoint],
    [2, diagnostics.right],
  ];
  const theoretical: Point[] = diagnostics.limits.map((value, index) => [index, value]);
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: theoretical, color: colors.muted, width: 1.5, dashed: true },
      { points: observed, color: colors.coral, width: 2.4 },
    ],
    { x: [-0.2, 2.2], y: yDomain([observed, theoretical], 0.18) },
    colors,
    { xLabel: "左端       中点       右端", zeroLine: true },
  );
  drawLabel(context, "有限分割", right.x + 52, right.y + 18, colors.coral);
  drawLabel(context, "極限", right.x + right.w - 14, right.y + 18, colors.muted, "right");
}

function drawItoCorrection(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const functions = [
    {
      value: (x: number) => x,
      expected: () => 0,
      baseline: 0,
      theoryLabel: "Itô: 補正 0",
    },
    {
      value: (x: number) => Math.exp(x),
      expected: (sigma: number, t: number) => Math.exp(0.5 * sigma * sigma * t),
      baseline: 1,
      theoryLabel: "Itô: 正の曲率補正",
    },
    {
      value: (x: number) => -Math.exp(-x),
      expected: (sigma: number, t: number) => -Math.exp(0.5 * sigma * sigma * t),
      baseline: -1,
      theoryLabel: "Itô: 負の曲率補正",
    },
  ];
  const selected = functions[clamp(Math.round(settings.functionChoice), 0, functions.length - 1)];
  const random = mulberry32(settings.seed);
  const pointsCount = 42;
  const samples = Math.max(settings.paths * 24, 600);
  const empirical: Point[] = [];
  const ito: Point[] = [];
  const naive: Point[] = [];
  for (let index = 0; index <= pointsCount; index += 1) {
    const t = (settings.horizon * index) / pointsCount;
    let total = 0;
    for (let sample = 0; sample < samples; sample += 1) {
      total += selected.value(settings.sigma * Math.sqrt(t) * normal(random));
    }
    empirical.push([t, total / samples]);
    ito.push([t, selected.expected(settings.sigma, t)]);
    naive.push([t, selected.baseline]);
  }
  drawRoundedRect(context, area, 16, colors.paper);
  drawChart(
    context,
    area,
    [
      { points: naive, color: colors.muted, width: 1.5, dashed: true },
      { points: ito, color: colors.amber, width: 2.5 },
      { points: empirical, color: colors.teal, width: 1.8 },
    ],
    { x: [0, settings.horizon], y: yDomain([empirical, ito, naive], 0.18) },
    colors,
    { xLabel: "時間 t" },
  );
  drawLabel(context, "Monte Carlo", area.x + 54, area.y + 18, colors.teal);
  drawLabel(context, selected.theoryLabel, area.x + 148, area.y + 18, colors.amber);
  drawLabel(context, "通常の連鎖律", area.x + 300, area.y + 18, colors.muted);
}

function driftDiffusionCoefficients(settings: Settings, state: number) {
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  if (choice === 1) {
    return { drift: settings.kappa * (settings.theta - state), diffusion: settings.sigma };
  }
  if (choice === 2) {
    return { drift: settings.mu * state, diffusion: settings.sigma * Math.abs(state) };
  }
  return { drift: settings.mu, diffusion: settings.sigma };
}

function driftDiffusionDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 101);
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  const steps = Math.max(settings.steps, 32);
  const dt = settings.horizon / steps;
  const paths: Point[][] = [];
  for (let pathIndex = 0; pathIndex < Math.min(settings.paths, 20); pathIndex += 1) {
    let value = settings.x0;
    const points: Point[] = [[0, value]];
    for (let index = 0; index < steps; index += 1) {
      const shock = normal(random);
      if (choice === 1) {
        const decay = Math.exp(-settings.kappa * dt);
        const sd = settings.sigma * Math.sqrt((1 - decay * decay) / (2 * settings.kappa));
        value = settings.theta + (value - settings.theta) * decay + sd * shock;
      } else if (choice === 2) {
        value *= Math.exp(
          (settings.mu - 0.5 * settings.sigma ** 2) * dt + settings.sigma * Math.sqrt(dt) * shock,
        );
      } else {
        value += settings.mu * dt + settings.sigma * Math.sqrt(dt) * shock;
      }
      points.push([(index + 1) * dt, value]);
    }
    paths.push(points);
  }
  return { paths, choice };
}

function drawDriftDiffusion(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = driftDiffusionDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.48 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const xCenter = diagnostics.choice === 1 ? settings.theta : settings.x0;
  const xSpan = diagnostics.choice === 2 ? Math.max(Math.abs(settings.x0) * 1.6, 0.8) : 1.6;
  const xDomain: [number, number] = [xCenter - xSpan, xCenter + xSpan];
  const shortDt = 0.06;
  const meanIncrement: Point[] = [];
  const upper: Point[] = [];
  const lower: Point[] = [];
  for (let index = 0; index <= 100; index += 1) {
    const state = xDomain[0] + (index / 100) * (xDomain[1] - xDomain[0]);
    const coefficients = driftDiffusionCoefficients(settings, state);
    const mean = coefficients.drift * shortDt;
    const sd = coefficients.diffusion * Math.sqrt(shortDt);
    meanIncrement.push([state, mean]);
    upper.push([state, mean + 1.96 * sd]);
    lower.push([state, mean - 1.96 * sd]);
  }
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: upper, color: colors.amber, width: 1.5, dashed: true },
      { points: lower, color: colors.amber, width: 1.5, dashed: true },
      { points: meanIncrement, color: colors.coral, width: 2.5 },
    ],
    { x: xDomain, y: yDomain([upper, lower, meanIncrement], 0.12) },
    colors,
    { xLabel: "現在状態 x", yLabel: "短時間増分", zeroLine: true },
  );
  drawLabel(context, "局所平均 b(x)Δt", left.x + 52, left.y + 18, colors.coral);
  drawLabel(context, "95% 幅", left.x + left.w - 14, left.y + 18, colors.amber, "right");

  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    diagnostics.paths.map((points, index) => ({
      points,
      color: index === 0 ? colors.teal : colors.violet,
      width: index === 0 ? 2.5 : 1,
      alpha: index === 0 ? 1 : 0.25,
    })),
    { x: [0, settings.horizon], y: yDomain(diagnostics.paths, 0.12) },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  const labels = ["加法ノイズ", "平均回帰", "乗法ノイズ"];
  drawLabel(context, labels[diagnostics.choice], right.x + 52, right.y + 18, colors.teal);
}

function arithmeticBrownianDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 127);
  const steps = Math.max(settings.steps, 32);
  const dt = settings.horizon / steps;
  const paths: Point[][] = [];
  for (let pathIndex = 0; pathIndex < Math.min(settings.paths, 24); pathIndex += 1) {
    let value = settings.x0;
    const points: Point[] = [[0, value]];
    for (let index = 0; index < steps; index += 1) {
      value += settings.mu * dt + settings.sigma * Math.sqrt(dt) * normal(random);
      points.push([(index + 1) * dt, value]);
    }
    paths.push(points);
  }
  const selectedTime = Math.max(settings.time * settings.horizon, 0.01);
  return { paths, selectedTime };
}

function drawArithmeticBrownian(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = arithmeticBrownianDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.64 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const meanPath: Point[] = [];
  const upperBand: Point[] = [];
  const lowerBand: Point[] = [];
  for (let index = 0; index <= 100; index += 1) {
    const time = (index / 100) * settings.horizon;
    const mean = settings.x0 + settings.mu * time;
    const halfWidth = 1.96 * settings.sigma * Math.sqrt(time);
    meanPath.push([time, mean]);
    upperBand.push([time, mean + halfWidth]);
    lowerBand.push([time, mean - halfWidth]);
  }
  const pathDomain = yDomain([...diagnostics.paths, upperBand, lowerBand], 0.1);
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...diagnostics.paths.map((points, index) => ({
        points,
        color: index === 0 ? colors.teal : colors.violet,
        width: index === 0 ? 2.4 : 1,
        alpha: index === 0 ? 1 : 0.24,
      })),
      { points: upperBand, color: colors.amber, width: 1.3, dashed: true },
      { points: lowerBand, color: colors.amber, width: 1.3, dashed: true },
      { points: meanPath, color: colors.coral, width: 2.2 },
      {
        points: [[diagnostics.selectedTime, pathDomain[0]], [diagnostics.selectedTime, pathDomain[1]]],
        color: colors.coral,
        width: 1.3,
        dashed: true,
      },
    ],
    { x: [0, settings.horizon], y: pathDomain },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "算術 Brownian 経路", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "解析平均", left.x + 178, left.y + 18, colors.coral);
  drawLabel(context, "95% 帯", left.x + left.w - 14, left.y + 18, colors.amber, "right");

  const times = [diagnostics.selectedTime / 3, diagnostics.selectedTime, settings.horizon];
  const maxTime = Math.max(...times);
  const center = settings.x0 + settings.mu * maxTime;
  const span = 4 * settings.sigma * Math.sqrt(maxTime);
  const xDomain: [number, number] = [center - span, center + span];
  const palette = [colors.violet, colors.amber, colors.teal];
  const densities = times.map((time) => Array.from({ length: 121 }, (_, index) => {
    const x = xDomain[0] + (index / 120) * (xDomain[1] - xDomain[0]);
    return [x, normalPdf(x, settings.x0 + settings.mu * time, settings.sigma * Math.sqrt(time))] as Point;
  }));
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    densities.map((points, index) => ({ points, color: palette[index], width: 2.1 })),
    { x: xDomain, y: [0, Math.max(...densities.flat().map((point) => point[1])) * 1.1] },
    colors,
    { xLabel: "状態 x" },
  );
  times.forEach((time, index) => {
    drawLabel(
      context,
      `t=${formatNumber(time, 2)}`,
      right.x + 52 + index * 70,
      right.y + 18,
      palette[index],
    );
  });
}

function simulateGbmPaths(settings: Settings, count: number) {
  const random = mulberry32(settings.seed);
  const dt = settings.horizon / settings.steps;
  const paths: Point[][] = [];
  const terminal: number[] = [];
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let price = 100;
    const points: Point[] = [[0, price]];
    for (let index = 0; index < settings.steps; index += 1) {
      price *= Math.exp(
        (settings.mu - 0.5 * settings.sigma * settings.sigma) * dt +
          settings.sigma * Math.sqrt(dt) * normal(random),
      );
      points.push([((index + 1) / settings.steps) * settings.horizon, price]);
    }
    paths.push(points);
    terminal.push(price);
  }
  return { paths, terminal };
}

function drawHistogram(
  context: CanvasRenderingContext2D,
  rect: Rect,
  values: number[],
  colors: ReturnType<typeof chartColors>,
  color: string,
  markers: Array<{ value: number; color: string; label: string }> = [],
) {
  const bins = 16;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const counts = Array.from({ length: bins }, () => 0);
  values.forEach((value) => {
    const index = clamp(Math.floor(((value - min) / span) * bins), 0, bins - 1);
    counts[index] += 1;
  });
  const peak = Math.max(...counts, 1);
  drawRoundedRect(context, rect, 14, colors.paper);
  const plot = { x: rect.x + 18, y: rect.y + 34, w: rect.w - 34, h: rect.h - 66 };
  counts.forEach((count, index) => {
    const barWidth = plot.w / bins;
    const barHeight = (count / peak) * plot.h;
    context.globalAlpha = 0.78;
    context.fillStyle = color;
    context.fillRect(plot.x + index * barWidth + 1, plot.y + plot.h - barHeight, Math.max(barWidth - 2, 1), barHeight);
  });
  context.globalAlpha = 1;
  markers.forEach((marker, index) => {
    const x = plot.x + ((marker.value - min) / span) * plot.w;
    context.strokeStyle = marker.color;
    context.setLineDash(index === 0 ? [] : [4, 3]);
    context.beginPath();
    context.moveTo(x, plot.y);
    context.lineTo(x, plot.y + plot.h);
    context.stroke();
    context.setLineDash([]);
  });
  drawLabel(context, "終端分布", rect.x + 18, rect.y + 20, colors.ink);
  drawLabel(context, formatNumber(min, 0), plot.x, rect.y + rect.h - 12, colors.muted);
  drawLabel(context, formatNumber(max, 0), plot.x + plot.w, rect.y + rect.h - 12, colors.muted, "right");
}

function drawGbm(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const { paths } = simulateGbmPaths(settings, Math.min(settings.paths, 24));
  const distribution = simulateGbmPaths({ ...settings, seed: settings.seed + 71 }, Math.max(settings.paths * 16, 500));
  const gap = 16;
  const left = { x: area.x, y: area.y, w: area.w * 0.65 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    paths.map((points, index) => ({
      points,
      color: index === 0 ? colors.amber : colors.teal,
      width: index === 0 ? 2.5 : 1.1,
      alpha: index === 0 ? 1 : 0.32,
    })),
    { x: [0, settings.horizon], y: yDomain(paths, 0.1) },
    colors,
    { xLabel: "時間 t" },
  );
  const mean = 100 * Math.exp(settings.mu * settings.horizon);
  const median = 100 * Math.exp((settings.mu - 0.5 * settings.sigma ** 2) * settings.horizon);
  drawHistogram(context, right, distribution.terminal, colors, colors.teal, [
    { value: mean, color: colors.amber, label: "平均" },
    { value: median, color: colors.violet, label: "中央値" },
  ]);
  drawLabel(context, "平均", right.x + 18, right.y + right.h - 34, colors.amber);
  drawLabel(context, "中央値", right.x + 58, right.y + right.h - 34, colors.violet);
}

function drawOu(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const random = mulberry32(settings.seed);
  const dt = settings.horizon / settings.steps;
  const decay = Math.exp(-settings.kappa * dt);
  const stepSd = settings.sigma * Math.sqrt((1 - decay * decay) / (2 * settings.kappa));
  const x0 = 1.2;
  const count = Math.min(settings.paths, 18);
  const paths: Point[][] = [];
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let x = x0;
    const points: Point[] = [[0, x]];
    for (let index = 0; index < settings.steps; index += 1) {
      x = settings.theta + (x - settings.theta) * decay + stepSd * normal(random);
      points.push([((index + 1) / settings.steps) * settings.horizon, x]);
    }
    paths.push(points);
  }
  const mean: Point[] = [];
  const upper: Point[] = [];
  const lower: Point[] = [];
  for (let index = 0; index <= 80; index += 1) {
    const t = (settings.horizon * index) / 80;
    const conditionalMean = settings.theta + (x0 - settings.theta) * Math.exp(-settings.kappa * t);
    const variance =
      (settings.sigma ** 2 * (1 - Math.exp(-2 * settings.kappa * t))) /
      (2 * settings.kappa);
    const sd = Math.sqrt(variance);
    mean.push([t, conditionalMean]);
    upper.push([t, conditionalMean + 1.96 * sd]);
    lower.push([t, conditionalMean - 1.96 * sd]);
  }
  const domain = yDomain([...paths, upper, lower], 0.08);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.65 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const rightTop = { x: right.x, y: right.y, w: right.w, h: right.h * 0.5 - gap / 2 };
  const rightBottom = {
    x: right.x,
    y: rightTop.y + rightTop.h + gap,
    w: right.w,
    h: right.h - rightTop.h - gap,
  };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...paths.map((points, index) => ({
        points,
        color: index === 0 ? colors.teal : colors.violet,
        width: index === 0 ? 2.2 : 1,
        alpha: index === 0 ? 1 : 0.24,
      })),
      { points: upper, color: colors.amber, width: 1.4, dashed: true },
      { points: lower, color: colors.amber, width: 1.4, dashed: true },
      { points: mean, color: colors.coral, width: 2.4 },
    ],
    { x: [0, settings.horizon], y: domain },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "経路", left.x + 54, left.y + 18, colors.teal);
  drawLabel(context, "条件付き平均", left.x + 96, left.y + 18, colors.coral);
  drawLabel(context, "95% 帯", left.x + 192, left.y + 18, colors.amber);

  const stationarySd = settings.sigma / Math.sqrt(2 * settings.kappa);
  const density: Point[] = Array.from({ length: 101 }, (_, index) => {
    const x = settings.theta - 3.5 * stationarySd + (index / 100) * 7 * stationarySd;
    return [x, normalPdf(x, settings.theta, stationarySd)];
  });
  drawRoundedRect(context, rightTop, 14, colors.paper);
  drawChart(
    context,
    rightTop,
    [{ points: density, color: colors.violet, width: 2.3 }],
    {
      x: [settings.theta - 3.5 * stationarySd, settings.theta + 3.5 * stationarySd],
      y: [0, Math.max(...density.map((point) => point[1])) * 1.12],
    },
    colors,
    { xLabel: "定常状態 x" },
  );
  drawLabel(context, "定常密度", rightTop.x + 52, rightTop.y + 18, colors.violet);

  const autocorrelation: Point[] = Array.from({ length: 81 }, (_, index) => {
    const lag = (settings.horizon * index) / 80;
    return [lag, Math.exp(-settings.kappa * lag)];
  });
  const halfLife = Math.log(2) / settings.kappa;
  const halfLifeLine: Point[] = halfLife <= settings.horizon
    ? [[halfLife, 0], [halfLife, 1]]
    : [];
  drawRoundedRect(context, rightBottom, 14, colors.paper);
  drawChart(
    context,
    rightBottom,
    [
      { points: autocorrelation, color: colors.teal, width: 2.3 },
      { points: halfLifeLine, color: colors.amber, width: 1.4, dashed: true },
    ],
    { x: [0, settings.horizon], y: [0, 1.05] },
    colors,
    { xLabel: "lag h" },
  );
  drawLabel(context, "自己相関 e⁻ᵏʰ", rightBottom.x + 52, rightBottom.y + 18, colors.teal);
}

function cirDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 137);
  const steps = Math.max(settings.steps, 64);
  const dt = settings.horizon / steps;
  const count = Math.min(settings.paths, 18);
  const cirPaths: Point[][] = [];
  const ouPaths: Point[][] = [];
  const ouSigma = settings.sigma * Math.sqrt(Math.max(settings.theta, 1e-4));
  const decay = Math.exp(-settings.kappa * dt);
  const ouStepSd = ouSigma * Math.sqrt((1 - decay * decay) / (2 * settings.kappa));
  let projectedSteps = 0;
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let cir = Math.max(settings.x0, 0);
    let ou = settings.x0;
    const cirPoints: Point[] = [[0, cir]];
    const ouPoints: Point[] = [[0, ou]];
    for (let index = 0; index < steps; index += 1) {
      const shock = normal(random);
      const positive = Math.max(cir, 0);
      const proposal =
        cir + settings.kappa * (settings.theta - positive) * dt +
        settings.sigma * Math.sqrt(positive) * Math.sqrt(dt) * shock;
      if (proposal < 0) projectedSteps += 1;
      cir = Math.max(0, proposal);
      ou = settings.theta + (ou - settings.theta) * decay + ouStepSd * shock;
      const time = (index + 1) * dt;
      cirPoints.push([time, cir]);
      ouPoints.push([time, ou]);
    }
    cirPaths.push(cirPoints);
    ouPaths.push(ouPoints);
  }
  return {
    cirPaths,
    ouPaths,
    ouSigma,
    fellerRatio: (2 * settings.kappa * settings.theta) / settings.sigma ** 2,
    projectionRate: projectedSteps / Math.max(count * steps, 1),
  };
}

function drawCir(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = cirDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.68 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const domain = yDomain([...diagnostics.cirPaths, ...diagnostics.ouPaths], 0.08);
  domain[0] = Math.min(domain[0], -0.1 * Math.max(settings.theta, 0.2));
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...diagnostics.ouPaths.map((points, index) => ({
        points,
        color: colors.coral,
        width: index === 0 ? 2 : 0.9,
        alpha: index === 0 ? 0.95 : 0.14,
      })),
      ...diagnostics.cirPaths.map((points, index) => ({
        points,
        color: colors.teal,
        width: index === 0 ? 2.5 : 1,
        alpha: index === 0 ? 1 : 0.22,
      })),
      {
        points: [[0, 0], [settings.horizon, 0]],
        color: colors.muted,
        width: 1.2,
        dashed: true,
      },
    ],
    { x: [0, settings.horizon], y: domain },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "CIR · 非負", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "OU · 負値あり", left.x + 128, left.y + 18, colors.coral);

  const stateMax = Math.max(settings.theta * 2.6, settings.x0 * 1.8, 0.8);
  const cirDiffusion: Point[] = [];
  const ouDiffusion: Point[] = [];
  for (let index = 0; index <= 100; index += 1) {
    const state = (index / 100) * stateMax;
    cirDiffusion.push([state, settings.sigma * Math.sqrt(state)]);
    ouDiffusion.push([state, diagnostics.ouSigma]);
  }
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: cirDiffusion, color: colors.teal, width: 2.5 },
      { points: ouDiffusion, color: colors.coral, width: 2, dashed: true },
    ],
    { x: [0, stateMax], y: [0, Math.max(...cirDiffusion.map((point) => point[1]), diagnostics.ouSigma) * 1.12] },
    colors,
    { xLabel: "状態 x", yLabel: "局所拡散" },
  );
  drawLabel(context, "σ√x", right.x + 52, right.y + 18, colors.teal);
  drawLabel(context, "OU 定数", right.x + right.w - 14, right.y + 18, colors.coral, "right");
}

function correlatedBrownianDiagnostics(settings: Settings, count: number) {
  const random = mulberry32(settings.seed + 149);
  const steps = Math.max(settings.steps, 16);
  const dt = settings.horizon / steps;
  const rho = clamp(settings.rho, -1, 1);
  const orthogonalScale = Math.sqrt(Math.max(1 - rho * rho, 0));
  const path1: Point[] = [[0, 0]];
  const path2: Point[] = [[0, 0]];
  const terminals: Point[] = [];
  for (let pathIndex = 0; pathIndex < Math.max(count, 1); pathIndex += 1) {
    let x = 0;
    let y = 0;
    for (let index = 0; index < steps; index += 1) {
      const z1 = normal(random);
      const z2 = normal(random);
      x += settings.mu * dt + settings.sigma * Math.sqrt(dt) * z1;
      y +=
        settings.mu * dt +
        settings.sigma2 * Math.sqrt(dt) * (rho * z1 + orthogonalScale * z2);
      if (pathIndex === 0) {
        const time = (index + 1) * dt;
        path1.push([time, x]);
        path2.push([time, y]);
      }
    }
    terminals.push([x, y]);
  }

  const xMean = terminals.reduce((sum, point) => sum + point[0], 0) / terminals.length;
  const yMean = terminals.reduce((sum, point) => sum + point[1], 0) / terminals.length;
  let covariance = 0;
  let xVariance = 0;
  let yVariance = 0;
  terminals.forEach(([x, y]) => {
    const xCentered = x - xMean;
    const yCentered = y - yMean;
    covariance += xCentered * yCentered;
    xVariance += xCentered * xCentered;
    yVariance += yCentered * yCentered;
  });
  const empiricalCorrelation = covariance / Math.sqrt(Math.max(xVariance * yVariance, 1e-12));

  const variance1 = settings.sigma ** 2 * settings.horizon;
  const variance2 = settings.sigma2 ** 2 * settings.horizon;
  const theoreticalCovariance = rho * settings.sigma * settings.sigma2 * settings.horizon;
  const spectralGap = Math.sqrt(
    (variance1 - variance2) ** 2 + 4 * theoreticalCovariance ** 2,
  );
  const eigenvalue1 = Math.max((variance1 + variance2 + spectralGap) / 2, 0);
  const eigenvalue2 = Math.max((variance1 + variance2 - spectralGap) / 2, 0);
  const angle = 0.5 * Math.atan2(2 * theoreticalCovariance, variance1 - variance2);
  const ellipseScale = Math.sqrt(5.991);
  const mean = settings.mu * settings.horizon;
  const ellipse: Point[] = Array.from({ length: 101 }, (_, index) => {
    const phase = (2 * Math.PI * index) / 100;
    const major = ellipseScale * Math.sqrt(eigenvalue1) * Math.cos(phase);
    const minor = ellipseScale * Math.sqrt(eigenvalue2) * Math.sin(phase);
    return [
      mean + major * Math.cos(angle) - minor * Math.sin(angle),
      mean + major * Math.sin(angle) + minor * Math.cos(angle),
    ];
  });
  return { path1, path2, terminals, ellipse, empiricalCorrelation, theoreticalCovariance };
}

function drawCorrelatedBrownian(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = correlatedBrownianDiagnostics(
    settings,
    Math.max(settings.paths * 8, 400),
  );
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.48 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: diagnostics.path1, color: colors.teal, width: 2.2 },
      { points: diagnostics.path2, color: colors.amber, width: 2.2 },
    ],
    { x: [0, settings.horizon], y: yDomain([diagnostics.path1, diagnostics.path2], 0.14) },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, `X · σ₁=${formatNumber(settings.sigma, 2)}`, left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, `Y · σ₂=${formatNumber(settings.sigma2, 2)}`, left.x + 144, left.y + 18, colors.amber);

  const mean = settings.mu * settings.horizon;
  const xRadius = 3.5 * settings.sigma * Math.sqrt(settings.horizon);
  const yRadius = 3.5 * settings.sigma2 * Math.sqrt(settings.horizon);
  const domain = {
    x: [mean - xRadius, mean + xRadius] as [number, number],
    y: [mean - yRadius, mean + yRadius] as [number, number],
  };
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(context, right, [], domain, colors, { xLabel: "終端 Xₜ", yLabel: "終端 Yₜ", zeroLine: true });
  const padding = { left: 42, right: 12, top: 14, bottom: 32 };
  const plot = {
    x: right.x + padding.left,
    y: right.y + padding.top,
    w: right.w - padding.left - padding.right,
    h: right.h - padding.top - padding.bottom,
  };
  const xMap = (value: number) => plot.x + ((value - domain.x[0]) / (domain.x[1] - domain.x[0])) * plot.w;
  const yMap = (value: number) => plot.y + plot.h - ((value - domain.y[0]) / (domain.y[1] - domain.y[0])) * plot.h;
  diagnostics.terminals.slice(0, 480).forEach(([xValue, yValue]) => {
    const x = xMap(xValue);
    const y = yMap(yValue);
    if (x < plot.x || x > plot.x + plot.w || y < plot.y || y > plot.y + plot.h) return;
    context.beginPath();
    context.arc(x, y, 2.1, 0, Math.PI * 2);
    context.fillStyle = colors.violet;
    context.globalAlpha = 0.34;
    context.fill();
  });
  context.globalAlpha = 1;
  context.beginPath();
  diagnostics.ellipse.forEach(([xValue, yValue], index) => {
    const x = xMap(xValue);
    const y = yMap(yValue);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.strokeStyle = colors.coral;
  context.lineWidth = 2.4;
  context.stroke();
  drawLabel(context, `ρ=${formatNumber(settings.rho, 2)}`, right.x + 52, right.y + 18, colors.ink);
  drawLabel(context, "95% 共分散楕円", right.x + right.w - 14, right.y + 18, colors.coral, "right");
}

function generatorTestFunction(choice: number) {
  if (choice === 0) {
    return {
      value: (x: number) => x,
      first: () => 1,
      second: () => 0,
      label: "f(x)=x",
    };
  }
  if (choice === 2) {
    return {
      value: (x: number) => Math.exp(x),
      first: (x: number) => Math.exp(x),
      second: (x: number) => Math.exp(x),
      label: "f(x)=exp(x)",
    };
  }
  return {
    value: (x: number) => x * x,
    first: (x: number) => 2 * x,
    second: () => 2,
    label: "f(x)=x²",
  };
}

function generatorDiagnostics(settings: Settings) {
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  const testFunction = generatorTestFunction(choice);
  const random = mulberry32(settings.seed + 173);
  const sampleCount = Math.max(settings.paths * 16, 800);
  const dt = Math.max(settings.localDt, 0.002);
  const xMin = settings.x0 - 1.6;
  const xMax = settings.x0 + 1.6;
  const functionCurve: Point[] = [];
  const analytic: Point[] = [];
  const empirical: Point[] = [];
  let localHalfWidth = 0;
  for (let index = 0; index <= 40; index += 1) {
    const x = xMin + (index / 40) * (xMax - xMin);
    const exact =
      settings.mu * testFunction.first(x) +
      0.5 * settings.sigma ** 2 * testFunction.second(x);
    let totalChange = 0;
    let squareChange = 0;
    for (let sample = 0; sample < sampleCount; sample += 1) {
      const next = x + settings.mu * dt + settings.sigma * Math.sqrt(dt) * normal(random);
      const change = testFunction.value(next) - testFunction.value(x);
      totalChange += change;
      squareChange += change * change;
    }
    functionCurve.push([x, testFunction.value(x)]);
    analytic.push([x, exact]);
    empirical.push([x, totalChange / sampleCount / dt]);
    if (index === 20) {
      const meanChange = totalChange / sampleCount;
      const varianceChange = Math.max(squareChange / sampleCount - meanChange ** 2, 0);
      localHalfWidth = 1.96 * Math.sqrt(varianceChange / sampleCount) / dt;
    }
  }
  const localAnalytic =
    settings.mu * testFunction.first(settings.x0) +
    0.5 * settings.sigma ** 2 * testFunction.second(settings.x0);
  const nearest = empirical[Math.floor(empirical.length / 2)][1];
  return {
    testFunction,
    functionCurve,
    analytic,
    empirical,
    localAnalytic,
    localEmpirical: nearest,
    localHalfWidth,
    sampleCount,
  };
}

function drawGenerator(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = generatorDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.42 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const xDomain: [number, number] = [
    diagnostics.functionCurve[0][0],
    diagnostics.functionCurve[diagnostics.functionCurve.length - 1][0],
  ];
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [{ points: diagnostics.functionCurve, color: colors.violet, width: 2.5 }],
    { x: xDomain, y: yDomain([diagnostics.functionCurve], 0.14) },
    colors,
    { xLabel: "状態 x", zeroLine: true },
  );
  drawLabel(context, diagnostics.testFunction.label, left.x + 52, left.y + 18, colors.violet);

  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: diagnostics.analytic, color: colors.teal, width: 2.6 },
      { points: diagnostics.empirical, color: colors.amber, width: 1.8, dashed: true },
    ],
    { x: xDomain, y: yDomain([diagnostics.analytic, diagnostics.empirical], 0.16) },
    colors,
    { xLabel: "状態 x", yLabel: "期待変化率", zeroLine: true },
  );
  drawLabel(context, "解析 ℒf", right.x + 52, right.y + 18, colors.teal);
  drawLabel(context, "一歩の標本平均 / Δt", right.x + 120, right.y + 18, colors.amber);
}

function terminalPayoff(choice: number, value: number, strike: number) {
  if (choice === 1) return value > strike ? 1 : 0;
  if (choice === 2) return value * value;
  return Math.max(value - strike, 0);
}

function backwardValue(settings: Settings, choice: number, time: number, state: number) {
  const tau = Math.max(settings.horizon - time, 0);
  if (tau < 1e-8) return terminalPayoff(choice, state, settings.strike);
  const mean = state + settings.mu * tau;
  const sd = settings.sigma * Math.sqrt(tau);
  if (choice === 1) return normalCdf((mean - settings.strike) / sd);
  if (choice === 2) return mean * mean + sd * sd;
  const distance = mean - settings.strike;
  const d = distance / sd;
  return distance * normalCdf(d) + sd * normalPdf(d, 0, 1);
}

function backwardDiagnostics(settings: Settings) {
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  const selectedTime = settings.time * settings.horizon;
  const center = choice === 2 ? settings.x0 : settings.strike;
  const span = Math.max(3.2 * settings.sigma * Math.sqrt(settings.horizon), 1.2);
  const xDomain: [number, number] = [center - span, center + span];
  const terminal: Point[] = [];
  const selected: Point[] = [];
  const initial: Point[] = [];
  for (let index = 0; index <= 140; index += 1) {
    const state = xDomain[0] + (index / 140) * (xDomain[1] - xDomain[0]);
    terminal.push([state, terminalPayoff(choice, state, settings.strike)]);
    selected.push([state, backwardValue(settings, choice, selectedTime, state)]);
    initial.push([state, backwardValue(settings, choice, 0, state)]);
  }
  return {
    choice,
    selectedTime,
    xDomain,
    terminal,
    selected,
    initial,
    valueAtState: backwardValue(settings, choice, selectedTime, settings.x0),
  };
}

function drawBackwardEquation(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = backwardDiagnostics(settings);
  drawRoundedRect(context, area, 16, colors.paper);
  drawChart(
    context,
    area,
    [
      { points: diagnostics.terminal, color: colors.muted, width: 1.7, dashed: true },
      { points: diagnostics.selected, color: colors.amber, width: 2.5 },
      { points: diagnostics.initial, color: colors.teal, width: 2.3 },
    ],
    {
      x: diagnostics.xDomain,
      y: yDomain([diagnostics.terminal, diagnostics.selected, diagnostics.initial], 0.12),
    },
    colors,
    { xLabel: "現在状態 x", yLabel: "条件付き価値 u(t,x)", zeroLine: true },
  );
  drawLabel(context, "終端 g(x)", area.x + 52, area.y + 18, colors.muted);
  drawLabel(
    context,
    `t=${formatNumber(diagnostics.selectedTime, 2)}`,
    area.x + 132,
    area.y + 18,
    colors.amber,
  );
  drawLabel(context, "t=0", area.x + 206, area.y + 18, colors.teal);
}

function drawFokkerPlanck(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const t = Math.max(settings.time * settings.horizon, 0.02);
  const random = mulberry32(settings.seed);
  const sampleCount = Math.max(settings.paths * 14, 600);
  const values = Array.from(
    { length: sampleCount },
    () => settings.mu * t + settings.sigma * Math.sqrt(t) * normal(random),
  );
  const mean = settings.mu * t;
  const sd = settings.sigma * Math.sqrt(t);
  const xMin = mean - 3.8 * sd;
  const xMax = mean + 3.8 * sd;
  const bins = 28;
  const counts = Array.from({ length: bins }, () => 0);
  values.forEach((value) => {
    const index = clamp(Math.floor(((value - xMin) / (xMax - xMin)) * bins), 0, bins - 1);
    counts[index] += 1;
  });
  const histogram: Point[] = counts.map((count, index) => [
    xMin + ((index + 0.5) / bins) * (xMax - xMin),
    count / values.length / ((xMax - xMin) / bins),
  ]);
  const density: Point[] = Array.from({ length: 121 }, (_, index) => {
    const x = xMin + (index / 120) * (xMax - xMin);
    return [x, normalPdf(x, mean, sd)];
  });
  const scatterHeight = 86;
  const scatter = { x: area.x, y: area.y, w: area.w, h: scatterHeight };
  const chart = { x: area.x, y: area.y + scatterHeight + 12, w: area.w, h: area.h - scatterHeight - 12 };
  drawRoundedRect(context, scatter, 14, colors.paper);
  drawLabel(context, `粒子断面  t=${formatNumber(t, 2)}`, scatter.x + 16, scatter.y + 20, colors.ink);
  const shown = values.slice(0, Math.min(settings.paths, 90));
  shown.forEach((value, index) => {
    const x = scatter.x + 24 + ((value - xMin) / (xMax - xMin)) * (scatter.w - 48);
    const y = scatter.y + 38 + (index % 4) * 9;
    context.beginPath();
    context.arc(x, y, 2.5, 0, Math.PI * 2);
    context.fillStyle = index % 7 === 0 ? colors.amber : colors.teal;
    context.globalAlpha = 0.78;
    context.fill();
  });
  context.globalAlpha = 1;
  drawRoundedRect(context, chart, 14, colors.paper);
  const upper = Math.max(...density.map((point) => point[1])) * 1.14;
  const barSeries: Point[] = [];
  histogram.forEach((point, index) => {
    const half = (xMax - xMin) / bins / 2;
    if (index === 0) barSeries.push([point[0] - half, 0]);
    barSeries.push([point[0] - half, point[1]], [point[0] + half, point[1]]);
    if (index === histogram.length - 1) barSeries.push([point[0] + half, 0]);
  });
  drawChart(
    context,
    chart,
    [
      { points: barSeries, color: colors.violet, width: 1.4, alpha: 0.72 },
      { points: density, color: colors.teal, width: 2.6 },
    ],
    { x: [xMin, xMax], y: [0, upper] },
    colors,
    { xLabel: "状態 x" },
  );
  drawLabel(context, "経験密度", chart.x + 54, chart.y + 18, colors.violet);
  drawLabel(context, "解析密度", chart.x + 126, chart.y + 18, colors.teal);
}

function feynmanKacExact(settings: Settings) {
  const variance = settings.sigma ** 2 * settings.horizon;
  const mean = settings.x0 + settings.mu * settings.horizon;
  return Math.exp(-settings.rate * settings.horizon) /
    Math.sqrt(1 + 2 * variance) *
    Math.exp(-(mean * mean) / (1 + 2 * variance));
}

function feynmanKacDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 211);
  const count = Math.max(settings.paths * 128, 2048);
  const discount = Math.exp(-settings.rate * settings.horizon);
  const analytic = feynmanKacExact(settings);
  const checkpoints = new Set(
    [64, 128, 256, 512, 1024, 2048, 4096, 8192, count].filter((value) => value <= count),
  );
  let total = 0;
  let squareTotal = 0;
  const estimate: Point[] = [];
  const upper: Point[] = [];
  const lower: Point[] = [];
  for (let index = 1; index <= count; index += 1) {
    const terminal =
      settings.x0 + settings.mu * settings.horizon +
      settings.sigma * Math.sqrt(settings.horizon) * normal(random);
    const payoff = discount * Math.exp(-terminal * terminal);
    total += payoff;
    squareTotal += payoff * payoff;
    if (checkpoints.has(index)) {
      const mean = total / index;
      const variance = Math.max(squareTotal / index - mean * mean, 0);
      const halfWidth = 1.96 * Math.sqrt(variance / index);
      const logCount = Math.log10(index);
      estimate.push([logCount, mean]);
      upper.push([logCount, mean + halfWidth]);
      lower.push([logCount, Math.max(mean - halfWidth, 0)]);
    }
  }

  const pathRandom = mulberry32(settings.seed + 223);
  const paths: Point[][] = [];
  const steps = 96;
  const dt = settings.horizon / steps;
  for (let pathIndex = 0; pathIndex < 14; pathIndex += 1) {
    let value = settings.x0;
    const points: Point[] = [[0, value]];
    for (let index = 0; index < steps; index += 1) {
      value += settings.mu * dt + settings.sigma * Math.sqrt(dt) * normal(pathRandom);
      points.push([(index + 1) * dt, value]);
    }
    paths.push(points);
  }
  const finalEstimate = estimate[estimate.length - 1][1];
  const finalHalfWidth = (upper[upper.length - 1][1] - lower[lower.length - 1][1]) / 2;
  return { analytic, estimate, upper, lower, paths, finalEstimate, finalHalfWidth, count };
}

function drawFeynmanKac(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = feynmanKacDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.5 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const pathDomain = yDomain(diagnostics.paths, 0.1);
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...diagnostics.paths.map((points, index) => ({
        points,
        color: index === 0 ? colors.teal : colors.violet,
        width: index === 0 ? 2.4 : 1,
        alpha: index === 0 ? 1 : 0.25,
      })),
    ],
    { x: [0, settings.horizon], y: pathDomain },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  drawLabel(context, "算術 Brownian 経路", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "g(x)=e⁻ˣ²", left.x + left.w - 14, left.y + 18, colors.amber, "right");

  const xMin = diagnostics.estimate[0][0];
  const xMax = diagnostics.estimate[diagnostics.estimate.length - 1][0];
  const analyticLine: Point[] = [[xMin, diagnostics.analytic], [xMax, diagnostics.analytic]];
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [
      { points: diagnostics.upper, color: colors.amber, width: 1.3, dashed: true },
      { points: diagnostics.lower, color: colors.amber, width: 1.3, dashed: true },
      { points: analyticLine, color: colors.teal, width: 2.2 },
      { points: diagnostics.estimate, color: colors.coral, width: 2.4 },
    ],
    {
      x: [xMin, xMax],
      y: yDomain([diagnostics.upper, diagnostics.lower, analyticLine], 0.18),
    },
    colors,
    { xLabel: "log₁₀ Monte Carlo 経路数", yLabel: "割引期待値" },
  );
  drawLabel(context, "PDE / 解析解", right.x + 52, right.y + 18, colors.teal);
  drawLabel(context, "Monte Carlo ±95%", right.x + 152, right.y + 18, colors.coral);
}

function firstPassageDiagnostics(settings: Settings) {
  const random = mulberry32(settings.seed + 251);
  const steps = Math.max(settings.steps, 64);
  const count = Math.max(settings.paths * 4, 256);
  const dt = settings.horizon / steps;
  const paths: Point[][] = [];
  const displayedHits: Array<{ time: number; value: number }> = [];
  const hitSteps: Array<number | null> = [];
  const hitTimes: number[] = [];
  let upperHits = 0;
  let lowerHits = 0;
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let value = settings.x0;
    let hitStep: number | null = null;
    const points: Point[] = [[0, value]];
    for (let index = 0; index < steps; index += 1) {
      const previous = value;
      value += settings.mu * dt + settings.sigma * Math.sqrt(dt) * normal(random);
      const time = (index + 1) * dt;
      if (pathIndex < 18) points.push([time, value]);
      if (value >= settings.upperBarrier || value <= settings.lowerBarrier) {
        hitStep = index + 1;
        const barrier = value >= settings.upperBarrier
          ? settings.upperBarrier
          : settings.lowerBarrier;
        const fraction = clamp((barrier - previous) / (value - previous), 0, 1);
        const interpolatedTime = (index + fraction) * dt;
        hitTimes.push(interpolatedTime);
        if (value >= settings.upperBarrier) upperHits += 1;
        else lowerHits += 1;
        if (pathIndex < 18) {
          points[points.length - 1] = [interpolatedTime, barrier];
          displayedHits.push({
            time: interpolatedTime,
            value: barrier,
          });
        }
        break;
      }
    }
    if (pathIndex < 18) paths.push(points);
    hitSteps.push(hitStep);
  }
  const survival: Point[] = [[0, 1]];
  for (let index = 1; index <= steps; index += 1) {
    const survivors = hitSteps.filter((hitStep) => hitStep === null || hitStep > index).length;
    survival.push([index * dt, survivors / count]);
  }
  const bins = 16;
  const counts = Array.from({ length: bins }, () => 0);
  hitTimes.forEach((time) => {
    const index = clamp(Math.floor((time / settings.horizon) * bins), 0, bins - 1);
    counts[index] += 1;
  });
  const histogram: Point[] = counts.flatMap((binCount, index) => {
    const left = (index / bins) * settings.horizon;
    const right = ((index + 1) / bins) * settings.horizon;
    const density = hitTimes.length > 0
      ? binCount / hitTimes.length / (settings.horizon / bins)
      : 0;
    return [[left, density], [right, density]] as Point[];
  });
  return {
    paths,
    displayedHits,
    survival,
    histogram,
    hitProbability: hitTimes.length / count,
    upperHitRate: upperHits / count,
    lowerHitRate: lowerHits / count,
    count,
  };
}

function drawFirstPassage(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const diagnostics = firstPassageDiagnostics(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.64 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  const rightTop = { x: right.x, y: right.y, w: right.w, h: right.h * 0.52 - gap / 2 };
  const rightBottom = {
    x: right.x,
    y: rightTop.y + rightTop.h + gap,
    w: right.w,
    h: right.h - rightTop.h - gap,
  };
  const yDomainValue: [number, number] = [
    settings.lowerBarrier - 0.12 * (settings.upperBarrier - settings.lowerBarrier),
    settings.upperBarrier + 0.12 * (settings.upperBarrier - settings.lowerBarrier),
  ];
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      ...diagnostics.paths.map((points, index) => ({
        points,
        color: index === 0 ? colors.teal : colors.violet,
        width: index === 0 ? 2.3 : 1,
        alpha: index === 0 ? 1 : 0.28,
      })),
      {
        points: [[0, settings.upperBarrier], [settings.horizon, settings.upperBarrier]],
        color: colors.coral,
        width: 1.5,
        dashed: true,
      },
      {
        points: [[0, settings.lowerBarrier], [settings.horizon, settings.lowerBarrier]],
        color: colors.coral,
        width: 1.5,
        dashed: true,
      },
    ],
    { x: [0, settings.horizon], y: yDomainValue },
    colors,
    { xLabel: "時間 t", zeroLine: true },
  );
  const padding = { left: 42, right: 12, top: 14, bottom: 32 };
  const plot = {
    x: left.x + padding.left,
    y: left.y + padding.top,
    w: left.w - padding.left - padding.right,
    h: left.h - padding.top - padding.bottom,
  };
  diagnostics.displayedHits.forEach((hit) => {
    const x = plot.x + (hit.time / settings.horizon) * plot.w;
    const y = plot.y + plot.h -
      ((hit.value - yDomainValue[0]) / (yDomainValue[1] - yDomainValue[0])) * plot.h;
    context.beginPath();
    context.arc(x, y, 3.1, 0, Math.PI * 2);
    context.fillStyle = colors.coral;
    context.fill();
  });
  drawLabel(context, "吸収までの経路", left.x + 52, left.y + 18, colors.teal);
  drawLabel(context, "● 初到達", left.x + left.w - 14, left.y + 18, colors.coral, "right");

  drawRoundedRect(context, rightTop, 14, colors.paper);
  drawChart(
    context,
    rightTop,
    [{ points: diagnostics.survival, color: colors.teal, width: 2.4 }],
    { x: [0, settings.horizon], y: [0, 1.05] },
    colors,
    { xLabel: "時間 t" },
  );
  drawLabel(context, "生存確率 P(τ>t)", rightTop.x + 52, rightTop.y + 18, colors.teal);

  drawRoundedRect(context, rightBottom, 14, colors.paper);
  const histogramUpper = Math.max(...diagnostics.histogram.map((point) => point[1]), 0.1) * 1.15;
  drawChart(
    context,
    rightBottom,
    [{ points: diagnostics.histogram, color: colors.amber, width: 1.8 }],
    { x: [0, settings.horizon], y: [0, histogramUpper] },
    colors,
    { xLabel: "到達時刻 τ" },
  );
  drawLabel(context, "条件付き到達時刻密度", rightBottom.x + 52, rightBottom.y + 18, colors.amber);
}

function simulateCoupledEuler(settings: Settings, seed = settings.seed) {
  const random = mulberry32(seed);
  const fineSteps = 4096;
  const fineDt = settings.horizon / fineSteps;
  const cumulative = [0];
  for (let index = 0; index < fineSteps; index += 1) {
    cumulative.push(cumulative[index] + Math.sqrt(fineDt) * normal(random));
  }
  let exact = 100;
  let euler = 100;
  const exactPoints: Point[] = [[0, exact]];
  const eulerPoints: Point[] = [[0, euler]];
  for (let index = 0; index < settings.steps; index += 1) {
    const fineStart = Math.round((index / settings.steps) * fineSteps);
    const fineEnd = Math.round(((index + 1) / settings.steps) * fineSteps);
    const t0 = fineStart * fineDt;
    const t1 = fineEnd * fineDt;
    const dt = t1 - t0;
    const dW = cumulative[fineEnd] - cumulative[fineStart];
    exact *= Math.exp((settings.mu - 0.5 * settings.sigma ** 2) * dt + settings.sigma * dW);
    euler *= 1 + settings.mu * dt + settings.sigma * dW;
    exactPoints.push([t1, exact]);
    eulerPoints.push([t1, euler]);
  }
  return { exact, euler, exactPoints, eulerPoints };
}

function eulerDiagnostics(settings: Settings) {
  const count = Math.max(settings.paths, 16);
  let absoluteError = 0;
  let exactMean = 0;
  let eulerMean = 0;
  for (let index = 0; index < count; index += 1) {
    const result = simulateCoupledEuler(settings, settings.seed + index * 1009);
    absoluteError += Math.abs(result.exact - result.euler);
    exactMean += result.exact;
    eulerMean += result.euler;
  }
  return {
    meanAbsoluteError: absoluteError / count,
    weakDifference: Math.abs(exactMean / count - eulerMean / count),
  };
}

function eulerConvergence(settings: Settings) {
  const samplePaths = Math.min(Math.max(settings.paths, 16), 48);
  const stepCounts = [8, 16, 32, 64, 128];
  const strong: Point[] = [];
  const weak: Point[] = [];
  stepCounts.forEach((steps) => {
    const diagnostics = eulerDiagnostics({ ...settings, steps, paths: samplePaths });
    const logDt = Math.log10(settings.horizon / steps);
    const exactExpectation = 100 * Math.exp(settings.mu * settings.horizon);
    const eulerExpectation = 100 * (1 + (settings.mu * settings.horizon) / steps) ** steps;
    strong.push([logDt, Math.log10(Math.max(diagnostics.meanAbsoluteError, 1e-5))]);
    weak.push([logDt, Math.log10(Math.max(Math.abs(exactExpectation - eulerExpectation), 1e-5))]);
  });
  return { strong, weak, samplePaths };
}

function drawEuler(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const { exact, euler, exactPoints, eulerPoints } = simulateCoupledEuler(settings);
  const convergence = eulerConvergence(settings);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.64 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: exactPoints, color: colors.teal, width: 2.6 },
      { points: eulerPoints, color: colors.coral, width: 2, dashed: true },
    ],
    { x: [0, settings.horizon], y: yDomain([exactPoints, eulerPoints], 0.14) },
    colors,
    { xLabel: "時間 t" },
  );
  drawLabel(context, "厳密解", left.x + 54, left.y + 18, colors.teal);
  drawLabel(context, "Euler", left.x + 110, left.y + 18, colors.coral);
  drawLabel(
    context,
    `終点差 ${formatNumber(Math.abs(exact - euler), 2)}`,
    left.x + left.w - 18,
    left.y + 18,
    colors.ink,
    "right",
  );

  drawRoundedRect(context, right, 16, colors.paper);
  const xValues = [...convergence.strong, ...convergence.weak].map((point) => point[0]);
  drawChart(
    context,
    right,
    [
      { points: convergence.strong, color: colors.teal, width: 2.3 },
      { points: convergence.weak, color: colors.amber, width: 2.3 },
    ],
    {
      x: [Math.min(...xValues), Math.max(...xValues)],
      y: yDomain([convergence.strong, convergence.weak], 0.16),
    },
    colors,
    { xLabel: "log₁₀ Δt" },
  );
  drawLabel(context, "強誤差", right.x + 52, right.y + 18, colors.teal);
  drawLabel(context, "弱誤差", right.x + 106, right.y + 18, colors.amber);
  drawLabel(
    context,
    `${convergence.samplePaths} 経路`,
    right.x + right.w - 14,
    right.y + 18,
    colors.muted,
    "right",
  );
}

function measureChangeDiagnostics(settings: Settings, count: number) {
  const random = mulberry32(settings.seed + 313);
  const s0 = 100;
  const t = settings.horizon;
  const lambda = (settings.mu - settings.rate) / settings.sigma;
  const samples: Array<{ price: number; weight: number }> = [];
  let weightTotal = 0;
  let weightedPriceTotal = 0;
  for (let index = 0; index < count; index += 1) {
    const w = Math.sqrt(t) * normal(random);
    const price = s0 * Math.exp(
      (settings.mu - 0.5 * settings.sigma ** 2) * t + settings.sigma * w,
    );
    const weight = Math.exp(-lambda * w - 0.5 * lambda ** 2 * t);
    samples.push({ price, weight });
    weightTotal += weight;
    weightedPriceTotal += weight * price;
  }
  const meanWeight = weightTotal / count;
  return {
    samples,
    meanWeight,
    discountedWeightedPrice:
      Math.exp(-settings.rate * t) * weightedPriceTotal / count,
  };
}

function drawMeasureChange(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: Settings,
  colors: ReturnType<typeof chartColors>,
) {
  const s0 = 100;
  const t = settings.horizon;
  const logSd = settings.sigma * Math.sqrt(t);
  const pLogMean = Math.log(s0) + (settings.mu - 0.5 * settings.sigma ** 2) * t;
  const qLogMean = Math.log(s0) + (settings.rate - 0.5 * settings.sigma ** 2) * t;
  const low = s0 * Math.exp((Math.min(settings.mu, settings.rate) - 0.5 * settings.sigma ** 2) * t - 3.5 * logSd);
  const high = s0 * Math.exp((Math.max(settings.mu, settings.rate) - 0.5 * settings.sigma ** 2) * t + 3.5 * logSd);
  const pDensity: Point[] = [];
  const qDensity: Point[] = [];
  for (let index = 0; index <= 140; index += 1) {
    const x = low + (index / 140) * (high - low);
    pDensity.push([x, lognormalPdf(x, pLogMean, logSd)]);
    qDensity.push([x, lognormalPdf(x, qLogMean, logSd)]);
  }
  const upper = Math.max(...pDensity.map((point) => point[1]), ...qDensity.map((point) => point[1])) * 1.12;
  const diagnostics = measureChangeDiagnostics(settings, 180);
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * 0.62 - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  drawRoundedRect(context, left, 16, colors.paper);
  drawChart(
    context,
    left,
    [
      { points: pDensity, color: colors.amber, width: 2.5 },
      { points: qDensity, color: colors.teal, width: 2.5 },
    ],
    { x: [low, high], y: [0, upper] },
    colors,
    { xLabel: "満期価格 Sₜ" },
  );
  drawLabel(context, `P · μ=${formatPercent(settings.mu)}`, left.x + 54, left.y + 18, colors.amber);
  drawLabel(context, `Q · r=${formatPercent(settings.rate)}`, left.x + 150, left.y + 18, colors.teal);
  drawLabel(
    context,
    `e⁻ʳᵀEQ[Sₜ] = ${formatNumber(s0, 0)}`,
    left.x + left.w - 18,
    left.y + 18,
    colors.ink,
    "right",
  );

  const normalized = diagnostics.samples.map((sample) => ({
    price: sample.price,
    weight: sample.weight / Math.max(diagnostics.meanWeight, 1e-12),
  }));
  const sortedWeights = normalized.map((sample) => sample.weight).sort((a, b) => a - b);
  const yMax = Math.max(1.6, sortedWeights[Math.floor(sortedWeights.length * 0.95)] * 1.15);
  drawRoundedRect(context, right, 16, colors.paper);
  drawChart(
    context,
    right,
    [{ points: [[low, 1], [high, 1]], color: colors.muted, width: 1.3, dashed: true }],
    { x: [low, high], y: [0, yMax] },
    colors,
    { xLabel: "Pで生成した満期価格" },
  );
  const padding = { left: 42, right: 12, top: 14, bottom: 32 };
  const plot = {
    x: right.x + padding.left,
    y: right.y + padding.top,
    w: right.w - padding.left - padding.right,
    h: right.h - padding.top - padding.bottom,
  };
  normalized.forEach((sample) => {
    const x = plot.x + ((sample.price - low) / (high - low)) * plot.w;
    const clippedWeight = Math.min(sample.weight, yMax);
    const y = plot.y + plot.h - (clippedWeight / yMax) * plot.h;
    if (x < plot.x || x > plot.x + plot.w) return;
    context.beginPath();
    context.arc(x, y, 2.3, 0, Math.PI * 2);
    context.fillStyle = sample.weight >= 1 ? colors.amber : colors.teal;
    context.globalAlpha = 0.58;
    context.fill();
  });
  context.globalAlpha = 1;
  drawLabel(context, "各経路の Q/P 重み", right.x + 52, right.y + 18, colors.ink);
  drawLabel(context, "重み=1", right.x + right.w - 14, right.y + 18, colors.muted, "right");
}

function drawLab(canvas: HTMLCanvasElement, lab: LabKind, settings: Settings, dark: boolean) {
  const prepared = prepareCanvas(canvas);
  if (!prepared) return;
  const { context, width, height } = prepared;
  const colors = chartColors(canvas, dark);
  context.fillStyle = colors.white;
  context.fillRect(0, 0, width, height);
  const area = { x: 8, y: 8, w: width - 16, h: height - 16 };
  switch (lab) {
    case "sde-overview":
      drawSdeOverview(context, area, settings, colors);
      break;
    case "random-walk":
      drawRandomWalk(context, area, settings, colors);
      break;
    case "brownian":
      drawBrownian(context, area, settings, colors);
      break;
    case "path-distribution":
      drawPathDistribution(context, area, settings, colors);
      break;
    case "roughness":
      drawRoughness(context, area, settings, colors);
      break;
    case "quadratic-variation":
      drawQuadraticVariation(context, area, settings, colors);
      break;
    case "stochastic-integral":
      drawStochasticIntegral(context, area, settings, colors);
      break;
    case "ito-correction":
      drawItoCorrection(context, area, settings, colors);
      break;
    case "drift-diffusion":
      drawDriftDiffusion(context, area, settings, colors);
      break;
    case "arithmetic-brownian":
      drawArithmeticBrownian(context, area, settings, colors);
      break;
    case "gbm":
      drawGbm(context, area, settings, colors);
      break;
    case "ou":
      drawOu(context, area, settings, colors);
      break;
    case "cir":
      drawCir(context, area, settings, colors);
      break;
    case "correlated-brownian":
      drawCorrelatedBrownian(context, area, settings, colors);
      break;
    case "generator":
      drawGenerator(context, area, settings, colors);
      break;
    case "backward-equation":
      drawBackwardEquation(context, area, settings, colors);
      break;
    case "fokker-planck":
      drawFokkerPlanck(context, area, settings, colors);
      break;
    case "feynman-kac":
      drawFeynmanKac(context, area, settings, colors);
      break;
    case "first-passage":
      drawFirstPassage(context, area, settings, colors);
      break;
    case "euler":
      drawEuler(context, area, settings, colors);
      break;
    case "measure-change":
      drawMeasureChange(context, area, settings, colors);
      break;
    default:
      drawExtendedLab(context, area, lab, settings, colors);
      break;
  }
}

function CanvasLab({
  lab,
  settings,
  dark,
  label,
}: {
  lab: LabKind;
  settings: Settings;
  dark: boolean;
  label: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const draw = useCallback(() => {
    if (canvasRef.current) drawLab(canvasRef.current, lab, settings, dark);
  }, [dark, lab, settings]);

  useEffect(() => {
    draw();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      className="lab-canvas"
      role="img"
      aria-label={label}
    />
  );
}

type ControlDefinition = {
  key: keyof Settings;
  label: string;
  min: number;
  max: number;
  step: number;
  format: (value: number) => string;
};

function choiceOptionsFor(lab: LabKind): Array<[number, string, string]> | null {
  switch (lab) {
    case "ito-correction":
      return [
        [0, "x", "線形"],
        [1, "exp(x)", "凸"],
        [2, "−exp(−x)", "凹"],
      ];
    case "drift-diffusion":
      return [
        [0, "μ, σ", "加法"],
        [1, "κ(θ−x), σ", "平均回帰"],
        [2, "μx, σx", "乗法"],
      ];
    case "generator":
      return [
        [0, "f(x)=x", "線形"],
        [1, "f(x)=x²", "二次"],
        [2, "f(x)=exp(x)", "凸"],
      ];
    case "backward-equation":
      return [
        [0, "(x−K)⁺", "コール"],
        [1, "1{x>K}", "閾値"],
        [2, "x²", "二次"],
      ];
    case "monte-carlo":
      return [
        [0, "単純", "baseline"],
        [1, "反対変数", "antithetic"],
        [2, "制御変数", "Zを利用"],
      ];
    case "model-selection":
      return [
        [0, "拡散", "連続"],
        [1, "ジャンプ", "離散イベント"],
        [2, "OU", "平均回帰"],
      ];
    case "model-criticism":
      return [
        [0, "適合", "白色残差"],
        [1, "依存", "自己相関"],
        [2, "裾", "重い尾"],
      ];
    default:
      return null;
  }
}

function choiceLegendFor(lab: LabKind) {
  if (lab === "drift-diffusion") return "局所モデル";
  if (lab === "backward-equation") return "終端関数 g(x)";
  if (lab === "monte-carlo") return "推定法";
  if (lab === "model-selection") return "候補モデル";
  if (lab === "model-criticism") return "残差シナリオ";
  return "関数 f(x)";
}

function controlsFor(lab: LabKind): ControlDefinition[] {
  const usesAdditiveDrift = [
    "sde-overview",
    "drift-diffusion",
    "arithmetic-brownian",
    "generator",
    "backward-equation",
    "fokker-planck",
    "first-passage",
    "sde-synthesis",
  ].includes(lab);
  const steps: ControlDefinition = {
    key: "steps",
    label: "時間分割",
    min: lab === "euler" ? 8 : 32,
    max: lab === "euler" ? 192 : 384,
    step: lab === "euler" ? 8 : 16,
    format: (value) => `${value}`,
  };
  const paths: ControlDefinition = {
    key: "paths",
    label:
      lab === "gbm"
        ? "経路 / 分布標本"
        : lab === "feynman-kac"
          ? "Monte Carlo 経路"
        : lab === "first-passage"
          ? "初到達標本"
        : lab === "correlated-brownian"
          ? "終端標本"
        : lab === "fokker-planck"
          ? "表示粒子 / 計算標本"
          : lab === "euler"
            ? "結合標本数"
            : "Monte Carlo 標本",
    min: 8,
    max: 96,
    step: 8,
    format: (value) => {
      if (lab === "gbm") return `${Math.min(value, 24)} / ${Math.max(value * 16, 500)}`;
      if (lab === "feynman-kac") return `${Math.max(value * 128, 2048)}`;
      if (lab === "first-passage") return `${Math.max(value * 4, 256)}`;
      if (lab === "correlated-brownian") return `${Math.max(value * 8, 400)}`;
      if (lab === "fokker-planck") return `${value} / ${Math.max(value * 14, 600)}`;
      if (lab === "ito-correction") return `${Math.max(value * 24, 600)}`;
      return `${Math.max(value, 16)}`;
    },
  };
  const sigma: ControlDefinition = {
    key: "sigma",
    label: "拡散 σ",
    min: 0.05,
    max: lab === "quadratic-variation" ? 1 : 0.9,
    step: 0.05,
    format: (value) => formatNumber(value, 2),
  };
  const mu: ControlDefinition = {
    key: "mu",
    label: "ドリフト μ",
    min: usesAdditiveDrift ? -0.8 : -0.2,
    max: usesAdditiveDrift ? 0.8 : 0.3,
    step: usesAdditiveDrift ? 0.05 : 0.01,
    format: usesAdditiveDrift
      ? (value) => formatNumber(value, 2)
      : formatPercent,
  };
  const horizon: ControlDefinition = {
    key: "horizon",
    label: "時間範囲 T",
    min: 0.5,
    max: 10,
    step: 0.5,
    format: (value) => formatNumber(value, 1),
  };
  const kappa: ControlDefinition = {
    key: "kappa",
    label: "速度 κ",
    min: 0.05,
    max: 4,
    step: 0.05,
    format: (value) => formatNumber(value, 2),
  };
  const theta: ControlDefinition = {
    key: "theta",
    label: "水準 θ",
    min: -1,
    max: 2,
    step: 0.05,
    format: (value) => formatNumber(value, 2),
  };
  const rate: ControlDefinition = {
    key: "rate",
    label: "率 r",
    min: 0,
    max: 2,
    step: 0.05,
    format: (value) => formatNumber(value, 2),
  };
  const positiveX0: ControlDefinition = {
    key: "x0",
    label: "初期値 x₀",
    min: 1,
    max: 120,
    step: 1,
    format: (value) => formatNumber(value, 0),
  };
  const sigma2: ControlDefinition = {
    key: "sigma2",
    label: "第2ノイズ σ₂",
    min: 0.02,
    max: 1.2,
    step: 0.02,
    format: (value) => formatNumber(value, 2),
  };
  const rho: ControlDefinition = {
    key: "rho",
    label: "相関 ρ",
    min: -0.95,
    max: 0.95,
    step: 0.05,
    format: (value) => formatNumber(value, 2),
  };

  switch (lab) {
    case "sde-overview":
      return [
        {
          key: "x0",
          label: "平均初期値 x₀",
          min: -1,
          max: 1,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        mu,
        {
          key: "time",
          label: "横断時刻",
          min: 0.1,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "sigma2",
          label: "初期値の標準偏差",
          min: 0.05,
          max: 0.9,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        sigma,
        paths,
      ];
    case "random-walk":
      return [steps, sigma, mu];
    case "brownian":
      return [
        {
          ...steps,
          label: "表示解像度",
          min: 64,
          max: 384,
          step: 64,
        },
      ];
    case "path-distribution":
      return [
        {
          key: "time",
          label: "観測時刻",
          min: 0.05,
          max: 0.95,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "selectedPath",
          label: "注目する経路",
          min: 0,
          max: 15,
          step: 1,
          format: (value) => `${value + 1}`,
        },
        sigma,
        paths,
      ];
    case "roughness":
      return [
        {
          key: "zoom",
          label: "拡大倍率",
          min: 0,
          max: 6,
          step: 1,
          format: (value) => `×${2 ** value}`,
        },
        {
          key: "time",
          label: "区間中心",
          min: 0,
          max: 1,
          step: 0.02,
          format: (value) => formatNumber(value, 2),
        },
      ];
    case "quadratic-variation":
      return [steps];
    case "stochastic-integral":
      return [steps];
    case "ito-correction":
      return [sigma, paths];
    case "drift-diffusion":
      return [
        {
          key: "x0",
          label: "初期状態 x₀",
          min: -1,
          max: 1,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        mu,
        sigma,
        {
          key: "kappa",
          label: "回帰速度 κ",
          min: 0.25,
          max: 3,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
      ];
    case "arithmetic-brownian":
      return [
        {
          key: "x0",
          label: "初期状態 x₀",
          min: -2,
          max: 2,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        mu,
        sigma,
        {
          key: "time",
          label: "密度の時刻",
          min: 0.1,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
      ];
    case "gbm":
      return [sigma, mu, paths];
    case "ou":
      return [
        {
          key: "kappa",
          label: "回帰速度 κ",
          min: 0.25,
          max: 4,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        sigma,
        {
          key: "theta",
          label: "長期平均 θ",
          min: -0.8,
          max: 0.8,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
      ];
    case "cir":
      return [
        {
          key: "x0",
          label: "初期状態 x₀",
          min: 0.05,
          max: 1.5,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "kappa",
          label: "回帰速度 κ",
          min: 0.25,
          max: 4,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "theta",
          label: "長期平均 θ",
          min: 0.1,
          max: 1.5,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        { ...sigma, max: 1.2 },
      ];
    case "correlated-brownian":
      return [
        {
          key: "rho",
          label: "相関 ρ",
          min: -1,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        { ...sigma, label: "拡散 σ₁" },
        {
          key: "sigma2",
          label: "拡散 σ₂",
          min: 0.05,
          max: 0.9,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        paths,
      ];
    case "generator":
      return [
        {
          key: "x0",
          label: "評価状態 x",
          min: -1,
          max: 1,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        {
          key: "localDt",
          label: "短時間 Δt",
          min: 0.01,
          max: 0.2,
          step: 0.01,
          format: (value) => formatNumber(value, 2),
        },
        mu,
        sigma,
      ];
    case "backward-equation":
      return [
        {
          key: "time",
          label: "現在時刻 t",
          min: 0,
          max: 0.95,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "strike",
          label: "閾値 K",
          min: -1,
          max: 1,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        mu,
        sigma,
      ];
    case "fokker-planck":
      return [
        {
          key: "time",
          label: "観測時刻",
          min: 0.05,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        sigma,
        mu,
        paths,
      ];
    case "feynman-kac":
      return [
        {
          key: "x0",
          label: "初期状態 x₀",
          min: -1,
          max: 1,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        { ...mu, min: -0.6, max: 0.6, step: 0.05, format: (value) => formatNumber(value, 2) },
        {
          key: "rate",
          label: "割引率 r",
          min: 0,
          max: 0.1,
          step: 0.005,
          format: formatPercent,
        },
        sigma,
        paths,
      ];
    case "first-passage":
      return [
        {
          key: "x0",
          label: "開始点 x₀",
          min: -0.15,
          max: 0.15,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        {
          key: "lowerBarrier",
          label: "下側境界 L",
          min: -2,
          max: -0.2,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        {
          key: "upperBarrier",
          label: "上側境界 U",
          min: 0.2,
          max: 2,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        mu,
        sigma,
        paths,
      ];
    case "euler":
      return [steps, sigma, mu, paths];
    case "measure-change":
      return [
        mu,
        {
          key: "rate",
          label: "金利 r",
          min: -0.02,
          max: 0.12,
          step: 0.01,
          format: formatPercent,
        },
        sigma,
      ];
    case "brownian-default":
      return [
        { ...steps, label: "集約数 n", min: 16, max: 384, step: 16 },
        sigma,
        { ...horizon, min: 0.5, max: 3, step: 0.25 },
      ];
    case "poisson-jumps":
      return [
        { ...kappa, label: "到着率 λ", max: 8, step: 0.1 },
        { ...horizon, max: 5, step: 0.25 },
      ];
    case "levy-tails":
      return [
        sigma,
        { ...kappa, label: "有限活動の率 λ", min: 0.2, max: 5, step: 0.1 },
        { ...sigma2, label: "ジャンプ幅 σⱼ" },
        { ...horizon, max: 5, step: 0.25 },
      ];
    case "colored-noise":
      return [
        { ...kappa, label: "相関減衰 κ" },
        { ...sigma, label: "積分強度 D", min: 0.05, max: 1, step: 0.05 },
        { ...horizon, max: 5, step: 0.25 },
      ];
    case "fractional-brownian":
      return [
        { ...rho, label: "Hurst 指数 H", min: 0.1, max: 0.9 },
        sigma,
      ];
    case "hawkes":
      return [
        { ...rate, label: "基礎強度 μ", min: 0.05, max: 2 },
        { ...sigma, label: "分枝比 n=α/β", min: 0, max: 0.95, step: 0.05 },
        { ...kappa, label: "減衰率 β", max: 4 },
        { ...horizon, min: 1, max: 8, step: 0.5 },
      ];
    case "milstein":
      return [steps, positiveX0, mu, sigma];
    case "monte-carlo":
      return [
        {
          key: "strike",
          label: "閾値 K",
          min: -1,
          max: 3,
          step: 0.1,
          format: (value) => formatNumber(value, 1),
        },
        {
          ...paths,
          label: "推定単位 N",
          format: (value) => `${Math.max(value * 256, 2048)}`,
        },
      ];
    case "parameter-inference":
      return [
        steps,
        {
          key: "x0",
          label: "初期状態 x₀",
          min: -1,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        { ...kappa, label: "平均回帰 κ" },
        { ...theta, label: "長期平均 θ", min: -1, max: 1 },
        sigma,
        { ...sigma2, label: "観測ノイズ", min: 0.02, max: 0.6 },
        { ...horizon, min: 2, max: 12, step: 0.5 },
      ];
    case "predictability":
      return [mu, sigma, { ...horizon, min: 0.5, max: 8, step: 0.5 }];
    case "martingale":
      return [
        positiveX0,
        mu,
        { ...rate, label: "無リスク金利 r", max: 0.12, step: 0.005, format: formatPercent },
        sigma,
        {
          key: "strike",
          label: "一期間の K",
          min: 60,
          max: 140,
          step: 5,
          format: (value) => formatNumber(value, 0),
        },
        paths,
      ];
    case "delta-hedging":
      return [
        steps,
        positiveX0,
        {
          key: "strike",
          label: "権利行使価格 K",
          min: 60,
          max: 140,
          step: 5,
          format: (value) => formatNumber(value, 0),
        },
        { ...rate, label: "無リスク金利 r", max: 0.12, step: 0.005, format: formatPercent },
        sigma,
      ];
    case "volatility-models":
      return [sigma, { ...sigma2, label: "ボラ変動 / smile" }, rho, kappa];
    case "short-rate":
      return [
        {
          key: "x0",
          label: "初期短期金利 r₀",
          min: 0,
          max: 0.12,
          step: 0.005,
          format: formatPercent,
        },
        { ...theta, label: "長期平均 θ", min: 0.005, max: 0.12, step: 0.005, format: formatPercent },
        { ...kappa, label: "平均回帰 κ" },
        { ...sigma, label: "金利ボラ σ", min: 0.01, max: 0.25, step: 0.01 },
        { ...horizon, min: 1, max: 10, step: 0.5 },
      ];
    case "forward-curve":
      return [
        { ...rate, label: "短期水準", max: 0.1, step: 0.005, format: formatPercent },
        { ...sigma, label: "曲線ショック σ", min: 0.005, max: 0.08, step: 0.005 },
        { ...kappa, label: "満期方向の減衰 κ", max: 2 },
      ];
    case "credit-default":
      return [
        { ...kappa, label: "デフォルト強度 λ", min: 0.02, max: 1, step: 0.02 },
        {
          ...rho,
          label: "回収率 R",
          min: 0,
          max: 0.9,
          step: 0.05,
          format: formatPercent,
        },
        { ...horizon, min: 1, max: 10, step: 0.5 },
      ];
    case "langevin":
      return [
        { ...kappa, label: "摩擦 γ", min: 0.2, max: 3 },
        { ...theta, label: "質量 m", min: 0.2, max: 2, step: 0.1 },
        { ...sigma, label: "温度 kBT", min: 0.05, max: 1.5, step: 0.05 },
        { ...horizon, min: 2, max: 10, step: 0.5 },
      ];
    case "chemical-reaction":
      return [
        { ...positiveX0, label: "初期分子数 N₀", min: 1, max: 100 },
        { ...rate, label: "生成率 k₊Ω", min: 1, max: 12, step: 0.5 },
        { ...kappa, label: "分解率 k₋", min: 0.05, max: 1, step: 0.05 },
        { ...horizon, min: 2, max: 12, step: 0.5 },
      ];
    case "population":
      return [
        { ...positiveX0, label: "初期個体数 N₀", min: 1, max: 50 },
        { ...theta, label: "収容力 K", min: 30, max: 200, step: 5, format: (value) => formatNumber(value, 0) },
        { ...rate, label: "成長率 r", min: 0.1, max: 2, step: 0.05 },
        { ...sigma, label: "人口ノイズ √γ" },
        { ...sigma2, label: "環境ノイズ σₑ", min: 0, max: 0.5, step: 0.02 },
        { ...horizon, min: 2, max: 12, step: 0.5 },
      ];
    case "epidemic":
      return [
        { ...positiveX0, label: "初期感染者 I₀", min: 1, max: 20 },
        { ...theta, label: "集団サイズ N", min: 50, max: 300, step: 10, format: (value) => formatNumber(value, 0) },
        { ...rate, label: "感染率 β", min: 0.2, max: 3, step: 0.05 },
        { ...kappa, label: "回復率 γ", min: 0.1, max: 1.5, step: 0.05 },
        { ...horizon, min: 3, max: 15, step: 0.5 },
      ];
    case "neuroscience":
      return [
        {
          key: "x0",
          label: "リセット電位",
          min: -1,
          max: 0.4,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        { ...theta, label: "平均入力", min: -0.2, max: 1, step: 0.05 },
        { ...kappa, label: "漏れ κ", min: 0.4, max: 4 },
        sigma,
        { ...rho, label: "共通入力率 ρ", min: 0, max: 0.95 },
        {
          key: "upperBarrier",
          label: "発火閾値",
          min: 0.5,
          max: 1.5,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
      ];
    case "filtering":
      return [
        { ...kappa, label: "状態回帰 κ", min: 0.05, max: 2 },
        { ...sigma, label: "プロセスノイズ" },
        { ...sigma2, label: "観測ノイズ" },
        { ...horizon, min: 2, max: 10, step: 0.5 },
      ];
    case "model-selection":
      return [kappa, sigma, { ...sigma2, label: "追加構造の強さ" }];
    case "model-criticism":
      return [{ ...rho, label: "誤指定の強さ q", min: 0.05, max: 0.9 }];
    case "sde-synthesis":
      return [
        {
          key: "x0",
          label: "初期状態 x₀",
          min: -1,
          max: 1,
          step: 0.05,
          format: (value) => formatNumber(value, 2),
        },
        mu,
        sigma,
        {
          key: "zoom",
          label: "粗視化ブロック",
          min: 1,
          max: 6,
          step: 1,
          format: (value) => `${2 ** value} step`,
        },
        {
          ...kappa,
          label: "微視的イベント強度",
          min: 0.5,
          max: 4,
          step: 0.1,
        },
        { ...horizon, min: 0.5, max: 4, step: 0.25 },
      ];
    default:
      return [];
  }
}

function metricsFor(lab: LabKind, settings: Settings) {
  switch (lab) {
    case "sde-overview": {
      const time = settings.time * settings.horizon;
      return [
        ["共通平均", formatNumber(settings.x0 + settings.mu * time, 2)],
        ["初期値分散", formatNumber(settings.sigma2 ** 2, 3)],
        ["SDE 過程分散", formatNumber(settings.sigma ** 2 * time, 3)],
      ];
    }
    case "random-walk":
      return [
        ["終点平均", formatNumber(settings.mu * settings.horizon, 2)],
        ["正しい尺度の分散", formatNumber(settings.sigma ** 2 * settings.horizon, 3)],
        ["Δt", formatNumber(settings.horizon / settings.steps, 4)],
      ];
    case "brownian":
      return [
        ["E[Wₜ]", "0"],
        ["Var(Wₜ)", formatNumber(settings.horizon, 2)],
        ["自己相似尺度", `√T = ${formatNumber(Math.sqrt(settings.horizon), 2)}`],
      ];
    case "path-distribution": {
      const diagnostics = pathDistributionDiagnostics(settings);
      const selectedValue = diagnostics.paths[diagnostics.selectedPath][diagnostics.selectedIndex][1];
      return [
        ["選択経路 Xₜ", formatNumber(selectedValue, 2)],
        ["横断標本平均", formatNumber(diagnostics.mean, 2)],
        ["横断標本分散", formatNumber(diagnostics.variance, 3)],
      ];
    }
    case "roughness": {
      const diagnostics = roughnessDiagnostics(settings);
      return [
        ["選択幅 Δt", formatNumber(diagnostics.window, 4)],
        ["Brownian |傾き|", formatNumber(diagnostics.brownianSlope, 2)],
        ["滑らかな |傾き|", formatNumber(diagnostics.smoothSlope, 2)],
      ];
    }
    case "quadratic-variation":
      return [
        ["理論二次変分", formatNumber(settings.horizon, 2)],
        ["増分の次数", "√dt"],
        ["二乗の次数", "dt"],
      ];
    case "stochastic-integral": {
      const diagnostics = stochasticIntegralDiagnostics(settings);
      return [
        ["左端 Itô 和", formatNumber(diagnostics.left, 3)],
        ["中点 Stratonovich 和", formatNumber(diagnostics.midpoint, 3)],
        ["Σ(ΔW)²", formatNumber(diagnostics.quadraticVariation, 3)],
      ];
    }
    case "ito-correction": {
      const choice = clamp(Math.round(settings.functionChoice), 0, 2);
      const baseline = choice === 0 ? 0 : choice === 1 ? 1 : -1;
      const prediction =
        choice === 0
          ? 0
          : (choice === 1 ? 1 : -1) * Math.exp(0.5 * settings.sigma ** 2 * settings.horizon);
      return [
        ["曲率", choice === 0 ? "0" : choice === 1 ? "正" : "負"],
        ["通常の連鎖律", formatNumber(baseline, 3)],
        ["Itô 予測", formatNumber(prediction, 3)],
      ];
    }
    case "drift-diffusion": {
      const coefficients = driftDiffusionCoefficients(settings, settings.x0);
      const shortDt = 0.06;
      return [
        ["E[ΔX|x]", formatNumber(coefficients.drift * shortDt, 3)],
        ["Var(ΔX|x)", formatNumber(coefficients.diffusion ** 2 * shortDt, 3)],
        ["局所標準偏差", formatNumber(coefficients.diffusion * Math.sqrt(shortDt), 3)],
      ];
    }
    case "arithmetic-brownian": {
      const time = settings.time * settings.horizon;
      return [
        ["解析平均", formatNumber(settings.x0 + settings.mu * time, 2)],
        ["解析分散", formatNumber(settings.sigma ** 2 * time, 3)],
        ["95% 半幅", formatNumber(1.96 * settings.sigma * Math.sqrt(time), 2)],
      ];
    }
    case "gbm":
      return [
        ["理論平均", formatNumber(100 * Math.exp(settings.mu * settings.horizon), 1)],
        ["中央値", formatNumber(100 * Math.exp((settings.mu - 0.5 * settings.sigma ** 2) * settings.horizon), 1)],
        ["対数ドリフト", formatPercent(settings.mu - 0.5 * settings.sigma ** 2)],
      ];
    case "ou":
      return [
        ["半減期", formatNumber(Math.log(2) / settings.kappa, 2)],
        ["長期平均", formatNumber(settings.theta, 2)],
        ["定常標準偏差", formatNumber(settings.sigma / Math.sqrt(2 * settings.kappa), 2)],
      ];
    case "cir": {
      const diagnostics = cirDiagnostics(settings);
      return [
        ["Feller 比", formatNumber(diagnostics.fellerRatio, 2)],
        ["0 の到達", diagnostics.fellerRatio >= 1 ? "到達不能" : "到達し得る"],
        ["射影ステップ率", formatPercent(diagnostics.projectionRate)],
      ];
    }
    case "correlated-brownian": {
      const diagnostics = correlatedBrownianDiagnostics(
        settings,
        Math.max(settings.paths * 12, 800),
      );
      return [
        ["理論相関", formatNumber(settings.rho, 2)],
        ["標本相関", formatNumber(diagnostics.empiricalCorrelation, 2)],
        ["終端共分散", formatNumber(diagnostics.theoreticalCovariance, 3)],
      ];
    }
    case "generator": {
      const diagnostics = generatorDiagnostics(settings);
      return [
        ["解析 ℒf(x)", formatNumber(diagnostics.localAnalytic, 3)],
        ["一歩の標本推定", formatNumber(diagnostics.localEmpirical, 3)],
        ["MC 95% 半幅", formatNumber(diagnostics.localHalfWidth, 3)],
      ];
    }
    case "backward-equation": {
      const diagnostics = backwardDiagnostics(settings);
      return [
        ["残存時間 T−t", formatNumber(settings.horizon - diagnostics.selectedTime, 2)],
        ["u(t,x₀)", formatNumber(diagnostics.valueAtState, 3)],
        ["終端 g(x₀)", formatNumber(terminalPayoff(diagnostics.choice, settings.x0, settings.strike), 3)],
      ];
    }
    case "fokker-planck": {
      const t = settings.time * settings.horizon;
      return [
        ["密度の中心", formatNumber(settings.mu * t, 2)],
        ["密度の標準偏差", formatNumber(settings.sigma * Math.sqrt(t), 2)],
        ["全確率", "1.000"],
      ];
    }
    case "feynman-kac": {
      const diagnostics = feynmanKacDiagnostics(settings);
      return [
        ["PDE / 解析値", formatNumber(diagnostics.analytic, 3)],
        ["Monte Carlo", formatNumber(diagnostics.finalEstimate, 3)],
        ["95% 半幅", formatNumber(diagnostics.finalHalfWidth, 3)],
      ];
    }
    case "first-passage": {
      const diagnostics = firstPassageDiagnostics(settings);
      return [
        ["上側到達率", formatPercent(diagnostics.upperHitRate)],
        ["下側到達率", formatPercent(diagnostics.lowerHitRate)],
        ["期限時点生存率", formatPercent(1 - diagnostics.hitProbability)],
      ];
    }
    case "euler": {
      const diagnostics = eulerDiagnostics(settings);
      return [
        ["平均絶対終点差", formatNumber(diagnostics.meanAbsoluteError, 3)],
        ["平均値の差", formatNumber(diagnostics.weakDifference, 3)],
        ["結合標本数", `${Math.max(settings.paths, 16)}`],
      ];
    }
    case "measure-change": {
      const diagnostics = measureChangeDiagnostics(settings, Math.max(settings.paths * 20, 1000));
      return [
        ["市場価格リスク λ", formatNumber((settings.mu - settings.rate) / settings.sigma, 2)],
        ["Eᴾ[dQ/dP]", formatNumber(diagnostics.meanWeight, 3)],
        ["割引 Q 期待値", formatNumber(diagnostics.discountedWeightedPrice, 1)],
      ];
    }
    default:
      return extendedMetrics(lab, settings) ?? [];
  }
}

function Icon({ name }: { name: "moon" | "sun" | "menu" | "check" | "copy" | "shuffle" }) {
  const symbols = {
    moon: "◐",
    sun: "☼",
    menu: "☰",
    check: "✓",
    copy: "⧉",
    shuffle: "↻",
  };
  return <span aria-hidden="true">{symbols[name]}</span>;
}

export function SDETextbook() {
  const [activeId, setActiveId] = useState(chapters[0].id);
  const [settings, setSettings] = useState<Settings>({
    ...baseSettings,
    ...labDefaults[chapters[0].lab],
  });
  const [completed, setCompleted] = useState<string[]>([]);
  const [dark, setDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const activeIndex = chapters.findIndex((chapter) => chapter.id === activeId);
  const chapter = chapters[Math.max(activeIndex, 0)];
  const progress = Math.round((completed.length / chapters.length) * 100);
  const controls = useMemo(() => controlsFor(chapter.lab), [chapter.lab]);
  const choiceOptions = useMemo(() => choiceOptionsFor(chapter.lab), [chapter.lab]);
  const metrics = useMemo(() => metricsFor(chapter.lab, settings), [chapter.lab, settings]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const storedProgress = localStorage.getItem("sde-textbook-progress");
      const storedTheme = localStorage.getItem("sde-textbook-theme");
      const hash = window.location.hash.replace(/^#chapter-/, "");
      if (storedProgress) {
        try {
          const parsed = JSON.parse(storedProgress) as string[];
          setCompleted(parsed.filter((id) => chapters.some((item) => item.id === id)));
        } catch {
          localStorage.removeItem("sde-textbook-progress");
        }
      }
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setDark(storedTheme ? storedTheme === "dark" : prefersDark);
      const hashChapter = chapters.find((item) => item.id === hash);
      if (hashChapter) {
        setActiveId(hashChapter.id);
        setSettings({ ...baseSettings, ...labDefaults[hashChapter.lab] });
      }
      setMounted(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("sde-textbook-theme", dark ? "dark" : "light");
  }, [dark, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem("sde-textbook-progress", JSON.stringify(completed));
  }, [completed, mounted]);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const frame = window.requestAnimationFrame(() => setIsMobile(media.matches));
    const onChange = (event: MediaQueryListEvent) => setIsMobile(event.matches);
    media.addEventListener("change", onChange);
    return () => {
      window.cancelAnimationFrame(frame);
      media.removeEventListener("change", onChange);
    };
  }, []);

  useEffect(() => {
    if (!isMobile || !sidebarOpen) return;
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : menuButtonRef.current;
    const frame = window.requestAnimationFrame(() => {
      sidebarRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    });
    const onDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSidebarOpen(false);
        return;
      }
      if (event.key !== "Tab" || !sidebarRef.current) return;
      const focusable = Array.from(
        sidebarRef.current.querySelectorAll<HTMLElement>("button, a[href], summary, [tabindex]:not([tabindex='-1'])"),
      ).filter((element) => !element.hasAttribute("disabled"));
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onDialogKeyDown);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onDialogKeyDown);
      previousFocus?.focus();
    };
  }, [isMobile, sidebarOpen]);

  const navigate = useCallback((id: string) => {
    const next = chapters.find((item) => item.id === id);
    if (!next) return;
    setActiveId(id);
    setSettings({ ...baseSettings, ...labDefaults[next.lab] });
    setCopied(false);
    setSidebarOpen(false);
    window.history.replaceState(null, "", `#chapter-${id}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(".chapter-hero h1")?.focus({ preventScroll: true });
    });
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, button, textarea, select, summary")) return;
      if (event.key === "j" && activeIndex < chapters.length - 1) {
        navigate(chapters[activeIndex + 1].id);
      }
      if (event.key === "k" && activeIndex > 0) {
        navigate(chapters[activeIndex - 1].id);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, navigate]);

  const toggleComplete = () => {
    setCompleted((current) =>
      current.includes(chapter.id)
        ? current.filter((id) => id !== chapter.id)
        : [...current, chapter.id],
    );
  };

  const copyFormula = async () => {
    try {
      await navigator.clipboard.writeText(chapter.formula);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="textbook-shell">
      <a className="skip-link" href="#main-content">
        本文へ移動
      </a>
      <header className="topbar" inert={isMobile && sidebarOpen ? true : undefined}>
        <button
          ref={menuButtonRef}
          className="icon-button mobile-menu"
          type="button"
          aria-label="章一覧を開く"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen((open) => !open)}
        >
          <Icon name="menu" />
        </button>
        <a className="brand" href={`#chapter-${chapters[0].id}`} onClick={() => navigate(chapters[0].id)}>
          <span className="brand-mark">dW</span>
          <span>
            <strong>Stochastic</strong>
            <small>不確かな世界の微分方程式</small>
          </span>
        </a>
        <div className="topbar-progress" aria-label={`学習進捗 ${progress}%`}>
          <span>{completed.length} / {chapters.length} 章</span>
          <span className="progress-track"><span style={{ width: `${progress}%` }} /></span>
        </div>
        <button
          className="icon-button"
          type="button"
          aria-label={dark ? "ライトモードに切り替える" : "ダークモードに切り替える"}
          onClick={() => setDark((value) => !value)}
        >
          <Icon name={dark ? "sun" : "moon"} />
        </button>
      </header>

      <div className="page-grid">
        <aside
          ref={sidebarRef}
          className={`sidebar ${sidebarOpen ? "is-open" : ""}`}
          aria-label="教科書の目次"
          role={isMobile ? "dialog" : undefined}
          aria-modal={isMobile ? true : undefined}
          inert={isMobile && !sidebarOpen ? true : undefined}
        >
          <div className="sidebar-head">
            <p className="overline">INTERACTIVE EDITION · {chapters.length} CHAPTERS</p>
            <h2>学習ルート</h2>
            <p>離散モデルから測度変更まで、同じ視覚言語でつなぎます。</p>
          </div>
          <nav>
            {chapterGroups.map((group) => (
              <div className="chapter-group" key={group}>
                <p>{group}</p>
                {chapters.filter((item) => item.part === group).map((item) => {
                  const isActive = item.id === chapter.id;
                  const isDone = completed.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`chapter-link ${isActive ? "is-active" : ""}`}
                      aria-current={isActive ? "page" : undefined}
                      onClick={() => navigate(item.id)}
                    >
                      <span className="chapter-number">{String(item.number).padStart(2, "0")}</span>
                      <span>{item.shortTitle}</span>
                      <span className={`completion-dot ${isDone ? "is-done" : ""}`} aria-label={isDone ? "完了" : "未完了"}>
                        {isDone ? "✓" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>
          <details className="glossary-panel">
            <summary>ミニ用語集</summary>
            <dl>
              {glossary.map((item) => (
                <div key={item.term}>
                  <dt>{item.term} <span>{item.symbol}</span></dt>
                  <dd>{item.definition}</dd>
                </div>
              ))}
            </dl>
          </details>
          <p className="keyboard-hint"><kbd>J</kbd> 次章　<kbd>K</kbd> 前章</p>
        </aside>

        <main
          id="main-content"
          className="chapter-main"
          inert={isMobile && sidebarOpen ? true : undefined}
        >
          <article key={chapter.id} className="chapter-article">
            <header className="chapter-hero">
              <div className="hero-meta">
                <span>{chapter.part}</span>
                <span>CHAPTER {String(chapter.number).padStart(2, "0")}</span>
                <span>{chapter.readTime}</span>
              </div>
              <p className="hero-question">{chapter.question}</p>
              <h1 tabIndex={-1}>{chapter.title}</h1>
              <p className="hero-lead">{chapter.lead}</p>
              <div className="hero-actions">
                <button
                  type="button"
                  className={`complete-button ${completed.includes(chapter.id) ? "is-complete" : ""}`}
                  onClick={toggleComplete}
                >
                  <Icon name="check" />
                  {completed.includes(chapter.id) ? "学習済みにしました" : "この章を学習済みにする"}
                </button>
                <a href="#experiment" className="text-link">実験から始める ↓</a>
              </div>
            </header>

            <section className="opening-grid" aria-label="章の学習目標と中心公式">
              {chapter.bridge && (
                <aside className="bridge-note">
                  <span>PREREQUISITE BRIDGE</span>
                  <p>{chapter.bridge}</p>
                </aside>
              )}
              <div className="objectives-card">
                <p className="overline">LEARNING OBJECTIVES</p>
                <h2>この章でできるようになること</h2>
                <ol>
                  {chapter.objectives.map((objective, index) => (
                    <li key={objective}><span>{index + 1}</span>{objective}</li>
                  ))}
                </ol>
              </div>
              <div className="formula-card">
                <div>
                  <p className="overline">CENTRAL RELATION</p>
                  <button type="button" className="copy-button" onClick={copyFormula} aria-label="中心公式をコピー">
                    <Icon name="copy" /> {copied ? "コピーしました" : "コピー"}
                  </button>
                </div>
                <p className="display-formula">{chapter.formula}</p>
                <p>{chapter.formulaLabel}</p>
              </div>
            </section>

            <section id="experiment" className="lab-section" aria-labelledby="lab-title">
              <div className="lab-heading">
                <div>
                  <p className="overline">NUMERICAL EXPERIMENT · SEE, THEN EXPLAIN</p>
                  <h2 id="lab-title">{chapter.labTitle}</h2>
                  <p>{chapter.labObjective}</p>
                </div>
                <button
                  type="button"
                  className="seed-button"
                  onClick={() => setSettings((current) => ({ ...current, seed: current.seed + 1 }))}
                >
                  <Icon name="shuffle" /> 新しい標本
                </button>
              </div>
              <div className="lab-workbench">
                <div className="lab-visual">
                  <CanvasLab
                    lab={chapter.lab}
                    settings={settings}
                    dark={dark}
                    label={`${chapter.labTitle}。${metrics.map(([label, value]) => `${label}: ${value}`).join("、")}`}
                  />
                  <div className="metric-row" aria-live="polite">
                    {metrics.map(([label, value]) => (
                      <div key={label}>
                        <span>{label}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="lab-controls">
                  <div className="controls-heading">
                    <span>PARAMETERS</span>
                    <button
                      type="button"
                      onClick={() => setSettings({ ...baseSettings, ...labDefaults[chapter.lab] })}
                    >
                      リセット
                    </button>
                  </div>
                  {choiceOptions && (
                    <fieldset className="choice-control">
                      <legend>{choiceLegendFor(chapter.lab)}</legend>
                      <div>
                        {choiceOptions.map(([value, formula, descriptor]) => (
                          <button
                            key={String(value)}
                            type="button"
                            className={settings.functionChoice === value ? "is-selected" : ""}
                            aria-pressed={settings.functionChoice === value}
                            onClick={() => setSettings((current) => ({
                              ...current,
                              functionChoice: Number(value),
                            }))}
                          >
                            <strong>{formula}</strong>
                            <span>{descriptor}</span>
                          </button>
                        ))}
                      </div>
                    </fieldset>
                  )}
                  {controls.map((control) => (
                    <label className="range-control" key={control.key}>
                      <span><b>{control.label}</b><output>{control.format(settings[control.key])}</output></span>
                      <input
                        type="range"
                        min={control.min}
                        max={control.max}
                        step={control.step}
                        value={settings[control.key]}
                        onChange={(event) => setSettings((current) => ({
                          ...current,
                          [control.key]: Number(event.target.value),
                        }))}
                      />
                    </label>
                  ))}
                  <div className="notice-panel">
                    <p className="overline">WHAT TO NOTICE</p>
                    <ul>
                      {chapter.notice.map((notice) => <li key={notice}>{notice}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
              <p className="lab-caption">
                線と色の意味は各図の凡例に示します。乱数 seed {settings.seed}。図は証明ではなく、式が予測する構造を検査するための数値実験です。
              </p>
            </section>

            <section className="exposition" aria-label="本文">
              {chapter.sections.map((section) => (
                <div className="prose-section" key={section.title}>
                  <p className="overline">{section.eyebrow}</p>
                  <h2>{section.title}</h2>
                  {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
                </div>
              ))}
              <aside className="key-idea">
                <span>KEY IDEA</span>
                <p>{chapter.keyIdea}</p>
              </aside>
              <details className="expandable-box">
                <summary><span>記号が意味すること</span><small>NOTATION</small></summary>
                <p>{chapter.notation}</p>
                <p>微分形は略記です。基本的には、時間積分と Itô 確率積分からなる積分方程式として読みます。</p>
              </details>
              <details className="expandable-box rigor-box">
                <summary><span>厳密さについて</span><small>RIGOR</small></summary>
                <p>本文の極限・期待値交換・解の存在には条件があります。現行版では直観と検証可能な公式を主経路に置き、収束モードや可測性などは章ごとの注記で補います。</p>
              </details>
            </section>

            <section className="exercise-card" aria-labelledby="exercise-title">
              <div className="exercise-index">EX<br />{String(chapter.number).padStart(2, "0")}</div>
              <div>
                <p className="overline">CHECK YOUR UNDERSTANDING</p>
                <h2 id="exercise-title">手を動かして確かめる</h2>
                <p>{chapter.exercise.prompt}</p>
                <div className="exercise-reveals">
                  <details><summary>ヒントを見る</summary><p>{chapter.exercise.hint}</p></details>
                  <details><summary>解答を見る</summary><p>{chapter.exercise.answer}</p></details>
                </div>
              </div>
            </section>

            <aside className="next-idea">
              <span>WHERE THIS APPEARS NEXT</span>
              <p>{chapter.next}</p>
            </aside>

            <nav className="chapter-pagination" aria-label="前後の章">
              {activeIndex > 0 ? (
                <button type="button" onClick={() => navigate(chapters[activeIndex - 1].id)}>
                  <span>← 前章</span>
                  <strong>{chapters[activeIndex - 1].shortTitle}</strong>
                </button>
              ) : <span />}
              {activeIndex < chapters.length - 1 ? (
                <button type="button" className="next" onClick={() => navigate(chapters[activeIndex + 1].id)}>
                  <span>次章 →</span>
                  <strong>{chapters[activeIndex + 1].shortTitle}</strong>
                </button>
              ) : (
                <button type="button" className="next" onClick={() => navigate(chapters[0].id)}>
                  <span>最初へ戻る ↺</span>
                  <strong>{chapters[0].shortTitle}</strong>
                </button>
              )}
            </nav>
          </article>
        </main>
      </div>
      {sidebarOpen && <button className="sidebar-scrim" aria-label="目次を閉じる" onClick={() => setSidebarOpen(false)} />}
    </div>
  );
}
