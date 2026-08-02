import type { LabKind } from "../content/chapters";
import { applicationMetrics, drawApplicationLab } from "./application-labs";

export type ExtendedSettings = {
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
export type ExtendedColors = {
  ink: string;
  muted: string;
  grid: string;
  paper: string;
  teal: string;
  amber: string;
  coral: string;
  violet: string;
  white: string;
};

function clamp(value: number, low: number, high: number) {
  return Math.min(Math.max(value, low), high);
}

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
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * random());
}

function normalCdf(value: number) {
  const sign = value < 0 ? -1 : 1;
  const x = Math.abs(value) / Math.sqrt(2);
  const t = 1 / (1 + 0.3275911 * x);
  const polynomial =
    (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
    t;
  return 0.5 * (1 + sign * (1 - polynomial * Math.exp(-x * x)));
}

function format(value: number, digits = 2) {
  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function rounded(context: CanvasRenderingContext2D, rect: Rect, radius: number, fill: string) {
  context.beginPath();
  context.roundRect(rect.x, rect.y, rect.w, rect.h, radius);
  context.fillStyle = fill;
  context.fill();
}

function label(
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

function domain(series: Point[][], padding = 0.12): [number, number] {
  const values = series.flat().map((point) => point[1]).filter(Number.isFinite);
  if (values.length === 0) return [-1, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = Math.max(high - low, Math.abs(high) * 0.08, 0.1);
  return [low - span * padding, high + span * padding];
}

function chart(
  context: CanvasRenderingContext2D,
  rect: Rect,
  series: Array<{
    points: Point[];
    color: string;
    width?: number;
    dashed?: boolean;
    alpha?: number;
  }>,
  bounds: { x: [number, number]; y: [number, number] },
  colors: ExtendedColors,
  xLabel = "",
  yLabel = "",
) {
  const padding = { left: 42, right: 12, top: 14, bottom: 32 };
  const plot = {
    x: rect.x + padding.left,
    y: rect.y + padding.top,
    w: rect.w - padding.left - padding.right,
    h: rect.h - padding.top - padding.bottom,
  };
  const xSpan = Math.max(bounds.x[1] - bounds.x[0], 1e-9);
  const ySpan = Math.max(bounds.y[1] - bounds.y[0], 1e-9);
  const mapX = (value: number) => plot.x + ((value - bounds.x[0]) / xSpan) * plot.w;
  const mapY = (value: number) => plot.y + plot.h - ((value - bounds.y[0]) / ySpan) * plot.h;
  context.save();
  context.strokeStyle = colors.grid;
  context.lineWidth = 1;
  for (let index = 0; index <= 4; index += 1) {
    const y = plot.y + (index / 4) * plot.h;
    context.beginPath();
    context.moveTo(plot.x, y);
    context.lineTo(plot.x + plot.w, y);
    context.stroke();
  }
  context.beginPath();
  context.rect(plot.x, plot.y, plot.w, plot.h);
  context.clip();
  series.forEach((item) => {
    if (item.points.length === 0) return;
    context.beginPath();
    item.points.forEach(([x, y], index) => {
      if (index === 0) context.moveTo(mapX(x), mapY(y));
      else context.lineTo(mapX(x), mapY(y));
    });
    context.strokeStyle = item.color;
    context.lineWidth = item.width ?? 1.8;
    context.globalAlpha = item.alpha ?? 1;
    context.setLineDash(item.dashed ? [5, 4] : []);
    context.stroke();
  });
  context.restore();
  context.globalAlpha = 1;
  context.setLineDash([]);
  label(context, format(bounds.y[1], 1), plot.x - 7, plot.y + 4, colors.muted, "right");
  label(context, format(bounds.y[0], 1), plot.x - 7, plot.y + plot.h, colors.muted, "right");
  if (xLabel) label(context, xLabel, plot.x + plot.w / 2, rect.y + rect.h - 8, colors.muted, "center");
  if (yLabel) {
    context.save();
    context.translate(rect.x + 12, plot.y + plot.h / 2);
    context.rotate(-Math.PI / 2);
    label(context, yLabel, 0, 0, colors.muted, "center");
    context.restore();
  }
  return { plot, mapX, mapY };
}

function panels(area: Rect, leftRatio = 0.58) {
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * leftRatio - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  return { left, right, gap };
}

function poisson(random: () => number, rate: number) {
  if (rate <= 0) return 0;
  const threshold = Math.exp(-rate);
  let product = 1;
  let count = 0;
  do {
    count += 1;
    product *= random();
  } while (product > threshold);
  return count - 1;
}

function empiricalCdf(values: number[]): Point[] {
  return [...values]
    .sort((a, b) => a - b)
    .map((value, index) => [value, (index + 1) / values.length]);
}

function drawBrownianDefault(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.58);
  const random = mulberry32(settings.seed + 307);
  const steps = clamp(Math.round(settings.steps), 16, 384);
  const dt = settings.horizon / steps;
  const drawShock = (kind: "gaussian" | "two-point" | "skewed") => {
    if (kind === "gaussian") return normal(random);
    if (kind === "two-point") return random() < 0.5 ? -1 : 1;
    return -Math.log(Math.max(random(), 1e-12)) - 1;
  };
  const gaussianPath: Point[] = [[0, 0]];
  const twoPointPath: Point[] = [[0, 0]];
  const skewedPath: Point[] = [[0, 0]];
  let gaussianValue = 0;
  let twoPointValue = 0;
  let skewedValue = 0;
  for (let index = 0; index < steps; index += 1) {
    gaussianValue += settings.sigma * Math.sqrt(dt) * drawShock("gaussian");
    twoPointValue += settings.sigma * Math.sqrt(dt) * drawShock("two-point");
    skewedValue += settings.sigma * Math.sqrt(dt) * drawShock("skewed");
    const time = (index + 1) * dt;
    gaussianPath.push([time, gaussianValue]);
    twoPointPath.push([time, twoPointValue]);
    skewedPath.push([time, skewedValue]);
  }
  rounded(context, left, 16, colors.paper);
  chart(
    context,
    left,
    [
      { points: gaussianPath, color: colors.teal, width: 2.3 },
      { points: twoPointPath, color: colors.amber, width: 1.9 },
      { points: skewedPath, color: colors.coral, width: 1.9 },
    ],
    { x: [0, settings.horizon], y: domain([gaussianPath, twoPointPath, skewedPath], 0.14) },
    colors,
    "時間 t",
  );
  label(context, "Gaussian", left.x + 52, left.y + 18, colors.teal);
  label(context, "±1", left.x + 126, left.y + 18, colors.amber);
  label(context, "歪み", left.x + 166, left.y + 18, colors.coral);

  const terminals: Record<"gaussian" | "two-point" | "skewed", number[]> = {
    gaussian: [],
    "two-point": [],
    skewed: [],
  };
  for (let sample = 0; sample < 700; sample += 1) {
    (["gaussian", "two-point", "skewed"] as const).forEach((kind) => {
      let value = 0;
      for (let index = 0; index < steps; index += 1) {
        value += settings.sigma * Math.sqrt(dt) * drawShock(kind);
      }
      terminals[kind].push(value);
    });
  }
  const xValues = [...terminals.gaussian, ...terminals["two-point"], ...terminals.skewed];
  rounded(context, right, 16, colors.paper);
  chart(
    context,
    right,
    [
      { points: empiricalCdf(terminals.gaussian), color: colors.teal, width: 2.3 },
      { points: empiricalCdf(terminals["two-point"]), color: colors.amber, width: 1.9 },
      { points: empiricalCdf(terminals.skewed), color: colors.coral, width: 1.9 },
    ],
    { x: [Math.min(...xValues), Math.max(...xValues)], y: [0, 1] },
    colors,
    "終端値",
    "経験 CDF",
  );
  label(context, `n=${steps} で集約`, right.x + 52, right.y + 18, colors.ink);
}

function drawPoissonJumps(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.6);
  const random = mulberry32(settings.seed + 331);
  const rate = Math.max(settings.kappa, 0.05);
  let time = 0;
  let count = 0;
  const counting: Point[] = [[0, 0]];
  while (time < settings.horizon) {
    const wait = -Math.log(Math.max(random(), 1e-12)) / rate;
    const next = time + wait;
    if (next > settings.horizon) break;
    counting.push([next, count], [next, count + 1]);
    count += 1;
    time = next;
  }
  counting.push([settings.horizon, count]);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [{ points: counting, color: colors.teal, width: 2.5 }], {
    x: [0, settings.horizon],
    y: [0, Math.max(count + 1, rate * settings.horizon * 1.4)],
  }, colors, "時間 t", "累積イベント Nₜ");
  label(context, `待ち時間 ~ Exp(${format(rate, 1)})`, left.x + 52, left.y + 18, colors.teal);

  const samples = Array.from({ length: 1200 }, () => poisson(random, rate * settings.horizon));
  const maxCount = Math.max(...samples, Math.ceil(rate * settings.horizon + 4 * Math.sqrt(rate * settings.horizon)));
  const frequencies = Array.from({ length: maxCount + 1 }, (_, value) => [
    value,
    samples.filter((sample) => sample === value).length / samples.length,
  ] as Point);
  const probabilities: Point[] = [];
  let probability = Math.exp(-rate * settings.horizon);
  probabilities.push([0, probability]);
  for (let value = 1; value <= maxCount; value += 1) {
    probability *= (rate * settings.horizon) / value;
    probabilities.push([value, probability]);
  }
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: frequencies, color: colors.amber, width: 2.2 },
    { points: probabilities, color: colors.teal, width: 2.2, dashed: true },
  ], {
    x: [0, maxCount],
    y: [0, Math.max(...frequencies.map((point) => point[1]), ...probabilities.map((point) => point[1])) * 1.15],
  }, colors, "期限内イベント数", "確率");
  label(context, "標本", right.x + 52, right.y + 18, colors.amber);
  label(context, "Poisson 理論", right.x + right.w - 14, right.y + 18, colors.teal, "right");
}

