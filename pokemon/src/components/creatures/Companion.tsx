import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { getSpecies, STARTER_SPECIES_ID } from '../../game/data/creatures'
import { playerPosition } from '../../game/state/playerRef'
import { PLAYER_SPAWN } from '../../game/data/world'
import { useGameStore } from '../../game/state/gameStore'
import { CreatureModel } from './CreatureModel'

const FOLLOW_DISTANCE = 1.8
const FOLLOW_SPEED = 5

const desired = new THREE.Vector3()
const toPlayer = new THREE.Vector3()

/** The active party member trails the player around the field (visual only). */
export function Companion() {
  const group = useRef<THREE.Group>(null)
  const activeSpeciesId = useGameStore((s) => {
    const member = s.party.find((m) => m.uid === s.activeUid)
    return member?.speciesId ?? STARTER_SPECIES_ID
  })
  const species = getSpecies(activeSpeciesId)

  useFrame((_, delta) => {
    const g = group.current
    if (!g) return
    toPlayer.copy(playerPosition).sub(g.position)
    toPlayer.y = 0
    const dist = toPlayer.length()
    if (dist > FOLLOW_DISTANCE) {
      desired
        .copy(playerPosition)
        .addScaledVector(toPlayer.normalize(), -FOLLOW_DISTANCE)
      desired.y = 0
      g.position.lerp(desired, 1 - Math.exp(-FOLLOW_SPEED * delta))
      g.rotation.y = Math.atan2(toPlayer.x, toPlayer.z)
    }
  })

  return (
    <group
      ref={group}
      position={[PLAYER_SPAWN[0] - 1.5, 0, PLAYER_SPAWN[2] + 1.5]}
    >
      <CreatureModel species={species} />
    </group>
  )
}
