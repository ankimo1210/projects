import { useFrame } from '@react-three/fiber'
import { CylinderCollider, RigidBody } from '@react-three/rapier'
import { WELL_POS } from '../../game/data/world'
import { useGameStore } from '../../game/state/gameStore'
import { playerPosition } from '../../game/state/playerRef'

const REST_DISTANCE = 2.6

/** Village well: stand close and press E to fully heal the party. */
export function Well() {
  const setNearWell = useGameStore((s) => s.setNearWell)

  useFrame(() => {
    const near =
      useGameStore.getState().mode === 'explore' &&
      Math.hypot(playerPosition.x - WELL_POS.x, playerPosition.z - WELL_POS.z) < REST_DISTANCE
    setNearWell(near)
  })

  return (
    <RigidBody type="fixed" colliders={false} position={[WELL_POS.x, 0, WELL_POS.z]}>
      <CylinderCollider args={[0.5, 0.85]} position={[0, 0.5, 0]} />
      <group>
        {/* stone ring */}
        <mesh position={[0, 0.4, 0]} castShadow>
          <cylinderGeometry args={[0.8, 0.9, 0.8, 12, 1, true]} />
          <meshStandardMaterial color="#8d8d8d" roughness={0.8} side={2} />
        </mesh>
        {/* water surface */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.62, 0]}>
          <circleGeometry args={[0.72, 16]} />
          <meshStandardMaterial color="#4f9ed9" roughness={0.3} />
        </mesh>
        {/* posts + small roof */}
        {[-0.7, 0.7].map((x) => (
          <mesh key={x} position={[x, 1.2, 0]}>
            <boxGeometry args={[0.12, 1.6, 0.12]} />
            <meshStandardMaterial color="#7a5230" roughness={0.85} />
          </mesh>
        ))}
        <mesh position={[0, 2.15, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
          <coneGeometry args={[1.05, 0.55, 4]} />
          <meshStandardMaterial color="#b5562e" roughness={0.8} flatShading />
        </mesh>
      </group>
    </RigidBody>
  )
}
