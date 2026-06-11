import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { getSpecies } from '../../game/data/creatures'
import type { BattleSideId } from '../../game/battle'
import { mulberry32 } from '../../game/utils/random'
import { CreatureModel } from '../creatures/CreatureModel'
import { onFx, type FxType } from './battleFx'

/**
 * The 3D backdrop of the battle screen: a small grassy clearing with the
 * player's creature seen from behind on the left and the wild one facing it
 * on the right — the classic monster-battle camera.
 */

const PLAYER_POS = new THREE.Vector3(-1.7, 0, 2.0)
const WILD_POS = new THREE.Vector3(1.7, 0, -2.4)

interface AnimState {
  type: FxType | null
  start: number
  fainted: boolean
}

function ArenaCreature({ speciesId, side }: { speciesId: string; side: BattleSideId }) {
  const group = useRef<THREE.Group>(null)
  const anim = useRef<AnimState>({ type: null, start: 0, fainted: false })
  const species = getSpecies(speciesId)

  const basePos = side === 'player' ? PLAYER_POS : WILD_POS
  const target = side === 'player' ? WILD_POS : PLAYER_POS
  const facing = Math.atan2(target.x - basePos.x, target.z - basePos.z)
  const lungeDir = useMemo(
    () => target.clone().sub(basePos).setY(0).normalize(),
    [basePos, target],
  )

  useEffect(
    () =>
      onFx((event) => {
        if (event.side !== side) return
        anim.current.type = event.type
        anim.current.start = performance.now() / 1000
        if (event.type === 'faint') anim.current.fainted = true
      }),
    [side],
  )

  useFrame(() => {
    const g = group.current
    if (!g) return
    const now = performance.now() / 1000
    const a = anim.current
    const t = now - a.start

    // resting transform
    g.position.set(basePos.x, 0, basePos.z)
    g.rotation.set(0, facing, 0)

    if (a.fainted && (a.type !== 'faint' || t > 0.7)) {
      // stay down after the faint animation finishes
      g.rotation.z = Math.PI / 2.2
      g.position.y = -0.15
      return
    }

    switch (a.type) {
      case 'lunge': {
        // dart toward the opponent and back (0.5s)
        if (t < 0.5) {
          const k = Math.sin((t / 0.5) * Math.PI)
          g.position.addScaledVector(lungeDir, k * 1.4)
        } else a.type = null
        break
      }
      case 'flinch': {
        // sharp decaying shake (0.45s)
        if (t < 0.45) {
          const decay = 1 - t / 0.45
          g.position.x += Math.sin(t * 55) * 0.09 * decay
          g.rotation.y = facing + Math.sin(t * 40) * 0.12 * decay
        } else a.type = null
        break
      }
      case 'faint': {
        // tip over sideways and sink (0.7s)
        const k = Math.min(1, t / 0.7)
        g.rotation.z = (Math.PI / 2.2) * k * k
        g.position.y = -0.15 * k
        break
      }
      case 'hop': {
        // two happy hops (0.7s) — recruit success
        if (t < 0.7) {
          g.position.y = Math.abs(Math.sin(t * Math.PI * 2 / 0.7)) * 0.35
        } else a.type = null
        break
      }
      case 'dodge': {
        // quick sidestep (0.35s) — attack missed
        if (t < 0.35) {
          g.position.x += Math.sin((t / 0.35) * Math.PI) * 0.5 * (side === 'wild' ? 1 : -1)
        } else a.type = null
        break
      }
      default:
        break
    }
  })

  return (
    <group ref={group} position={basePos}>
      <CreatureModel species={species} />
    </group>
  )
}

function CameraRig() {
  const camera = useThree((s) => s.camera)
  useFrame(() => {
    const t = performance.now() / 1000
    // gentle drift keeps the still scene alive
    camera.position.set(Math.sin(t * 0.25) * 0.25, 2.5 + Math.sin(t * 0.4) * 0.08, 6.2)
    camera.lookAt(0, 0.8, -0.8)
  })
  return null
}

