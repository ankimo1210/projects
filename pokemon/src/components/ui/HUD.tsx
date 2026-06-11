import { useState, type CSSProperties } from 'react'
import { NPC_BY_ID } from '../../game/data/npcs'
import { CREATURES, getSpecies } from '../../game/data/creatures'
import { maxHpOf, useGameStore, type PartyMember } from '../../game/state/gameStore'
import { isMuted, toggleMuted } from '../../game/audio'
import { ACCENT, button, chip, hpColor, INK, keycap, PAPER } from '../../ui/theme'

const titleStyle: CSSProperties = {
  position: 'absolute',
  top: 14,
  left: 16,
  color: '#fdfaf2',
  userSelect: 'none',
  pointerEvents: 'none',
}

const promptStyle: CSSProperties = {
  ...chip,
  position: 'absolute',
  left: '50%',
  bottom: 38,
  transform: 'translateX(-50%)',
  animation: 'qw-rise-in 0.25s ease-out',
}

function PartyCard({
  member,
  active,
  onClick,
}: {
  member: PartyMember
  active: boolean
  onClick: () => void
}) {
  const species = getSpecies(member.speciesId)
  const max = maxHpOf(member)
  const ratio = member.hp / max
  return (
    <button
      className="qw-btn"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 9,
        padding: '7px 11px',
        borderRadius: 11,
        border: active ? `2px solid ${ACCENT}` : `2px solid rgba(51, 46, 38, 0.45)`,
        background: PAPER,
        color: INK,
        cursor: 'pointer',
        opacity: member.hp <= 0 ? 0.55 : 1,
        minWidth: 158,
        boxShadow: active
          ? '0 3px 10px rgba(20, 16, 8, 0.3)'
          : '0 2px 6px rgba(20, 16, 8, 0.2)',
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: species.palette.primary,
          border: `2px solid ${species.palette.accent}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          fontWeight: 700,
          color: '#fff',
          textShadow: '0 1px 2px rgba(0,0,0,0.4)',
          flexShrink: 0,
        }}
      >
        {species.name[0]}
      </div>
      <div style={{ textAlign: 'left', flex: 1 }}>
        <div style={{ fontSize: 12.5, fontWeight: 700 }}>
          {species.name}{' '}
          <span style={{ opacity: 0.6, fontWeight: 500 }}>Lv.{member.level}</span>
        </div>
        <div
          style={{
            height: 6,
            background: '#d9d2bf',
            borderRadius: 3,
            marginTop: 4,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.max(0, ratio) * 100}%`,
              height: '100%',
              background: hpColor(ratio),
              borderRadius: 3,
              transition: 'width 0.4s ease-out',
            }}
          />
        </div>
      </div>
    </button>
  )
}

export function HUD() {
  const mode = useGameStore((s) => s.mode)
  const collection = useGameStore((s) => s.collection)
  const party = useGameStore((s) => s.party)
  const activeUid = useGameStore((s) => s.activeUid)
  const nearbyNpcId = useGameStore((s) => s.nearbyNpcId)
  const nearWell = useGameStore((s) => s.nearWell)
  const notice = useGameStore((s) => s.notice)
  const toggleCollection = useGameStore((s) => s.toggleCollection)
  const setActive = useGameStore((s) => s.setActive)

  const friends = Object.values(collection).filter((e) => e.recruited).length
  const [muted, setMuted] = useState(isMuted)

  return (
    <>
      <div style={titleStyle}>
        <div
          style={{
            fontSize: 23,
            fontWeight: 800,
            letterSpacing: 0.6,
            textShadow: '0 1px 0 rgba(0,0,0,0.45), 0 2px 8px rgba(0,0,0,0.35)',
          }}
        >
          Quokka Wilds
        </div>
        <div style={{ ...chip, marginTop: 7, fontSize: 12, padding: '5px 10px' }}>
          WASD move · E talk / rest · C collection · M sound
        </div>
      </div>

      {mode === 'explore' && (
        <div style={{ position: 'absolute', top: 14, right: 14, display: 'flex', gap: 8 }}>
          <button
            className="qw-btn"
            onClick={() => setMuted(toggleMuted())}
            aria-label="toggle sound"
            style={{ ...button, padding: '8px 12px' }}
          >
            {muted ? '🔇' : '🔊'}
          </button>
          <button className="qw-btn" onClick={toggleCollection} style={button}>
            Collection{' '}
            <span style={{ color: ACCENT, fontWeight: 700 }}>
              {friends}/{CREATURES.length}
            </span>
          </button>
        </div>
      )}

      {/* party strip — click a card to make that creature the companion */}
      {mode === 'explore' && (
        <div
          style={{
            position: 'absolute',
            left: 14,
            bottom: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 7,
          }}
        >
          {party.map((member) => (
            <PartyCard
              key={member.uid}
              member={member}
              active={member.uid === activeUid}
              onClick={() => setActive(member.uid)}
            />
          ))}
        </div>
      )}

      {/* transient toast */}
      {notice && (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 66,
            transform: 'translateX(-50%)',
            background: PAPER,
            border: `2px solid ${INK}`,
            borderLeft: `5px solid ${ACCENT}`,
            borderRadius: 10,
            padding: '10px 18px',
            color: INK,
            fontSize: 14,
            fontWeight: 600,
            boxShadow: '0 4px 14px rgba(20, 16, 8, 0.3)',
            userSelect: 'none',
            pointerEvents: 'none',
            animation: 'qw-pop-in 0.25s ease-out',
          }}
        >
          {notice}
        </div>
      )}

      {mode === 'explore' && nearbyNpcId && (
        <div style={promptStyle}>
          Press <span style={keycap}>E</span> to talk to {NPC_BY_ID[nearbyNpcId].name}
        </div>
      )}
      {mode === 'explore' && !nearbyNpcId && nearWell && (
        <div style={promptStyle}>
          Press <span style={keycap}>E</span> to rest your party at the well
        </div>
      )}
    </>
  )
}
