import type { LabKind } from "../content/chapters";
import type { ExtendedColors, ExtendedSettings } from "./extended-labs";

type Point = [number, number];
type Rect = { x: number; y: number; w: number; h: number };
type Series = {
  points: Point[];
  color: string;
  width?: number;
  alpha?: number;
  dashed?: boolean;
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

function poisson(random: () => number, mean: number) {
  if (mean <= 0) return 0;
  if (mean > 32) return Math.max(0, Math.round(mean + Math.sqrt(mean) * normal(random)));
  const threshold = Math.exp(-mean);
  let product = 1;
  let count = 0;
  do {
    count += 1;
    product *= random();
  } while (product > threshold);
  return count - 1;
}

function binomial(random: () => number, trials: number, probability: number) {
  const n = Math.max(0, Math.round(trials));
  const p = clamp(probability, 0, 1);
  if (n === 0 || p === 0) return 0;
  if (p === 1) return n;
  if (n <= 48) {
    let count = 0;
    for (let index = 0; index < n; index += 1) if (random() < p) count += 1;
    return count;
  }
  const mean = n * p;
  const sd = Math.sqrt(n * p * (1 - p));
  return clamp(Math.round(mean + sd * normal(random)), 0, n);
}

function format(value: number, digits = 2) {
  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function percent(value: number, digits = 0) {
  return `${format(100 * value, digits)}%`;
}

function rounded(context: CanvasRenderingContext2D, rect: Rect, color: string) {
  context.beginPath();
  context.roundRect(rect.x, rect.y, rect.w, rect.h, 16);
  context.fillStyle = color;
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

function panels(area: Rect, leftRatio = 0.58) {
  const gap = 14;
  const left = { x: area.x, y: area.y, w: area.w * leftRatio - gap / 2, h: area.h };
  const right = { x: left.x + left.w + gap, y: area.y, w: area.w - left.w - gap, h: area.h };
  return { left, right };
}

function splitVertical(area: Rect, topRatio = 0.5) {
  const gap = 12;
  const top = { x: area.x, y: area.y, w: area.w, h: area.h * topRatio - gap / 2 };
  const bottom = { x: area.x, y: top.y + top.h + gap, w: area.w, h: area.h - top.h - gap };
  return { top, bottom };
}

function yDomain(series: Point[][], padding = 0.12): [number, number] {
  const values = series.flatMap((points) => points.map((point) => point[1])).filter(Number.isFinite);
  if (values.length === 0) return [-1, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = Math.max(high - low, Math.abs(high) * 0.08, 0.1);
  return [low - padding * span, high + padding * span];
}

function chart(
  context: CanvasRenderingContext2D,
  rect: Rect,
  series: Series[],
  bounds: { x: [number, number]; y: [number, number] },
  colors: ExtendedColors,
  xLabel = "",
  yLabel = "",
) {
  const padding = { left: 43, right: 12, top: 25, bottom: 31 };
  const plot = {
    x: rect.x + padding.left,
    y: rect.y + padding.top,
    w: Math.max(rect.w - padding.left - padding.right, 20),
    h: Math.max(rect.h - padding.top - padding.bottom, 20),
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

function histogram(
  context: CanvasRenderingContext2D,
  rect: Rect,
  values: number[],
  colors: ExtendedColors,
  color: string,
  options: {
    bounds?: [number, number];
    bins?: number;
    xLabel?: string;
    marker?: number;
    curve?: Point[];
  } = {},
) {
  const finite = values.filter(Number.isFinite);
  const observedLow = finite.length > 0 ? Math.min(...finite) : -1;
  const observedHigh = finite.length > 0 ? Math.max(...finite) : 1;
  const observedSpan = Math.max(observedHigh - observedLow, 1);
  const bounds = options.bounds ?? [observedLow - 0.06 * observedSpan, observedHigh + 0.06 * observedSpan];
  const bins = options.bins ?? 18;
  const width = Math.max((bounds[1] - bounds[0]) / bins, 1e-9);
  const counts = Array.from({ length: bins }, () => 0);
  finite.forEach((value) => {
    const index = clamp(Math.floor((value - bounds[0]) / width), 0, bins - 1);
    counts[index] += 1;
  });
  const densities = counts.map((count) => count / Math.max(finite.length * width, 1));
  const curveHigh = options.curve ? Math.max(...options.curve.map((point) => point[1]), 0) : 0;
  const yHigh = Math.max(...densities, curveHigh, 0.1) * 1.15;
  const frame = chart(context, rect, [], { x: bounds, y: [0, yHigh] }, colors, options.xLabel ?? "");
  context.save();
  context.beginPath();
  context.rect(frame.plot.x, frame.plot.y, frame.plot.w, frame.plot.h);
  context.clip();
  densities.forEach((density, index) => {
    const x0 = frame.mapX(bounds[0] + index * width);
    const x1 = frame.mapX(bounds[0] + (index + 1) * width);
    const y = frame.mapY(density);
    context.fillStyle = color;
    context.globalAlpha = 0.58;
    context.fillRect(x0 + 1, y, Math.max(x1 - x0 - 2, 1), frame.mapY(0) - y);
  });
  if (options.curve && options.curve.length > 0) {
    context.beginPath();
    options.curve.forEach(([x, y], index) => {
      if (index === 0) context.moveTo(frame.mapX(x), frame.mapY(y));
      else context.lineTo(frame.mapX(x), frame.mapY(y));
    });
    context.strokeStyle = colors.teal;
    context.lineWidth = 2.1;
    context.globalAlpha = 1;
    context.stroke();
  }
  if (options.marker !== undefined) {
    const x = frame.mapX(options.marker);
    context.beginPath();
    context.moveTo(x, frame.plot.y);
    context.lineTo(x, frame.plot.y + frame.plot.h);
    context.strokeStyle = colors.amber;
    context.lineWidth = 1.7;
    context.setLineDash([5, 4]);
    context.stroke();
  }
  context.restore();
  context.globalAlpha = 1;
  context.setLineDash([]);
}

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
}

function variance(values: number[]) {
  const center = mean(values);
  return values.reduce((sum, value) => sum + (value - center) ** 2, 0) / Math.max(values.length - 1, 1);
}

function correlation(left: number[], right: number[]) {
  const size = Math.min(left.length, right.length);
  if (size < 2) return 0;
  const x = left.slice(0, size);
  const y = right.slice(0, size);
  const xMean = mean(x);
  const yMean = mean(y);
  let covariance = 0;
  let xVariance = 0;
  let yVariance = 0;
  for (let index = 0; index < size; index += 1) {
    covariance += (x[index] - xMean) * (y[index] - yMean);
    xVariance += (x[index] - xMean) ** 2;
    yVariance += (y[index] - yMean) ** 2;
  }
  return covariance / Math.max(Math.sqrt(xVariance * yVariance), 1e-12);
}

function langevinDiagnostics(settings: ExtendedSettings) {
  const steps = 240;
  const count = clamp(Math.round(settings.paths * 3), 72, 150);
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const mass = Math.max(settings.theta, 0.2);
  const friction = Math.max(settings.kappa, 0.08);
  const thermal = Math.max(settings.sigma, 0.02);
  const tau = mass / friction;
  const diffusion = thermal / friction;
  const decay = Math.exp((-friction / mass) * dt);
  const velocitySd = Math.sqrt(thermal / mass);
  const innovationSd = velocitySd * Math.sqrt(1 - decay ** 2);
  const random = mulberry32(settings.seed + 3901);
  const paths: Point[][] = [];
  const msd = Array.from({ length: steps + 1 }, () => 0);

  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let position = settings.x0;
    let velocity = velocitySd * normal(random);
    const path: Point[] = [[0, position]];
    for (let index = 1; index <= steps; index += 1) {
      const previousVelocity = velocity;
      velocity = decay * velocity + innovationSd * normal(random);
      position += 0.5 * (previousVelocity + velocity) * dt;
      msd[index] += (position - settings.x0) ** 2;
      if (pathIndex < 7) path.push([index * dt, position]);
    }
    if (pathIndex < 7) paths.push(path);
  }

  const empiricalMsd = msd.map((value, index) => [index * dt, value / count] as Point);
  const theoryMsd = msd.map((_, index) => {
    const time = index * dt;
    return [time, 2 * diffusion * (time - tau * (1 - Math.exp(-time / tau)))] as Point;
  });
  const empiricalFinal = empiricalMsd[empiricalMsd.length - 1][1];
  const theoryFinal = theoryMsd[theoryMsd.length - 1][1];
  return { paths, empiricalMsd, theoryMsd, tau, diffusion, empiricalFinal, theoryFinal };
}

function drawLangevin(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area);
  const diagnostics = langevinDiagnostics(settings);
  rounded(context, left, colors.paper);
  chart(
    context,
    left,
    diagnostics.paths.map((points, index) => ({
      points,
      color: index === 0 ? colors.teal : colors.violet,
      width: index === 0 ? 2.5 : 1.2,
      alpha: index === 0 ? 1 : 0.35,
    })),
    { x: [0, settings.horizon], y: yDomain(diagnostics.paths, 0.1) },
    colors,
    "時間 t",
    "位置 Q",
  );
  label(context, "不足減衰 Langevin 経路", left.x + 52, left.y + 18, colors.teal);

  rounded(context, right, colors.paper);
  chart(
    context,
    right,
    [
      { points: diagnostics.empiricalMsd, color: colors.coral, width: 2.2 },
      { points: diagnostics.theoryMsd, color: colors.teal, width: 2.2, dashed: true },
    ],
    {
      x: [0, settings.horizon],
      y: [0, Math.max(diagnostics.empiricalFinal, diagnostics.theoryFinal, 0.1) * 1.15],
    },
    colors,
    "時間 t",
    "平均二乗変位",
  );
  label(context, "標本 MSD", right.x + 52, right.y + 18, colors.coral);
  label(context, "揺動散逸理論", right.x + right.w - 14, right.y + 18, colors.teal, "right");
}

function chemicalDiagnostics(settings: ExtendedSettings) {
  const steps = 240;
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const birth = Math.max(settings.rate, 0.05);
  const death = Math.max(settings.kappa, 0.05);
  const initial = Math.max(0, Math.round(settings.x0));
  const equilibrium = birth / death;
  const random = mulberry32(settings.seed + 4001);
  let jump = initial;
  let diffusion = initial;
  const jumpPath: Point[] = [[0, jump]];
  const diffusionPath: Point[] = [[0, diffusion]];
  const deterministic: Point[] = [[0, initial]];
  let negativeSteps = 0;
  const survival = Math.exp(-death * dt);
  const immigrants = equilibrium * (1 - survival);

  for (let index = 1; index <= steps; index += 1) {
    jump = binomial(random, jump, survival) + poisson(random, immigrants);
    const local = Math.max(diffusion, 0);
    diffusion +=
      (birth - death * local) * dt + Math.sqrt(Math.max(birth + death * local, 0) * dt) * normal(random);
    if (diffusion < 0) negativeSteps += 1;
    const time = index * dt;
    jumpPath.push([time, jump]);
    diffusionPath.push([time, diffusion]);
    deterministic.push([time, equilibrium + (initial - equilibrium) * Math.exp(-death * time)]);
  }

  const terminalCount = 360;
  const terminalSurvival = Math.exp(-death * horizon);
  const terminalImmigrants = equilibrium * (1 - terminalSurvival);
  const terminals = Array.from(
    { length: terminalCount },
    () => binomial(random, initial, terminalSurvival) + poisson(random, terminalImmigrants),
  );
  const expectedTerminal = equilibrium + (initial - equilibrium) * terminalSurvival;
  const terminalVariance = initial * terminalSurvival * (1 - terminalSurvival) + terminalImmigrants;
  return {
    jumpPath,
    diffusionPath,
    deterministic,
    terminals,
    equilibrium,
    expectedTerminal,
    terminalVariance,
    negativeRate: negativeSteps / steps,
  };
}

function drawChemicalReaction(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area);
  const diagnostics = chemicalDiagnostics(settings);
  rounded(context, left, colors.paper);
  const pathDomain = yDomain(
    [diagnostics.jumpPath, diagnostics.diffusionPath, diagnostics.deterministic],
    0.1,
  );
  chart(
    context,
    left,
    [
      { points: diagnostics.jumpPath, color: colors.teal, width: 2.3 },
      { points: diagnostics.diffusionPath, color: colors.coral, width: 1.8 },
      { points: diagnostics.deterministic, color: colors.amber, width: 2, dashed: true },
    ],
    { x: [0, settings.horizon], y: [Math.min(pathDomain[0], 0), pathDomain[1]] },
    colors,
    "時間 t",
    "分子数 N",
  );
  label(context, "整数ジャンプ", left.x + 52, left.y + 18, colors.teal);
  label(context, "CLE", left.x + 134, left.y + 18, colors.coral);
  label(context, "ODE", left.x + 178, left.y + 18, colors.amber);

  rounded(context, right, colors.paper);
  histogram(context, right, diagnostics.terminals, colors, colors.violet, {
    bins: 16,
    xLabel: "終端分子数",
    marker: diagnostics.expectedTerminal,
  });
  label(context, "ジャンプ過程の終端分布", right.x + 52, right.y + 18, colors.violet);
  label(context, "解析平均", right.x + right.w - 14, right.y + 18, colors.amber, "right");
}

function populationDiagnostics(settings: ExtendedSettings) {
  const steps = 240;
  const count = clamp(Math.round(settings.paths * 2), 64, 140);
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const initial = Math.max(settings.x0, 0.1);
  const capacity = Math.max(settings.theta, initial * 1.1, 1);
  const growth = Math.max(settings.rate, 0.01);
  const demographic = Math.max(settings.sigma, 0);
  const environmental = Math.max(settings.sigma2, 0);
  const random = mulberry32(settings.seed + 4101);
  const paths: Point[][] = [];
  const terminals: number[] = [];
  let extinct = 0;

  for (let pathIndex = 0; pathIndex < count; pathIndex += 1) {
    let state = initial;
    const path: Point[] = [[0, state]];
    for (let index = 1; index <= steps; index += 1) {
      if (state > 0) {
        const next =
          state +
          growth * state * (1 - state / capacity) * dt +
          demographic * Math.sqrt(state * dt) * normal(random) +
          environmental * state * Math.sqrt(dt) * normal(random);
        state = next <= 0 ? 0 : next;
      }
      if (pathIndex < 9) path.push([index * dt, state]);
    }
    if (state === 0) extinct += 1;
    terminals.push(state);
    if (pathIndex < 9) paths.push(path);
  }

  const deterministic = Array.from({ length: steps + 1 }, (_, index) => {
    const time = index * dt;
    const value = capacity / (1 + (capacity / initial - 1) * Math.exp(-growth * time));
    return [time, value] as Point;
  });
  const survivors = terminals.filter((value) => value > 0);
  return {
    paths,
    terminals,
    deterministic,
    capacity,
    crossover: environmental > 0 ? demographic ** 2 / environmental ** 2 : Number.POSITIVE_INFINITY,
    extinctionRate: extinct / count,
    terminalMean: mean(terminals),
    survivorMean: mean(survivors),
  };
}

function drawPopulation(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area);
  const diagnostics = populationDiagnostics(settings);
  rounded(context, left, colors.paper);
  const pathSeries = diagnostics.paths.map((points, index) => ({
    points,
    color: index === 0 ? colors.teal : colors.violet,
    width: index === 0 ? 2.3 : 1.1,
    alpha: index === 0 ? 1 : 0.32,
  }));
  chart(
    context,
    left,
    [...pathSeries, { points: diagnostics.deterministic, color: colors.coral, width: 2.3, dashed: true }],
    {
      x: [0, settings.horizon],
      y: [0, Math.max(yDomain([...diagnostics.paths, diagnostics.deterministic])[1], 1)],
    },
    colors,
    "時間 t",
    "個体数 N",
  );
  label(context, "確率経路束", left.x + 52, left.y + 18, colors.teal);
  label(context, "決定論 logistic", left.x + left.w - 14, left.y + 18, colors.coral, "right");

  rounded(context, right, colors.paper);
  histogram(context, right, diagnostics.terminals, colors, colors.violet, {
    bins: 18,
    xLabel: "終端個体数",
    marker: diagnostics.capacity,
  });
  label(context, `絶滅質量 ${percent(diagnostics.extinctionRate)}`, right.x + 52, right.y + 18, colors.coral);
  label(context, "K", right.x + right.w - 14, right.y + 18, colors.amber, "right");
}

type SirPath = {
  infected: Point[];
  susceptible: Point[];
  finalSize: number;
  peak: number;
};

function simulateSir(
  random: () => number,
  population: number,
  initialInfected: number,
  infectionRate: number,
  recoveryRate: number,
  horizon: number,
  steps: number,
  retainPath: boolean,
): SirPath {
  const dt = horizon / steps;
  let susceptible = population - initialInfected;
  let infected = initialInfected;
  let recovered = 0;
  let peak = infected;
  const infectedPath: Point[] = retainPath ? [[0, infected]] : [];
  const susceptiblePath: Point[] = retainPath ? [[0, susceptible]] : [];
  for (let index = 1; index <= steps; index += 1) {
    if (infected > 0) {
      const infectionProbability = 1 - Math.exp((-infectionRate * infected * dt) / population);
      const recoveryProbability = 1 - Math.exp(-recoveryRate * dt);
      const infections = binomial(random, susceptible, infectionProbability);
      const recoveries = binomial(random, infected, recoveryProbability);
      susceptible -= infections;
      infected += infections - recoveries;
      recovered += recoveries;
      peak = Math.max(peak, infected);
    }
    if (retainPath) {
      infectedPath.push([index * dt, infected]);
      susceptiblePath.push([index * dt, susceptible]);
    }
  }
  return {
    infected: infectedPath,
    susceptible: susceptiblePath,
    finalSize: infected + recovered,
    peak,
  };
}

function epidemicDiagnostics(settings: ExtendedSettings) {
  const population = clamp(Math.round(settings.theta), 50, 3000);
  const initialInfected = clamp(Math.round(settings.x0), 1, population - 1);
  const infectionRate = Math.max(settings.rate, 0.01);
  const recoveryRate = Math.max(settings.kappa, 0.01);
  const horizon = Math.max(settings.horizon, 0.5);
  const steps = 300;
  const random = mulberry32(settings.seed + 4201);
  const sample = simulateSir(
    random,
    population,
    initialInfected,
    infectionRate,
    recoveryRate,
    horizon,
    steps,
    true,
  );
  const dt = horizon / steps;
  let susceptible = population - initialInfected;
  let infected = initialInfected;
  const deterministic: Point[] = [[0, infected]];
  for (let index = 1; index <= steps; index += 1) {
    const infections = (infectionRate * susceptible * infected * dt) / population;
    const recoveries = recoveryRate * infected * dt;
    susceptible -= infections;
    infected += infections - recoveries;
    deterministic.push([index * dt, infected]);
  }

  const terminalRuns = 160;
  const outcomes = Array.from({ length: terminalRuns }, () =>
    simulateSir(
      random,
      population,
      initialInfected,
      infectionRate,
      recoveryRate,
      horizon,
      steps,
      false,
    ),
  );
  const finalSizes = outcomes.map((outcome) => outcome.finalSize);
  const outbreakThreshold = Math.max(0.2 * population, initialInfected + 10);
  const empiricalOutbreak =
    outcomes.filter((outcome) => outcome.finalSize >= outbreakThreshold).length / terminalRuns;
  const reproduction = infectionRate / recoveryRate;
  const effectiveReproduction = reproduction * (population - initialInfected) / population;
  const branchingOutbreak =
    effectiveReproduction > 1
      ? 1 - (1 / effectiveReproduction) ** initialInfected
      : 0;
  return {
    population,
    sample,
    deterministic,
    finalSizes,
    reproduction,
    effectiveReproduction,
    empiricalOutbreak,
    branchingOutbreak,
    meanPeak: mean(outcomes.map((outcome) => outcome.peak)),
  };
}

function drawEpidemic(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area);
  const diagnostics = epidemicDiagnostics(settings);
  rounded(context, left, colors.paper);
  chart(
    context,
    left,
    [
      { points: diagnostics.sample.infected, color: colors.coral, width: 2.5 },
      { points: diagnostics.deterministic, color: colors.teal, width: 2.2, dashed: true },
      { points: diagnostics.sample.susceptible, color: colors.violet, width: 1.3, alpha: 0.5 },
    ],
    { x: [0, settings.horizon], y: [0, diagnostics.population] },
    colors,
    "時間 t",
    "人数",
  );
  label(context, "確率 I(t)", left.x + 52, left.y + 18, colors.coral);
  label(context, "決定論 I(t)", left.x + 120, left.y + 18, colors.teal);
  label(context, "S(t)", left.x + left.w - 14, left.y + 18, colors.violet, "right");

  rounded(context, right, colors.paper);
  histogram(context, right, diagnostics.finalSizes, colors, colors.amber, {
    bins: 18,
    bounds: [0, diagnostics.population],
    xLabel: "累積感染者数",
  });
  label(context, `R₀=${format(diagnostics.reproduction, 2)}`, right.x + 52, right.y + 18, colors.ink);
  label(
    context,
    `大流行 ${percent(diagnostics.empiricalOutbreak)}`,
    right.x + right.w - 14,
    right.y + 18,
    colors.coral,
    "right",
  );
}

