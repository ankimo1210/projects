import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import type { CreatureSpecies } from '../../game/data/creatures'

/**
 * Procedural semi-real creature models (design doc: docs/character-design.md).
 * Built from primitives, but following real-animal skeletal proportions:
 * - bipeds ~2.9 head-heights, quadrupeds near real ratios
 * - eyes small and dark (width <= ~18% of head width), no sclera
 * - material contrast via roughness: fur / bare skin / keratin / scale
 * - natural palettes; accent colors only on small signature features
 * Models face +Z.
 */

interface BodyProps {
  species: CreatureSpecies
}

// roughness per material zone
const R_FUR = 0.92
const R_FEATHER = 0.78
const R_SKIN = 0.55
const R_KERATIN = 0.42
const R_SCALE = 0.55
const R_STONE = 0.6

// shared natural constants (not part of species palettes)
const NOSE_COLOR = '#4a4038'
const EYE_COLOR = '#1c1410'
const CHARCOAL = '#2e2622'
const SLATE = '#6e6a63'
const BIRD_LEG = '#5a5346'

function Fur({ color }: { color: string }) {
  return <meshStandardMaterial color={color} roughness={R_FUR} />
}
function Feather({ color }: { color: string }) {
  return <meshStandardMaterial color={color} roughness={R_FEATHER} />
}
function Skin({ color }: { color: string }) {
  return <meshStandardMaterial color={color} roughness={R_SKIN} />
}
function Keratin({ color }: { color: string }) {
  return <meshStandardMaterial color={color} roughness={R_KERATIN} />
}
function Scale({ color }: { color: string }) {
  return <meshStandardMaterial color={color} roughness={R_SCALE} />
}

/** Small dark animal eyes, no sclera. */
function Eyes({
  y,
  z,
  spread = 0.11,
  r = 0.042,
}: {
  y: number
  z: number
  spread?: number
  r?: number
}) {
  return (
    <>
      {[-spread, spread].map((x) => (
        <mesh key={x} position={[x, y, z]}>
          <sphereGeometry args={[r, 8, 6]} />
          <meshStandardMaterial color={EYE_COLOR} roughness={0.25} />
        </mesh>
      ))}
    </>
  )
}

/** Fur muzzle with a bare-skin nose tip — keeps a real snout, never flat. */
function Muzzle({
  position,
  scale,
  furColor,
  noseR = 0.05,
}: {
  position: [number, number, number]
  scale: [number, number, number]
  furColor: string
  noseR?: number
}) {
  return (
    <group position={position}>
      <mesh scale={scale}>
        <sphereGeometry args={[1, 12, 10]} />
        <Fur color={furColor} />
      </mesh>
      <mesh position={[0, scale[1] * 0.25, scale[2] * 0.92]}>
        <sphereGeometry args={[noseR, 8, 6]} />
        <Skin color={NOSE_COLOR} />
      </mesh>
    </group>
  )
}

