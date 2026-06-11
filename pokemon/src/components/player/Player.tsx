import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { useKeyboardControls } from '@react-three/drei'
import { CapsuleCollider, RigidBody, type RapierRigidBody } from '@react-three/rapier'
import { Controls } from '../../game/types'
import { PLAYER_SPAWN } from '../../game/data/world'
import { playerPosition } from '../../game/state/playerRef'
import { useGameStore } from '../../game/state/gameStore'

const SPEED = 7
const CAMERA_OFFSET = new THREE.Vector3(0, 9, 13)

const moveDir = new THREE.Vector3()
const camTarget = new THREE.Vector3()
const lookTarget = new THREE.Vector3()
const worldPos = new THREE.Vector3()

export function Player() {
  const body = useRef<RapierRigidBody>(null)
  const visual = useRef<THREE.Group>(null)
  const heading = useRef(0)
  const [, getKeys] = useKeyboardControls<typeof Controls[keyof typeof Controls]>()

  useFrame((state, delta) => {
    const rb = body.current
    const v = visual.current
    if (!rb || !v) return

    // raw physics position — only for the respawn check
    const pos = rb.translation()

    // respawn if fallen off the island
    if (pos.y < -6) {
      rb.setTranslation(
        { x: PLAYER_SPAWN[0], y: PLAYER_SPAWN[1], z: PLAYER_SPAWN[2] },
        true,
      )
      rb.setLinvel({ x: 0, y: 0, z: 0 }, true)
      return
    }

    // rapier interpolates the rendered transform between fixed physics steps;
    // the camera and followers must track that (not rb.translation(), which
    // jumps at the 60Hz physics rate and makes the screen judder)
    v.getWorldPosition(worldPos)
    playerPosition.copy(worldPos)

    const exploring = useGameStore.getState().mode === 'explore'
    const keys = getKeys()
    moveDir.set(0, 0, 0)
    if (exploring) {
      if (keys.forward) moveDir.z -= 1
      if (keys.back) moveDir.z += 1
      if (keys.left) moveDir.x -= 1
      if (keys.right) moveDir.x += 1
    }

    const vel = rb.linvel()
    if (moveDir.lengthSq() > 0) {
      moveDir.normalize().multiplyScalar(SPEED)
      heading.current = Math.atan2(moveDir.x, moveDir.z)
    }
    rb.setLinvel({ x: moveDir.x, y: vel.y, z: moveDir.z }, true)

    // turn the visual toward the heading
    const current = v.rotation.y
    let diff = heading.current - current
    diff = Math.atan2(Math.sin(diff), Math.cos(diff))
    v.rotation.y = current + diff * Math.min(1, delta * 12)

    // follow camera
    camTarget.copy(worldPos).add(CAMERA_OFFSET)
    state.camera.position.lerp(camTarget, 1 - Math.exp(-5 * delta))
    lookTarget.set(worldPos.x, worldPos.y + 1.5, worldPos.z)
    state.camera.lookAt(lookTarget)
  })

  return (
    <RigidBody
      ref={body}
      colliders={false}
      position={PLAYER_SPAWN}
      enabledRotations={[false, false, false]}
      linearDamping={0.5}
    >
      <CapsuleCollider args={[0.5, 0.45]} position={[0, 0.95, 0]} />
      <group ref={visual}>
        {/* body */}
        <mesh position={[0, 0.85, 0]} castShadow>
          <capsuleGeometry args={[0.42, 0.7, 6, 12]} />
          <meshStandardMaterial color="#d96c3a" />
        </mesh>
        {/* head */}
        <mesh position={[0, 1.75, 0]} castShadow>
          <sphereGeometry args={[0.34, 16, 12]} />
          <meshStandardMaterial color="#f2c9a0" />
        </mesh>
        {/* cap */}
        <mesh position={[0, 1.95, 0]}>
          <sphereGeometry args={[0.32, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color="#3a6ed9" />
        </mesh>
        {/* nose marker showing facing direction (+Z) */}
        <mesh position={[0, 1.72, 0.32]}>
          <coneGeometry args={[0.07, 0.18, 6]} />
          <meshStandardMaterial color="#c98961" />
        </mesh>
      </group>
    </RigidBody>
  )
}
