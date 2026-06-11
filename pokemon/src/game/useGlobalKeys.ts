import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import { sfx, toggleMuted } from './audio'

/**
 * Window-level key handling for UI actions (the in-canvas KeyboardControls
 * polling only drives movement):
 * - C: toggle collection book
 * - E / Space: talk to a nearby NPC, or advance dialog
 * - M: mute / unmute audio
 * - Escape: close collection book
 */
export function useGlobalKeys(): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const store = useGameStore.getState()
      switch (event.code) {
        case 'KeyC':
          store.toggleCollection()
          break
        case 'KeyM':
          toggleMuted()
          break
        case 'Escape':
          if (store.mode === 'collection') store.toggleCollection()
          break
        case 'KeyE':
        case 'Space':
          if (store.mode === 'dialog') {
            store.advanceDialog()
          } else if (store.mode === 'explore' && store.nearbyNpcId) {
            store.startDialog(store.nearbyNpcId)
          } else if (store.mode === 'explore' && store.nearWell) {
            store.restParty()
            sfx.heal()
          }
          break
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}
