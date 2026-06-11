# Quokka Wilds — MVP Spec

Original 3D monster-collection web game prototype. No Pokémon/Nintendo assets,
names, UI, sounds, balls, or copied mechanics.

## Stack

- Vite + React + TypeScript
- React Three Fiber + Drei + @react-three/rapier
- Zustand for global game state
- localStorage save (no backend, no login, no API keys)
- Runtime: WSL Ubuntu, browser

## Goal — playable browser MVP

1. Small 3D island field
2. Third-person player movement with WASD
3. Follow camera
4. Simple terrain, trees, rocks, pond, small village
5. Two NPCs with short dialog
6. 20 animal-inspired original creatures
7. Main companion based on a quokka, named Nikokka
8. Wild creature spawning in grass zones
9. Proximity encounter
10. Simple 1v1 turn-based battle
11. Recruit/capture mechanic called Friend Link
12. Collection book UI
13. localStorage save/load

## Implementation rules

- TypeScript types everywhere
- Small components
- All creature data in `src/game/data/creatures.ts`
- Procedural low-poly models (no external 3D files)
- Zustand for global game state
- @react-three/rapier for colliders
- npm scripts: dev, build, test, lint
- After each phase: `npm run build`, fix errors
- Simple working gameplay over visual polish

## Phases

1. Scaffold and 3D field movement
2. Creature data and procedural models
3. Encounter and battle system
4. Collection book and save system
5. Polish HUD, dialog, balancing

## Acceptance criteria

- `npm install` succeeds
- `npm run dev` launches
- Player can walk in 3D field
- At least 5 visible wild creatures spawn
- Encounter opens battle UI
- Battle can end in win/lose/run/recruit
- Recruited creatures appear in collection book
- Refreshing page keeps save data