/** Nikokka's signature: a tiny three-leaf sprout rooted at the left ear. */
function EarSprout({ accent }: { accent: string }) {
  return (
    <group position={[-0.18, 1.5, 0.05]} rotation={[0, 0, 0.3]}>
      <mesh position={[0, 0.06, 0]}>
        <cylinderGeometry args={[0.012, 0.02, 0.16, 5]} />
        <meshStandardMaterial color="#5a7d4a" roughness={0.8} />
      </mesh>
      {[-0.5, 0, 0.5].map((rot) => (
        <mesh key={rot} position={[rot * 0.05, 0.13, 0]} rotation={[0.25, 0, rot]}>
          <coneGeometry args={[0.034, 0.1, 5]} />
          <meshStandardMaterial color={accent} roughness={0.75} side={THREE.DoubleSide} />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Macropod biped (quokka / glider / kangaroo / koala): hunched posture,
 * strong hind legs with long feet, small forearms, thick tail base.
 * ~2.9 head-heights tall.
 */
function BipedBody({ species }: BodyProps) {
  const p = species.palette
  // signature variations within the shared macropod skeleton
  const isEmberoo = species.id === 'emberoo' // charcoal "scorched" forearms & feet
  const isGlider = species.id === 'glidewisp' // gliding membrane flaps
  const isKoala = species.id === 'gumdrowse' // big leathery nose
  const limbColor = isEmberoo ? CHARCOAL : p.primary
  const feetColor = isEmberoo ? CHARCOAL : p.secondary
  return (
    <group>
      {/* torso, leaning forward */}
      <mesh position={[0, 0.64, -0.02]} rotation={[-0.22, 0, 0]} scale={[0.42, 0.52, 0.4]} castShadow>
        <sphereGeometry args={[1, 16, 12]} />
        <Fur color={p.primary} />
      </mesh>
      {/* chest / belly patch */}
      <mesh position={[0, 0.6, 0.2]} rotation={[-0.2, 0, 0]} scale={[0.28, 0.38, 0.22]}>
        <sphereGeometry args={[1, 12, 10]} />
        <Fur color={p.secondary} />
      </mesh>
      {/* head — kept distinct from torso, with a real snout */}
      <mesh position={[0, 1.28, 0.12]} castShadow>
        <sphereGeometry args={[0.29, 16, 12]} />
        <Fur color={p.primary} />
      </mesh>
      {/* lighter cheeks/lower face so the face reads at distance */}
      <mesh position={[0, 1.18, 0.22]} scale={[0.22, 0.15, 0.18]}>
        <sphereGeometry args={[1, 12, 10]} />
        <Fur color={p.secondary} />
      </mesh>
      <Muzzle
        position={[0, 1.21, 0.34]}
        scale={isKoala ? [0.15, 0.12, 0.14] : [0.13, 0.11, 0.17]}
        furColor={p.secondary}
        noseR={isKoala ? 0.075 : 0.05}
      />
      <Eyes y={1.35} z={0.385} spread={0.115} r={0.044} />
      {/* short rounded ears */}
      {[-0.18, 0.18].map((x) => (
        <mesh key={x} position={[x, 1.54, 0.04]} scale={[0.085, 0.12, 0.055]}>
          <sphereGeometry args={[1, 10, 8]} />
          <Fur color={p.primary} />
        </mesh>
      ))}
      {species.id === 'nikokka' && <EarSprout accent={p.accent} />}
      {/* small forearms hanging in front of the chest */}
      {[-0.27, 0.27].map((x) => (
        <mesh key={x} position={[x, 0.76, 0.24]} rotation={[0.9, 0, x > 0 ? -0.15 : 0.15]}>
          <capsuleGeometry args={[0.05, 0.24, 4, 8]} />
          <Fur color={limbColor} />
        </mesh>
      ))}
      {/* gliding membrane folds along the flanks (sugar glider) */}
      {isGlider &&
        [-1, 1].map((s) => (
          <mesh
            key={s}
            position={[s * 0.36, 0.58, 0.08]}
            rotation={[0, 0, s * 0.35]}
            scale={[0.035, 0.28, 0.26]}
          >
            <sphereGeometry args={[1, 8, 6]} />
            <Skin color={p.secondary} />
          </mesh>
        ))}
      {/* thighs */}
      {[-0.26, 0.26].map((x) => (
        <mesh key={x} position={[x, 0.4, -0.04]} scale={[0.15, 0.22, 0.24]} castShadow>
          <sphereGeometry args={[1, 12, 10]} />
          <Fur color={p.primary} />
        </mesh>
      ))}
      {/* shins, angled back to the heel */}
      {[-0.27, 0.27].map((x) => (
        <mesh key={x} position={[x, 0.2, 0.04]} rotation={[0.55, 0, 0]}>
          <cylinderGeometry args={[0.055, 0.065, 0.3, 8]} />
          <Fur color={p.primary} />
        </mesh>
      ))}
      {/* long macropod feet */}
      {[-0.25, 0.25].map((x) => (
        <mesh key={x} position={[x, 0.06, 0.16]}>
          <boxGeometry args={[0.15, 0.1, 0.42]} />
          <Fur color={feetColor} />
        </mesh>
      ))}
      {/* tail: thick base, props on the ground behind */}
      <mesh position={[0, 0.3, -0.42]} rotation={[1.05, 0, 0]}>
        <cylinderGeometry args={[0.06, 0.1, 0.55, 8]} />
        <Fur color={p.primary} />
      </mesh>
      {/* tail tip: bare skin; smoldering ember gradient for Emberoo */}
      <mesh position={[0, 0.08, -0.72]} rotation={[1.45, 0, 0]}>
        <cylinderGeometry args={[0.03, 0.06, 0.35, 8]} />
        {isEmberoo ? (
          <meshStandardMaterial
            color={p.accent}
            roughness={0.7}
            emissive={p.accent}
            emissiveIntensity={0.2}
          />
        ) : (
          <Skin color={NOSE_COLOR} />
        )}
      </mesh>
    </group>
  )
}

/**
 * Quadruped with two-segment legs (thigh + shin + paw), proper snout,
 * small ears and a tapering tail. Head only slightly enlarged over real ratio.
 */
function QuadrupedBody({ species }: BodyProps) {
  const p = species.palette
  const isPlatypus = species.id === 'billabog'
  return (
    <group>
      {/* torso */}
      <mesh position={[0, 0.55, 0]} scale={[0.42, 0.38, 0.68]} castShadow>
        <sphereGeometry args={[1, 16, 12]} />
        <Fur color={p.primary} />
      </mesh>
      {/* deeper chest */}
      <mesh position={[0, 0.52, 0.3]} scale={[0.36, 0.34, 0.32]}>
        <sphereGeometry args={[1, 12, 10]} />
        <Fur color={p.primary} />
      </mesh>
      {/* belly */}
      <mesh position={[0, 0.42, 0.02]} scale={[0.32, 0.26, 0.5]}>
        <sphereGeometry args={[1, 12, 10]} />
        <Fur color={p.secondary} />
      </mesh>
      {/* neck + head */}
      <mesh position={[0, 0.74, 0.55]} rotation={[1.0, 0, 0]}>
        <cylinderGeometry args={[0.13, 0.17, 0.3, 10]} />
        <Fur color={p.primary} />
      </mesh>
      <mesh position={[0, 0.86, 0.7]} castShadow>
        <sphereGeometry args={[0.25, 16, 12]} />
        <Fur color={p.primary} />
      </mesh>
      {isPlatypus ? (
        // leathery duck-bill instead of a furred muzzle
        <mesh position={[0, 0.78, 0.95]}>
          <boxGeometry args={[0.26, 0.06, 0.28]} />
          <Skin color={p.secondary} />
        </mesh>
      ) : (
        <Muzzle position={[0, 0.79, 0.9]} scale={[0.11, 0.095, 0.16]} furColor={p.secondary} noseR={0.045} />
      )}
      <Eyes y={0.95} z={0.91} spread={0.1} r={0.04} />
      {/* small natural ears (none for the platypus) */}
      {!isPlatypus &&
        [-0.13, 0.13].map((x) => (
          <mesh key={x} position={[x, 1.07, 0.6]} rotation={[0.25, 0, x > 0 ? 0.18 : -0.18]}>
            <coneGeometry args={[0.07, 0.15, 6]} />
            <Fur color={p.primary} />
          </mesh>
        ))}
      {/* legs: thigh + shin + paw, four of them */}
      {(
        [
          [-0.24, 0.38],
          [0.24, 0.38],
          [-0.24, -0.4],
          [0.24, -0.4],
        ] as const
      ).map(([x, z], i) => (
        <group key={i} position={[x, 0, z]}>
          <mesh position={[0, 0.42, 0]} scale={[0.1, 0.18, 0.13]}>
            <sphereGeometry args={[1, 10, 8]} />
            <Fur color={p.primary} />
          </mesh>
          <mesh position={[0, 0.18, 0]}>
            <cylinderGeometry args={[0.05, 0.06, 0.28, 8]} />
            <Fur color={p.primary} />
          </mesh>
          <mesh position={[0, 0.04, 0.03]}>
            <boxGeometry args={[0.12, 0.07, 0.17]} />
            <Fur color={p.secondary} />
          </mesh>
        </group>
      ))}
      {/* tail: platypus gets a flat paddle, others a tapering two-segment tail */}
      {isPlatypus ? (
        <mesh position={[0, 0.45, -0.8]} rotation={[-0.15, 0, 0]}>
          <boxGeometry args={[0.3, 0.07, 0.45]} />
          <Fur color={p.primary} />
        </mesh>
      ) : (
        <>
          <mesh position={[0, 0.58, -0.72]} rotation={[-1.0, 0, 0]}>
            <cylinderGeometry args={[0.05, 0.08, 0.35, 8]} />
            <Fur color={p.primary} />
          </mesh>
          <mesh position={[0, 0.72, -0.92]} rotation={[-0.6, 0, 0]}>
            <cylinderGeometry args={[0.025, 0.05, 0.3, 8]} />
            <Fur color={p.primary} />
          </mesh>
        </>
      )}
      {/* signature features */}
      {species.id === 'wombolt' &&
        // slate scutes embedded over the rump
        ([
          [0, 0.78, -0.38, 0.13],
          [-0.16, 0.72, -0.46, 0.1],
          [0.16, 0.72, -0.46, 0.1],
          [0, 0.66, -0.58, 0.11],
        ] as const).map(([x, y, z, s], i) => (
          <mesh key={i} position={[x, y, z]} rotation={[0.4, i, 0]} scale={s}>
            <dodecahedronGeometry args={[1, 0]} />
            <meshStandardMaterial color={SLATE} roughness={R_STONE} flatShading />
          </mesh>
        ))}
      {species.id === 'quollast' &&
        // quartz-pebble spots along the back
        ([
          [-0.18, 0.84, 0.1],
          [0.2, 0.82, -0.12],
          [-0.14, 0.8, -0.3],
          [0.12, 0.86, 0.25],
          [0.02, 0.88, -0.05],
        ] as const).map(([x, y, z], i) => (
          <mesh key={i} position={[x, y, z]}>
            <sphereGeometry args={[0.035, 8, 6]} />
            <meshStandardMaterial color={p.accent} roughness={0.3} />
          </mesh>
        ))}
      {species.id === 'quillvolt' &&
        // keratin quills with charged amber tips
        Array.from({ length: 10 }, (_, i) => {
          const a = (i / 10) * Math.PI * 1.5 - Math.PI * 0.75
          const x = Math.sin(a) * 0.32
          const z = -0.1 - Math.cos(a) * 0.25
          return (
            <group key={i} position={[x, 0.82, z]} rotation={[-0.4 - Math.cos(a) * 0.2, 0, x * 1.2]}>
              <mesh>
                <coneGeometry args={[0.035, 0.26, 5]} />
                <Keratin color={p.secondary} />
              </mesh>
              <mesh position={[0, 0.14, 0]}>
                <coneGeometry args={[0.018, 0.08, 5]} />
                <meshStandardMaterial
                  color={p.accent}
                  roughness={0.4}
                  emissive={p.accent}
                  emissiveIntensity={0.25}
                />
              </mesh>
            </group>
          )
        })}
    </group>
  )
}

/**
 * Bird with folded wings, keratin beak, scaly legs.
 * Species variants: cassowary casque, cockatoo crest, emu neck/legs,
 * kookaburra oversized head (all grounded in the real birds).
 */
function BirdBody({ species }: BodyProps) {
  const p = species.palette
  const isEmu = species.id === 'dunestrider'
  const isCassowary = species.id === 'casshelm'
  const isCockatoo = species.id === 'crestoo'
  const isKooka = species.id === 'chucklewing'

  const legH = isEmu || isCassowary ? 0.55 : 0.3
  const headY = isEmu ? 1.65 : isCassowary ? 1.5 : 1.18
  const headR = isKooka ? 0.27 : isEmu ? 0.2 : 0.23
  const bodyY = 0.55 + legH * 0.6

  return (
    <group>
      {/* body */}
      <mesh position={[0, bodyY, 0]} rotation={[0.25, 0, 0]} scale={[0.38, 0.42, 0.5]} castShadow>
        <sphereGeometry args={[1, 16, 12]} />
        <Feather color={p.primary} />
      </mesh>
      {/* breast */}
      <mesh position={[0, bodyY - 0.06, 0.24]} scale={[0.28, 0.32, 0.22]}>
        <sphereGeometry args={[1, 12, 10]} />
        <Feather color={p.secondary} />
      </mesh>
      {/* neck */}
      <mesh
        position={[0, (bodyY + headY) / 2, 0.12]}
        rotation={[0.12, 0, 0]}
        scale={[1, (headY - bodyY) * 1.1, 1]}
      >
        <cylinderGeometry args={[0.07, 0.12, 1, 8]} />
        {/* emu and cassowary have bare-skin necks; others feathered */}
        {isEmu || isCassowary ? (
          <Skin color={isCassowary ? p.secondary : p.accent} />
        ) : (
          <Feather color={p.primary} />
        )}
      </mesh>
      {/* head */}
      <mesh position={[0, headY, 0.16]} castShadow>
        <sphereGeometry args={[headR, 16, 12]} />
        {isCassowary ? <Skin color={p.secondary} /> : <Feather color={p.primary} />}
      </mesh>
      {/* beak — keratin, sized to species */}
      <mesh
        position={[0, headY - 0.03, 0.16 + headR + (isKooka ? 0.12 : 0.06)]}
        rotation={[Math.PI / 2, 0, 0]}
      >
        <coneGeometry args={[isKooka ? 0.085 : 0.06, isKooka ? 0.3 : 0.2, 6]} />
        <Keratin color={isCockatoo ? CHARCOAL : BIRD_LEG} />
      </mesh>
      <Eyes y={headY + 0.06} z={0.16 + headR * 0.85} spread={headR * 0.45} r={0.038} />
      {/* casque: layered slate (cassowary) */}
      {isCassowary && (
        <mesh position={[0, headY + 0.18, 0.1]} rotation={[-0.3, 0, 0]} scale={[0.5, 1, 1]}>
          <coneGeometry args={[0.18, 0.42, 6]} />
          <meshStandardMaterial color={p.accent} roughness={R_STONE} flatShading />
        </mesh>
      )}
      {/* jagged lightning crest (cockatoo only) */}
      {isCockatoo &&
        [0, 1, 2].map((i) => (
          <mesh
            key={i}
            position={[0, headY + 0.17 + i * 0.05, 0.06 - i * 0.09]}
            rotation={[-0.5 - i * 0.35, 0, 0]}
          >
            <coneGeometry args={[0.045, 0.22 - i * 0.04, 5]} />
            <Feather color={p.accent} />
          </mesh>
        ))}
      {/* folded wings along the body (cassowary wings vanish into the plumage) */}
      {[-1, 1].map((s) => (
        <mesh
          key={s}
          position={[s * 0.32, bodyY + 0.04, -0.04]}
          rotation={[0.3, 0, s * 0.25]}
          scale={[0.08, 0.26, 0.36]}
        >
          <sphereGeometry args={[1, 10, 8]} />
          <Feather color={isKooka ? p.accent : isCassowary ? p.primary : p.secondary} />
        </mesh>
      ))}
      {/* tail feathers */}
      <mesh position={[0, bodyY + 0.05, -0.48]} rotation={[1.25, 0, 0]}>
        <coneGeometry args={[0.14, 0.42, 6]} />
        <Feather color={p.secondary} />
      </mesh>
      {/* scaly legs + simple feet */}
      {[-0.12, 0.12].map((x) => (
        <group key={x} position={[x, 0, 0]}>
          <mesh position={[0, legH / 2 + 0.05, 0]}>
            <cylinderGeometry args={[0.032, 0.042, legH, 6]} />
            <Scale color={BIRD_LEG} />
          </mesh>
          <mesh position={[0, 0.035, 0.05]}>
            <boxGeometry args={[0.09, 0.05, 0.18]} />
            <Scale color={BIRD_LEG} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

/**
 * Low crawler (crocodile / frilled lizard): tapering spine segments,
 * flat head, four splayed stub legs, scale material throughout.
 */
function SerpentBody({ species }: BodyProps) {
  const p = species.palette
  const isCroc = species.id === 'snapyle'
  const segments: { z: number; y: number; r: number; color: string }[] = [
    { z: 0.35, y: 0.3, r: 0.26, color: p.primary },
    { z: 0.0, y: 0.28, r: 0.25, color: p.primary },
    { z: -0.34, y: 0.25, r: 0.21, color: p.primary },
    { z: -0.64, y: 0.21, r: 0.16, color: p.primary },
    { z: -0.9, y: 0.17, r: 0.11, color: p.primary },
    { z: -1.1, y: 0.14, r: 0.07, color: p.primary },
  ]
  return (
    <group>
      {segments.map((seg, i) => (
        <mesh key={i} position={[0, seg.y, seg.z]} scale={[1, 0.8, 1.15]} castShadow>
          <sphereGeometry args={[seg.r, 12, 10]} />
          <Scale color={seg.color} />
        </mesh>
      ))}
      {/* waterline two-tone belly */}
      {segments.slice(0, 4).map((seg, i) => (
        <mesh key={i} position={[0, seg.y - 0.08, seg.z]} scale={[0.95, 0.5, 1.1]}>
          <sphereGeometry args={[seg.r, 10, 8]} />
          <Scale color={p.secondary} />
        </mesh>
      ))}
      {/* flat head with eyes on top */}
      <mesh position={[0, 0.3, 0.62]} scale={[0.2, 0.11, 0.3]} castShadow>
        <sphereGeometry args={[1, 12, 10]} />
        <Scale color={p.primary} />
      </mesh>
      <Eyes y={0.4} z={0.6} spread={0.1} r={0.038} />
      {/* nostril bump at the snout tip */}
      <mesh position={[0, 0.32, 0.88]} scale={[0.07, 0.04, 0.06]}>
        <sphereGeometry args={[1, 8, 6]} />
        <Scale color={p.secondary} />
      </mesh>
      {/* four splayed stub legs */}
      {(
        [
          [-0.24, 0.18],
          [0.24, 0.18],
          [-0.2, -0.5],
          [0.2, -0.5],
        ] as const
      ).map(([x, z], i) => (
        <group key={i} position={[x, 0.12, z]}>
          <mesh rotation={[0, 0, x > 0 ? -0.7 : 0.7]}>
            <cylinderGeometry args={[0.045, 0.055, 0.2, 6]} />
            <Scale color={p.primary} />
          </mesh>
          <mesh position={[x > 0 ? 0.08 : -0.08, -0.09, 0.02]}>
            <boxGeometry args={[0.1, 0.05, 0.13]} />
            <Scale color={p.secondary} />
          </mesh>
        </group>
      ))}
      {isCroc
        ? // river-stone osteoderms along the back
          segments.slice(0, 5).map((seg, i) => (
            <mesh
              key={i}
              position={[(i % 2) * 0.08 - 0.04, seg.y + seg.r * 0.62, seg.z]}
              rotation={[0.2, i * 1.3, 0]}
              scale={seg.r * 0.42}
            >
              <dodecahedronGeometry args={[1, 0]} />
              <meshStandardMaterial color={p.accent} roughness={R_STONE} flatShading />
            </mesh>
          ))
        : // frill collar with ember inner pattern (frilled lizard)
          (
            <group position={[0, 0.32, 0.42]} rotation={[Math.PI / 2 - 0.35, 0, 0]}>
              <mesh>
                <torusGeometry args={[0.27, 0.06, 8, 16]} />
                <Scale color={p.primary} />
              </mesh>
              <mesh>
                <torusGeometry args={[0.18, 0.035, 8, 16]} />
                <meshStandardMaterial
                  color={p.accent}
                  roughness={0.5}
                  emissive={p.accent}
                  emissiveIntensity={0.18}
                />
              </mesh>
            </group>
          )}
    </group>
  )
}

/**
 * Turtle: mineral shell with mossy growth, leathery skin, stumpy column legs.
 */
function AquaticBody({ species }: BodyProps) {
  const p = species.palette
  return (
    <group>
      {/* shell dome */}
      <mesh position={[0, 0.42, -0.05]} scale={[0.5, 0.32, 0.58]} castShadow>
        <sphereGeometry args={[1, 16, 12]} />
        <meshStandardMaterial color={p.primary} roughness={0.5} />
      </mesh>
      {/* shell rim */}
      <mesh position={[0, 0.28, -0.05]} scale={[0.56, 0.1, 0.64]}>
        <sphereGeometry args={[1, 12, 8]} />
        <meshStandardMaterial color={SLATE} roughness={R_STONE} />
      </mesh>
      {/* moss cushions in the growth-line grooves */}
      {(
        [
          [0.2, 0.62, -0.18, 0.11],
          [-0.24, 0.58, 0.05, 0.09],
          [0.02, 0.68, -0.32, 0.08],
        ] as const
      ).map(([x, y, z, s], i) => (
        <mesh key={i} position={[x, y, z]} scale={[s, s * 0.5, s]}>
          <sphereGeometry args={[1, 8, 6]} />
          <meshStandardMaterial color={p.accent} roughness={1.0} />
        </mesh>
      ))}
      {/* one tiny fern */}
      <group position={[-0.08, 0.7, -0.15]}>
        {[-0.4, 0.2, 0.7].map((rot) => (
          <mesh key={rot} position={[rot * 0.04, 0.05, 0]} rotation={[0.3, 0, rot]}>
            <coneGeometry args={[0.025, 0.12, 4]} />
            <meshStandardMaterial color={p.accent} roughness={0.8} side={THREE.DoubleSide} />
          </mesh>
        ))}
      </group>
      {/* leathery head on a short neck */}
      <mesh position={[0, 0.38, 0.5]} rotation={[0.9, 0, 0]}>
        <cylinderGeometry args={[0.09, 0.12, 0.22, 8]} />
        <Skin color={p.secondary} />
      </mesh>
      <mesh position={[0, 0.42, 0.62]} castShadow>
        <sphereGeometry args={[0.16, 14, 10]} />
        <Skin color={p.secondary} />
      </mesh>
      <Eyes y={0.48} z={0.74} spread={0.075} r={0.034} />
      {/* stumpy column legs */}
      {(
        [
          [-0.32, 0.28],
          [0.32, 0.28],
          [-0.32, -0.34],
          [0.32, -0.34],
        ] as const
      ).map(([x, z], i) => (
        <mesh key={i} position={[x, 0.12, z]}>
          <cylinderGeometry args={[0.07, 0.09, 0.24, 8]} />
          <Skin color={p.secondary} />
        </mesh>
      ))}
      {/* small tail */}
      <mesh position={[0, 0.3, -0.68]} rotation={[-1.2, 0, 0]}>
        <coneGeometry args={[0.05, 0.16, 6]} />
        <Skin color={p.secondary} />
      </mesh>
    </group>
  )
}

const ARCHETYPE_BODIES = {
  biped: BipedBody,
  quadruped: QuadrupedBody,
  bird: BirdBody,
  serpent: SerpentBody,
  aquatic: AquaticBody,
} as const

interface CreatureModelProps {
  species: CreatureSpecies
  /** subtle idle breathing */
  animate?: boolean
}

export function CreatureModel({ species, animate = true }: CreatureModelProps) {
  const group = useRef<THREE.Group>(null)
  const phase = useRef(species.dexNo * 1.7)

  useFrame((_, delta) => {
    if (!animate || !group.current) return
    phase.current += delta * 1.6
    // breathing, not bouncing — semi-real creatures don't hop in place
    const s = 1 + Math.sin(phase.current) * 0.012
    group.current.scale.set(1, s, 1)
  })

  const Body = ARCHETYPE_BODIES[species.archetype]
  return (
    <group scale={species.size}>
      <group ref={group}>
        <Body species={species} />
      </group>
    </group>
  )
}