function symmetricStable(random: () => number, alpha: number) {
  const angle = Math.PI * (random() - 0.5);
  const exponential = -Math.log(Math.max(random(), 1e-12));
  return Math.sin(alpha * angle) / Math.cos(angle) ** (1 / alpha) *
    (Math.cos((1 - alpha) * angle) / exponential) ** ((1 - alpha) / alpha);
}

function drawLevyTails(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.58);
  const random = mulberry32(settings.seed + 347);
  const steps = 220;
  const dt = settings.horizon / steps;
  const alpha = 1.5;
  let gaussianValue = 0;
  let compoundValue = 0;
  let stableValue = 0;
  const gaussianPath: Point[] = [[0, 0]];
  const compoundPath: Point[] = [[0, 0]];
  const stablePath: Point[] = [[0, 0]];
  for (let index = 0; index < steps; index += 1) {
    gaussianValue += settings.sigma * Math.sqrt(dt) * normal(random);
    const events = poisson(random, settings.kappa * dt);
    for (let event = 0; event < events; event += 1) {
      compoundValue += settings.sigma2 * normal(random);
    }
    stableValue += settings.sigma * dt ** (1 / alpha) * symmetricStable(random, alpha);
    const time = (index + 1) * dt;
    gaussianPath.push([time, gaussianValue]);
    compoundPath.push([time, compoundValue]);
    stablePath.push([time, stableValue]);
  }
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: gaussianPath, color: colors.teal, width: 2.2 },
    { points: compoundPath, color: colors.amber, width: 2 },
    { points: stablePath, color: colors.coral, width: 2.1 },
  ], { x: [0, settings.horizon], y: domain([gaussianPath, compoundPath, stablePath], 0.14) }, colors, "時間 t");
  label(context, "Brownian", left.x + 52, left.y + 18, colors.teal);
  label(context, "有限活動", left.x + 130, left.y + 18, colors.amber);
  label(context, "α-stable", left.x + 198, left.y + 18, colors.coral);

  const gaussian = Array.from({ length: 5000 }, () => Math.abs(normal(random)));
  const compoundScale = Math.max(Math.sqrt(settings.kappa) * settings.sigma2, 1e-6);
  const compound = Array.from({ length: 5000 }, () => {
    let value = 0;
    const events = poisson(random, settings.kappa);
    for (let event = 0; event < events; event += 1) value += settings.sigma2 * normal(random);
    return Math.abs(value / compoundScale);
  });
  const stable = Array.from({ length: 5000 }, () => Math.abs(symmetricStable(random, alpha)));
  const thresholds = Array.from({ length: 60 }, (_, index) => 0.2 + (index / 59) * 7.8);
  const gaussianTail: Point[] = thresholds.map((threshold) => [
    threshold,
    Math.log10(Math.max(gaussian.filter((value) => value > threshold).length / gaussian.length, 1e-4)),
  ]);
  const compoundTail: Point[] = thresholds.map((threshold) => [
    threshold,
    Math.log10(Math.max(compound.filter((value) => value > threshold).length / compound.length, 1e-4)),
  ]);
  const stableTail: Point[] = thresholds.map((threshold) => [
    threshold,
    Math.log10(Math.max(stable.filter((value) => value > threshold).length / stable.length, 1e-4)),
  ]);
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: gaussianTail, color: colors.teal, width: 2.3 },
    { points: compoundTail, color: colors.amber, width: 2.1 },
    { points: stableTail, color: colors.coral, width: 2.3 },
  ], { x: [0.2, 8], y: [-4.2, 0] }, colors, "標準化閾値 |z|", "log₁₀ P(|Z|>z)");
  label(context, "裾確率の比較", right.x + 52, right.y + 18, colors.ink);
}

function drawColoredNoise(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.62);
  const random = mulberry32(settings.seed + 359);
  const steps = 260;
  const dt = settings.horizon / steps;
  const decayRate = Math.max(settings.kappa, 0.01);
  const slowRate = decayRate / 4;
  const intensity = Math.max(settings.sigma, 0.01);
  const decay = Math.exp(-decayRate * dt);
  const slowDecay = Math.exp(-slowRate * dt);
  const stationaryVariance = intensity * decayRate;
  const slowVariance = intensity * slowRate;
  const innovation = Math.sqrt(stationaryVariance * (1 - decay ** 2));
  const slowInnovation = Math.sqrt(slowVariance * (1 - slowDecay ** 2));
  let colored = Math.sqrt(stationaryVariance) * normal(random);
  let slow = Math.sqrt(slowVariance) * normal(random);
  let whiteState = 0;
  let coloredState = 0;
  let slowState = 0;
  const whitePath: Point[] = [[0, 0]];
  const coloredPath: Point[] = [[0, 0]];
  const slowPath: Point[] = [[0, 0]];
  for (let index = 1; index <= steps; index += 1) {
    colored = decay * colored + innovation * normal(random);
    slow = slowDecay * slow + slowInnovation * normal(random);
    whiteState += Math.sqrt(2 * intensity * dt) * normal(random);
    coloredState += colored * dt;
    slowState += slow * dt;
    const time = index * dt;
    whitePath.push([time, whiteState]);
    coloredPath.push([time, coloredState]);
    slowPath.push([time, slowState]);
  }
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: whitePath, color: colors.muted, width: 1.4, dashed: true },
    { points: coloredPath, color: colors.teal, width: 2.2 },
    { points: slowPath, color: colors.coral, width: 2.1 },
  ], { x: [0, settings.horizon], y: domain([whitePath, coloredPath, slowPath], 0.08) }, colors, "時間 t", "駆動状態 Xₜ=∫ηds");
  label(context, "白色極限", left.x + 52, left.y + 18, colors.muted);
  label(context, "OU", left.x + 122, left.y + 18, colors.teal);
  label(context, "slow OU", left.x + 158, left.y + 18, colors.coral);

  const whiteAcf: Point[] = [[0, 1], [0.001, 0], [settings.horizon, 0]];
  const coloredAcf: Point[] = Array.from({ length: 101 }, (_, index) => {
    const lag = (index / 100) * settings.horizon;
    return [lag, Math.exp(-decayRate * lag)];
  });
  const slowAcf: Point[] = Array.from({ length: 101 }, (_, index) => {
    const lag = (index / 100) * settings.horizon;
    return [lag, Math.exp(-slowRate * lag)];
  });
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: whiteAcf, color: colors.muted, width: 1.6, dashed: true },
    { points: coloredAcf, color: colors.teal, width: 2.4 },
    { points: slowAcf, color: colors.coral, width: 2.1 },
  ], { x: [0, settings.horizon], y: [0, 1.05] }, colors, "lag h", "自己相関");
  label(context, `相関時間 τc=${format(1 / decayRate, 2)}`, right.x + 52, right.y + 18, colors.teal);
}

