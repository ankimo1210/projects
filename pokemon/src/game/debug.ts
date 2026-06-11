import { useGameStore } from './state/gameStore'
import { playerPosition } from './state/playerRef'

declare global {
  interface Window {
    __qw?: {
      store: typeof useGameStore
      playerPosition: typeof playerPosition
    }
  }
}

/** Expose game internals for E2E tests (read access + real store actions). */
export function exposeDebugHandle(): void {
  if (typeof window !== 'undefined') {
    window.__qw = { store: useGameStore, playerPosition }
  }
}
