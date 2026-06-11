import { useFrame } from '@react-three/fiber'
import { CapsuleCollider, RigidBody } from '@react-three/rapier'
import { NPCS, type NpcDef } from '../../game/data/npcs'
import { useGameStore } from '../../game/state/gameStore'
import { playerPosition } from '../../game/state/playerRef'

const TALK_DISTANCE = 2.8

function Npc({ npc }: { npc: NpcDef }) {
  return (
    <RigidBody
      type="fixed"
      colliders={false}
      position={[npc.position[0], 0, npc.position[1]]}
      rotation={[0, npc.facing, 0]}
    >
      <CapsuleCollider args={[0.5, 0.4]} position={[0, 0.9, 0]} />
      <group>
        <mesh position={[0, 0.8, 0]} castShadow>
          <capsuleGeometry args={[0.38, 0.65, 6, 12]} />
          <meshStandardMaterial color={npc.color} />
        </mesh>
        <mesh position={[0, 1.62, 0]} castShadow>
          <sphereGeometry args={[0.3, 16, 12]} />
          <meshStandardMaterial color="#f2c9a0" />
        </mesh>
        {/* hair */}
        <mesh position={[0, 1.78, -0.05]}>
          <sphereGeometry args={[0.28, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color="#4a3528" />
        </mesh>
        {/* eyes */}
        <mesh position={[-0.1, 1.65, 0.26]}>
          <sphereGeometry args={[0.04, 8, 6]} />
          <meshStandardMaterial color="#1c1c24" />
        </mesh>
        <mesh position={[0.1, 1.65, 0.26]}>
          <sphereGeometry args={[0.04, 8, 6]} />
          <meshStandardMaterial color="#1c1c24" />
        </mesh>
      </group>
    </RigidBody>
  )
}

/** Both villagers; tracks which one (if any) is in talking range. */
export function Npcs() {
  const setNearbyNpc = useGameStore((s) => s.setNearbyNpc)

  useFrame(() => {
    if (useGameStore.getState().mode !== 'explore') return
    let nearest: string | null = null
    let nearestDist = TALK_DISTANCE
    for (const npc of NPCS) {
      const dist = Math.hypot(
        playerPosition.x - npc.position[0],
        playerPosition.z - npc.position[1],
      )
      if (dist < nearestDist) {
        nearest = npc.id
        nearestDist = dist
      }
    }
    setNearbyNpc(nearest)
  })

  return (
    <group>
      {NPCS.map((npc) => (
        <Npc key={npc.id} npc={npc} />
      ))}
    </group>
  )
}