function fractionalGaussianPath(settings: ExtendedSettings) {
  const steps = 96;
  const hurst = clamp(settings.rho, 0.1, 0.9);
  const covariance = Array.from({ length: steps }, (_, lag) =>
    0.5 * ((lag + 1) ** (2 * hurst) - 2 * lag ** (2 * hurst) + Math.abs(lag - 1) ** (2 * hurst))
  );
  const cholesky = Array.from({ length: steps }, () => Array.from({ length: steps }, () => 0));
  for (let row = 0; row < steps; row += 1) {
    for (let column = 0; column <= row; column += 1) {
      let sum = covariance[row - column];
      for (let inner = 0; inner < column; inner += 1) {
        sum -= cholesky[row][inner] * cholesky[column][inner];
      }
      cholesky[row][column] = row === column
        ? Math.sqrt(Math.max(sum, 1e-12))
        : sum / cholesky[column][column];
    }
  }
  const random = mulberry32(settings.seed + 373);
  const normals = Array.from({ length: steps }, () => normal(random));
  const dt = settings.horizon / steps;
  let value = 0;
  const path: Point[] = [[0, 0]];
  for (let row = 0; row < steps; row += 1) {
    let increment = 0;
    for (let column = 0; column <= row; column += 1) {
      increment += cholesky[row][column] * normals[column];
    }
    value += settings.sigma * dt ** hurst * increment;
    path.push([(row + 1) * dt, value]);
  }
  return { path, covariance, hurst };
}

function drawFractionalBrownian(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.64);
  const diagnostics = fractionalGaussianPath(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [{ points: diagnostics.path, color: colors.teal, width: 2.4 }], {
    x: [0, settings.horizon],
    y: domain([diagnostics.path], 0.14),
  }, colors, "時間 t");
  label(context, `fBM · H=${format(diagnostics.hurst, 2)}`, left.x + 52, left.y + 18, colors.teal);

  const acf: Point[] = diagnostics.covariance.slice(0, 25).map((value, lag) => [lag, value]);
  const gap = 10;
  const rightTop = { ...right, h: (right.h - gap) / 2 };
  const rightBottom = {
    x: right.x,
    y: right.y + rightTop.h + gap,
    w: right.w,
    h: rightTop.h,
  };
  rounded(context, rightTop, 14, colors.paper);
  chart(context, rightTop, [{ points: acf, color: colors.amber, width: 2.4 }], {
    x: [0, 24],
    y: [Math.min(-0.55, ...acf.map((point) => point[1])), 1.05],
  }, colors, "increment lag", "相関");
  label(context, diagnostics.hurst > 0.5 ? "持続性" : diagnostics.hurst < 0.5 ? "反持続性" : "独立増分", rightTop.x + 52, rightTop.y + 18, colors.amber);

  const values = diagnostics.path.map((point) => point[1]);
  const dt = settings.horizon / (diagnostics.path.length - 1);
  const empiricalScaling: Point[] = [1, 2, 4, 8, 16].map((lag) => {
    const increments = values.slice(lag).map((value, index) => value - values[index]);
    const mean = increments.reduce((sum, value) => sum + value, 0) / increments.length;
    const variance = increments.reduce((sum, value) => sum + (value - mean) ** 2, 0) /
      Math.max(increments.length - 1, 1);
    return [Math.log10(lag * dt), Math.log10(Math.max(variance, 1e-9))];
  });
  const theoreticalScaling: Point[] = empiricalScaling.map(([x]) => [
    x,
    Math.log10(settings.sigma ** 2) + 2 * diagnostics.hurst * x,
  ]);
  rounded(context, rightBottom, 14, colors.paper);
  chart(context, rightBottom, [
    { points: empiricalScaling, color: colors.coral, width: 2.2 },
    { points: theoreticalScaling, color: colors.teal, width: 1.8, dashed: true },
  ], {
    x: [empiricalScaling[0][0], empiricalScaling[empiricalScaling.length - 1][0]],
    y: domain([empiricalScaling, theoreticalScaling], 0.12),
  }, colors, "log₁₀ Δ", "log₁₀ Var");
  label(context, `理論傾き 2H=${format(2 * diagnostics.hurst, 2)}`, rightBottom.x + 52, rightBottom.y + 18, colors.teal);
}

function hawkesPath(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 389);
  const baseline = Math.max(settings.rate, 0.05);
  const decayRate = Math.max(settings.kappa, 0.1);
  const branchingRatio = clamp(settings.sigma, 0, 0.95);
  const excitation = branchingRatio * decayRate;
  const burnIn = 10 / decayRate;
  let time = -burnIn;
  let excitationState = 0;
  let initialExcitation = 0;
  const eventTimes: number[] = [];
  while (time < settings.horizon && eventTimes.length < 10000) {
    const upperIntensity = baseline + excitationState;
    const wait = -Math.log(Math.max(random(), 1e-12)) / upperIntensity;
    const candidate = time + wait;
    if (time < 0 && candidate >= 0) {
      initialExcitation = excitationState * Math.exp(decayRate * time);
    }
    if (candidate > settings.horizon) break;
    const candidateExcitation = excitationState * Math.exp(-decayRate * wait);
    const candidateIntensity = baseline + candidateExcitation;
    time = candidate;
    excitationState = candidateExcitation;
    if (random() <= candidateIntensity / upperIntensity) {
      excitationState += excitation;
      if (time >= 0) eventTimes.push(time);
    }
  }
  const steps = 420;
  const intensity: Point[] = Array.from({ length: steps + 1 }, (_, index) => {
    const sampleTime = (index / steps) * settings.horizon;
    const inherited = initialExcitation * Math.exp(-decayRate * sampleTime);
    const triggered = eventTimes.reduce(
      (sum, eventTime) => eventTime <= sampleTime
        ? sum + excitation * Math.exp(-decayRate * (sampleTime - eventTime))
        : sum,
      0,
    );
    return [sampleTime, baseline + inherited + triggered];
  });
  const counting: Point[] = [[0, 0]];
  eventTimes.forEach((eventTime, index) => {
    counting.push([eventTime, index], [eventTime, index + 1]);
  });
  counting.push([settings.horizon, eventTimes.length]);
  const count = eventTimes.length;
  const matchedRate = branchingRatio < 0.98
    ? baseline / (1 - branchingRatio)
    : Math.max(count / settings.horizon, baseline);
  const poissonCounting: Point[] = [[0, 0]];
  let poissonTime = 0;
  let poissonCount = 0;
  while (poissonTime < settings.horizon) {
    poissonTime += -Math.log(Math.max(random(), 1e-12)) / matchedRate;
    if (poissonTime > settings.horizon) break;
    poissonCounting.push([poissonTime, poissonCount], [poissonTime, poissonCount + 1]);
    poissonCount += 1;
  }
  poissonCounting.push([settings.horizon, poissonCount]);
  return {
    intensity,
    counting,
    poissonCounting,
    count,
    baseline,
    excitation,
    decayRate,
    matchedRate,
  };
}

function drawHawkes(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.52);
  const diagnostics = hawkesPath(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: diagnostics.poissonCounting, color: colors.muted, width: 1.7, dashed: true },
    { points: diagnostics.counting, color: colors.teal, width: 2.4 },
  ], {
    x: [0, settings.horizon],
    y: [0, Math.max(
      diagnostics.count + 1,
      diagnostics.poissonCounting[diagnostics.poissonCounting.length - 1][1] + 1,
      2,
    )],
  }, colors, "時間 t", "累積イベント");
  label(context, "Hawkes", left.x + 52, left.y + 18, colors.teal);
  label(context, "同平均Poisson", left.x + 116, left.y + 18, colors.muted);

  rounded(context, right, 16, colors.paper);
  chart(context, right, [{ points: diagnostics.intensity, color: colors.coral, width: 2.3 }], {
    x: [0, settings.horizon],
    y: [0, Math.max(...diagnostics.intensity.map((point) => point[1])) * 1.12],
  }, colors, "時間 t", "条件付き強度 λₜ");
  label(context, `分枝比 α/β=${format(diagnostics.excitation / diagnostics.decayRate, 2)}`, right.x + 52, right.y + 18, colors.coral);
}

