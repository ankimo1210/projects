import type { Collection, Panel, SceneStats } from './types';

export type RendererName = 'three' | 'babylon';
export type Pose = { yaw: number; pitch: number };
export type RenderFrame = {
  timestamp: number;
  width: number;
  height: number;
  renderer: string;
};
export type SceneProps = {
  collection: Collection;
  playing: boolean;
  speed: number;
  wireframe: boolean;
  resetKey: number;
  onReady: () => void;
  onStats: (stats: SceneStats) => void;
  onPanel: (panel: Panel) => void;
  onError?: () => void;
  comparison?: Pose;
  onFrame?: (frame: RenderFrame) => void;
};

export const studioUrl = '/assets/comparison-studio.hdr';
export const fieldOfView = 43;
export const exposure = 1.2;
export function cameraPosition(
  collection: Collection,
): [number, number, number] {
  return [0, collection === 'cafe' ? 2.8 : 1.25, 7.8];
}
export function initialYaw(collection: Collection) {
  return collection === 'cafe' ? -0.5 : 0;
}
export function modelExtent(collection: Collection, comparison = false) {
  return collection === 'core' ? 5.2 : comparison ? 4.4 : 5;
}
export const nodes: {
  panel: Panel;
  position: [number, number, number];
  number: string;
}[] = [
  { panel: 'code', position: [-2.4, 0.85, 0.1], number: '01' },
  { panel: 'data', position: [2.5, 0.4, 0.1], number: '02' },
  { panel: 'research', position: [0.8, -1.85, 0.9], number: '03' },
];

export function rendererInfo(canvas: HTMLCanvasElement) {
  const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
  if (!gl) return 'WebGL';
  const extension = gl.getExtension('WEBGL_debug_renderer_info');
  return extension
    ? String(gl.getParameter(extension.UNMASKED_RENDERER_WEBGL))
    : String(gl.getParameter(gl.RENDERER));
}
