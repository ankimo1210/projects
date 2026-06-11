import { CuboidCollider, RigidBody } from '@react-three/rapier'
import { VILLAGE_CENTER, VILLAGE_RADIUS } from '../../game/data/world'

interface HouseProps {
  position: [number, number, number]
  rotation?: number
  wallColor?: string
}

function House({ position, rotation = 0, wallColor = '#f0e6d2' }: HouseProps) {
  return (
    <RigidBody type="fixed" colliders={false} position={position} rotation={[0, rotation, 0]}>
      <CuboidCollider args={[1.8, 1.4, 1.8]} position={[0, 1.4, 0]} />
      <group>
        <mesh position={[0, 1.3, 0]} castShadow>
          <boxGeometry args={[3.6, 2.6, 3.6]} />
          <meshStandardMaterial color={wallColor} />
        </mesh>
        <mesh position={[0, 3.4, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
          <coneGeometry args={[3.2, 1.8, 4]} />
          <meshStandardMaterial color="#b5562e" flatShading />
        </mesh>
        <mesh position={[0, 0.9, 1.81]}>
          <boxGeometry args={[1.0, 1.8, 0.05]} />
          <meshStandardMaterial color="#5d4023" />
        </mesh>
      </group>
    </RigidBody>
  )
}

/** Three small houses plus a central plaza disc. */
export function Village() {
  const { x, z } = VILLAGE_CENTER
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[x, 0.015, z]} receiveShadow>
        <circleGeometry args={[VILLAGE_RADIUS - 2, 32]} />
        <meshStandardMaterial color="#cbb27a" />
      </mesh>
      <House position={[x - 6, 0, z - 4]} rotation={0.4} />
      <House position={[x + 6, 0, z - 3]} rotation={-0.5} wallColor="#e3d3b3" />
      <House position={[x, 0, z + 6]} rotation={Math.PI} wallColor="#ead9c0" />
    </group>
  )
}