function coupledGbm(settings: ExtendedSettings, steps: number, seed: number) {
  const random = mulberry32(seed);
  const dt = settings.horizon / steps;
  let exact = Math.max(settings.x0, 1);
  let euler = exact;
  let milstein = exact;
  const exactPath: Point[] = [[0, exact]];
  const eulerPath: Point[] = [[0, euler]];
  const milsteinPath: Point[] = [[0, milstein]];
  for (let index = 0; index < steps; index += 1) {
    const dW = Math.sqrt(dt) * normal(random);
    exact *= Math.exp((settings.mu - 0.5 * settings.sigma ** 2) * dt + settings.sigma * dW);
    euler += settings.mu * euler * dt + settings.sigma * euler * dW;
    milstein +=
      settings.mu * milstein * dt + settings.sigma * milstein * dW +
      0.5 * settings.sigma ** 2 * milstein * (dW * dW - dt);
    const time = (index + 1) * dt;
    exactPath.push([time, exact]);
    eulerPath.push([time, euler]);
    milsteinPath.push([time, milstein]);
  }
  return { exact, euler, milstein, exactPath, eulerPath, milsteinPath };
}

function milsteinDiagnostics(settings: ExtendedSettings) {
  const stepCounts = [8, 16, 32, 64, 128];
  const eulerError: Point[] = [];
  const milsteinError: Point[] = [];
  for (const steps of stepCounts) {
    let eulerTotal = 0;
    let milsteinTotal = 0;
    for (let sample = 0; sample < 48; sample += 1) {
      const result = coupledGbm(settings, steps, settings.seed + 401 + sample * 1013);
      eulerTotal += Math.abs(result.euler - result.exact);
      milsteinTotal += Math.abs(result.milstein - result.exact);
    }
    const x = Math.log10(settings.horizon / steps);
    eulerError.push([x, Math.log10(Math.max(eulerTotal / 48, 1e-6))]);
    milsteinError.push([x, Math.log10(Math.max(milsteinTotal / 48, 1e-6))]);
  }
  const selected = coupledGbm(settings, Math.max(settings.steps, 8), settings.seed + 397);
  return { eulerError, milsteinError, selected };
}

function drawMilstein(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.6);
  const diagnostics = milsteinDiagnostics(settings);
  const selected = diagnostics.selected;
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: selected.exactPath, color: colors.teal, width: 2.5 },
    { points: selected.eulerPath, color: colors.coral, width: 1.8, dashed: true },
    { points: selected.milsteinPath, color: colors.amber, width: 2 },
  ], {
    x: [0, settings.horizon],
    y: domain([selected.exactPath, selected.eulerPath, selected.milsteinPath], 0.12),
  }, colors, "時間 t");
  label(context, "厳密", left.x + 52, left.y + 18, colors.teal);
  label(context, "Euler", left.x + 102, left.y + 18, colors.coral);
  label(context, "Milstein", left.x + 158, left.y + 18, colors.amber);

  const xs = [...diagnostics.eulerError, ...diagnostics.milsteinError].map((point) => point[0]);
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: diagnostics.eulerError, color: colors.coral, width: 2.2 },
    { points: diagnostics.milsteinError, color: colors.amber, width: 2.2 },
  ], {
    x: [Math.min(...xs), Math.max(...xs)],
    y: domain([diagnostics.eulerError, diagnostics.milsteinError], 0.12),
  }, colors, "log₁₀ Δt", "log₁₀ 強誤差");
  label(context, "収束次数 1/2 vs 1", right.x + 52, right.y + 18, colors.ink);
}

function monteCarloDiagnostics(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 431);
  const maxSamples = Math.max(settings.paths * 256, 2048);
  const threshold = settings.strike;
  const exact = 1 - normalCdf(threshold);
  const method = clamp(Math.round(settings.functionChoice), 0, 2);
  const controlBeta = Math.exp(-0.5 * threshold ** 2) / Math.sqrt(2 * Math.PI);
  const checkpoints = new Set(
    [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, maxSamples]
      .filter((value) => value <= maxSamples),
  );
  let total = 0;
  let squaredTotal = 0;
  let hits = 0;
  const estimate: Point[] = [];
  const upper: Point[] = [];
  const lower: Point[] = [];
  for (let index = 1; index <= maxSamples; index += 1) {
    const z = normal(random);
    const value = method === 1
      ? 0.5 * (Number(z > threshold) + Number(-z > threshold))
      : method === 2
        ? Number(z > threshold) - controlBeta * z
        : Number(z > threshold);
    if (z > threshold) hits += 1;
    total += value;
    squaredTotal += value ** 2;
    if (checkpoints.has(index)) {
      const mean = total / index;
      const variance = index > 1
        ? Math.max((squaredTotal - index * mean ** 2) / (index - 1), 1e-9)
        : 0;
      const x = Math.log10(index);
      estimate.push([x, mean]);
      if (method === 0) {
        const zScore = 1.96;
        const proportion = hits / index;
        const denominator = 1 + zScore ** 2 / index;
        const center = (proportion + zScore ** 2 / (2 * index)) / denominator;
        const half = zScore / denominator * Math.sqrt(
          proportion * (1 - proportion) / index + zScore ** 2 / (4 * index ** 2),
        );
        upper.push([x, center + half]);
        lower.push([x, Math.max(center - half, 0)]);
      } else {
        const half = 1.96 * Math.sqrt(variance / index);
        upper.push([x, mean + half]);
        lower.push([x, mean - half]);
      }
    }
  }
  return {
    exact,
    estimate,
    upper,
    lower,
    maxSamples,
    method: ["単純", "antithetic pair", "control variate"][method],
    interval: method === 0 ? "Wilson 95%" : "漸近 95%",
  };
}

function drawMonteCarlo(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const diagnostics = monteCarloDiagnostics(settings);
  rounded(context, area, 16, colors.paper);
  const xMin = diagnostics.estimate[0][0];
  const xMax = diagnostics.estimate[diagnostics.estimate.length - 1][0];
  chart(context, area, [
    { points: [[xMin, diagnostics.exact], [xMax, diagnostics.exact]], color: colors.teal, width: 2.4 },
    { points: diagnostics.upper, color: colors.amber, width: 1.3, dashed: true },
    { points: diagnostics.lower, color: colors.amber, width: 1.3, dashed: true },
    { points: diagnostics.estimate, color: colors.coral, width: 2.4 },
  ], {
    x: [xMin, xMax],
    y: domain([diagnostics.upper, diagnostics.lower], 0.16),
  }, colors, "log₁₀ 推定単位数", "P(Z>K) 推定");
  label(context, `解析値 · K=${format(settings.strike, 1)}`, area.x + 52, area.y + 18, colors.teal);
  label(context, `${diagnostics.method} · ${diagnostics.interval}`, area.x + 166, area.y + 18, colors.coral);
}

