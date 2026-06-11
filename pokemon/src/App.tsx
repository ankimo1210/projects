import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { KeyboardControls, Sky, type KeyboardControlsEntry } from '@react-three/drei'
import { Physics } from '@react-three/rapier'
import { Controls, type ControlName } from './game/types'
import { useGlobalKeys } from './game/useGlobalKeys'
import { exposeDebugHandle } from './game/debug'
import { playTheme, unlockAudio } from './game/audio'
import { useGameStore } from './game/state/gameStore'
import { Island } from './components/world/Island'
import { Pond } from './components/world/Pond'
import { Trees } from './components/world/Trees'
import { Rocks } from './components/world/Rocks'
import { Village } from './components/world/Village'
import { Well } from './components/world/Well'
import { GrassZones } from './components/world/GrassZones'
import { Player } from './components/player/Player'
import { Companion } from './components/creatures/Companion'
import { WildCreatures } from './components/creatures/WildCreatures'
import { Npcs } from './components/npc/Npcs'
import { BattleScreen } from './components/battle/BattleScreen'
import { CollectionBook } from './components/ui/CollectionBook'
import { DialogBox } from './components/ui/DialogBox'
import { HUD } from './components/ui/HUD'
import { GalleryApp } from './components/dev/Gallery'

const controlMap: KeyboardControlsEntry<ControlName>[] = [
  { name: Controls.forward, keys: ['KeyW', 'ArrowUp'] },
  { name: Controls.back, keys: ['KeyS', 'ArrowDown'] },
  { name: Controls.left, keys: ['KeyA', 'ArrowLeft'] },
  { name: Controls.right, keys: ['KeyD', 'ArrowRight'] },
  { name: Controls.interact, keys: ['KeyE', 'Space'] },
]

exposeDebugHandle()

const isGallery = new URLSearchParams(window.location.search).has('gallery')

/** Creates the AudioContext on first input and swaps BGM with the game mode. */
function useAudio() {
  useEffect(() => {
    const unlock = () => {
      unlockAudio()
      playTheme(useGameStore.getState().mode === 'battle' ? 'battle' : 'field')
    }
    window.addEventListener('pointerdown', unlock, { once: true })
    window.addEventListener('keydown', unlock, { once: true })
    const unsubscribe = useGameStore.subscribe((state, prev) => {
      if (state.mode !== prev.mode) {
        playTheme(state.mode === 'battle' ? 'battle' : 'field')
      }
    })
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      unsubscribe()
    }
  }, [])
}

export default function App() {
  useGlobalKeys()
  useAudio()

  if (isGallery) return <GalleryApp />

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <KeyboardControls map={controlMap}>
        <Canvas shadows dpr={[1, 1.75]} camera={{ position: [8, 11, 27], fov: 50 }}>
          <Sky sunPosition={[60, 80, 20]} turbidity={5} rayleigh={1.4} />
          <fog attach="fog" args={['#cfe3d8', 65, 140]} />
          {/* sky/ground bounce light gives softer, more natural shading */}
          <hemisphereLight args={['#cde4f5', '#7f9a5e', 0.55]} />
          <ambientLight intensity={0.18} />
          <directionalLight
            castShadow
            position={[50, 70, 30]}
            intensity={1.45}
            color="#fff6e8"
            shadow-mapSize={[2048, 2048]}
            shadow-bias={-0.00015}
            shadow-camera-left={-80}
            shadow-camera-right={80}
            shadow-camera-top={80}
            shadow-camera-bottom={-80}
          />
          <Suspense fallback={null}>
            <Physics>
              <Island />
              <Pond />
              <Trees />
              <Rocks />
              <Village />
              <Well />
              <GrassZones />
              <Player />
              <Companion />
              <WildCreatures />
              <Npcs />
            </Physics>
          </Suspense>
        </Canvas>
        <HUD />
        <BattleScreen />
        <CollectionBook />
        <DialogBox />
      </KeyboardControls>
    </div>
  )
}
