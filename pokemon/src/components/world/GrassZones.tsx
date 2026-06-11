import { useMemo } from 'react'
import { Instance, Instances } from '@react-three/drei'
import { GRASS_ZONES } from '../../game/data/world'
import { mulberry32, pointInCircle } from '../../game/utils/random'

interface Tuft {
  x: number
  z: number
  scale: number
  rotation: number
}

function makeTufts(): Tuft[] {
  const rand = mulberry32(2026)
  const tufts: Tuft[] = []
  for (const zone of GRASS_ZONES) {
    for (let i = 0; i < 70; i++) {
      const [x, z] = pointInCircle(rand, zone.x, zone.z, zone.radius - 0.5)
      tufts.push({ x, z, scale: 0.7 + rand() * 0.7, rotation: rand() * Math.PI })
    }
  }
  return tufts
}

/** Tall-grass encounter zones: darker discs covered in cone tufts. */
export function GrassZones() {
  const tufts = useMemo(() => makeTufts(), [])
  return (
    <group>
      {GRASS_ZONES.map((zone) => (
        <mesh
          key={zone.id}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[zone.x, 0.02, zone.z]}
          receiveShadow
        >
          <circleGeometry args={[zone.radius, 32]} />
          <meshStandardMaterial color="#4c8a3a" />
        </mesh>
      ))}
      <Instances limit={tufts.length} castShadow>
        <coneGeometry args={[0.18, 0.9, 5]} />
        <meshStandardMaterial color="#2f7d32" />
        {tufts.map((tuft, i) => (
          <Instance
            key={i}
            position={[tuft.x, 0.45 * tuft.scale, tuft.z]}
            scale={tuft.scale}
            rotation={[0, tuft.rotation, 0]}
          />
        ))}
      </Instances>
    </group>
  )
}