function inferenceDiagnostics(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 449);
  const maxSteps = Math.max(settings.steps, 64);
  const dt = settings.horizon / maxSteps;
  const meanReversion = Math.max(settings.kappa, 0.02);
  const transition = Math.exp(-meanReversion * dt);
  const processVariance = settings.sigma ** 2 * (1 - transition ** 2) / (2 * meanReversion);
  const observationVariance = Math.max(settings.sigma2 ** 2, 1e-6);
  let state = settings.x0;
  const states = [state];
  const observations = [state + settings.sigma2 * normal(random)];
  for (let index = 0; index < maxSteps; index += 1) {
    state = settings.theta + transition * (state - settings.theta) +
      Math.sqrt(processVariance) * normal(random);
    states.push(state);
    observations.push(state + settings.sigma2 * normal(random));
  }

  let filteredMean = settings.x0;
  let filteredVariance = 0;
  const filtered: Point[] = [[0, filteredMean]];
  const upper: Point[] = [[0, filteredMean + 1.96 * Math.sqrt(filteredVariance)]];
  const lower: Point[] = [[0, filteredMean - 1.96 * Math.sqrt(filteredVariance)]];
  for (let index = 1; index <= maxSteps; index += 1) {
    const predictedMean = settings.theta + transition * (filteredMean - settings.theta);
    const predictedVariance = transition ** 2 * filteredVariance + processVariance;
    const gain = predictedVariance / (predictedVariance + observationVariance);
    filteredMean = predictedMean + gain * (observations[index] - predictedMean);
    filteredVariance = (1 - gain) * predictedVariance;
    const time = index * dt;
    filtered.push([time, filteredMean]);
    upper.push([time, filteredMean + 1.96 * Math.sqrt(filteredVariance)]);
    lower.push([time, filteredMean - 1.96 * Math.sqrt(filteredVariance)]);
  }

  const checkpoints = [16, 32, 64, 128, 256, 384].filter((value) => value <= maxSteps);
  if (!checkpoints.includes(maxSteps)) checkpoints.push(maxSteps);
  const kappaEstimate: Point[] = [];
  const sigmaEstimate: Point[] = [];
  checkpoints.forEach((count) => {
    const previous = observations.slice(0, count);
    const next = observations.slice(1, count + 1);
    const previousMean = previous.reduce((sum, value) => sum + value, 0) / count;
    const nextMean = next.reduce((sum, value) => sum + value, 0) / count;
    const covariance = previous.reduce(
      (sum, value, index) => sum + (value - previousMean) * (next[index] - nextMean),
      0,
    );
    const variance = previous.reduce((sum, value) => sum + (value - previousMean) ** 2, 0);
    const estimatedTransition = clamp(covariance / Math.max(variance, 1e-9), 0.001, 0.9995);
    const estimatedKappa = -Math.log(estimatedTransition) / dt;
    const intercept = nextMean - estimatedTransition * previousMean;
    const residuals = next.map(
      (value, index) => value - intercept - estimatedTransition * previous[index],
    );
    const residualVariance = residuals.reduce((sum, value) => sum + value ** 2, 0) /
      Math.max(count - 2, 1);
    const estimatedSigma = Math.sqrt(
      Math.max(residualVariance * 2 * estimatedKappa / (1 - estimatedTransition ** 2), 0),
    );
    kappaEstimate.push([count, estimatedKappa]);
    sigmaEstimate.push([count, estimatedSigma]);
  });
  const truePath: Point[] = states.map((value, index) => [index * dt, value]);
  const observedPath: Point[] = observations.map((value, index) => [index * dt, value]);
  const rmse = Math.sqrt(filtered.reduce(
    (sum, point, index) => sum + (point[1] - states[index]) ** 2,
    0,
  ) / filtered.length);
  return {
    truePath,
    observedPath,
    filtered,
    upper,
    lower,
    kappaEstimate,
    sigmaEstimate,
    rmse,
  };
}

function drawParameterInference(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.64);
  const diagnostics = inferenceDiagnostics(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: diagnostics.upper, color: colors.amber, width: 1.1, dashed: true },
    { points: diagnostics.lower, color: colors.amber, width: 1.1, dashed: true },
    { points: diagnostics.observedPath, color: colors.muted, width: 1, alpha: 0.35 },
    { points: diagnostics.truePath, color: colors.teal, width: 2.1 },
    { points: diagnostics.filtered, color: colors.coral, width: 2.4 },
  ], {
    x: [0, settings.horizon],
    y: domain([
      diagnostics.truePath,
      diagnostics.observedPath,
      diagnostics.upper,
      diagnostics.lower,
    ], 0.1),
  }, colors, "時間 t", "潜在状態 / 観測");
  label(context, "真値", left.x + 52, left.y + 18, colors.teal);
  label(context, "Kalman", left.x + 92, left.y + 18, colors.coral);
  label(context, "95%帯", left.x + 158, left.y + 18, colors.amber);

  const gap = 10;
  const top = { ...right, h: (right.h - gap) / 2 };
  const bottom = { x: right.x, y: right.y + top.h + gap, w: right.w, h: top.h };
  const maxCount = diagnostics.kappaEstimate[diagnostics.kappaEstimate.length - 1][0];
  rounded(context, top, 14, colors.paper);
  chart(context, top, [
    { points: [[16, settings.kappa], [maxCount, settings.kappa]], color: colors.teal, width: 1.8, dashed: true },
    { points: diagnostics.kappaEstimate, color: colors.coral, width: 2.2 },
  ], {
    x: [16, maxCount],
    y: domain([diagnostics.kappaEstimate, [[16, settings.kappa], [maxCount, settings.kappa]]], 0.15),
  }, colors, "標本数", "κ 推定");
  label(context, "観測ノイズ無視の推定", top.x + 52, top.y + 18, colors.coral);

  rounded(context, bottom, 14, colors.paper);
  chart(context, bottom, [
    { points: [[16, settings.sigma], [maxCount, settings.sigma]], color: colors.teal, width: 1.8, dashed: true },
    { points: diagnostics.sigmaEstimate, color: colors.amber, width: 2.2 },
  ], {
    x: [16, maxCount],
    y: domain([diagnostics.sigmaEstimate, [[16, settings.sigma], [maxCount, settings.sigma]]], 0.15),
  }, colors, "標本数", "σ 推定");
  label(context, "真値とのずれが診断", bottom.x + 52, bottom.y + 18, colors.amber);
}

function predictabilityDiagnostics(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 467);
  const steps = 180;
  const dt = settings.horizon / steps;
  const logDrift = settings.mu - 0.5 * settings.sigma ** 2;
  const paths: Point[][] = [];
  for (let pathIndex = 0; pathIndex < 18; pathIndex += 1) {
    let value = 0;
    const points: Point[] = [[0, 0]];
    for (let index = 0; index < steps; index += 1) {
      value += logDrift * dt + settings.sigma * Math.sqrt(dt) * normal(random);
      points.push([(index + 1) * dt, value]);
    }
    paths.push(points);
  }
  const signalNoise: Point[] = Array.from({ length: 100 }, (_, index) => {
    const time = Math.max(((index + 1) / 100) * settings.horizon, 1e-4);
    return [time, Math.abs(logDrift) * Math.sqrt(time) / settings.sigma];
  });
  return { paths, signalNoise, logDrift };
}

function drawPredictability(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.66);
  const diagnostics = predictabilityDiagnostics(settings);
  const mean: Point[] = [[0, 0], [settings.horizon, diagnostics.logDrift * settings.horizon]];
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    ...diagnostics.paths.map((points, index) => ({
      points,
      color: index === 0 ? colors.teal : colors.violet,
      width: index === 0 ? 2.2 : 1,
      alpha: index === 0 ? 1 : 0.2,
    })),
    { points: mean, color: colors.coral, width: 2.3 },
  ], { x: [0, settings.horizon], y: domain([...diagnostics.paths, mean], 0.1) }, colors, "予測期間", "対数収益 log(Sₜ/S₀)");
  label(context, "実現経路", left.x + 52, left.y + 18, colors.teal);
  label(context, "条件付き平均", left.x + 128, left.y + 18, colors.coral);

  rounded(context, right, 16, colors.paper);
  chart(context, right, [{ points: diagnostics.signalNoise, color: colors.amber, width: 2.5 }], {
    x: [0, settings.horizon],
    y: [0, Math.max(...diagnostics.signalNoise.map((point) => point[1]), 0.1) * 1.15],
  }, colors, "予測期間 T", "|μ−σ²/2|√T/σ");
  label(context, "予測信号 / ノイズ", right.x + 52, right.y + 18, colors.amber);
}

function martingaleDiagnostics(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 479);
  const steps = 160;
  const count = Math.max(settings.paths, 48);
  const dt = settings.horizon / steps;
  const shownQ: Point[][] = [];
  const sumsQ = Array.from({ length: steps + 1 }, () => 0);
  const sumsP = Array.from({ length: steps + 1 }, () => 0);
  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let priceQ = Math.max(settings.x0, 1);
    let priceP = priceQ;
    const points: Point[] = [[0, priceQ]];
    sumsQ[0] += priceQ;
    sumsP[0] += priceP;
    for (let index = 0; index < steps; index += 1) {
      const shock = normal(random);
      priceQ *= Math.exp(
        (settings.rate - 0.5 * settings.sigma ** 2) * dt +
          settings.sigma * Math.sqrt(dt) * shock,
      );
      priceP *= Math.exp(
        (settings.mu - 0.5 * settings.sigma ** 2) * dt +
          settings.sigma * Math.sqrt(dt) * shock,
      );
      const time = (index + 1) * dt;
      const discount = Math.exp(-settings.rate * time);
      const discountedQ = priceQ * discount;
      sumsQ[index + 1] += discountedQ;
      sumsP[index + 1] += priceP * discount;
      if (pathIndex < 12) points.push([time, discountedQ]);
    }
    if (pathIndex < 12) shownQ.push(points);
  }
  const meanQ: Point[] = sumsQ.map(
    (sum, index) => [(index / steps) * settings.horizon, sum / count],
  );
  const meanP: Point[] = sumsP.map(
    (sum, index) => [(index / steps) * settings.horizon, sum / count],
  );
  const spot = Math.max(settings.x0, 1);
  const growth = Math.exp(settings.rate * settings.horizon);
  const up = growth * Math.exp(settings.sigma * Math.sqrt(settings.horizon));
  const down = growth * Math.exp(-settings.sigma * Math.sqrt(settings.horizon));
  const stockUp = spot * up;
  const stockDown = spot * down;
  const payoffUp = Math.max(stockUp - settings.strike, 0);
  const payoffDown = Math.max(stockDown - settings.strike, 0);
  const delta = (payoffUp - payoffDown) / (stockUp - stockDown);
  const terminalCash = payoffDown - delta * stockDown;
  const initialCash = terminalCash * Math.exp(-settings.rate * settings.horizon);
  const replicationPrice = delta * spot + initialCash;
  return {
    shownQ,
    meanQ,
    meanP,
    terminalMeanQ: meanQ[meanQ.length - 1][1],
    terminalMeanP: meanP[meanP.length - 1][1],
    replication: {
      stockDown,
      stockUp,
      payoffDown,
      payoffUp,
      delta,
      initialCash,
      replicationPrice,
    },
  };
}

