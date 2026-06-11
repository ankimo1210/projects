import { useMemo } from 'react'
import { CylinderCollider, RigidBody } from '@react-three/rapier'
import { ISLAND_RADIUS, isOpenGround } from '../../game/data/world'
import { mulberry32, pointInCircle } from '../../game/utils/random'

interface TreeSpot {
  x: number
  z: number
  scale: number
}

function makeTreeSpots(count: number, seed: number): TreeSpot[] {
  const rand = mulberry32(seed)
  const spots: TreeSpot[] = []
  let guard = 0
  while (spots.length < count && guard < count * 30) {
    guard++
    const [x, z] = pointInCircle(rand, 0, 0, ISLAND_RADIUS - 8)
    if (!isOpenGround(x, z, 2.5)) continue
    if (Math.hypot(x, z) < 6) continue // keep player spawn area clear
    spots.push({ x, z, scale: 0.8 + rand() * 0.6 })
  }
  return spots
}

function Tree({ x, z, scale }: TreeSpot) {
  return (
    <RigidBody type="fixed" colliders={false} position={[x, 0, z]}>
      <CylinderCollider args={[1.2 * scale, 0.4 * scale]} position={[0, 1.2 * scale, 0]} />
      <group scale={scale}>
        <mesh position={[0, 0.9, 0]} castShadow>
          <cylinderGeometry args={[0.22, 0.3, 1.8, 8]} />
          <meshStandardMaterial color="#7a5230" />
        </mesh>
        <mesh position={[0, 2.6, 0]} castShadow>
          <coneGeometry args={[1.5, 2.6, 8]} />
          <meshStandardMaterial color="#3e7d32" />
        </mesh>
        <mesh position={[0, 3.9, 0]} castShadow>
          <coneGeometry args={[1.0, 1.8, 8]} />
          <meshStandardMaterial color="#4c9440" />
        </mesh>
      </group>
    </RigidBody>
  )
}

export function Trees() {
  const spots = useMemo(() => makeTreeSpots(36, 1210), [])
  return (
    <group>
      {spots.map((spot, i) => (
        <Tree key={i} {...spot} />
      ))}
    </group>
  )
}
