export type Parameters = {
  level: number;
  skew: number;
  curvature: number;
  term: number;
};
export type PointIndex = { row: number; column: number };
export type SurfaceGrid = {
  id: string;
  moneyness: number[];
  tenors: number[];
  iv: number[][];
  domain: {
    moneyness: [number, number];
    tenor: [number, number];
    iv: [number, number];
  };
  source: { kind: 'demo' | 'csv'; label: string };
};
export const presets = {
  equity: {
    label: 'Equity smile',
    description: '左側のスキューと緩やかな期間構造',
    parameters: { level: 20, skew: -18, curvature: 40, term: 3 },
  },
  symmetric: {
    label: 'Symmetric smile',
    description: '両ウィングが対称に持ち上がる形',
    parameters: { level: 18, skew: 0, curvature: 55, term: 2 },
  },
  stress: {
    label: 'Short-end stress',
    description: '短い満期と左ウィングが高い形',
    parameters: { level: 32, skew: -25, curvature: 55, term: -5 },
  },
} as const;

function identity(moneyness: number[], tenors: number[], iv: number[][]) {
  let hash = 2166136261;
  for (const char of JSON.stringify([moneyness, tenors, iv])) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16);
}

export function createDemoSurface(parameters: Parameters): SurfaceGrid {
  const moneyness = Array.from(
    { length: 25 },
    (_, index) => (70 + index * 2.5) / 100,
  );
  const tenors = Array.from({ length: 24 }, (_, index) => (index + 1) / 12);
  const iv = tenors.map((tenor) =>
    moneyness.map((m) => {
      const k = Math.log(m);
      return Math.max(
        0.01,
        (parameters.level +
          parameters.term * (Math.sqrt(tenor) - 1) +
          parameters.skew * k +
          (parameters.curvature * k * k) / Math.sqrt(tenor + 0.1)) /
          100,
      );
    }),
  );
  return {
    // Parameter identity is stable across JS runtimes; log/sqrt may differ by an ULP.
    id: `demo:${parameters.level}:${parameters.skew}:${parameters.curvature}:${parameters.term}`,
    moneyness,
    tenors,
    iv,
    domain: { moneyness: [0.7, 1.3], tenor: [1 / 12, 2], iv: [0, 0.7] },
    source: { kind: 'demo', label: '解析式による模擬データ' },
  };
}

export function parseSurfaceCsv(
  text: string,
  name = 'surface.csv',
): SurfaceGrid {
  const lines = text
    .replace(/^\uFEFF/, '')
    .trim()
    .split(/\r\n|\n|\r/)
    .filter((line) => line.trim());
  const header = lines[0]?.split(',').map((field) => field.trim());
  const columns = ['tenor_years', 'moneyness', 'iv'];
  if (
    header?.length !== 3 ||
    columns.some((column) => !header.includes(column))
  )
    throw new Error('列は tenor_years,moneyness,iv の3つにしてください。');
  if (lines.length - 1 > 5000)
    throw new Error('格子は5,000点以下にしてください。');
  const quotes = new Map<string, number>();
  const tenorSet = new Set<number>();
  const moneySet = new Set<number>();
  for (let line = 1; line < lines.length; line++) {
    const fields = lines[line].split(',').map((field) => field.trim());
    if (
      fields.length !== 3 ||
      fields.some((field) => field === '' || !Number.isFinite(Number(field)))
    )
      throw new Error(`${line + 1}行目に有効な数値がありません。`);
    const [tenor, moneyness, iv] = columns.map((column) =>
      Number(fields[header.indexOf(column)]),
    );
    if (tenor <= 0 || tenor > 100)
      throw new Error(
        `${line + 1}行目: 満期は0より大きく100年以下にしてください。`,
      );
    if (moneyness <= 0 || moneyness > 10)
      throw new Error(
        `${line + 1}行目: K/Fは0より大きく10以下にしてください。`,
      );
    if (iv <= 0 || iv > 5)
      throw new Error(
        `${line + 1}行目: IVは小数で入力してください（25%なら0.25、0より大きく5以下）。`,
      );
    const key = `${tenor}:${moneyness}`;
    if (quotes.has(key))
      throw new Error(`${line + 1}行目: 満期とK/Fが重複しています。`);
    quotes.set(key, iv);
    tenorSet.add(tenor);
    moneySet.add(moneyness);
  }
  const tenors = [...tenorSet].sort((a, b) => a - b);
  const moneyness = [...moneySet].sort((a, b) => a - b);
  if (tenors.length < 2 || moneyness.length < 2)
    throw new Error('満期とK/Fをそれぞれ2種類以上含む格子が必要です。');
  if (quotes.size !== tenors.length * moneyness.length)
    throw new Error(
      '格子に欠損があります。すべての満期×K/Fの組み合わせを入力してください。',
    );
  const iv = tenors.map((tenor) =>
    moneyness.map((m) => quotes.get(`${tenor}:${m}`)!),
  );
  const maximum = Math.max(...iv.flat());
  return {
    id: identity(moneyness, tenors, iv),
    moneyness,
    tenors,
    iv,
    domain: {
      moneyness: [moneyness[0], moneyness[moneyness.length - 1]],
      tenor: [tenors[0], tenors[tenors.length - 1]],
      iv: [0, Math.max(0.1, Math.ceil(maximum * 10) / 10)],
    },
    source: { kind: 'csv', label: name },
  };
}

export function toSurfaceCsv(grid: SurfaceGrid) {
  return (
    'tenor_years,moneyness,iv\n' +
    grid.tenors
      .flatMap((tenor, row) =>
        grid.moneyness.map(
          (m, column) => `${tenor},${m},${grid.iv[row][column]}`,
        ),
      )
      .join('\n') +
    '\n'
  );
}

export function nearestPoint(
  grid: SurfaceGrid,
  moneyness: number,
  tenor: number,
): PointIndex {
  const nearest = (values: number[], target: number) =>
    values.reduce(
      (best, value, index) =>
        Math.abs(value - target) < Math.abs(values[best] - target)
          ? index
          : best,
      0,
    );
  return {
    row: nearest(grid.tenors, tenor),
    column: nearest(grid.moneyness, moneyness),
  };
}

export function tenorLabel(years: number) {
  const months = years * 12;
  return Math.abs(months - Math.round(months)) < 0.001
    ? `${Math.round(months)}M`
    : `${years.toFixed(2)}Y`;
}
