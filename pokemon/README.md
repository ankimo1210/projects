# Quokka Wilds

An original 3D monster-collection web game prototype. Explore a small island,
meet wild creatures in the tall grass, battle them, and befriend them with
**Friend Link**. Your companion is **Nikokka**, an ever-smiling quokka-inspired
creature.

All creatures, names, and mechanics are original. No external 3D assets — every
model is procedural low-poly built from primitives.

## Stack

- Vite + React 19 + TypeScript
- React Three Fiber + Drei (3D), @react-three/rapier (physics)
- Zustand (state) with localStorage persistence
- Web Audio API — all music and SFX are synthesized at runtime (no audio files)
- Vitest (logic tests), Playwright (E2E acceptance)

## Run

```bash
npm install
npm run dev      # http://localhost:5173
```

| Script          | What it does                  |
| --------------- | ----------------------------- |
| `npm run dev`   | dev server                    |
| `npm run build` | type-check + production build |
| `npm test`      | vitest (battle/store/data)    |
| `npm run lint`  | eslint                        |

## Controls

- **WASD / arrows** — move
- **E / Space** — talk to NPC, advance dialog, rest at the well
- **C** — collection book
- **M** — sound on/off (also a 🔊 button top-right)
- Walk close to a wild creature in tall grass to start a battle.

## Gameplay

- 20 original creatures (`src/game/data/creatures.ts`), each inspired by a real
  (mostly Australian) animal, with element, stats, moves, and habitat.
- Elements: two effectiveness triangles — leaf > tide > ember > leaf and
  spark > breeze > stone > spark (×1.5 / ×0.75).
- Battle: 1v1 turn-based. Attack, **Friend Link** (recruit — easier when the
  wild creature is weakened), or **Run** (speed-dependent).
- **Battle scene**: encounters open a dedicated 3D arena — your creature seen
  from behind, the wild one across the clearing. Turns replay as sequenced
  events (`battle.events`): lunge / flinch / dodge / faint animations, synced
  HP drain, and a typed-out message box.
- **Music & SFX**: a field theme and a battle theme play from a procedural
  step sequencer; battle events trigger synthesized SFX (hits by
  effectiveness, miss, faint, XP, level-up fanfare, Friend Link jingle,
  flee, heal). Audio starts on the first input (autoplay policy) and the
  mute state persists.
- **Levels & XP** (`src/game/progression.ts`): winning or recruiting grants XP;
  level-ups scale stats (level 1 = base stats, max 30). Wild levels depend on
  the zone: north meadow Lv2-4, west Lv4-7, east Lv6-9.
- **Party**: recruits join your party (max 6) at their wild level, keeping the
  HP they had in battle. Click a party card (bottom-left) to change the active
  companion — it fights and follows you in the field. If the active creature
  faints, the next healthy one takes the lead; a total wipe gets you carried
  back and healed.
- **Resting**: HP persists between battles; press E at the village well to
  fully heal the party.
- Collection book tracks seen/recruited; party, levels and collection persist
  across reloads (localStorage key `quokka-wilds-save`).

## Art direction

Semi-real creature design (70% real animal / 30% fantasy) — see
`docs/character-design.md` for the full direction, per-creature specs, and 3D
production rules. Models are still primitive-based but follow real skeletal
proportions, small dark eyes, natural palettes, and roughness-based material
contrast (fur / skin / keratin / scale).

Dev model viewer: `/?gallery=1` shows all 20 creatures;
`/?gallery=1&focus=<speciesId>` for a single-creature close-up.

## Layout

```
src/
  game/
    data/        creatures, world layout, NPCs
    state/       zustand store (modes, battle, collection, spawns)
    battle.ts    pure turn logic + events (rng injected, unit-tested)
    audio.ts     procedural BGM sequencer + synthesized SFX
  components/
    world/       island, trees, rocks, pond, village, grass zones
    player/      rapier capsule + WASD + follow camera
    creatures/   procedural models, companion, wild spawns
    npc/         villagers + proximity talk
    battle/ ui/  3D battle arena + screen, collection book, dialog, HUD
e2e/verify_mvp.py  Playwright acceptance script (17 checks)
```

## E2E acceptance

```bash
# requires python playwright (uv workspace) + chromium
uv run python <webapp-testing-skill>/scripts/with_server.py \
  --server "npm run dev" --port 5173 -- uv run python e2e/verify_mvp.py
```

Verifies: load/canvas, ≥5 wild spawns, WASD movement, proximity encounter,
battle outcomes (win/flee/recruit), collection book, save survives reload.