function drawMartingale(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const diagnostics = martingaleDiagnostics(settings);
  const { left, right } = panels(area, 0.68);
  rounded(context, left, 16, colors.paper);
  const reference: Point[] = [[0, settings.x0], [settings.horizon, settings.x0]];
  chart(context, left, [
    ...diagnostics.shownQ.map((points) => ({ points, color: colors.violet, width: 1, alpha: 0.2 })),
    { points: reference, color: colors.muted, width: 1.5, dashed: true },
    { points: diagnostics.meanP, color: colors.amber, width: 2.2 },
    { points: diagnostics.meanQ, color: colors.teal, width: 2.7 },
  ], {
    x: [0, settings.horizon],
    y: domain([...diagnostics.shownQ, diagnostics.meanP, diagnostics.meanQ], 0.1),
  }, colors, "時間 t", "割引価格 e⁻ʳᵗSₜ");
  label(context, "P平均", left.x + 52, left.y + 18, colors.amber);
  label(context, "Q平均", left.x + 108, left.y + 18, colors.teal);

  const replication = diagnostics.replication;
  const claim: Point[] = [
    [replication.stockDown, replication.payoffDown],
    [replication.stockUp, replication.payoffUp],
  ];
  const portfolio: Point[] = [
    [replication.stockDown, replication.delta * replication.stockDown +
      replication.initialCash * Math.exp(settings.rate * settings.horizon)],
    [replication.stockUp, replication.delta * replication.stockUp +
      replication.initialCash * Math.exp(settings.rate * settings.horizon)],
  ];
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: claim, color: colors.coral, width: 3.4 },
    { points: portfolio, color: colors.teal, width: 1.8, dashed: true },
  ], {
    x: [replication.stockDown * 0.96, replication.stockUp * 1.04],
    y: [Math.min(0, replication.payoffDown), Math.max(replication.payoffUp, 1) * 1.15],
  }, colors, "満期株価", "請求権 / 複製価値");
  label(context, `Δ=${format(replication.delta, 3)}`, right.x + 52, right.y + 18, colors.teal);
  label(context, `V₀=${format(replication.replicationPrice, 2)}`, right.x + right.w - 14, right.y + 18, colors.coral, "right");
}

function callValueDelta(spot: number, strike: number, rate: number, sigma: number, tau: number) {
  if (tau <= 1e-9) return { value: Math.max(spot - strike, 0), delta: spot > strike ? 1 : 0 };
  const vol = sigma * Math.sqrt(tau);
  const d1 = (Math.log(spot / strike) + (rate + 0.5 * sigma ** 2) * tau) / vol;
  const d2 = d1 - vol;
  return {
    value: spot * normalCdf(d1) - strike * Math.exp(-rate * tau) * normalCdf(d2),
    delta: normalCdf(d1),
  };
}

function hedgeOnce(settings: ExtendedSettings, steps: number, seed: number, keepPath = false) {
  const random = mulberry32(seed);
  const dt = settings.horizon / steps;
  let spot = Math.max(settings.x0, 1);
  const initial = callValueDelta(spot, settings.strike, settings.rate, settings.sigma, settings.horizon);
  let delta = initial.delta;
  let cash = initial.value - delta * spot;
  const optionPath: Point[] = [[0, initial.value]];
  const hedgePath: Point[] = [[0, initial.value]];
  for (let index = 0; index < steps; index += 1) {
    cash *= Math.exp(settings.rate * dt);
    spot *= Math.exp(
      (settings.rate - 0.5 * settings.sigma ** 2) * dt + settings.sigma * Math.sqrt(dt) * normal(random),
    );
    const time = (index + 1) * dt;
    const remaining = settings.horizon - time;
    const option = callValueDelta(spot, settings.strike, settings.rate, settings.sigma, remaining);
    const portfolio = delta * spot + cash;
    if (keepPath) {
      optionPath.push([time, option.value]);
      hedgePath.push([time, portfolio]);
    }
    if (index < steps - 1) {
      cash = portfolio - option.delta * spot;
      delta = option.delta;
    }
  }
  const payoff = Math.max(spot - settings.strike, 0);
  return { error: delta * spot + cash - payoff, optionPath, hedgePath };
}

function deltaHedgeDiagnostics(settings: ExtendedSettings) {
  const selectedSteps = Math.max(Math.min(settings.steps, 384), 8);
  const selected = hedgeOnce(settings, selectedSteps, settings.seed + 503, true);
  const stepCounts = [4, 8, 16, 32, 64, 128];
  const errorSd: Point[] = stepCounts.map((steps) => {
    const errors = Array.from({ length: 160 }, (_, sample) =>
      hedgeOnce(settings, steps, settings.seed + 509 + sample * 977).error
    );
    const mean = errors.reduce((sum, value) => sum + value, 0) / errors.length;
    const variance = errors.reduce((sum, value) => sum + (value - mean) ** 2, 0) / errors.length;
    return [steps, Math.sqrt(variance)];
  });
  return { selected, errorSd };
}

function drawDeltaHedging(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.6);
  const diagnostics = deltaHedgeDiagnostics(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: diagnostics.selected.optionPath, color: colors.teal, width: 2.5 },
    { points: diagnostics.selected.hedgePath, color: colors.coral, width: 2.1, dashed: true },
  ], {
    x: [0, settings.horizon],
    y: domain([diagnostics.selected.optionPath, diagnostics.selected.hedgePath], 0.14),
  }, colors, "時間 t", "価値");
  label(context, "オプション", left.x + 52, left.y + 18, colors.teal);
  label(context, "離散ヘッジ", left.x + 132, left.y + 18, colors.coral);

  rounded(context, right, 16, colors.paper);
  chart(context, right, [{ points: diagnostics.errorSd, color: colors.amber, width: 2.5 }], {
    x: [4, 128],
    y: [0, Math.max(...diagnostics.errorSd.map((point) => point[1])) * 1.15],
  }, colors, "リバランス回数", "ヘッジ誤差 SD");
  label(context, "頻度を上げると低下", right.x + 52, right.y + 18, colors.amber);
}

function volatilityDiagnostics(settings: ExtendedSettings) {
  const random = mulberry32(settings.seed + 541);
  const steps = 180;
  const dt = settings.horizon / steps;
  const s0 = Math.max(settings.x0, 1);
  let constant = s0;
  let local = s0;
  let stochastic = s0;
  let variance = settings.sigma ** 2;
  const constantPath: Point[] = [[0, constant]];
  const localPath: Point[] = [[0, local]];
  const stochasticPath: Point[] = [[0, stochastic]];
  const volPath: Point[] = [[0, settings.sigma]];
  for (let index = 0; index < steps; index += 1) {
    const z1 = normal(random);
    const z2 = settings.rho * z1 + Math.sqrt(Math.max(1 - settings.rho ** 2, 0)) * normal(random);
    const localVol = clamp(settings.sigma * (1 + settings.sigma2 * (1 - local / s0)), 0.05, 1.5);
    const stochasticVol = clamp(Math.sqrt(Math.max(variance, 0)), 0.03, 1.5);
    constant *= Math.exp(-0.5 * settings.sigma ** 2 * dt + settings.sigma * Math.sqrt(dt) * z1);
    local *= Math.exp(-0.5 * localVol ** 2 * dt + localVol * Math.sqrt(dt) * z1);
    stochastic *= Math.exp(-0.5 * stochasticVol ** 2 * dt + stochasticVol * Math.sqrt(dt) * z1);
    variance = Math.max(
      0,
      variance + settings.kappa * (settings.sigma ** 2 - variance) * dt +
        settings.sigma2 * Math.sqrt(Math.max(variance, 0)) * Math.sqrt(dt) * z2,
    );
    const time = (index + 1) * dt;
    constantPath.push([time, constant]);
    localPath.push([time, local]);
    stochasticPath.push([time, stochastic]);
    volPath.push([time, Math.sqrt(variance)]);
  }
  return { constantPath, localPath, stochasticPath, volPath };
}