type NeuralDiagnostics = {
  voltageA: Point[];
  voltageB: Point[];
  spikesA: number[];
  spikesB: number[];
  threshold: number;
  firingRate: number;
  isiCv: number;
  coincidence: number;
};

function neuralDiagnostics(settings: ExtendedSettings): NeuralDiagnostics {
  const steps = 520;
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const rest = settings.x0;
  const threshold = Math.max(settings.upperBarrier, rest + 0.15);
  const input = settings.theta;
  const leak = Math.max(settings.kappa, 0.05);
  const noise = Math.max(settings.sigma, 0);
  const shared = clamp(settings.rho, 0, 0.95);
  const independentWeight = Math.sqrt(1 - shared);
  const sharedWeight = Math.sqrt(shared);
  const refractorySteps = Math.max(1, Math.round(0.018 / dt));
  const random = mulberry32(settings.seed + 4301);
  let voltageA = rest;
  let voltageB = rest;
  let refractoryA = 0;
  let refractoryB = 0;
  const pathA: Point[] = [[0, voltageA]];
  const pathB: Point[] = [[0, voltageB]];
  const spikesA: number[] = [];
  const spikesB: number[] = [];

  for (let index = 1; index <= steps; index += 1) {
    const time = index * dt;
    const common = normal(random);
    const shockA = sharedWeight * common + independentWeight * normal(random);
    const shockB = sharedWeight * common + independentWeight * normal(random);
    if (refractoryA > 0) {
      refractoryA -= 1;
      voltageA = rest;
    } else {
      voltageA += (-leak * (voltageA - rest) + input) * dt + noise * Math.sqrt(dt) * shockA;
      if (voltageA >= threshold) {
        spikesA.push(time);
        voltageA = rest;
        refractoryA = refractorySteps;
      }
    }
    if (refractoryB > 0) {
      refractoryB -= 1;
      voltageB = rest;
    } else {
      voltageB += (-leak * (voltageB - rest) + input) * dt + noise * Math.sqrt(dt) * shockB;
      if (voltageB >= threshold) {
        spikesB.push(time);
        voltageB = rest;
        refractoryB = refractorySteps;
      }
    }
    pathA.push([time, voltageA]);
    pathB.push([time, voltageB]);
  }

  const intervals = spikesA.slice(1).map((value, index) => value - spikesA[index]);
  const isiMean = mean(intervals);
  const isiCv = intervals.length > 1 ? Math.sqrt(variance(intervals)) / Math.max(isiMean, 1e-9) : 0;
  const coincidenceWindow = 2.5 * dt;
  const coincidences = spikesA.filter((time) =>
    spikesB.some((other) => Math.abs(other - time) <= coincidenceWindow),
  ).length;
  return {
    voltageA: pathA,
    voltageB: pathB,
    spikesA,
    spikesB,
    threshold,
    firingRate: (spikesA.length + spikesB.length) / (2 * horizon),
    isiCv,
    coincidence: coincidences / Math.max(spikesA.length, 1),
  };
}

