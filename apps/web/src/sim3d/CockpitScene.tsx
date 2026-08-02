import { useEffect, useRef, useState } from 'react';
import { interpolator } from '../state/connection.js';
import { inputManager } from '../input/inputManager.js';
import { createSimWorld } from './scene.js';

/**
 * Babylon canvas host. Rendering runs at display refresh and reads the
 * interpolated state directly — React is not involved per frame (spec §6).
 */
export function CockpitScene(): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hover, setHover] = useState<{ label: string; hint?: string } | null>(null);
  const [cockpitMeshes, setCockpitMeshes] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const world = createSimWorld(canvas, {
      onHoverControl: setHover,
      onCockpitLoaded: setCockpitMeshes,
    });
    const keyHandler = (e: KeyboardEvent): void => {
      if (e.code === 'KeyC') world.centerView();
    };
    window.addEventListener('keydown', keyHandler);
    world.engine.runRenderLoop(() => {
      const state = interpolator.sample(Date.now());
      if (state) {
        // yoke display follows the input device (explicit pending display)
        world.update(state, { pitch: inputManager.axes.pitch, roll: inputManager.axes.roll });
      }
      world.scene.render();
    });
    return () => {
      window.removeEventListener('keydown', keyHandler);
      world.dispose();
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        className="sim-canvas"
        data-testid="sim-canvas"
        data-cockpit-meshes={cockpitMeshes}
      />
      {hover && (
        <div className="control-tooltip" data-testid="control-tooltip">
          <b>{hover.label}</b>
          {hover.hint && <span> — {hover.hint}</span>}
        </div>
      )}
    </>
  );
}
