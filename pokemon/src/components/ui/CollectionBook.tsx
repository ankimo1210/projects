import type { CSSProperties } from 'react'
import { CREATURES, type CreatureSpecies } from '../../game/data/creatures'
import { useGameStore, type CollectionEntry } from '../../game/state/gameStore'
import {
  ACCENT,
  button,
  ELEMENT_COLORS,
  INK,
  INK_SOFT,
  paper,
  PAPER_SHADE,
  SCRIM,
} from '../../ui/theme'

const overlay: CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: SCRIM,
  backdropFilter: 'blur(3px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  animation: 'qw-fade-in 0.2s ease-out',
}

const panel: CSSProperties = {
  ...paper,
  width: 'min(880px, 96vw)',
  maxHeight: '90vh',
  overflowY: 'auto',
  padding: 22,
}

const grid: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(195px, 1fr))',
  gap: 10,
  marginTop: 16,
}

function Card({ species, entry }: { species: CreatureSpecies; entry?: CollectionEntry }) {
  const seen = entry?.seen ?? false
  const recruited = entry?.recruited ?? false
  return (
    <div
      style={{
        background: seen ? '#fffdf6' : PAPER_SHADE,
        borderRadius: 10,
        padding: 12,
        border: recruited
          ? `2px solid ${species.palette.accent}`
          : `1.5px solid rgba(51, 46, 38, 0.3)`,
        opacity: seen ? 1 : 0.62,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            background: seen ? species.palette.primary : '#c9c1ac',
            border: `2px solid ${recruited ? species.palette.accent : 'rgba(51,46,38,0.35)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            color: '#fff',
            textShadow: '0 1px 2px rgba(0,0,0,0.4)',
            flexShrink: 0,
          }}
        >
          {seen ? species.name[0] : '?'}
        </div>
        <div>
          <div style={{ fontSize: 11.5, color: INK_SOFT }}>
            No.{String(species.dexNo).padStart(2, '0')}
          </div>
          <strong style={{ fontSize: 14 }}>{seen ? species.name : '???'}</strong>
        </div>
        {recruited && (
          <span
            style={{
              marginLeft: 'auto',
              fontSize: 11,
              fontWeight: 700,
              background: ACCENT,
              color: '#fff',
              borderRadius: 6,
              padding: '2px 7px',
            }}
          >
            friend
          </span>
        )}
      </div>
      {recruited ? (
        <div style={{ fontSize: 12, marginTop: 9, lineHeight: 1.5 }}>
          <div>
            <span
              style={{
                background: ELEMENT_COLORS[species.element],
                color: '#fff',
                borderRadius: 5,
                padding: '1px 7px',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              {species.element}
            </span>
            <span style={{ color: INK_SOFT, marginLeft: 7 }}>
              inspired by {species.inspiration}
            </span>
          </div>
          <div style={{ marginTop: 5 }}>{species.description}</div>
          <div style={{ marginTop: 5, color: INK_SOFT }}>
            HP {species.baseStats.hp} · ATK {species.baseStats.attack} · DEF{' '}
            {species.baseStats.defense} · SPD {species.baseStats.speed}
          </div>
        </div>
      ) : seen ? (
        <div style={{ fontSize: 12, marginTop: 9, color: INK_SOFT }}>
          Spotted in the wild. Form a Friend Link to learn more.
        </div>
      ) : (
        <div style={{ fontSize: 12, marginTop: 9, color: INK_SOFT }}>Not yet encountered.</div>
      )}
    </div>
  )
}

export function CollectionBook() {
  const mode = useGameStore((s) => s.mode)
  const collection = useGameStore((s) => s.collection)
  const toggleCollection = useGameStore((s) => s.toggleCollection)
  if (mode !== 'collection') return null

  const recruitedCount = Object.values(collection).filter((e) => e.recruited).length

  return (
    <div style={overlay}>
      <div className="qw-scroll" style={panel}>
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <h2 style={{ fontSize: 21, letterSpacing: 0.4, color: INK }}>Collection Book</h2>
          <span style={{ marginLeft: 12, color: INK_SOFT, fontSize: 14 }}>
            {recruitedCount} / {CREATURES.length} friends
          </span>
          <button
            className="qw-btn"
            onClick={toggleCollection}
            style={{ ...button, marginLeft: 'auto' }}
          >
            Close (C)
          </button>
        </div>
        <div style={grid}>
          {CREATURES.map((species) => (
            <Card key={species.id} species={species} entry={collection[species.id]} />
          ))}
        </div>
      </div>
    </div>
  )
}
