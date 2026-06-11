import { POND } from '../../game/data/world'

/** Decorative pond: dark rim disc with lighter water disc on top. */
export function Pond() {
  return (
    <group position={[POND.x, 0, POND.z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <circleGeometry args={[POND.radius, 32]} />
        <meshStandardMaterial color="#3b5e43" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
        <circleGeometry args={[POND.radius - 1, 32]} />
        <meshStandardMaterial color="#4f9ed9" />
      </mesh>
    </group>
  )
}