/** Static clearing dressing: grass tufts, rocks, distant treeline. */
function Clearing() {
  const scatter = useMemo(() => {
    const rng = mulberry32(20260611)
    const tufts = Array.from({ length: 46 }, () => {
      const angle = rng() * Math.PI * 2
      const radius = 2.8 + rng() * 6.5
      return {
        x: Math.cos(angle) * radius,
        z: Math.sin(angle) * radius,
        s: 0.5 + rng() * 0.7,
        rot: rng() * Math.PI,
      }
    })
    const trees = Array.from({ length: 14 }, (_, i) => {
      const angle = (i / 14) * Math.PI * 2 + rng() * 0.3
      const radius = 12 + rng() * 4
      return {
        x: Math.cos(angle) * radius,
        z: Math.sin(angle) * radius,
        h: 2.6 + rng() * 1.8,
      }
    })
    return { tufts, trees }
  }, [])

  return (
    <group>
      {/* ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[20, 40]} />
        <meshStandardMaterial color="#7aab58" roughness={1} />
      </mesh>
      {/* worn patch where the battle happens */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <circleGeometry args={[3.4, 32]} />
        <meshStandardMaterial color="#9c8d62" roughness={1} />
      </mesh>
      {scatter.tufts.map((tuft, i) => (
        <mesh key={i} position={[tuft.x, 0.18 * tuft.s, tuft.z]} rotation={[0, tuft.rot, 0]}>
          <coneGeometry args={[0.16 * tuft.s, 0.5 * tuft.s, 5]} />
          <meshStandardMaterial color="#5d8f43" roughness={1} />
        </mesh>
      ))}
      {scatter.trees.map((tree, i) => (
        <group key={i} position={[tree.x, 0, tree.z]}>
          <mesh position={[0, tree.h * 0.25, 0]}>
            <cylinderGeometry args={[0.14, 0.2, tree.h * 0.5, 6]} />
            <meshStandardMaterial color="#6b5138" roughness={1} />
          </mesh>
          <mesh position={[0, tree.h * 0.72, 0]}>
            <coneGeometry args={[tree.h * 0.32, tree.h * 0.75, 7]} />
            <meshStandardMaterial color="#4a7a3a" roughness={1} />
          </mesh>
        </group>
      ))}
      {/* a couple of rocks */}
      <mesh position={[-4.6, 0.25, -3.2]} rotation={[0.3, 0.8, 0]}>
        <dodecahedronGeometry args={[0.45]} />
        <meshStandardMaterial color="#8a857c" roughness={0.9} />
      </mesh>
      <mesh position={[4.2, 0.18, 1.8]} rotation={[0.1, 0.4, 0.2]}>
        <dodecahedronGeometry args={[0.32]} />
        <meshStandardMaterial color="#938e84" roughness={0.9} />
      </mesh>
    </group>
  )
}

export function BattleArena({
  playerSpeciesId,
  wildSpeciesId,
}: {
  playerSpeciesId: string
  wildSpeciesId: string
}) {
  return (
    <Canvas
      shadows
      dpr={[1, 1.75]}
      camera={{ position: [0, 2.5, 6.2], fov: 45 }}
      style={{ position: 'absolute', inset: 0 }}
    >
      <color attach="background" args={['#aedcf5']} />
      <fog attach="fog" args={['#bfe2f2', 14, 26]} />
      <hemisphereLight args={['#cde4f5', '#7f9a5e', 0.6]} />
      <ambientLight intensity={0.25} />
      <directionalLight
        castShadow
        position={[6, 10, 4]}
        intensity={1.5}
        color="#fff6e8"
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.00015}
      />
      <CameraRig />
      <Clearing />
      <ArenaCreature speciesId={playerSpeciesId} side="player" />
      <ArenaCreature speciesId={wildSpeciesId} side="wild" />
    </Canvas>
  )
}