function drawNeuroscience(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area);
  const diagnostics = neuralDiagnostics(settings);
  const thresholdLine: Point[] = [
    [0, diagnostics.threshold],
    [settings.horizon, diagnostics.threshold],
  ];
  rounded(context, left, colors.paper);
  chart(
    context,
    left,
    [
      { points: diagnostics.voltageA, color: colors.teal, width: 2.1 },
      { points: diagnostics.voltageB, color: colors.violet, width: 1.5, alpha: 0.65 },
      { points: thresholdLine, color: colors.coral, width: 1.7, dashed: true },
    ],
    {
      x: [0, settings.horizon],
      y: yDomain([diagnostics.voltageA, diagnostics.voltageB, thresholdLine], 0.1),
    },
    colors,
    "時間 t",
    "膜電位 V",
  );
  label(context, "細胞 A", left.x + 52, left.y + 18, colors.teal);
  label(context, "細胞 B", left.x + 110, left.y + 18, colors.violet);
  label(context, "閾値→reset", left.x + left.w - 14, left.y + 18, colors.coral, "right");

  rounded(context, right, colors.paper);
  const frame = chart(
    context,
    right,
    [],
    { x: [0, settings.horizon], y: [0, 3] },
    colors,
    "時間 t",
    "spike raster",
  );
  context.save();
  context.beginPath();
  context.rect(frame.plot.x, frame.plot.y, frame.plot.w, frame.plot.h);
  context.clip();
  [
    { times: diagnostics.spikesA, low: 0.55, high: 1.25, color: colors.teal },
    { times: diagnostics.spikesB, low: 1.75, high: 2.45, color: colors.violet },
  ].forEach((row) => {
    row.times.forEach((time) => {
      context.beginPath();
      context.moveTo(frame.mapX(time), frame.mapY(row.low));
      context.lineTo(frame.mapX(time), frame.mapY(row.high));
      context.strokeStyle = row.color;
      context.lineWidth = 2;
      context.stroke();
    });
  });
  context.restore();
  label(context, "A", frame.plot.x - 10, frame.mapY(0.9), colors.teal, "right");
  label(context, "B", frame.plot.x - 10, frame.mapY(2.1), colors.violet, "right");
  label(context, `共通入力 ρ=${format(clamp(settings.rho, 0, 0.95), 2)}`, right.x + 52, right.y + 18, colors.ink);
}

