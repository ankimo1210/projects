'use client';

import {
  Component,
  Suspense,
  lazy,
  useCallback,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import { engineLabels, type EngineName, type SurfaceProps } from './contract';

const scenes = {
  plotly: lazy(() => import('./plotly-surface')),
  three: lazy(() => import('./three-surface')),
  babylon: lazy(() => import('./babylon-surface')),
};
const subscribe = () => () => {};
class Boundary extends Component<
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

export default function SurfaceCard({
  engine,
  ...props
}: Omit<SurfaceProps, 'onReady' | 'onError'> & { engine: EngineName }) {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const [readyId, setReadyId] = useState('');
  const [failedId, setFailedId] = useState('');
  const onError = useCallback(
    () => setFailedId(props.grid.id),
    [props.grid.id],
  );
  const failed = failedId === props.grid.id;
  const ready = readyId === props.grid.id && !failed;
  const Scene = scenes[engine];
  return (
    <article
      className="vol-surface-card"
      data-engine={engine}
      data-ready={ready}
      data-grid-id={props.grid.id}
      data-view={`${props.view.yaw.toFixed(3)},${props.view.pitch.toFixed(3)},${props.view.distance.toFixed(3)}`}
      aria-label={`${engineLabels[engine].name} 3D Viewer`}
    >
      <header>
        <div>
          <span className="vol-engine-dot" />
          <strong>{engineLabels[engine].name}</strong>
          <span className="vol-engine-detail">
            {engineLabels[engine].detail}
          </span>
        </div>
        <span className={`vol-state ${ready ? 'is-ready' : ''}`}>
          {failed ? '3Dを利用できません' : ready ? 'LIVE VIEW' : '読み込み中'}
        </span>
      </header>
      <div className="vol-canvas">
        <span className="vol-axis-caption">IV（年率 %）</span>
        {failed ? (
          <output className="vol-unavailable">
            3Dの描画に失敗しました。点の数値と下の断面グラフは引き続き確認できます。
          </output>
        ) : (
          mounted && (
            <Boundary key={failedId} onError={onError}>
              <Suspense fallback={null}>
                <Scene {...props} onReady={setReadyId} onError={onError} />
              </Suspense>
            </Boundary>
          )
        )}
        {!ready && !failed && (
          <output className="vol-loading">
            <span />
            サーフェスを描画しています
          </output>
        )}
      </div>
      <footer>
        <span>ドラッグで回転 · スクロールで拡大</span>
        <span>クリックで断面を選択</span>
      </footer>
    </article>
  );
}
