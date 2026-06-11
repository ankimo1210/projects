/**
 * Tiny imperative channel from the battle UI (which sequences turn events)
 * to the 3D arena creatures (which animate inside useFrame). Not in zustand:
 * these are fire-and-forget animation triggers, not state.
 */
import type { BattleSideId } from '../../game/battle'

export type FxType = 'lunge' | 'flinch' | 'faint' | 'hop' | 'dodge'

export interface FxEvent {
  type: FxType
  side: BattleSideId
}

type Listener = (event: FxEvent) => void

const listeners = new Set<Listener>()

export function emitFx(event: FxEvent): void {
  for (const listener of listeners) listener(event)
}

export function onFx(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
