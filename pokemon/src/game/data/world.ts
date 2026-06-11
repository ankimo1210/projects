/** Static layout of the island. All distances in meters, XZ plane. */

export interface CircleZone {
  id: string
  x: number
  z: number
  radius: number
}

export const ISLAND_RADIUS = 60
export const ISLAND_HEIGHT = 2

export const POND: CircleZone = { id: 'pond', x: -20, z: 14, radius: 9 }

export const VILLAGE_CENTER = { x: 20, z: 26 }
export const VILLAGE_RADIUS = 14

export const GRASS_ZONES: CircleZone[] = [
  { id: 'meadow-north', x: 6, z: -30, radius: 12 },
  { id: 'meadow-west', x: -34, z: -10, radius: 10 },
  { id: 'meadow-east', x: 34, z: 4, radius: 11 },
]

/** Wild creature level range per grass zone (north is the beginner meadow). */
export const ZONE_LEVEL_RANGES: Record<string, [number, number]> = {
  'meadow-north': [2, 4],
  'meadow-west': [4, 7],
  'meadow-east': [6, 9],
}

/** Resting well in the village plaza; heals the party. */
export const WELL_POS = { x: VILLAGE_CENTER.x + 1.5, z: VILLAGE_CENTER.z + 1 }

export const PLAYER_SPAWN: [number, number, number] = [8, 2, 14]

/** True if (x, z) is clear of the pond, village and grass zones. */
export function isOpenGround(x: number, z: number, margin = 2): boolean {
  const zones: CircleZone[] = [
    POND,
    { id: 'village', ...VILLAGE_CENTER, radius: VILLAGE_RADIUS },
    ...GRASS_ZONES,
  ]
  return zones.every((zone) => {
    const dx = x - zone.x
    const dz = z - zone.z
    return Math.hypot(dx, dz) > zone.radius + margin
  })
}