function filteringDiagnostics(settings: ExtendedSettings) {
  const steps = 216;
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const observationEvery = 9;
  const reversion = Math.max(settings.kappa, 0.05);
  const processNoise = Math.max(settings.sigma, 0.001);
  const observationNoise = Math.max(settings.sigma2, 0.001);
  const transition = Math.exp(-reversion * dt);
  const processVariance =
    (processNoise ** 2 * (1 - transition ** 2)) / (2 * reversion);
  const observationVariance = observationNoise ** 2;
  const stationaryVariance = processNoise ** 2 / (2 * reversion);
  const random = mulberry32(settings.seed + 4401);
  let state = settings.x0;
  let estimate = 0;
  let estimateVariance = stationaryVariance;
  const truth: Point[] = [[0, state]];
  const filtered: Point[] = [[0, estimate]];
  const upper: Point[] = [[0, estimate + 1.96 * Math.sqrt(estimateVariance)]];
  const lower: Point[] = [[0, estimate - 1.96 * Math.sqrt(estimateVariance)]];
  const observations: Point[] = [];
  const innovations: Point[] = [];
  const gains: number[] = [];
  const squaredFilterErrors: number[] = [];
  const squaredObservationErrors: number[] = [];
  let covered = 0;

  for (let index = 1; index <= steps; index += 1) {
    state = transition * state + Math.sqrt(processVariance) * normal(random);
    estimate = transition * estimate;
    estimateVariance = transition ** 2 * estimateVariance + processVariance;
    const time = index * dt;
    if (index % observationEvery === 0) {
      const observation = state + observationNoise * normal(random);
      const innovation = observation - estimate;
      const innovationVariance = estimateVariance + observationVariance;
      const gain = estimateVariance / innovationVariance;
      estimate += gain * innovation;
      estimateVariance *= 1 - gain;
      observations.push([time, observation]);
      innovations.push([time, innovation / Math.sqrt(innovationVariance)]);
      gains.push(gain);
      squaredObservationErrors.push((observation - state) ** 2);
    }
    truth.push([time, state]);
    filtered.push([time, estimate]);
    upper.push([time, estimate + 1.96 * Math.sqrt(estimateVariance)]);
    lower.push([time, estimate - 1.96 * Math.sqrt(estimateVariance)]);
    squaredFilterErrors.push((estimate - state) ** 2);
    if (Math.abs(estimate - state) <= 1.96 * Math.sqrt(estimateVariance)) covered += 1;
  }
  return {
    truth,
    filtered,
    upper,
    lower,
    observations,
    innovations,
    filterRmse: Math.sqrt(mean(squaredFilterErrors)),
    observationRmse: Math.sqrt(mean(squaredObservationErrors)),
    averageGain: mean(gains),
    coverage: covered / steps,
  };
}

