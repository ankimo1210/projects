/**
 * All creature species data for Quokka Wilds.
 * Every creature is an original design loosely inspired by a real animal
 * (mostly Australian, to match the quokka companion theme).
 */

export type ElementType = 'leaf' | 'ember' | 'tide' | 'spark' | 'stone' | 'breeze' | 'neutral'

export type CreatureArchetype = 'biped' | 'quadruped' | 'bird' | 'serpent' | 'aquatic'

export type HabitatId = 'meadow-north' | 'meadow-west' | 'meadow-east' | 'anywhere'

export interface MoveDef {
  id: string
  name: string
  element: ElementType
  power: number
  accuracy: number // 0..1
}

export interface CreaturePalette {
  primary: string
  secondary: string
  accent: string
}

export interface BaseStats {
  hp: number
  attack: number
  defense: number
  speed: number
}

export interface CreatureSpecies {
  id: string
  dexNo: number
  name: string
  inspiration: string
  element: ElementType
  archetype: CreatureArchetype
  palette: CreaturePalette
  baseStats: BaseStats
  moveIds: [string, string]
  /** 0..1 — base ease of recruiting via Friend Link */
  friendliness: number
  habitat: HabitatId
  /** model scale multiplier */
  size: number
  description: string
}

export const MOVES: Record<string, MoveDef> = {
  pounce: { id: 'pounce', name: 'Pounce', element: 'neutral', power: 9, accuracy: 1.0 },
  headbutt: { id: 'headbutt', name: 'Headbutt', element: 'neutral', power: 12, accuracy: 0.85 },
  nuzzle: { id: 'nuzzle', name: 'Nuzzle', element: 'neutral', power: 7, accuracy: 1.0 },
  leaf_lash: { id: 'leaf_lash', name: 'Leaf Lash', element: 'leaf', power: 11, accuracy: 0.95 },
  seed_flick: { id: 'seed_flick', name: 'Seed Flick', element: 'leaf', power: 9, accuracy: 1.0 },
  ember_spit: { id: 'ember_spit', name: 'Ember Spit', element: 'ember', power: 11, accuracy: 0.95 },
  tail_flare: { id: 'tail_flare', name: 'Tail Flare', element: 'ember', power: 13, accuracy: 0.85 },
  tide_jet: { id: 'tide_jet', name: 'Tide Jet', element: 'tide', power: 11, accuracy: 0.95 },
  bubble_pop: { id: 'bubble_pop', name: 'Bubble Pop', element: 'tide', power: 9, accuracy: 1.0 },
  spark_zap: { id: 'spark_zap', name: 'Spark Zap', element: 'spark', power: 11, accuracy: 0.95 },
  static_fuzz: { id: 'static_fuzz', name: 'Static Fuzz', element: 'spark', power: 9, accuracy: 1.0 },
  stone_toss: { id: 'stone_toss', name: 'Stone Toss', element: 'stone', power: 11, accuracy: 0.95 },
  boulder_roll: { id: 'boulder_roll', name: 'Boulder Roll', element: 'stone', power: 13, accuracy: 0.85 },
  gust_flap: { id: 'gust_flap', name: 'Gust Flap', element: 'breeze', power: 11, accuracy: 0.95 },
  whirl_hop: { id: 'whirl_hop', name: 'Whirl Hop', element: 'breeze', power: 9, accuracy: 1.0 },
}