function drawVolatilityModels(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.7);
  const diagnostics = volatilityDiagnostics(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: diagnostics.constantPath, color: colors.muted, width: 1.7, dashed: true },
    { points: diagnostics.localPath, color: colors.teal, width: 2.2 },
    { points: diagnostics.stochasticPath, color: colors.coral, width: 2.2 },
  ], { x: [0, settings.horizon], y: domain([diagnostics.constantPath, diagnostics.localPath, diagnostics.stochasticPath], 0.12) }, colors, "時間 t", "割引価格");
  label(context, "定数", left.x + 52, left.y + 18, colors.muted);
  label(context, "Local", left.x + 98, left.y + 18, colors.teal);
  label(context, "Stochastic", left.x + 152, left.y + 18, colors.coral);

  rounded(context, right, 16, colors.paper);
  chart(context, right, [{ points: diagnostics.volPath, color: colors.coral, width: 2.4 }], {
    x: [0, settings.horizon],
    y: [0, Math.max(...diagnostics.volPath.map((point) => point[1])) * 1.15],
  }, colors, "時間 t", "瞬間ボラ");
  label(context, "ボラティリティも状態", right.x + 52, right.y + 18, colors.coral);
}

function drawShortRate(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.62);
  const random = mulberry32(settings.seed + 563);
  const steps = 220;
  const dt = settings.horizon / steps;
  let vasicek = settings.x0;
  let cir = Math.max(settings.x0, 0);
  const vasicekPath: Point[] = [[0, vasicek]];
  const cirPath: Point[] = [[0, cir]];
  for (let index = 0; index < steps; index += 1) {
    const shock = normal(random);
    vasicek += settings.kappa * (settings.theta - vasicek) * dt + settings.sigma * Math.sqrt(dt) * shock;
    cir = Math.max(0, cir + settings.kappa * (settings.theta - cir) * dt + settings.sigma * Math.sqrt(cir) * Math.sqrt(dt) * shock);
    const time = (index + 1) * dt;
    vasicekPath.push([time, vasicek]);
    cirPath.push([time, cir]);
  }
  rounded(context, left, 16, colors.paper);
  chart(context, left, [
    { points: vasicekPath, color: colors.coral, width: 2.2 },
    { points: cirPath, color: colors.teal, width: 2.3 },
  ], { x: [0, settings.horizon], y: domain([vasicekPath, cirPath], 0.14) }, colors, "時間 t", "短期金利 rₜ");
  label(context, "Vasicek", left.x + 52, left.y + 18, colors.coral);
  label(context, "CIR", left.x + 124, left.y + 18, colors.teal);

  const zeroYield: Point[] = Array.from({ length: 101 }, (_, index) => {
    const maturity = 0.05 + (index / 100) * 9.95;
    const bondLoading = (1 - Math.exp(-settings.kappa * maturity)) / settings.kappa;
    const logA = (settings.theta - settings.sigma ** 2 / (2 * settings.kappa ** 2)) *
      (bondLoading - maturity) - settings.sigma ** 2 * bondLoading ** 2 / (4 * settings.kappa);
    const logBondPrice = logA - bondLoading * settings.x0;
    return [maturity, -logBondPrice / maturity];
  });
  rounded(context, right, 16, colors.paper);
  chart(context, right, [{ points: zeroYield, color: colors.amber, width: 2.5 }], {
    x: [0.05, 10],
    y: domain([zeroYield], 0.16),
  }, colors, "満期 T", "Vasicek ゼロ利回り");
  label(context, "Q の解析的な債券価格から算出", right.x + 52, right.y + 18, colors.amber);
}

function drawForwardCurve(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.68);
  const random = mulberry32(settings.seed + 587);
  const maturities = Array.from({ length: 121 }, (_, index) => 0.05 + (index / 120) * 9.95);
  const curves: Point[][] = [];
  let factor = 0;
  for (let snapshot = 0; snapshot < 4; snapshot += 1) {
    factor = 0.65 * factor + settings.sigma * 0.35 * normal(random);
    curves.push(maturities.map((maturity) => [
      maturity,
      settings.rate + 0.02 * (1 - Math.exp(-0.7 * maturity)) + factor * Math.exp(-settings.kappa * maturity),
    ]));
  }
  rounded(context, left, 16, colors.paper);
  const palette = [colors.muted, colors.violet, colors.amber, colors.teal];
  chart(context, left, curves.map((points, index) => ({
    points,
    color: palette[index],
    width: index === curves.length - 1 ? 2.7 : 1.8,
  })), { x: [0.05, 10], y: domain(curves, 0.16) }, colors, "満期 T", "瞬間フォワード f(t,T)");
  curves.forEach((_curve, index) => label(context, `shock ${index}`, left.x + 52 + index * 58, left.y + 18, palette[index]));

  const hjmDrift: Point[] = maturities.map((maturity) => {
    const loading = settings.sigma * Math.exp(-settings.kappa * maturity);
    const integratedLoading = settings.sigma * (1 - Math.exp(-settings.kappa * maturity)) /
      settings.kappa;
    return [maturity, loading * integratedLoading];
  });
  const omittedDrift: Point[] = [[0.05, 0], [10, 0]];
  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: hjmDrift, color: colors.coral, width: 2.4 },
    { points: omittedDrift, color: colors.muted, width: 1.6, dashed: true },
  ], { x: [0.05, 10], y: domain([hjmDrift, omittedDrift], 0.18) }, colors, "満期 T", "Qドリフト α(0,T)");
  label(context, "HJM制約", right.x + 52, right.y + 18, colors.coral);
  label(context, "任意に0は不可", right.x + 116, right.y + 18, colors.muted);
}

function creditDiagnostics(settings: ExtendedSettings) {
  const intensity = Math.max(settings.kappa, 0.01);
  const recovery = clamp(settings.rho, 0, 0.9);
  const survival: Point[] = Array.from({ length: 121 }, (_, index) => {
    const time = (index / 120) * settings.horizon;
    return [time, Math.exp(-intensity * time)];
  });
  const random = mulberry32(settings.seed + 601);
  const defaults = Array.from({ length: 1200 }, () => -Math.log(Math.max(random(), 1e-12)) / intensity)
    .filter((time) => time <= settings.horizon);
  const bins = 18;
  const counts = Array.from({ length: bins }, () => 0);
  defaults.forEach((time) => counts[clamp(Math.floor((time / settings.horizon) * bins), 0, bins - 1)] += 1);
  const density: Point[] = counts.flatMap((count, index) => {
    const x0 = (index / bins) * settings.horizon;
    const x1 = ((index + 1) / bins) * settings.horizon;
    const value = count / 1200 / (settings.horizon / bins);
    return [[x0, value], [x1, value]] as Point[];
  });
  const theoreticalDensity: Point[] = survival.map(([time, probability]) => [
    time,
    intensity * probability,
  ]);
  return {
    intensity,
    recovery,
    survival,
    density,
    theoreticalDensity,
    defaultRate: defaults.length / 1200,
    spreadApproximation: (1 - recovery) * intensity,
  };
}

