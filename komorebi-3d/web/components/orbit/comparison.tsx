'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent,
} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowLeft,
  ArrowUpRight,
  Fingerprint,
  MoveHorizontal,
  RotateCcw,
  ScanLine,
  Timer,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import SceneRenderer from './renderer';
import { collections, type Collection, type SceneStats } from './types';
import { createFrameMeasurement, type FrameMeasurement } from './measurement';
import type { Pose, RenderFrame, RendererName } from './render-contract';

const engines = ['three', 'babylon'] as const;
const names = { three: 'Three.js', babylon: 'Babylon.js' };
const ignorePanel = () => {};
const defaultPose = { yaw: 0, pitch: 0 };
type Result = FrameMeasurement & Omit<RenderFrame, 'timestamp'>;
type Run = { id: number; engine: RendererName; first: RendererName };

function Viewport({
  engine,
  collection,
  pose,
  wireframe,
  enabled,
  running,
  onMove,
  onReady,
  onError,
  onFrame,
}: {
  engine: RendererName;
  collection: Collection;
  pose: Pose;
  wireframe: boolean;
  enabled: boolean;
  running: boolean;
  onMove: (dx: number, dy: number) => void;
  onReady: (engine: RendererName) => void;
  onError: () => void;
  onFrame: (engine: RendererName, frame: RenderFrame) => void;
}) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [stats, setStats] = useState<SceneStats | null>(null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const markReady = useCallback(() => {
    setReady(true);
    onReady(engine);
  }, [engine, onReady]);
  const markError = useCallback(() => {
    setFailed(true);
    onError();
  }, [onError]);
  const sample = useCallback(
    (frame: RenderFrame) => onFrame(engine, frame),
    [engine, onFrame],
  );
  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    if (running || !ready || failed) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { x: event.clientX, y: event.clientY };
  }
  function pointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current || running) return;
    onMove(event.clientX - drag.current.x, event.clientY - drag.current.y);
    drag.current = { x: event.clientX, y: event.clientY };
  }
  return (
    <article
      className="engine-view"
      data-engine={engine}
      data-ready={enabled && ready && !failed}
    >
      <header className="engine-heading">
        <span className="engine-letter">{engine === 'three' ? 'A' : 'B'}</span>
        <div>
          <h2>{names[engine]}</h2>
          <p>
            {engine === 'three'
              ? 'THREE 0.185.1 · R3F 9.7.0'
              : 'NATIVE ENGINE · 9.25.0'}
          </p>
        </div>
        <Link
          href={engine === 'three' ? '/' : '/babylon'}
          aria-label={`${names[engine]}版のサイトを開く`}
        >
          <ArrowUpRight size={20} />
        </Link>
      </header>
      <div
        className="compare-canvas"
        onPointerDown={pointerDown}
        onPointerMove={pointerMove}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <div className="comparison-crosshair" aria-hidden="true" />
        {enabled ? (
          <>
            {(!ready || failed) && (
              <Image
                className="comparison-fallback"
                src={collections[collection].image}
                width={600}
                height={550}
                unoptimized
                alt="Blenderで描画した参考画像"
              />
            )}
            <SceneRenderer
              engine={engine}
              collection={collection}
              comparison={pose}
              playing={false}
              speed={1}
              wireframe={wireframe}
              resetKey={0}
              onReady={markReady}
              onError={markError}
              onStats={setStats}
              onPanel={ignorePanel}
              onFrame={sample}
            />
            <span className={`viewport-status ${failed ? 'has-error' : ''}`}>
              <span className="live-dot" />
              {failed
                ? '読み込み失敗 · 参考画像'
                : ready
                  ? running
                    ? 'MEASURING'
                    : 'LIVE 3D'
                  : 'LOADING 3D'}
            </span>
          </>
        ) : (
          <div className="engine-standby">
            <ScanLine size={32} strokeWidth={1} />
            <p>もう一方を計測中</p>
            <span>この描画エンジンは停止しています</span>
          </div>
        )}
        <span className="viewport-axis" aria-hidden="true">
          Y ↑<br />X →
        </span>
      </div>
      <footer className="engine-readout">
        <span>
          {stats && enabled ? stats.meshes.toLocaleString() : '—'}{' '}
          <small>MESHES</small>
        </span>
        <span>
          {stats && enabled ? stats.triangles.toLocaleString() : '—'}{' '}
          <small>TRIANGLES</small>
        </span>
        <span className="readout-mode">
          {wireframe ? 'WIREFRAME' : 'STUDIO'}
        </span>
      </footer>
    </article>
  );
}

