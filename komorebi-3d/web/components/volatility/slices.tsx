import { fraction, ink, palette } from './contract';
import { tenorLabel, type PointIndex, type SurfaceGrid } from './model';

function Slice({
  title,
  subtitle,
  xs,
  ys,
  selected,
  xLabel,
  formatX,
  grid,
  id,
}: {
  title: string;
  subtitle: string;
  xs: number[];
  ys: number[];
  selected: number;
  xLabel: string;
  formatX: (x: number) => string;
  grid: SurfaceGrid;
  id: string;
}) {
  const w = 560,
    h = 210,
    left = 49,
    right = 18,
    top = 14,
    bottom = 40;
  const x = (value: number) =>
    left + fraction(value, [xs[0], xs.at(-1)!]) * (w - left - right);
  const y = (value: number) =>
    h - bottom - fraction(value, grid.domain.iv) * (h - top - bottom);
  const path = xs
    .map((value, index) => `${index ? 'L' : 'M'}${x(value)},${y(ys[index])}`)
    .join(' ');
  return (
    <article className="vol-slice" data-testid={id}>
      <header>
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span>IV · 年率 %</span>
      </header>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        aria-label={`${title}、${subtitle}。選択点のIV ${(ys[selected] * 100).toFixed(2)}%`}
      >
        <defs>
          <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={palette[2][1]} stopOpacity=".2" />
            <stop offset="100%" stopColor={palette[2][1]} stopOpacity=".015" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const value =
            grid.domain.iv[0] + t * (grid.domain.iv[1] - grid.domain.iv[0]);
          return (
            <g key={t}>
              <line
                x1={left}
                x2={w - right}
                y1={y(value)}
                y2={y(value)}
                className="vol-chart-grid"
              />
              <text x={left - 10} y={y(value) + 4} textAnchor="end">
                {(value * 100).toFixed(1)}
              </text>
            </g>
          );
        })}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const value = xs[0] + t * (xs.at(-1)! - xs[0]);
          return (
            <text key={t} x={x(value)} y={h - 20} textAnchor="middle">
              {formatX(value)}
            </text>
          );
        })}
        <path
          d={`${path} L${x(xs.at(-1)!)},${h - bottom} L${x(xs[0])},${h - bottom} Z`}
          fill={`url(#${id}-fill)`}
        />
        <path
          d={path}
          fill="none"
          stroke={ink.selected}
          strokeWidth="2.3"
          strokeLinejoin="round"
        />
        <line
          x1={x(xs[selected])}
          x2={x(xs[selected])}
          y1={top}
          y2={h - bottom}
          stroke={ink.selected}
          strokeOpacity=".35"
          strokeDasharray="3 5"
        />
        <circle
          cx={x(xs[selected])}
          cy={y(ys[selected])}
          r="4"
          fill={ink.selected}
        />
        <text x={w - right} y={h - 1} textAnchor="end">
          {xLabel}
        </text>
      </svg>
    </article>
  );
}
export default function Slices({
  grid,
  selected,
}: {
  grid: SurfaceGrid;
  selected: PointIndex;
}) {
  return (
    <section className="vol-slices" aria-label="選択点を通る断面">
      <Slice
        id="smile-slice"
        title="Volatility smile"
        subtitle={`満期 ${tenorLabel(grid.tenors[selected.row])} の断面`}
        xs={grid.moneyness}
        ys={grid.iv[selected.row]}
        selected={selected.column}
        xLabel="K / F (%)"
        formatX={(x) => `${(x * 100).toFixed(1)}%`}
        grid={grid}
      />
      <Slice
        id="term-slice"
        title="Term structure"
        subtitle={`K/F ${(grid.moneyness[selected.column] * 100).toFixed(1)}% の断面`}
        xs={grid.tenors}
        ys={grid.tenors.map((_, row) => grid.iv[row][selected.column])}
        selected={selected.row}
        xLabel="T（年）"
        formatX={(x) => x.toFixed(2)}
        grid={grid}
      />
    </section>
  );
}
