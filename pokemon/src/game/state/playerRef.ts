import * as THREE from 'three'

/**
 * Player world position, mutated every physics frame by <Player>.
 * Kept outside Zustand so frame-rate updates never trigger React renders.
 * Readers (encounter checks, NPC proximity) sample it inside useFrame.
 */
export const playerPosition = new THREE.Vector3()