function drawFiltering(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.62);
  const diagnostics = filteringDiagnostics(settings);
  rounded(context, left, colors.paper);
  const frame = chart(
    context,
    left,
    [
      { points: diagnostics.truth, color: colors.ink, width: 2 },
      { points: diagnostics.filtered, color: colors.teal, width: 2.4 },
      { points: diagnostics.upper, color: colors.amber, width: 1.2, dashed: true },
      { points: diagnostics.lower, color: colors.amber, width: 1.2, dashed: true },
    ],
    {
      x: [0, settings.horizon],
      y: yDomain([
        diagnostics.truth,
        diagnostics.filtered,
        diagnostics.upper,
        diagnostics.lower,
        diagnostics.observations,
      ]),
    },
    colors,
    "時間 t",
    "状態 X",
  );
  context.save();
  diagnostics.observations.forEach(([time, value]) => {
    context.beginPath();
    context.arc(frame.mapX(time), frame.mapY(value), 2.4, 0, 2 * Math.PI);
    context.fillStyle = colors.coral;
    context.fill();
  });
  context.restore();
  label(context, "真値", left.x + 52, left.y + 18, colors.ink);
  label(context, "filter", left.x + 88, left.y + 18, colors.teal);
  label(context, "観測", left.x + 132, left.y + 18, colors.coral);
  label(context, "95% 帯", left.x + left.w - 14, left.y + 18, colors.amber, "right");

  rounded(context, right, colors.paper);
  const upperBand: Point[] = [
    [0, 1.96],
    [settings.horizon, 1.96],
  ];
  const lowerBand: Point[] = [
    [0, -1.96],
    [settings.horizon, -1.96],
  ];
  chart(
    context,
    right,
    [
      { points: diagnostics.innovations, color: colors.violet, width: 1.7 },
      { points: upperBand, color: colors.coral, width: 1.2, dashed: true },
      { points: lowerBand, color: colors.coral, width: 1.2, dashed: true },
    ],
    { x: [0, settings.horizon], y: [-3.5, 3.5] },
    colors,
    "時間 t",
    "標準化 innovation",
  );
  label(context, "観測−予測", right.x + 52, right.y + 18, colors.violet);
  label(context, "±1.96", right.x + right.w - 14, right.y + 18, colors.coral, "right");
}

