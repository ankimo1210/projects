import { CylinderCollider, RigidBody } from '@react-three/rapier'
import { ISLAND_HEIGHT, ISLAND_RADIUS } from '../../game/data/world'

/** Flat island disc with a sand rim, sitting in a large sea plane. */
export function Island() {
  return (
    <group>
      <RigidBody type="fixed" colliders={false}>
        <CylinderCollider
          args={[ISLAND_HEIGHT / 2, ISLAND_RADIUS]}
          position={[0, -ISLAND_HEIGHT / 2, 0]}
        />
        <mesh position={[0, -ISLAND_HEIGHT / 2, 0]} receiveShadow>
          <cylinderGeometry
            args={[ISLAND_RADIUS, ISLAND_RADIUS * 1.06, ISLAND_HEIGHT, 48]}
          />
          <meshStandardMaterial color="#d9c38a" />
        </mesh>
      </RigidBody>
      {/* grass top */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]} receiveShadow>
        <circleGeometry args={[ISLAND_RADIUS - 4, 48]} />
        <meshStandardMaterial color="#6aa84f" />
      </mesh>
      {/* sea */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.2, 0]}>
        <circleGeometry args={[400, 32]} />
        <meshStandardMaterial color="#2e6f9e" />
      </mesh>
    </group>
  )
}