export default function EngineComparison() {
  const [collection, setCollection] = useState<Collection>('core');
  const [pose, setPose] = useState<Pose>(defaultPose);
  const [wireframe, setWireframe] = useState(false);
  const [ready, setReady] = useState<Partial<Record<RendererName, boolean>>>(
    {},
  );
  const [run, setRun] = useState<Run | null>(null);
  const [results, setResults] = useState<Partial<Record<RendererName, Result>>>(
    {},
  );
  const [notice, setNotice] = useState('');
  const [assetBytes, setAssetBytes] = useState<number | null>(null);
  const runNumber = useRef(0);
  const measurement = useRef<ReturnType<typeof createFrameMeasurement> | null>(
    null,
  );
  const completedEngine = useRef<RendererName | null>(null);
  const running = run !== null;
  const markReady = useCallback((engine: RendererName) => {
    setReady((previous) =>
      previous[engine] ? previous : { ...previous, [engine]: true },
    );
  }, []);
  const cancel = useCallback((message = '計測を中止しました。') => {
    measurement.current = null;
    setRun(null);
    setResults({});
    setNotice(message);
  }, []);
  const markError = useCallback(() => {
    setReady({});
    cancel('3Dを読み込めませんでした。作品を切り替えて再試行できます。');
  }, [cancel]);
  useEffect(() => {
    const controller = new AbortController();
    fetch(collections[collection].asset, {
      method: 'HEAD',
      signal: controller.signal,
    })
      .then(async (response) => {
        const bytes = Number(response.headers.get('content-length'));
        if (response.ok && bytes > 0) {
          setAssetBytes(bytes);
        } else if (response.ok) {
          // Some local servers omit Content-Length on cached HEAD responses.
          const asset = await fetch(collections[collection].asset, {
            signal: controller.signal,
          });
          if (asset.ok) {
            const buffer = await asset.arrayBuffer();
            if (!controller.signal.aborted) setAssetBytes(buffer.byteLength);
          }
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, [collection]);
  useEffect(() => {
    if (!run) return;
    const visibility = () => {
      if (document.hidden)
        cancel('タブが非表示になったため計測を中止しました。');
    };
    const resize = () => cancel('画面サイズが変わったため計測を中止しました。');
    const timeout = window.setTimeout(
      () =>
        cancel('計測が時間内に完了しませんでした。もう一度試してください。'),
      35000,
    );
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('resize', resize);
    return () => {
      window.clearTimeout(timeout);
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('resize', resize);
    };
  }, [run, cancel]);

  const onFrame = useCallback(
    (engine: RendererName, frame: RenderFrame) => {
      if (
        !run ||
        run.engine !== engine ||
        completedEngine.current === engine ||
        !measurement.current
      )
        return;
      const result = measurement.current(frame.timestamp);
      if (!result) return;
      completedEngine.current = engine;
      setResults((previous) => ({
        ...previous,
        [engine]: {
          ...result,
          width: frame.width,
          height: frame.height,
          renderer: frame.renderer,
        },
      }));
      if (engine === run.first) {
        measurement.current = createFrameMeasurement();
        setRun({ ...run, engine: engine === 'three' ? 'babylon' : 'three' });
      } else {
        measurement.current = null;
        setRun(null);
        setNotice('計測が完了しました。同じ端末・この設定での参考値です。');
      }
    },
    [run],
  );
  function start() {
    const id = ++runNumber.current;
    const first = id % 2 === 1 ? 'three' : 'babylon';
    completedEngine.current = null;
    measurement.current = createFrameMeasurement();
    setResults({});
    setNotice('');
    setRun({ id, engine: first, first });
  }
  function updatePose(next: Pose) {
    setPose(next);
    setResults({});
    setNotice('');
  }
  const move = useCallback((dx: number, dy: number) => {
    setPose((previous) => ({
      yaw:
        ((previous.yaw + dx * 0.008 + 3 * Math.PI) % (2 * Math.PI)) - Math.PI,
      pitch: Math.max(
        -Math.PI / 3,
        Math.min(Math.PI / 3, previous.pitch + dy * 0.006),
      ),
    }));
    setResults({});
    setNotice('');
  }, []);
  const complete = results.three && results.babylon && !running;
  const current = collections[collection];
  const degrees = (radians: number) => Math.round((radians * 180) / Math.PI);

  return (
    <main className="comparison-page">
      <header className="site-header compare-header">
        <Link href="/" className="wordmark">
          <Fingerprint size={28} strokeWidth={1.3} /> ORBIT
          <span className="lab-mark">LAB</span>
        </Link>
        <span className="compare-header-note">
          ONE SCENE. TWO PERSPECTIVES.
        </span>
        <Link className="back-link" href="/">
          <ArrowLeft size={15} />
          <span>Playground</span>
        </Link>
      </header>
      <section className="comparison-intro">
        <p className="eyebrow">
          <span className="live-dot" /> EXPERIMENT 002 / ENGINE STUDY
        </p>
        <div className="comparison-title-row">
          <h1>
            Same scene.
            <br />
            <em>Different engines.</em>
          </h1>
          <p>
            つくる道具が変わると、どう見える？
            <br />
            同じ作品を、ふたつの3Dエンジンで。
            <br />
            <span>光の反射、細部、描画の速さを比べてみよう。</span>
          </p>
        </div>
      </section>
      <Tabs
        value={collection}
        onValueChange={(value) => {
          if (running || value === collection) return;
          setCollection(value as Collection);
          setPose(defaultPose);
          setWireframe(false);
          setReady({});
          setResults({});
          setNotice('');
          setAssetBytes(null);
        }}
        className="comparison-tabs"
      >
        <div className="comparison-toolbar">
          <TabsList className="collection-tabs" aria-label="比較する作品">
            <TabsTrigger value="core" disabled={running}>
              01 <span>Orbital core</span>
            </TabsTrigger>
            <TabsTrigger value="cafe" disabled={running}>
              02 <span>Komorebi café</span>
            </TabsTrigger>
          </TabsList>
          <span className="shared-badge">
            <span /> SAME GLB · SAME LIGHT · SAME VIEW
          </span>
        </div>
        <TabsContent value={collection}>
          <div className="comparison-grid">
            {engines.map((engine) => (
              <Viewport
                key={`${collection}:${engine}:${run ? `${run.id}:${run.engine}` : 'preview'}`}
                engine={engine}
                collection={collection}
                pose={pose}
                wireframe={wireframe}
                enabled={!run || run.engine === engine}
                running={running}
                onMove={move}
                onReady={markReady}
                onError={markError}
                onFrame={onFrame}
              />
            ))}
          </div>
          <div className="synchronization-bar">
            <span className="sync-label">
              <MoveHorizontal size={17} />
              ドラッグで両方を回転
            </span>
            <div className="angle-control">
              <label id="yaw-label">
                横方向 <span>{degrees(pose.yaw)}°</span>
              </label>
              <Slider
                aria-labelledby="yaw-label"
                min={-180}
                max={180}
                step={1}
                value={[degrees(pose.yaw)]}
                disabled={running}
                onValueChange={(value) =>
                  updatePose({
                    ...pose,
                    yaw:
                      ((Array.isArray(value) ? value[0] : value) * Math.PI) /
                      180,
                  })
                }
              />
            </div>
            <div className="angle-control">
              <label id="pitch-label">
                縦方向 <span>{degrees(pose.pitch)}°</span>
              </label>
              <Slider
                aria-labelledby="pitch-label"
                min={-60}
                max={60}
                step={1}
                value={[degrees(pose.pitch)]}
                disabled={running}
                onValueChange={(value) =>
                  updatePose({
                    ...pose,
                    pitch:
                      ((Array.isArray(value) ? value[0] : value) * Math.PI) /
                      180,
                  })
                }
              />
            </div>
            <label className="compare-wireframe" htmlFor="compare-wireframe">
              Wireframe
              <Switch
                checked={wireframe}
                disabled={running}
                onCheckedChange={(value) => {
                  setWireframe(value);
                  setResults({});
                  setNotice('');
                }}
                id="compare-wireframe"
                aria-label="両方をワイヤーフレーム表示"
              />
            </label>
            <Button
              variant="ghost"
              size="icon"
              disabled={running}
              onClick={() => updatePose(defaultPose)}
              aria-label="両方の角度をリセット"
            >
              <RotateCcw size={16} />
            </Button>
          </div>
        </TabsContent>
      </Tabs>
      <section
        className="measurement-section"
        aria-labelledby="measurement-title"
      >
        <div className="measurement-copy">
          <p className="eyebrow">02 / FEEL THE DIFFERENCE</p>
          <h2 id="measurement-title">見た目の、その先。</h2>
          <p>
            この端末で、ひとつずつ描画して計測。
            <br />
            1秒の準備後、4秒間の描画間隔を調べます。
          </p>
          <Button
            className="benchmark-button"
            disabled={!ready.three || !ready.babylon || running}
            onClick={start}
          >
            <Timer size={17} />
            {running ? `${names[run.engine]} を計測中…` : 'この端末で計測する'}
            <ArrowUpRight size={16} />
          </Button>
          {running && (
            <Button variant="ghost" onClick={() => cancel()}>
              <X size={14} />
              中止
            </Button>
          )}
          <output className="measurement-notice">
            {running
              ? 'もう一方の描画を停止しています。このタブを表示したままお待ちください。'
              : notice ||
                '初回ダウンロード時間は含みません。計測中は操作を一時停止します。'}
          </output>
        </div>
        <div className="measurement-table-wrap">
          <table className="measurement-table">
            <caption className="sr-only">単独描画の計測結果</caption>
            <thead>
              <tr>
                <th>このシーンでの実測</th>
                <th>Three.js</th>
                <th>Babylon.js</th>
              </tr>
            </thead>
            <tbody>
              <tr className="fps-row">
                <th>
                  描画速度<small>FPS · 大きいほど滑らか</small>
                </th>
                {engines.map((engine) => (
                  <td key={engine} data-testid={`${engine}-fps`}>
                    {complete ? results[engine]!.fps.toFixed(1) : '—'}
                    <small>fps</small>
                  </td>
                ))}
              </tr>
              <tr>
                <th>
                  遅いフレームの目安<small>p95 · 小さいほど待ちが少ない</small>
                </th>
                {engines.map((engine) => (
                  <td key={engine}>
                    {complete ? `${results[engine]!.p95Ms.toFixed(1)} ms` : '—'}
                  </td>
                ))}
              </tr>
              <tr>
                <th>描画バッファ</th>
                {engines.map((engine) => (
                  <td key={engine}>
                    {complete
                      ? `${results[engine]!.width} × ${results[engine]!.height}`
                      : 'DPR 1'}
                  </td>
                ))}
              </tr>
              <tr>
                <th>計測したフレーム</th>
                {engines.map((engine) => (
                  <td key={engine}>
                    {complete
                      ? `${results[engine]!.frames} / ${(results[engine]!.durationMs / 1000).toFixed(1)} s`
                      : '—'}
                  </td>
                ))}
              </tr>
              <tr>
                <th>共通モデルの容量</th>
                <td colSpan={2}>
                  {assetBytes
                    ? `${(assetBytes / 1024 / 1024).toFixed(2)} MiB`
                    : '—'}{' '}
                  <span className="table-muted">· 同一のGLB</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p className="measurement-footnote">
            FPSはディスプレイの更新頻度や端末の負荷にも制限されます。これは現在の作品・設定での比較です。
          </p>
          {complete && (
            <p className="gpu-info">GPU / {results.three!.renderer}</p>
          )}
        </div>
      </section>
      <section className="comparison-notes">
        <div>
          <span className="eyebrow">WHAT TO LOOK FOR</span>
          <h3>形は同じ。表情は？</h3>
          <p>
            {collection === 'core'
              ? '銀色の結び目のハイライト、暗部の階調、緑のリングの発色を見比べてください。'
              : '窓ガラスの透け方、看板の発色、屋根や植栽の細部を見比べてください。'}
          </p>
        </div>
        <div>
          <span className="eyebrow">CONTROLLED SETUP</span>
          <h3>比較条件をそろえて。</h3>
          <p>
            同じGLBとHDR照明、視野角43°、露出1.2、ACES、DPR
            1。環境光の処理や材質の計算方法はエンジンごとに異なります。
          </p>
        </div>
        <div>
          <span className="eyebrow">GO A LITTLE FURTHER</span>
          <h3>サイトごと体験する。</h3>
          <p>
            同じ操作パネル・作品切り替えを備えた、ふたつのORBITも用意しました。
          </p>
          <div className="engine-site-links">
            <Link href="/">
              Three.js版 <ArrowUpRight size={14} />
            </Link>
            <Link href="/babylon">
              Babylon.js版 <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>
      </section>
      <footer className="site-footer">
        <span>ORBIT LAB / {current.title.toUpperCase()}</span>
        <span>
          Blender → GLB → two engines.<span className="footer-star">✳</span>
        </span>
      </footer>
    </main>
  );
}