function drawCreditDefault(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.5);
  const diagnostics = creditDiagnostics(settings);
  rounded(context, left, 16, colors.paper);
  chart(context, left, [{ points: diagnostics.survival, color: colors.teal, width: 2.5 }], {
    x: [0, settings.horizon], y: [0, 1.05],
  }, colors, "時間 t", "生存確率");
  label(context, `強度 λ=${format(diagnostics.intensity, 2)}`, left.x + 52, left.y + 18, colors.teal);

  rounded(context, right, 16, colors.paper);
  chart(context, right, [
    { points: diagnostics.density, color: colors.coral, width: 2.1 },
    { points: diagnostics.theoreticalDensity, color: colors.teal, width: 1.8, dashed: true },
  ], {
    x: [0, settings.horizon],
    y: [0, Math.max(
      ...diagnostics.density.map((point) => point[1]),
      ...diagnostics.theoreticalDensity.map((point) => point[1]),
      0.1,
    ) * 1.15],
  }, colors, "デフォルト時刻 τ", "全標本あたり密度");
  label(context, "未デフォルトは右打切り", right.x + 52, right.y + 18, colors.coral);
  label(
    context,
    `R=${format(diagnostics.recovery, 2)} · spread≈${format(diagnostics.spreadApproximation, 3)}`,
    right.x + right.w - 14,
    right.y + 18,
    colors.teal,
    "right",
  );
}

export function drawExtendedLab(
  context: CanvasRenderingContext2D,
  area: Rect,
  lab: LabKind,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  switch (lab) {
    case "brownian-default":
      drawBrownianDefault(context, area, settings, colors);
      return true;
    case "poisson-jumps":
      drawPoissonJumps(context, area, settings, colors);
      return true;
    case "levy-tails":
      drawLevyTails(context, area, settings, colors);
      return true;
    case "colored-noise":
      drawColoredNoise(context, area, settings, colors);
      return true;
    case "fractional-brownian":
      drawFractionalBrownian(context, area, settings, colors);
      return true;
    case "hawkes":
      drawHawkes(context, area, settings, colors);
      return true;
    case "milstein":
      drawMilstein(context, area, settings, colors);
      return true;
    case "monte-carlo":
      drawMonteCarlo(context, area, settings, colors);
      return true;
    case "parameter-inference":
      drawParameterInference(context, area, settings, colors);
      return true;
    case "predictability":
      drawPredictability(context, area, settings, colors);
      return true;
    case "martingale":
      drawMartingale(context, area, settings, colors);
      return true;
    case "delta-hedging":
      drawDeltaHedging(context, area, settings, colors);
      return true;
    case "volatility-models":
      drawVolatilityModels(context, area, settings, colors);
      return true;
    case "short-rate":
      drawShortRate(context, area, settings, colors);
      return true;
    case "forward-curve":
      drawForwardCurve(context, area, settings, colors);
      return true;
    case "credit-default":
      drawCreditDefault(context, area, settings, colors);
      return true;
    default:
      return drawApplicationLab(context, area, lab, settings, colors);
  }
}

export function extendedMetrics(
  lab: LabKind,
  settings: ExtendedSettings,
): Array<[string, string]> | null {
  switch (lab) {
    case "brownian-default":
      return [
        ["集約数 n", `${clamp(Math.round(settings.steps), 16, 384)}`],
        ["各ショック平均", "0"],
        ["共通終点分散", format(settings.sigma ** 2 * settings.horizon, 3)],
      ];
    case "poisson-jumps":
      return [
        ["E[Nₜ]", format(settings.kappa * settings.horizon, 2)],
        ["Var(Nₜ)", format(settings.kappa * settings.horizon, 2)],
        ["P(Nₜ=0)", format(Math.exp(-settings.kappa * settings.horizon), 3)],
      ];
    case "levy-tails":
      return [
        ["stable 指数 α", "1.50"],
        ["有限活動 E[Nₜ]", format(settings.kappa * settings.horizon, 2)],
        ["α-stable 分散", "発散"],
      ];
    case "colored-noise":
      return [
        ["相関時間", format(1 / settings.kappa, 2)],
        ["lag 1 自己相関", format(Math.exp(-settings.kappa * settings.horizon / 260), 3)],
        ["OU 定常分散 Dκ", format(settings.sigma * settings.kappa, 3)],
      ];
    case "fractional-brownian": {
      const hurst = clamp(settings.rho, 0.1, 0.9);
      return [
        ["Hurst H", format(hurst, 2)],
        ["分散指数 2H", format(2 * hurst, 2)],
        ["増分 lag1 相関", format(2 ** (2 * hurst - 1) - 1, 3)],
      ];
    }
    case "hawkes": {
      const diagnostics = hawkesPath(settings);
      const ratio = diagnostics.excitation / diagnostics.decayRate;
      return [
        ["分枝比 α/β", format(ratio, 2)],
        ["定常条件", ratio < 1 ? "α/β < 1" : "不安定域"],
        ["定常平均強度", ratio < 1 ? format(diagnostics.matchedRate, 2) : "未定義"],
      ];
    }
    case "milstein": {
      const selected = milsteinDiagnostics(settings).selected;
      return [
        ["Euler 終点誤差", format(Math.abs(selected.euler - selected.exact), 3)],
        ["Milstein 終点誤差", format(Math.abs(selected.milstein - selected.exact), 3)],
        ["理論強収束次数", "1/2 vs 1"],
      ];
    }
    case "monte-carlo": {
      const diagnostics = monteCarloDiagnostics(settings);
      const estimate = diagnostics.estimate[diagnostics.estimate.length - 1][1];
      const upper = diagnostics.upper[diagnostics.upper.length - 1][1];
      const lower = diagnostics.lower[diagnostics.lower.length - 1][1];
      return [
        ["解析確率", format(diagnostics.exact, 4)],
        [`${diagnostics.method}推定`, format(estimate, 4)],
        [`${diagnostics.interval} 半幅`, format((upper - lower) / 2, 4)],
      ];
    }
    case "parameter-inference": {
      const diagnostics = inferenceDiagnostics(settings);
      return [
        ["真の κ", format(settings.kappa, 3)],
        ["単純推定 κ", format(diagnostics.kappaEstimate[diagnostics.kappaEstimate.length - 1][1], 3)],
        ["filter RMSE", format(diagnostics.rmse, 3)],
      ];
    }
    case "predictability": {
      const logDrift = settings.mu - 0.5 * settings.sigma ** 2;
      const signalNoise = Math.abs(logDrift) * Math.sqrt(settings.horizon) / settings.sigma;
      return [
        ["期待対数収益", format(logDrift * settings.horizon, 3)],
        ["信号 / ノイズ", format(signalNoise, 3)],
        ["P(Sₜ > S₀)", format(normalCdf(logDrift * Math.sqrt(settings.horizon) / settings.sigma), 3)],
      ];
    }
    case "martingale": {
      const diagnostics = martingaleDiagnostics(settings);
      return [
        ["Q平均誤差", format(diagnostics.terminalMeanQ - settings.x0, 2)],
        ["P割引平均", format(diagnostics.terminalMeanP, 2)],
        ["一期間複製価格", format(diagnostics.replication.replicationPrice, 2)],
      ];
    }
    case "delta-hedging": {
      const diagnostics = deltaHedgeDiagnostics(settings);
      return [
        ["選択経路の誤差", format(diagnostics.selected.error, 3)],
        ["最小頻度 SD", format(diagnostics.errorSd[0][1], 3)],
        ["最大頻度 SD", format(diagnostics.errorSd[diagnostics.errorSd.length - 1][1], 3)],
      ];
    }
    case "volatility-models": {
      const diagnostics = volatilityDiagnostics(settings);
      const currentVol = diagnostics.volPath[diagnostics.volPath.length - 1][1];
      return [
        ["基準ボラ", format(settings.sigma, 3)],
        ["終点確率ボラ", format(currentVol, 3)],
        ["価格・分散shock相関", format(settings.rho, 2)],
      ];
    }
    case "short-rate":
      return [
        ["長期平均 θ", format(settings.theta, 3)],
        ["平均回帰半減期", format(Math.log(2) / settings.kappa, 2)],
        ["CIR Feller 比", format(2 * settings.kappa * settings.theta / settings.sigma ** 2, 2)],
      ];
    case "forward-curve":
      return [
        ["短期水準", format(settings.rate, 3)],
        ["因子減衰 κ", format(settings.kappa, 2)],
        ["曲線ショック σ", format(settings.sigma, 3)],
      ];
    case "credit-default": {
      const diagnostics = creditDiagnostics(settings);
      return [
        ["強度 λ", format(diagnostics.intensity, 3)],
        ["満期生存確率", format(Math.exp(-diagnostics.intensity * settings.horizon), 3)],
        ["近似spread (1−R)λ", format(diagnostics.spreadApproximation, 3)],
      ];
    }
    default:
      return applicationMetrics(lab, settings);
  }
}
