'use client';

import {
  Component,
  Suspense,
  lazy,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import type { RendererName, SceneProps } from './render-contract';

const ThreeScene = lazy(() => import('./scene'));
const BabylonScene = lazy(() => import('./babylon-scene'));
const subscribe = () => () => {};
class SceneBoundary extends Component<
  { children: ReactNode; onError?: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError?.();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export default function SceneRenderer({
  engine = 'three',
  ...props
}: SceneProps & { engine?: RendererName }) {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const Scene = engine === 'three' ? ThreeScene : BabylonScene;
  return mounted ? (
    <SceneBoundary
      key={`${engine}:${props.collection}`}
      onError={props.onError}
    >
      <Suspense fallback={null}>
        <Scene {...props} />
      </Suspense>
    </SceneBoundary>
  ) : null;
}