function excessKurtosis(values: number[]) {
  const center = mean(values);
  const second = mean(values.map((value) => (value - center) ** 2));
  if (second <= 1e-12) return 0;
  const fourth = mean(values.map((value) => (value - center) ** 4));
  return fourth / second ** 2 - 3;
}

function candidateScores(
  context: CanvasRenderingContext2D,
  rect: Rect,
  scores: Array<{ label: string; value: number; color: string }>,
  colors: ExtendedColors,
) {
  const plot = {
    x: rect.x + 48,
    y: rect.y + 42,
    w: rect.w - 66,
    h: rect.h - 76,
  };
  context.save();
  context.strokeStyle = colors.grid;
  context.lineWidth = 1;
  for (let index = 0; index <= 4; index += 1) {
    const x = plot.x + (index / 4) * plot.w;
    context.beginPath();
    context.moveTo(x, plot.y);
    context.lineTo(x, plot.y + plot.h);
    context.stroke();
  }
  const rowHeight = plot.h / scores.length;
  scores.forEach((score, index) => {
    const y = plot.y + index * rowHeight + rowHeight * 0.22;
    const height = rowHeight * 0.56;
    context.fillStyle = colors.grid;
    context.fillRect(plot.x, y, plot.w, height);
    context.fillStyle = score.color;
    context.fillRect(plot.x, y, clamp(score.value, 0, 1) * plot.w, height);
    label(context, score.label, plot.x - 7, y + height * 0.72, colors.ink, "right");
    label(context, percent(score.value), plot.x + plot.w - 5, y + height * 0.72, colors.white, "right");
  });
  context.restore();
  label(context, "特徴から見た候補適合度", rect.x + 48, rect.y + 20, colors.ink);
  label(context, "0", plot.x, rect.y + rect.h - 10, colors.muted);
  label(context, "1", plot.x + plot.w, rect.y + rect.h - 10, colors.muted, "right");
}

function modelSelectionDiagnostics(settings: ExtendedSettings) {
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  const steps = 260;
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / steps;
  const random = mulberry32(settings.seed + 4501);
  let state = settings.x0;
  const path: Point[] = [[0, state]];
  const increments: number[] = [];
  const states: number[] = [];
  let jumpCount = 0;

  for (let index = 1; index <= steps; index += 1) {
    const previous = state;
    if (choice === 0) {
      state += settings.mu * dt + Math.max(settings.sigma, 0.05) * Math.sqrt(dt) * normal(random);
    } else if (choice === 1) {
      state += settings.mu * dt + 0.25 * Math.max(settings.sigma, 0.05) * Math.sqrt(dt) * normal(random);
      const events = poisson(random, Math.max(settings.kappa, 1) * dt);
      for (let event = 0; event < events; event += 1) {
        state += Math.max(settings.sigma2, 0.25) * normal(random);
        jumpCount += 1;
      }
    } else {
      state +=
        Math.max(settings.kappa, 0.1) * (settings.theta - state) * dt +
        Math.max(settings.sigma, 0.05) * Math.sqrt(dt) * normal(random);
    }
    states.push(previous);
    increments.push(state - previous);
    path.push([index * dt, state]);
  }

  const incrementRates = increments.map((value) => value / dt);
  const stateMean = mean(states);
  const rateMean = mean(incrementRates);
  let covariance = 0;
  let stateVariance = 0;
  for (let index = 0; index < states.length; index += 1) {
    covariance += (states[index] - stateMean) * (incrementRates[index] - rateMean);
    stateVariance += (states[index] - stateMean) ** 2;
  }
  const estimatedKappa = Math.max(-covariance / Math.max(stateVariance, 1e-12), 0);
  const lagCorrelation = correlation(
    path.slice(0, -1).map((point) => point[1]),
    path.slice(1).map((point) => point[1]),
  );
  const labels = ["Brownian 拡散", "jump-diffusion", "OU 平均回帰"];
  const kurtosis = excessKurtosis(increments);
  const incrementSd = Math.sqrt(variance(increments));
  const largestStandardizedIncrement = Math.max(
    ...increments.map((value) => Math.abs(value - mean(increments)) / Math.max(incrementSd, 1e-9)),
  );
  const jumpScore = clamp(
    Math.max(largestStandardizedIncrement - 3, 0) / 4 + Math.max(kurtosis, 0) / 12,
    0,
    1,
  );
  const reversionScore = clamp(estimatedKappa / (estimatedKappa + 0.7), 0, 1) *
    (1 - 0.35 * jumpScore);
  const diffusionScore = clamp(1 - 0.8 * jumpScore - 0.75 * reversionScore, 0, 1);
  const scores = [diffusionScore, jumpScore, reversionScore];
  const selected = scores.indexOf(Math.max(...scores));
  return {
    choice,
    path,
    increments,
    jumpCount,
    estimatedKappa,
    lagCorrelation,
    kurtosis,
    candidate: labels[selected],
    generatedFamily: labels[choice],
    scores,
  };
}

function drawModelSelection(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.59);
  const diagnostics = modelSelectionDiagnostics(settings);
  rounded(context, left, colors.paper);
  chart(
    context,
    left,
    [{ points: diagnostics.path, color: colors.teal, width: 2.3 }],
    { x: [0, settings.horizon], y: yDomain([diagnostics.path], 0.12) },
    colors,
    "観測時刻",
    "状態 X",
  );
  label(context, `生成: ${diagnostics.generatedFamily}`, left.x + 52, left.y + 18, colors.teal);
  if (diagnostics.choice === 1) {
    label(context, `${diagnostics.jumpCount} jumps`, left.x + left.w - 14, left.y + 18, colors.coral, "right");
  } else if (diagnostics.choice === 2) {
    label(context, `中心 θ=${format(settings.theta, 1)}`, left.x + left.w - 14, left.y + 18, colors.coral, "right");
  } else {
    label(context, "連続経路", left.x + left.w - 14, left.y + 18, colors.violet, "right");
  }

  rounded(context, right, colors.paper);
  candidateScores(
    context,
    right,
    [
      { label: "拡散", value: diagnostics.scores[0], color: colors.teal },
      { label: "jump", value: diagnostics.scores[1], color: colors.coral },
      { label: "回帰", value: diagnostics.scores[2], color: colors.violet },
    ],
    colors,
  );
}