export const CREATURES: CreatureSpecies[] = [
  {
    id: 'nikokka',
    dexNo: 1,
    name: 'Nikokka',
    inspiration: 'quokka',
    element: 'leaf',
    archetype: 'biped',
    palette: { primary: '#8d7a5f', secondary: '#d9c9a8', accent: '#8fae5d' },
    baseStats: { hp: 44, attack: 12, defense: 10, speed: 12 },
    moveIds: ['leaf_lash', 'nuzzle'],
    friendliness: 0.9,
    habitat: 'anywhere',
    size: 0.85,
    description: 'An ever-smiling companion. Its grin never fades, even mid-battle.',
  },
  {
    id: 'wombolt',
    dexNo: 2,
    name: 'Wombolt',
    inspiration: 'wombat',
    element: 'stone',
    archetype: 'quadruped',
    palette: { primary: '#8a7866', secondary: '#bfae98', accent: '#b08d4f' },
    baseStats: { hp: 56, attack: 11, defense: 15, speed: 6 },
    moveIds: ['boulder_roll', 'headbutt'],
    friendliness: 0.55,
    habitat: 'meadow-west',
    size: 1.0,
    description: 'Digs cube-shaped burrows. Its rump is hard as granite.',
  },
  {
    id: 'quillvolt',
    dexNo: 3,
    name: 'Quillvolt',
    inspiration: 'echidna',
    element: 'spark',
    archetype: 'quadruped',
    palette: { primary: '#6b5a3e', secondary: '#d9c878', accent: '#f5d442' },
    baseStats: { hp: 40, attack: 13, defense: 11, speed: 9 },
    moveIds: ['spark_zap', 'pounce'],
    friendliness: 0.5,
    habitat: 'meadow-east',
    size: 0.75,
    description: 'Static charge gathers on its quills during dry afternoons.',
  },
  {
    id: 'billabog',
    dexNo: 4,
    name: 'Billabog',
    inspiration: 'platypus',
    element: 'tide',
    archetype: 'quadruped',
    palette: { primary: '#5d7a8a', secondary: '#c98e54', accent: '#4f9ed9' },
    baseStats: { hp: 46, attack: 12, defense: 10, speed: 10 },
    moveIds: ['tide_jet', 'nuzzle'],
    friendliness: 0.6,
    habitat: 'meadow-west',
    size: 0.8,
    description: 'Slaps its bill on puddles to forecast rain. Usually wrong.',
  },
  {
    id: 'glidewisp',
    dexNo: 5,
    name: 'Glidewisp',
    inspiration: 'sugar glider',
    element: 'breeze',
    archetype: 'biped',
    palette: { primary: '#9aa7b8', secondary: '#e3e8ee', accent: '#4a5a70' },
    baseStats: { hp: 36, attack: 12, defense: 8, speed: 15 },
    moveIds: ['gust_flap', 'pounce'],
    friendliness: 0.65,
    habitat: 'meadow-north',
    size: 0.65,
    description: 'Rides night breezes between treetops, trailing faint sparkles.',
  },
  {
    id: 'emberoo',
    dexNo: 6,
    name: 'Emberoo',
    inspiration: 'kangaroo',
    element: 'ember',
    archetype: 'biped',
    palette: { primary: '#c4663a', secondary: '#e8b48a', accent: '#e8612f' },
    baseStats: { hp: 50, attack: 15, defense: 9, speed: 12 },
    moveIds: ['tail_flare', 'headbutt'],
    friendliness: 0.45,
    habitat: 'meadow-east',
    size: 1.2,
    description: 'Each hop leaves a fading scorch ring in the grass.',
  },
  {
    id: 'gumdrowse',
    dexNo: 7,
    name: 'Gumdrowse',
    inspiration: 'koala',
    element: 'leaf',
    archetype: 'biped',
    palette: { primary: '#9c9c94', secondary: '#d8d8d0', accent: '#54705a' },
    baseStats: { hp: 48, attack: 10, defense: 13, speed: 5 },
    moveIds: ['seed_flick', 'nuzzle'],
    friendliness: 0.75,
    habitat: 'meadow-north',
    size: 0.8,
    description: 'Sleeps twenty hours a day. Battles count as a nap interruption.',
  },
  {
    id: 'sundingo',
    dexNo: 8,
    name: 'Sundingo',
    inspiration: 'dingo',
    element: 'ember',
    archetype: 'quadruped',
    palette: { primary: '#d49a52', secondary: '#f0d9b0', accent: '#b3431f' },
    baseStats: { hp: 44, attack: 14, defense: 9, speed: 13 },
    moveIds: ['ember_spit', 'pounce'],
    friendliness: 0.4,
    habitat: 'meadow-east',
    size: 0.95,
    description: 'Its howl at dusk sounds like a crackling campfire.',
  },
  {
    id: 'casshelm',
    dexNo: 9,
    name: 'Casshelm',
    inspiration: 'cassowary',
    element: 'stone',
    archetype: 'bird',
    palette: { primary: '#2e3440', secondary: '#4f8a8b', accent: '#d9d3c0' },
    baseStats: { hp: 52, attack: 14, defense: 12, speed: 9 },
    moveIds: ['stone_toss', 'headbutt'],
    friendliness: 0.3,
    habitat: 'meadow-west',
    size: 1.3,
    description: 'The casque on its head can crack riverbed stones.',
  },
  {
    id: 'numbuzz',
    dexNo: 10,
    name: 'Numbuzz',
    inspiration: 'numbat',
    element: 'spark',
    archetype: 'quadruped',
    palette: { primary: '#b3683a', secondary: '#e8cfa0', accent: '#f5d442' },
    baseStats: { hp: 38, attack: 12, defense: 9, speed: 13 },
    moveIds: ['static_fuzz', 'pounce'],
    friendliness: 0.6,
    habitat: 'meadow-east',
    size: 0.7,
    description: 'Its striped back flickers like a loose lightbulb when excited.',
  },
  {
    id: 'quollast',
    dexNo: 11,
    name: 'Quollast',
    inspiration: 'quoll',
    element: 'stone',
    archetype: 'quadruped',
    palette: { primary: '#7d6b5d', secondary: '#cfc0ae', accent: '#e8e3d8' },
    baseStats: { hp: 42, attack: 13, defense: 12, speed: 8 },
    moveIds: ['stone_toss', 'pounce'],
    friendliness: 0.5,
    habitat: 'meadow-west',
    size: 0.75,
    description: 'The pale spots on its coat are actually tiny embedded pebbles.',
  },
  {
    id: 'moonbilby',
    dexNo: 12,
    name: 'Moonbilby',
    inspiration: 'bilby',
    element: 'breeze',
    archetype: 'quadruped',
    palette: { primary: '#aab0c4', secondary: '#e8e6f0', accent: '#6470a0' },
    baseStats: { hp: 38, attack: 11, defense: 9, speed: 14 },
    moveIds: ['whirl_hop', 'nuzzle'],
    friendliness: 0.7,
    habitat: 'meadow-north',
    size: 0.7,
    description: 'Its oversized ears catch whispers carried on the night wind.',
  },
  {
    id: 'frillare',
    dexNo: 13,
    name: 'Frillare',
    inspiration: 'frilled lizard',
    element: 'ember',
    archetype: 'serpent',
    palette: { primary: '#a3552e', secondary: '#e0a060', accent: '#e83b2f' },
    baseStats: { hp: 40, attack: 14, defense: 10, speed: 11 },
    moveIds: ['ember_spit', 'headbutt'],
    friendliness: 0.35,
    habitat: 'meadow-east',
    size: 0.9,
    description: 'Snaps its frill open with a sound like striking a match.',
  },
  {
    id: 'chucklewing',
    dexNo: 14,
    name: 'Chucklewing',
    inspiration: 'kookaburra',
    element: 'breeze',
    archetype: 'bird',
    palette: { primary: '#8d9aa8', secondary: '#e8e2d5', accent: '#4a6fa5' },
    baseStats: { hp: 40, attack: 13, defense: 9, speed: 13 },
    moveIds: ['gust_flap', 'pounce'],
    friendliness: 0.55,
    habitat: 'meadow-north',
    size: 0.75,
    description: 'Laughs before, during, and unfortunately after every battle.',
  },
  {
    id: 'dunestrider',
    dexNo: 15,
    name: 'Dunestrider',
    inspiration: 'emu',
    element: 'breeze',
    archetype: 'bird',
    palette: { primary: '#7a6f5a', secondary: '#b8ad94', accent: '#3e4a5a' },
    baseStats: { hp: 50, attack: 12, defense: 10, speed: 15 },
    moveIds: ['whirl_hop', 'headbutt'],
    friendliness: 0.4,
    habitat: 'meadow-east',
    size: 1.35,
    description: 'Never walks backward. Nobody knows if it can or simply refuses.',
  },
  {
    id: 'snapyle',
    dexNo: 16,
    name: 'Snapyle',
    inspiration: 'crocodile',
    element: 'tide',
    archetype: 'serpent',
    palette: { primary: '#5a7a4e', secondary: '#cfd9a8', accent: '#3a5230' },
    baseStats: { hp: 54, attack: 15, defense: 12, speed: 6 },
    moveIds: ['tide_jet', 'headbutt'],
    friendliness: 0.25,
    habitat: 'meadow-west',
    size: 1.1,
    description: 'Naps with one eye open and both nostrils above the waterline.',
  },
  {
    id: 'shellbrook',
    dexNo: 17,
    name: 'Shellbrook',
    inspiration: 'turtle',
    element: 'tide',
    archetype: 'aquatic',
    palette: { primary: '#4e7a6a', secondary: '#d9c88a', accent: '#5d8a3e' },
    baseStats: { hp: 58, attack: 9, defense: 16, speed: 4 },
    moveIds: ['bubble_pop', 'headbutt'],
    friendliness: 0.65,
    habitat: 'meadow-west',
    size: 0.85,
    description: 'Tiny ferns sprout from the mossy ridges of its shell.',
  },
  {
    id: 'gnashling',
    dexNo: 18,
    name: 'Gnashling',
    inspiration: 'tasmanian devil',
    element: 'ember',
    archetype: 'quadruped',
    palette: { primary: '#3a3338', secondary: '#e8e3d8', accent: '#e8612f' },
    baseStats: { hp: 44, attack: 16, defense: 9, speed: 10 },
    moveIds: ['tail_flare', 'pounce'],
    friendliness: 0.2,
    habitat: 'meadow-east',
    size: 0.8,
    description: 'Grumbles constantly. The grumble smells faintly of smoke.',
  },
  {
    id: 'drowsum',
    dexNo: 19,
    name: 'Drowsum',
    inspiration: 'possum',
    element: 'leaf',
    archetype: 'quadruped',
    palette: { primary: '#9a8ba0', secondary: '#ded5e3', accent: '#8a7340' },
    baseStats: { hp: 42, attack: 11, defense: 10, speed: 11 },
    moveIds: ['leaf_lash', 'nuzzle'],
    friendliness: 0.7,
    habitat: 'meadow-north',
    size: 0.75,
    description: 'Pretends to faint when startled, then peeks to check if it worked.',
  },
  {
    id: 'crestoo',
    dexNo: 20,
    name: 'Crestoo',
    inspiration: 'cockatoo',
    element: 'spark',
    archetype: 'bird',
    palette: { primary: '#ecebe6', secondary: '#f5f4f0', accent: '#f5d442' },
    baseStats: { hp: 38, attack: 13, defense: 8, speed: 14 },
    moveIds: ['spark_zap', 'gust_flap'],
    friendliness: 0.6,
    habitat: 'meadow-north',
    size: 0.7,
    description: 'Raises its crackling yellow crest to mimic a lightning bolt.',
  },
]

export const SPECIES_BY_ID: Record<string, CreatureSpecies> = Object.fromEntries(
  CREATURES.map((c) => [c.id, c]),
)

export const STARTER_SPECIES_ID = 'nikokka'

export function getSpecies(id: string): CreatureSpecies {
  const species = SPECIES_BY_ID[id]
  if (!species) throw new Error(`Unknown species id: ${id}`)
  return species
}
