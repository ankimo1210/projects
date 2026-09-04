'use client';

import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from 'react';
import Link from 'next/link';
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpFromLine,
  RotateCcw,
  Orbit,
  Layers3,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  constrainView,
  engineLabels,
  initialView,
  palette,
  sameView,
  type EngineName,
  type View,
} from './contract';
import {
  createDemoSurface,
  nearestPoint,
  parseSurfaceCsv,
  presets,
  tenorLabel,
  toSurfaceCsv,
  type Parameters,
  type PointIndex,
  type SurfaceGrid,
} from './model';
import SurfaceCard from './renderer';
import Slices from './slices';
import './styles.css';

const engines: EngineName[] = ['plotly', 'three', 'babylon'];
type Mode = EngineName | 'compare';
const parameterControls: {
  key: keyof Parameters;
  label: string;
  min: number;
  max: number;
}[] = [
  { key: 'level', label: 'ATM・1年', min: 10, max: 35 },
  { key: 'skew', label: 'スキュー', min: -25, max: 15 },
  { key: 'curvature', label: 'カーブ', min: 0, max: 60 },
  { key: 'term', label: '期間の傾き', min: -6, max: 8 },
];

function Range({
  label,
  value,
  min,
  max,
  display,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  display: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="vol-range">
      <div>
        <span>{label}</span>
        <output>{display}</output>
      </div>
      <Slider
        aria-label={label}
        value={[value]}
        min={min}
        max={max}
        step={1}
        disabled={disabled}
        onValueChange={(value) =>
          onChange(Array.isArray(value) ? value[0] : value)
        }
      />
    </div>
  );
}

