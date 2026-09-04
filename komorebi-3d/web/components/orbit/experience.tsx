'use client';

import {
  Component,
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
  Activity,
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Braces,
  Check,
  Copy,
  Expand,
  Fingerprint,
  Layers3,
  MousePointer2,
  Pause,
  Play,
  RotateCcw,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  collections,
  type Collection,
  type Panel,
  type SceneStats,
} from './types';

const OrbitScene = lazy(() => import('./scene'));
const subscribeHydration = () => () => {};
const subscribeMotion = (notify: () => void) => {
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  media.addEventListener('change', notify);
  return () => media.removeEventListener('change', notify);
};

class SceneBoundary extends Component<
  { children: ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

const panels = {
  code: {
    label: 'Shape your space',
    eyebrow: '01 / CODE',
    description: 'この空間を、あなたの手で。動きと構造を変えてみましょう。',
    icon: Braces,
  },
  data: {
    label: 'Behind the scene',
    eyebrow: '02 / DATA',
    description: 'いま、このブラウザで描かれている3Dシーンの実測値。',
    icon: Activity,
  },
  research: {
    label: 'A little exploration',
    eyebrow: '03 / RESEARCH',
    description:
      'ひとつのアイデアから、もうひとつの世界へ。コレクションを切り替えて眺めましょう。',
    icon: Layers3,
  },
} as const;

export default function OrbitExperience() {
  const mounted = useSyncExternalStore(
    subscribeHydration,
    () => true,
    () => false,
  );
  const reducedMotion = useSyncExternalStore(
    subscribeMotion,
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => true,
  );
  const [playOverride, setPlaying] = useState<boolean | null>(null);
  const playing = playOverride ?? !reducedMotion;
  const [speed, setSpeed] = useState(1);
  const [wireframe, setWireframe] = useState(false);
  const [collection, setCollection] = useState<Collection>('core');
  const [panel, setPanel] = useState<Panel | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const [stats, setStats] = useState<SceneStats | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [immersive, setImmersive] = useState(false);
  const panelTrigger = useRef<HTMLElement | null>(null);
  const readyCallback = useCallback(() => setReady(true), []);
  const failedCallback = useCallback(() => setFailed(true), []);
  const statsCallback = useCallback((next: SceneStats) => {
    setStats(next);
    setHistory((previous) => [...previous.slice(-23), next.fps]);
  }, []);
  const openPanel = useCallback((next: Panel) => {
    panelTrigger.current = document.activeElement as HTMLElement;
    setPanel(next);
  }, []);

  useEffect(() => {
    if (!immersive) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setImmersive(false);
    };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, [immersive]);

  function selectCollection(next: Collection) {
    if (next !== collection) {
      setReady(false);
      setFailed(false);
      setStats(null);
      setHistory([]);
    }
    setCollection(next);
    setWireframe(false);
    setResetKey((key) => key + 1);
    setPanel(null);
  }

  async function copySettings() {
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(
          { collection, rotationSpeed: speed, autoRotate: playing, wireframe },
          null,
          2,
        ),
      );
      setCopied(true);
      setCopyError(false);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      setCopyError(true);
    }
  }

  const current = collections[collection];
  const details = panels[panel ?? 'code'];

  return (
    <main className={`orbit-page ${immersive ? 'is-immersive' : ''}`}>
      <a className="skip-link" href="#explore">
        3Dコレクションへ
      </a>
      <header className="site-header">
        <Link href="/" className="wordmark" aria-label="ORBIT ホーム">
          <span className="brand-symbol">
            <Fingerprint size={27} strokeWidth={1.3} />
          </span>
          ORBIT<span className="wordmark-dot">®</span>
        </Link>
        <nav aria-label="メインナビゲーション">
          <a href="#explore" className="nav-active">
            Playground
          </a>
          <button onClick={() => openPanel('research')}>
            Collection <span>02</span>
          </button>
        </nav>
        <div className="header-note">
          <span className="live-dot" />A space for possibility
        </div>
        <button
          className="mobile-collection"
          onClick={() => openPanel('research')}
          aria-label="コレクションを開く"
        >
          <Layers3 size={21} />
        </button>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-copy">
          <p className="eyebrow">
            <span /> YOUR IDEAS, IN ANOTHER DIMENSION
          </p>
          <h1 id="hero-title">
            Ideas.
            <br />
            <span>In orbit.</span>
          </h1>
          <p className="hero-description">
            触れて、動かして、広がる。
            <br />
            アイデアのための、小さな3Dユニバース。
          </p>
          <Button className="explore-button" onClick={() => openPanel('code')}>
            <span>空間をあそぶ</span>
            <ArrowUpRight size={20} />
          </Button>
          <div className="hero-caption">
            <span className="caption-line" /> BUILT TO BE EXPLORED.
          </div>
        </div>

        <div
          className="scene-stage"
          id="explore"
          aria-label={`${current.title} のインタラクティブ3Dビュー`}
        >
          <div className="stage-halo" aria-hidden="true" />
          <div
            className={`scene-fallback ${ready && !failed ? 'is-hidden' : ''}`}
          >
            <Image
              src={current.image}
              width={1200}
              height={1100}
              unoptimized
              priority
              alt={
                collection === 'core'
                  ? '銀色の結び目を光の軌道が包む3D彫刻'
                  : '夕暮れに灯るミニチュアの喫茶店'
              }
            />
          </div>
          {mounted && (
            <SceneBoundary key={collection} onError={failedCallback}>
              <Suspense fallback={null}>
                <OrbitScene
                  collection={collection}
                  playing={playing}
                  speed={speed}
                  wireframe={wireframe}
                  resetKey={resetKey}
                  onReady={readyCallback}
                  onStats={statsCallback}
                  onPanel={openPanel}
                />
              </Suspense>
            </SceneBoundary>
          )}
          <div className="scene-index">
            <span className="live-dot" />
            <span>
              {failed ? 'PREVIEW MODE' : ready ? 'LIVE 3D' : 'LOADING 3D'}
              <br />
              <small>{current.kind}</small>
            </span>
          </div>
          {failed && (
            <p className="webgl-note">
              3Dを読み込めませんでした。プレビュー画像でご覧ください。
            </p>
          )}
          <button
            className="immersive-button"
            onClick={() => setImmersive(!immersive)}
            aria-label={immersive ? '通常表示に戻す' : '3Dを大きく表示'}
          >
            {immersive ? <X size={18} /> : <Expand size={18} />}
          </button>
          <div className="scene-instructions" hidden={failed}>
            <MousePointer2 size={14} />
            <span>ドラッグで回転</span>
            {collection === 'core' && (
              <>
                <i />
                <span>ノードをクリックして探索</span>
              </>
            )}
          </div>
        </div>

        <div className="hero-bottom">
          <div className="model-label">
            <span className="model-number">
              {current.number} <span>/ 02</span>
            </span>
            <div>
              <span className="model-name">{current.title}</span>
              <span className="model-subtitle">INTERACTIVE STUDY</span>
            </div>
          </div>
          <div className="scene-controls">
            <Button
              variant="ghost"
              className="control-button"
              disabled={!ready || failed}
              onClick={() => setPlaying(!playing)}
              aria-label={playing ? '自動回転を停止' : '自動回転を再生'}
              aria-pressed={playing}
            >
              {playing ? <Pause size={15} /> : <Play size={15} />}
              <span>{playing ? 'Pause' : 'Play'}</span>
            </Button>
            <Button
              variant="ghost"
              className="reset-button"
              disabled={!ready || failed}
              onClick={() => setResetKey((key) => key + 1)}
              aria-label="視点をリセット"
            >
              <RotateCcw size={17} />
            </Button>
          </div>
        </div>
        <a
          href="#workspaces"
          className="scroll-indicator"
          aria-label="ワークスペースへスクロール"
        >
          <ArrowDown size={16} />
        </a>
      </section>

      <section
        className="workspaces"
        id="workspaces"
        aria-label="ワークスペース"
      >
        <div className="workspace-intro">
          <span className="eyebrow">THREE WAYS IN</span>
          <p>
            思いついたら、
            <br />
            そこから始めよう。
          </p>
        </div>
        {(Object.keys(panels) as Panel[]).map((key, index) => {
          const Icon = panels[key].icon;
          return (
            <button
              key={key}
              className="workspace-link"
              onClick={() => openPanel(key)}
            >
              <div className="workspace-top">
                <span>0{index + 1}</span>
                <Icon size={20} strokeWidth={1.5} />
              </div>
              <h2>
                {key.toUpperCase()}
                <ArrowUpRight size={22} />
              </h2>
              <p>
                {key === 'code'
                  ? '動きをつくる。構造をのぞく。'
                  : key === 'data'
                    ? '3Dの裏側を、数字で見る。'
                    : '次の小さな世界を見つける。'}
              </p>
            </button>
          );
        })}
      </section>
      <footer className="site-footer">
        <span>ORBIT / A SPATIAL WEB EXPERIMENT</span>
        <span>
          Made with curiosity.<span className="footer-star">✳</span>
        </span>
      </footer>

      <Sheet
        open={panel !== null}
        onOpenChange={(open) => {
          if (!open) setPanel(null);
        }}
      >
        <SheetContent
          className="orbit-sheet"
          showCloseButton={false}
          finalFocus={panelTrigger}
        >
          <SheetClose className="panel-close" aria-label="パネルを閉じる">
            <X size={22} />
          </SheetClose>
          <SheetHeader>
            <p className="eyebrow panel-eyebrow">{details.eyebrow}</p>
            <SheetTitle className="panel-title">{details.label}</SheetTitle>
            <SheetDescription className="panel-description">
              {details.description}
            </SheetDescription>
          </SheetHeader>
          <div className="panel-body">
            {panel === 'code' && (
              <>
                <div className="panel-preview">
                  <Image
                    src={current.image}
                    width={120}
                    height={110}
                    unoptimized
                    alt=""
                  />
                  <span>
                    {current.title}
                    <small>SCENE CONTROLS</small>
                  </span>
                </div>
                <div className="setting-row">
                  <div>
                    <label htmlFor="rotation">Auto rotation</label>
                    <p>ゆっくり、自動で回す</p>
                  </div>
                  <Switch
                    id="rotation"
                    disabled={!ready || failed}
                    checked={playing}
                    onCheckedChange={setPlaying}
                  />
                </div>
                <div className="speed-setting">
                  <div>
                    <span id="speed-label">Rotation speed</span>
                    <output>{speed.toFixed(1)}×</output>
                  </div>
                  <Slider
                    disabled={!ready || failed}
                    aria-labelledby="speed-label"
                    min={0.2}
                    max={2}
                    step={0.1}
                    value={[speed]}
                    onValueChange={(value) =>
                      setSpeed(Array.isArray(value) ? value[0] : value)
                    }
                  />
                </div>
                <div className="setting-row">
                  <div>
                    <label htmlFor="wireframe">Wireframe</label>
                    <p>形をつくるメッシュを表示</p>
                  </div>
                  <Switch
                    id="wireframe"
                    disabled={!ready || failed}
                    checked={wireframe}
                    onCheckedChange={setWireframe}
                  />
                </div>
                <Button
                  variant="outline"
                  className="wide-button"
                  onClick={() => setResetKey((key) => key + 1)}
                >
                  <RotateCcw size={16} />
                  視点をリセット
                </Button>
                <pre className="config-preview">
                  {JSON.stringify(
                    {
                      collection,
                      rotationSpeed: speed,
                      autoRotate: playing,
                      wireframe,
                    },
                    null,
                    2,
                  )}
                </pre>
                <Button className="wide-button" onClick={copySettings}>
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? 'コピーしました' : 'シーン設定をコピー'}
                </Button>
                <output className="copy-status">
                  {copyError
                    ? 'コピーできませんでした。上の設定テキストを選択してコピーできます。'
                    : ''}
                </output>
              </>
            )}
            {panel === 'data' && (
              <>
                <div className="telemetry-status">
                  <span className="live-dot" />
                  {failed
                    ? 'PREVIEW · 3D未接続'
                    : stats
                      ? 'LIVE · THIS BROWSER'
                      : 'シーンを読み込み中'}
                </div>
                <div className="fps-reading">
                  <strong>{stats?.fps ?? '—'}</strong>
                  <span>
                    FPS<small>現在の描画速度</small>
                  </span>
                </div>
                <figure
                  className="fps-chart"
                  aria-label="直近24秒間の描画速度の推移"
                >
                  {history.map((fps, index) => (
                    <span
                      key={index}
                      style={{
                        height: `${Math.max(4, (fps / Math.max(60, ...history)) * 100)}%`,
                      }}
                    />
                  ))}
                  <figcaption className="sr-only">
                    最新の描画速度: {stats?.fps ?? '計測中'} FPS
                  </figcaption>
                </figure>
                <div className="chart-labels">
                  <span>24-SECOND WINDOW</span>
                  <span>NOW</span>
                </div>
                <dl className="stats-list">
                  <div>
                    <dt>
                      Meshes <small>アセットのメッシュ数</small>
                    </dt>
                    <dd>{stats?.meshes.toLocaleString() ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>
                      Triangles <small>アセットの三角形数</small>
                    </dt>
                    <dd>{stats?.triangles.toLocaleString() ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>
                      Draw calls <small>現在のシーン描画命令</small>
                    </dt>
                    <dd>{stats?.calls.toLocaleString() ?? '—'}</dd>
                  </div>
                </dl>
                <p className="panel-footnote">
                  数値は端末やウィンドウの状態によって変わります。フレームレートは約1秒ごとに計測しています。
                </p>
              </>
            )}
            {panel === 'research' && (
              <>
                {(Object.keys(collections) as Collection[]).map((key) => (
                  <button
                    className={`collection-item ${collection === key ? 'selected' : ''}`}
                    onClick={() => selectCollection(key)}
                    key={key}
                    aria-label={`${collections[key].title}を表示`}
                  >
                    <div className={`collection-image ${key}`}>
                      <Image
                        src={collections[key].image}
                        width={400}
                        height={360}
                        unoptimized
                        alt=""
                      />
                      <span>{collections[key].number} / STUDY</span>
                      {collection === key && (
                        <b>
                          <Check size={12} />
                          表示中
                        </b>
                      )}
                    </div>
                    <div className="collection-info">
                      <h3>
                        {collections[key].title}
                        <ArrowUpRight size={20} />
                      </h3>
                      <p>{collections[key].description}</p>
                    </div>
                  </button>
                ))}
                <p className="panel-footnote">
                  どちらもこのプロジェクトで制作した3D作品です。選んだ作品を、同じ空間で操作できます。
                </p>
              </>
            )}
          </div>
          <div className="panel-bottom">
            <span>KEEP EXPLORING</span>
            <ArrowRight size={16} />
          </div>
        </SheetContent>
      </Sheet>
    </main>
  );
}