function normalQuantile(probability: number) {
  const p = clamp(probability, 1e-12, 1 - 1e-12);
  const a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924];
  const b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857];
  const c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878];
  const d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742];
  const low = 0.02425;
  const high = 1 - low;
  if (p < low) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > high) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const q = p - 0.5;
  const r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

function modelCriticismDiagnostics(settings: ExtendedSettings) {
  const choice = clamp(Math.round(settings.functionChoice), 0, 2);
  const count = 220;
  const random = mulberry32(settings.seed + 4601);
  const residuals: number[] = [];
  let previous = 0;
  const misspecificationStrength = clamp(Math.abs(settings.rho), 0.05, 0.9);
  const autoregression = misspecificationStrength;
  const tailDegrees = clamp(Math.round(10 - 8 * misspecificationStrength), 3, 9);
  for (let index = 0; index < count; index += 1) {
    if (choice === 0) {
      previous = normal(random);
    } else if (choice === 1) {
      previous = autoregression * previous + Math.sqrt(1 - autoregression ** 2) * normal(random);
    } else {
      let chiSquare = 0;
      for (let degree = 0; degree < tailDegrees; degree += 1) {
        chiSquare += normal(random) ** 2;
      }
      previous = normal(random) / Math.sqrt(Math.max(chiSquare / tailDegrees, 1e-9));
    }
    residuals.push(previous);
  }
  const center = mean(residuals);
  const scale = Math.sqrt(variance(residuals));
  const standardized = residuals.map((value) => (value - center) / Math.max(scale, 1e-9));
  const acf = Array.from({ length: 11 }, (_, lag) => {
    if (lag === 0) return [0, 1] as Point;
    return [lag, correlation(standardized.slice(0, -lag), standardized.slice(lag))] as Point;
  });
  const ordered = [...standardized].sort((left, right) => left - right);
  const qq = ordered.map((value, index) => [normalQuantile((index + 0.5) / count), value] as Point);
  const labels = ["基準に適合", "自己相関が残存", "重い裾が残存"];
  return {
    choice,
    residualPath: standardized.map((value, index) => [index, value] as Point),
    acf,
    qq,
    lagOne: acf[1][1],
    kurtosis: excessKurtosis(standardized),
    diagnosis: labels[choice],
  };
}

function drawModelCriticism(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.57);
  const { top, bottom } = splitVertical(right, 0.47);
  const diagnostics = modelCriticismDiagnostics(settings);
  rounded(context, left, colors.paper);
  const residualBand: Point[] = [
    [0, 1.96],
    [diagnostics.residualPath.length - 1, 1.96],
  ];
  const negativeBand: Point[] = [
    [0, -1.96],
    [diagnostics.residualPath.length - 1, -1.96],
  ];
  chart(
    context,
    left,
    [
      { points: diagnostics.residualPath, color: colors.violet, width: 1.5 },
      { points: residualBand, color: colors.coral, width: 1.1, dashed: true },
      { points: negativeBand, color: colors.coral, width: 1.1, dashed: true },
    ],
    {
      x: [0, diagnostics.residualPath.length - 1],
      y: yDomain([diagnostics.residualPath, residualBand, negativeBand], 0.08),
    },
    colors,
    "時点 k",
    "標準化残差 zₖ",
  );
  label(context, diagnostics.diagnosis, left.x + 52, left.y + 18, colors.violet);

  rounded(context, top, colors.paper);
  const acfBand = 1.96 / Math.sqrt(diagnostics.residualPath.length);
  chart(
    context,
    top,
    [
      { points: diagnostics.acf, color: colors.teal, width: 2 },
      { points: [[0, acfBand], [10, acfBand]], color: colors.coral, width: 1, dashed: true },
      { points: [[0, -acfBand], [10, -acfBand]], color: colors.coral, width: 1, dashed: true },
    ],
    { x: [0, 10], y: [-1, 1] },
    colors,
    "lag",
    "ACF",
  );
  label(context, "残差自己相関", top.x + 52, top.y + 18, colors.teal);

  rounded(context, bottom, colors.paper);
  const qqLimit = Math.max(3, ...diagnostics.qq.flatMap((point) => point.map(Math.abs))) * 1.05;
  chart(
    context,
    bottom,
    [
      { points: diagnostics.qq, color: colors.violet, width: 1.6 },
      { points: [[-qqLimit, -qqLimit], [qqLimit, qqLimit]], color: colors.teal, width: 1.2, dashed: true },
    ],
    { x: [-qqLimit, qqLimit], y: [-qqLimit, qqLimit] },
    colors,
    "理論正規分位",
    "標本分位",
  );
  label(context, "Normal QQ", bottom.x + 52, bottom.y + 18, colors.violet);
}

function normalPdf(value: number) {
  return Math.exp(-0.5 * value ** 2) / Math.sqrt(2 * Math.PI);
}

function synthesisDiagnostics(settings: ExtendedSettings) {
  const fineSteps = 512;
  const horizon = Math.max(settings.horizon, 0.2);
  const dt = horizon / fineSteps;
  const blockSize = clamp(2 ** Math.round(settings.zoom), 2, 64);
  const blockDt = blockSize * dt;
  const intensity = Math.max(20, settings.kappa * 40);
  const varianceRate = Math.max(settings.sigma ** 2, 0.04);
  const jumpSd = Math.sqrt(varianceRate / intensity);
  const random = mulberry32(settings.seed + 4701);
  let state = settings.x0;
  let events = 0;
  const finePath: Point[] = [[0, state]];
  for (let index = 1; index <= fineSteps; index += 1) {
    state += settings.mu * dt;
    const arrivals = poisson(random, intensity * dt);
    events += arrivals;
    for (let event = 0; event < arrivals; event += 1) state += jumpSd * normal(random);
    finePath.push([index * dt, state]);
  }

  const coarsePath: Point[] = [];
  const standardizedIncrements: number[] = [];
  for (let index = 0; index + blockSize <= fineSteps; index += blockSize) {
    const start = finePath[index];
    const end = finePath[index + blockSize];
    if (coarsePath.length === 0) coarsePath.push(start);
    coarsePath.push(end);
    standardizedIncrements.push(
      (end[1] - start[1] - settings.mu * blockDt) / Math.sqrt(varianceRate * blockDt),
    );
  }
  const normalCurve = Array.from({ length: 101 }, (_, index) => {
    const value = -4 + (8 * index) / 100;
    return [value, normalPdf(value)] as Point;
  });
  const expectedEvents = intensity * blockDt;
  return {
    finePath,
    coarsePath,
    standardizedIncrements,
    normalCurve,
    blockDt,
    expectedEvents,
    theoreticalExcess: 3 / expectedEvents,
    events,
    representation: expectedEvents >= 5 ? "拡散近似" : "イベント / jump",
  };
}