export default function VolatilityViewer() {
  const [mode, setMode] = useState<Mode>('plotly');
  const [preset, setPreset] = useState<keyof typeof presets>('equity');
  const [parameters, setParameters] = useState<Parameters>({
    ...presets.equity.parameters,
  });
  const [imported, setImported] = useState<SurfaceGrid | null>(null);
  const demo = useMemo(() => createDemoSurface(parameters), [parameters]);
  const grid = imported ?? demo;
  const [selection, setSelection] = useState({ moneyness: 1, tenor: 1 });
  const selected = useMemo(
    () => nearestPoint(grid, selection.moneyness, selection.tenor),
    [grid, selection],
  );
  const [hover, setHover] = useState<PointIndex | null>(null);
  const [view, setView] = useState(initialView);
  const [wireframe, setWireframe] = useState(false);
  const [fileError, setFileError] = useState('');
  const [fileBusy, setFileBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const changeView = useCallback((next: View) => {
    if (![next.yaw, next.pitch, next.distance].every(Number.isFinite)) return;
    setView((previous) => {
      const value = constrainView(next);
      return sameView(previous, value) ? previous : value;
    });
  }, []);
  const choosePoint = useCallback(
    (point: PointIndex) =>
      setSelection({
        moneyness: grid.moneyness[point.column],
        tenor: grid.tenors[point.row],
      }),
    [grid],
  );
  const choosePreset = (next: keyof typeof presets) => {
    setPreset(next);
    setParameters({ ...presets[next].parameters });
    setImported(null);
    setHover(null);
    setFileError('');
  };
  const importCsv = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileBusy(true);
    try {
      if (file.size > 1_000_000)
        throw new Error('CSVは1 MB以下にしてください。');
      const next = parseSurfaceCsv(await file.text(), file.name);
      setImported(next);
      setHover(null);
      setFileError('');
    } catch (error) {
      setFileError(
        error instanceof Error ? error.message : 'CSVを読み込めませんでした。',
      );
    } finally {
      setFileBusy(false);
      event.target.value = '';
    }
  };
  const downloadCsv = () => {
    const url = URL.createObjectURL(
      new Blob([toSurfaceCsv(grid)], { type: 'text/csv;charset=utf-8' }),
    );
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = imported
      ? 'volatility-imported.csv'
      : `volatility-demo-${preset}.csv`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const inspected =
    hover && grid.iv[hover.row]?.[hover.column] !== undefined
      ? hover
      : selected;
  const selectedIv = grid.iv[selected.row][selected.column] * 100;
  const sceneProps = {
    grid,
    selected,
    wireframe,
    view,
    onView: changeView,
    onHover: setHover,
    onSelect: choosePoint,
  };

  return (
    <main className="vol-app">
      <header className="vol-nav">
        <Link href="/" prefetch={false} className="vol-wordmark">
          <Orbit size={22} /> ORBIT <span>LAB</span>
        </Link>
        <span className="vol-nav-caption">
          A different perspective on data.
        </span>
        <Link href="/compare" prefetch={false} className="vol-back">
          <ArrowLeft size={15} /> 3Dツール比較
        </Link>
      </header>
      <div className="vol-workspace">
        <section className="vol-heading">
          <div>
            <div className="vol-eyebrow">
              QUANTITATIVE PLAYGROUND <span>01 / SURFACE</span>
            </div>
            <h1>
              Volatility surface<span>.</span>
            </h1>
            <p>
              同じデータを、3つの描画ツールで。形を動かして、違いを見つける。
            </p>
          </div>
          <div className="vol-source">
            <span className={`vol-badge ${imported ? 'is-import' : ''}`}>
              {imported ? 'CSVデータ' : '模擬データ'}
            </span>
            <strong>
              {grid.moneyness.length * grid.tenors.length}
              <span> points</span>
            </strong>
            <small>
              {grid.moneyness.length} strikes × {grid.tenors.length} tenors
            </small>
          </div>
        </section>
        <Tabs
          value={mode}
          onValueChange={(value) => {
            setMode(value as Mode);
            setHover(null);
          }}
          className="vol-tabs"
        >
          <div className="vol-toolbar">
            <TabsList aria-label="描画ツール" className="vol-engine-tabs">
              {engines.map((engine) => (
                <TabsTrigger key={engine} value={engine}>
                  {engineLabels[engine].name}
                </TabsTrigger>
              ))}
              <TabsTrigger value="compare">
                <Layers3 size={15} />
                3つ比較
              </TabsTrigger>
            </TabsList>
            <div className="vol-view-tools">
              <label htmlFor="vol-wireframe">
                ワイヤー
                <Switch
                  id="vol-wireframe"
                  checked={wireframe}
                  onCheckedChange={setWireframe}
                />
              </label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setView({ ...initialView })}
              >
                <RotateCcw size={14} />
                視点リセット
              </Button>
            </div>
          </div>
          <div
            className={`vol-main ${mode === 'compare' ? 'is-comparison' : ''}`}
          >
            <div className="vol-stage">
              {engines.map((engine) => (
                <TabsContent key={engine} value={engine}>
                  <SurfaceCard engine={engine} {...sceneProps} />
                </TabsContent>
              ))}
              <TabsContent value="compare">
                <div className="vol-compare-grid">
                  {engines.map((engine) => (
                    <SurfaceCard key={engine} engine={engine} {...sceneProps} />
                  ))}
                </div>
              </TabsContent>
              <div className="vol-scale">
                <div>
                  <span>IV · 年率</span>
                  <div
                    className="vol-gradient"
                    style={{
                      background: `linear-gradient(90deg, ${palette.map(([stop, color]) => `${color} ${stop * 100}%`).join(',')})`,
                    }}
                  />
                  <span>
                    {(grid.domain.iv[0] * 100).toFixed(0)}–
                    {(grid.domain.iv[1] * 100).toFixed(0)}%
                  </span>
                </div>
                <span>
                  {mode === 'compare'
                    ? 'データ・軸・色・視点を同期'
                    : 'K/F = ストライク ÷ 各満期のフォワード'}
                </span>
              </div>
            </div>
            <aside className="vol-controls" aria-label="サーフェス設定">
              <section className="vol-point">
                <div className="vol-section-label">
                  SELECTED POINT<span>断面の交点</span>
                </div>
                <div className="vol-quote">
                  <output data-testid="selected-iv">
                    {selectedIv.toFixed(2)}
                  </output>
                  <span>
                    %<small>implied volatility</small>
                  </span>
                </div>
                <div className="vol-coordinate">
                  <span>
                    T{' '}
                    <strong data-testid="selected-tenor">
                      {tenorLabel(grid.tenors[selected.row])}
                    </strong>
                  </span>
                  <span>
                    K/F{' '}
                    <strong data-testid="selected-moneyness">
                      {(grid.moneyness[selected.column] * 100).toFixed(1)}%
                    </strong>
                  </span>
                </div>
                <Range
                  label="満期"
                  value={selected.row}
                  min={0}
                  max={grid.tenors.length - 1}
                  display={tenorLabel(grid.tenors[selected.row])}
                  onChange={(row) => {
                    setHover(null);
                    choosePoint({ ...selected, row });
                  }}
                />
                <Range
                  label="マネーネス K/F"
                  value={selected.column}
                  min={0}
                  max={grid.moneyness.length - 1}
                  display={`${(grid.moneyness[selected.column] * 100).toFixed(1)}%`}
                  onChange={(column) => {
                    setHover(null);
                    choosePoint({ ...selected, column });
                  }}
                />
                <p className="vol-hover-readout">
                  {hover ? 'カーソル' : '選択点'} ·{' '}
                  {tenorLabel(grid.tenors[inspected.row])} /{' '}
                  {(grid.moneyness[inspected.column] * 100).toFixed(1)}% / IV{' '}
                  {(grid.iv[inspected.row][inspected.column] * 100).toFixed(2)}%
                </p>
              </section>
              <section className="vol-shape">
                <div className="vol-section-label">
                  SURFACE SHAPE
                  <span>{imported ? 'CSVの値を保持' : '形状を調整'}</span>
                </div>
                <div className="vol-presets" aria-label="デモ形状">
                  {(Object.keys(presets) as (keyof typeof presets)[]).map(
                    (key) => (
                      <Button
                        key={key}
                        variant="outline"
                        size="sm"
                        aria-pressed={!imported && preset === key}
                        onClick={() => choosePreset(key)}
                      >
                        {presets[key].label}
                      </Button>
                    ),
                  )}
                </div>
                <p>
                  {imported
                    ? 'プリセットを選ぶと模擬データに戻ります。'
                    : presets[preset].description}
                </p>
                <div className="vol-parameters">
                  {parameterControls.map(({ key, label, min, max }) => (
                    <Range
                      key={key}
                      label={label}
                      value={parameters[key]}
                      min={min}
                      max={max}
                      disabled={!!imported}
                      display={`${parameters[key]}${key === 'level' ? '%' : ''}`}
                      onChange={(value) => {
                        setParameters((previous) => ({
                          ...previous,
                          [key]: value,
                        }));
                        setHover(null);
                      }}
                    />
                  ))}
                </div>
              </section>
            </aside>
          </div>
        </Tabs>
        <div className="vol-section-heading">
          <h2>
            Look beneath the surface<span>2Dの断面で数値を確かめる</span>
          </h2>
          <span>3D上のラインと連動</span>
        </div>
        <Slices grid={grid} selected={selected} />
        <section className="vol-data">
          <div>
            <div className="vol-section-label">YOUR DATA, YOUR SURFACE</div>
            <h2>手元のデータでも、同じ比較を。</h2>
            <p>
              CSVはこのブラウザ内で処理します。フォーマットは{' '}
              <code>tenor_years,moneyness,iv</code>。<br />
              例：1年・ATM・IV 20% → <code>1,1,0.20</code>
            </p>
          </div>
          <div className="vol-data-actions">
            <div>
              <Button
                variant="outline"
                onClick={() => fileInput.current?.click()}
                disabled={fileBusy}
              >
                <ArrowUpFromLine size={15} />
                {fileBusy ? '読み込み中…' : 'CSVを読み込む'}
              </Button>
              <Button variant="outline" onClick={downloadCsv}>
                <ArrowDownToLine size={15} />
                CSVを保存
              </Button>
            </div>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              aria-label="サーフェスCSV"
              className="sr-only"
              onChange={importCsv}
            />
            <span>
              {imported ? grid.source.label : '現在の模擬データを書き出せます'}
            </span>
            {fileError && (
              <p className="vol-file-error" role="alert">
                {fileError}
              </p>
            )}
          </div>
        </section>
        <footer className="vol-notes">
          <p>
            {imported
              ? 'CSVの観測値を使用。'
              : '解析式で生成した模擬データです。市場価格から推定したIVではありません。'}{' '}
            点の間は表示用の線・面で接続しています。数値は最も近い格子点を表示します。
          </p>
          <details>
            <summary>データの条件と比較について</summary>
            <p>
              Tは年、K/Fは比率、IVは年率の小数で入力します。各軸2点以上の完全な格子が必要です。重複・欠損・無限値は読み込まず、補間もしません。上限は5,000点・1
              MBです。CSVの値は金融的な妥当性や無裁定性を検証していません。
            </p>
            <p>
              3種類は同じデータ・軸範囲・カラーマップ・カメラ位置で描画します。文字、線、面の補間や操作感は各ツールの実装で異なります。このページでは描画速度を計測していません。
            </p>
          </details>
        </footer>
      </div>
    </main>
  );
}
