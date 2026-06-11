import { VILLAGE_CENTER } from './world'

export interface NpcDef {
  id: string
  name: string
  /** shirt color, to tell them apart */
  color: string
  position: [number, number]
  /** initial facing angle (radians, around Y) */
  facing: number
  lines: string[]
}

export const NPCS: NpcDef[] = [
  {
    id: 'maro',
    name: 'Elder Maro',
    color: '#7a4fa0',
    position: [VILLAGE_CENTER.x - 2, VILLAGE_CENTER.z - 1],
    facing: Math.PI * 0.75,
    lines: [
      'Welcome to Pebble Hollow, traveler.',
      'The tall grass in the meadows is full of wild creatures.',
      'Walk up to one and you can challenge it — weaken it first, then offer a Friend Link.',
      'Your little Nikokka there is a fine first friend. Treat it well!',
    ],
  },
  {
    id: 'juni',
    name: 'Juni',
    color: '#3a8fa0',
    position: [VILLAGE_CENTER.x + 4, VILLAGE_CENTER.z + 2],
    facing: -Math.PI * 0.5,
    lines: [
      "Oh! You have a creature too? I'm trying to befriend a Moonbilby.",
      'They hop around the north meadow at all hours.',
      'Press C to open your collection book — I want to see it when it\'s full!',
    ],
  },
]

export const NPC_BY_ID: Record<string, NpcDef> = Object.fromEntries(
  NPCS.map((n) => [n.id, n]),
)