function drawSdeSynthesis(
  context: CanvasRenderingContext2D,
  area: Rect,
  settings: ExtendedSettings,
  colors: ExtendedColors,
) {
  const { left, right } = panels(area, 0.6);
  const diagnostics = synthesisDiagnostics(settings);
  rounded(context, left, colors.paper);
  chart(
    context,
    left,
    [
      { points: diagnostics.finePath, color: colors.coral, width: 1.3, alpha: 0.72 },
      { points: diagnostics.coarsePath, color: colors.teal, width: 2.6 },
    ],
    { x: [0, settings.horizon], y: yDomain([diagnostics.finePath, diagnostics.coarsePath], 0.1) },
    colors,
    "時間 t",
    "状態 X",
  );
  label(context, "微視的イベント", left.x + 52, left.y + 18, colors.coral);
  label(context, `粗視化 Δ=${format(diagnostics.blockDt, 3)}`, left.x + left.w - 14, left.y + 18, colors.teal, "right");

  rounded(context, right, colors.paper);
  histogram(context, right, diagnostics.standardizedIncrements, colors, colors.violet, {
    bounds: [-4, 4],
    bins: 16,
    xLabel: "標準化した粗視化増分",
    curve: diagnostics.normalCurve,
  });
  label(context, diagnostics.representation, right.x + 52, right.y + 18, colors.violet);
  label(context, "正規基準", right.x + right.w - 14, right.y + 18, colors.teal, "right");
}

export function drawApplicationLab(
  context: CanvasRenderingContext2D,
  area: Rect,
  lab: LabKind,
  settings: ExtendedSettings,
  colors: ExtendedColors,
): boolean {
  switch (lab) {
    case "langevin":
      drawLangevin(context, area, settings, colors);
      return true;
    case "chemical-reaction":
      drawChemicalReaction(context, area, settings, colors);
      return true;
    case "population":
      drawPopulation(context, area, settings, colors);
      return true;
    case "epidemic":
      drawEpidemic(context, area, settings, colors);
      return true;
    case "neuroscience":
      drawNeuroscience(context, area, settings, colors);
      return true;
    case "filtering":
      drawFiltering(context, area, settings, colors);
      return true;
    case "model-selection":
      drawModelSelection(context, area, settings, colors);
      return true;
    case "model-criticism":
      drawModelCriticism(context, area, settings, colors);
      return true;
    case "sde-synthesis":
      drawSdeSynthesis(context, area, settings, colors);
      return true;
    default:
      return false;
  }
}

export function applicationMetrics(
  lab: LabKind,
  settings: ExtendedSettings,
): Array<[string, string]> | null {
  switch (lab) {
    case "langevin": {
      const diagnostics = langevinDiagnostics(settings);
      return [
        ["速度緩和時間 m/γ", format(diagnostics.tau, 2)],
        ["長時間拡散 D", format(diagnostics.diffusion, 3)],
        ["MSD 標本 / 理論", format(diagnostics.empiricalFinal / Math.max(diagnostics.theoryFinal, 1e-9), 2)],
      ];
    }
    case "chemical-reaction": {
      const diagnostics = chemicalDiagnostics(settings);
      return [
        ["平衡平均 k₊Ω/k₋", format(diagnostics.equilibrium, 2)],
        ["終端 Fano 因子", format(diagnostics.terminalVariance / Math.max(diagnostics.expectedTerminal, 1e-9), 2)],
        ["CLE 負値ステップ", percent(diagnostics.negativeRate, 1)],
      ];
    }
    case "population": {
      const diagnostics = populationDiagnostics(settings);
      return [
        ["環境収容力 K", format(diagnostics.capacity, 0)],
        ["有限期間絶滅率", percent(diagnostics.extinctionRate)],
        ["二ノイズ分岐 N*", Number.isFinite(diagnostics.crossover) ? format(diagnostics.crossover, 1) : "∞"],
      ];
    }
    case "epidemic": {
      const diagnostics = epidemicDiagnostics(settings);
      return [
        ["基本再生産数 R₀", format(diagnostics.reproduction, 2)],
        [`初期分枝近似 (Rₑ=${format(diagnostics.effectiveReproduction, 2)})`, percent(diagnostics.branchingOutbreak)],
        ["標本大流行率", percent(diagnostics.empiricalOutbreak)],
      ];
    }
    case "neuroscience": {
      const diagnostics = neuralDiagnostics(settings);
      return [
        ["平均発火率", `${format(diagnostics.firingRate, 1)} /時間`],
        ["ISI 変動係数", diagnostics.spikesA.length > 2 ? format(diagnostics.isiCv, 2) : "標本不足"],
        ["A発火のB近接率", percent(diagnostics.coincidence)],
      ];
    }
    case "filtering": {
      const diagnostics = filteringDiagnostics(settings);
      return [
        ["観測 RMSE", format(diagnostics.observationRmse, 3)],
        ["Filter RMSE", format(diagnostics.filterRmse, 3)],
        ["95% 帯の被覆", percent(diagnostics.coverage)],
      ];
    }
    case "model-selection": {
      const diagnostics = modelSelectionDiagnostics(settings);
      return [
        ["第一候補", diagnostics.candidate],
        ["増分の超過尖度", format(diagnostics.kurtosis, 2)],
        ["推定平均回帰 κ", format(diagnostics.estimatedKappa, 2)],
      ];
    }
    case "model-criticism": {
      const diagnostics = modelCriticismDiagnostics(settings);
      return [
        ["診断シナリオ", diagnostics.diagnosis],
        ["残差 lag 1 ACF", format(diagnostics.lagOne, 2)],
        ["残差の超過尖度", format(diagnostics.kurtosis, 2)],
      ];
    }
    case "sde-synthesis": {
      const diagnostics = synthesisDiagnostics(settings);
      return [
        ["観測区間の期待事象数", format(diagnostics.expectedEvents, 2)],
        ["理論超過尖度", format(diagnostics.theoreticalExcess, 2)],
        ["有効表現", diagnostics.representation],
      ];
    }
    default:
      return null;
  }
}
