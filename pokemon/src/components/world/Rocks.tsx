import { useMemo } from 'react'
import { BallCollider, RigidBody } from '@react-three/rapier'
import { ISLAND_RADIUS, isOpenGround } from '../../game/data/world'
import { mulberry32, pointInCircle } from '../../game/utils/random'

interface RockSpot {
  x: number
  z: number
  scale: number
  rotation: number
}

function makeRockSpots(count: number, seed: number): RockSpot[] {
  const rand = mulberry32(seed)
  const spots: RockSpot[] = []
  let guard = 0
  while (spots.length < count && guard < count * 30) {
    guard++
    const [x, z] = pointInCircle(rand, 0, 0, ISLAND_RADIUS - 6)
    if (!isOpenGround(x, z, 1.5)) continue
    if (Math.hypot(x, z) < 6) continue
    spots.push({ x, z, scale: 0.5 + rand() * 0.9, rotation: rand() * Math.PI * 2 })
  }
  return spots
}

export function Rocks() {
  const spots = useMemo(() => makeRockSpots(14, 4667), [])
  return (
    <group>
      {spots.map((spot, i) => (
        <RigidBody key={i} type="fixed" colliders={false} position={[spot.x, 0, spot.z]}>
          <BallCollider args={[spot.scale * 0.8]} position={[0, spot.scale * 0.4, 0]} />
          <mesh
            position={[0, spot.scale * 0.4, 0]}
            rotation={[0, spot.rotation, 0]}
            scale={spot.scale}
            castShadow
          >
            <dodecahedronGeometry args={[1, 0]} />
            <meshStandardMaterial color="#8d8d8d" flatShading />
          </mesh>
        </RigidBody>
      ))}
    </group>
  )
}
