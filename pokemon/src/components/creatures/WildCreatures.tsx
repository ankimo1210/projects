import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { getSpecies } from '../../game/data/creatures'
import { useGameStore, type WildSpawn } from '../../game/state/gameStore'
import { playerPosition } from '../../game/state/playerRef'
import { CreatureModel } from './CreatureModel'

const ENCOUNTER_DISTANCE = 1.9
const WANDER_RADIUS = 1.3

function WildCreature({ spawn }: { spawn: WildSpawn }) {
  const group = useRef<THREE.Group>(null)
  const phase = useRef(spawn.key * 2.39)
  const species = getSpecies(spawn.speciesId)

  useFrame((_, delta) => {
    const g = group.current
    if (!g) return
    const store = useGameStore.getState()
    if (store.mode !== 'explore') return

    // slow figure-eight wander around the spawn point
    phase.current += delta * 0.5
    const prevX = g.position.x
    const prevZ = g.position.z
    const x = spawn.x + Math.cos(phase.current) * WANDER_RADIUS
    const z = spawn.z + Math.sin(phase.current * 0.7) * WANDER_RADIUS
    g.position.set(x, 0, z)
    const dx = x - prevX
    const dz = z - prevZ
    if (dx * dx + dz * dz > 1e-8) g.rotation.y = Math.atan2(dx, dz)

    // proximity encounter
    if (Date.now() < store.encounterCooldownUntil) return
    const px = playerPosition.x - x
    const pz = playerPosition.z - z
    if (px * px + pz * pz < ENCOUNTER_DISTANCE * ENCOUNTER_DISTANCE) {
      store.startEncounter(spawn.key)
    }
  })

  return (
    <group ref={group} position={[spawn.x, 0, spawn.z]}>
      <CreatureModel species={species} />
    </group>
  )
}

/** All wild creatures currently roaming the grass zones. */
export function WildCreatures() {
  const spawns = useGameStore((s) => s.wildSpawns)
  return (
    <group>
      {spawns.map((spawn) => (
        <WildCreature key={spawn.key} spawn={spawn} />
      ))}
    </group>
  )
}
