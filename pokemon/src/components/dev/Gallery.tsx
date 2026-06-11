import { Canvas } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import { CREATURES } from '../../game/data/creatures'
import { CreatureModel } from '../creatures/CreatureModel'

const COLS = 5
const SPACING_X = 2.6
const SPACING_Z = 3.0

/**
 * Dev-only model lineup, served at /?gallery=1.
 * Add &focus=<speciesId> for a single-creature close-up.
 * Lets us review all 20 semi-real redesigns side by side.
 */
export function GalleryApp() {
  const focusId = new URLSearchParams(window.location.search).get('focus')
  const focused = CREATURES.find((c) => c.id === focusId)

  if (focused) {
    const d = focused.size // pull the camera back for bigger species
    return (
      <div style={{ width: '100%', height: '100%' }}>
        <Canvas shadows camera={{ position: [1.6 * d, 1.5 * d, 2.6 * d], fov: 45 }}>
          <color attach="background" args={['#27313f']} />
          <ambientLight intensity={0.65} />
          <directionalLight castShadow position={[4, 7, 5]} intensity={1.4} />
          <directionalLight position={[-4, 3, -4]} intensity={0.4} />
          <CreatureModel species={focused} />
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
            <planeGeometry args={[10, 10]} />
            <meshStandardMaterial color="#3a4656" />
          </mesh>
          <OrbitControls target={[0, 0.8, 0]} />
        </Canvas>
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Canvas shadows camera={{ position: [0, 10, 14], fov: 50 }}>
        <color attach="background" args={['#27313f']} />
        <ambientLight intensity={0.65} />
        <directionalLight castShadow position={[8, 14, 10]} intensity={1.4} />
        <directionalLight position={[-6, 6, -8]} intensity={0.4} />
        <group position={[0, 0, 0]}>
          {CREATURES.map((species, i) => {
            const col = i % COLS
            const row = Math.floor(i / COLS)
            const x = (col - (COLS - 1) / 2) * SPACING_X
            const z = (row - 1.5) * SPACING_Z
            return (
              <group key={species.id} position={[x, 0, z]}>
                <CreatureModel species={species} />
                <Html position={[0, -0.35, 0.9]} center distanceFactor={12}>
                  <div
                    style={{
                      color: '#e8e8e8',
                      fontSize: 12,
                      fontFamily: 'system-ui, sans-serif',
                      whiteSpace: 'nowrap',
                      textShadow: '0 1px 2px #000',
                    }}
                  >
                    {species.name}
                    <span style={{ opacity: 0.6 }}> · {species.inspiration}</span>
                  </div>
                </Html>
              </group>
            )
          })}
        </group>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
          <planeGeometry args={[40, 30]} />
          <meshStandardMaterial color="#3a4656" />
        </mesh>
        <OrbitControls target={[0, 0.8, 0]} />
      </Canvas>
    </div>
  )
}
