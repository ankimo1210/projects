import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { getSpecies, MOVES } from '../../game/data/creatures'
import type { BattleEvent, BattleState } from '../../game/battle'
import { useGameStore, type BattleAction } from '../../game/state/gameStore'
import { sfx } from '../../game/audio'
import { ACCENT_DARK, ELEMENT_COLORS, hpColor, INK, paper } from '../../ui/theme'
import { BattleArena } from './BattleArena'
import { emitFx } from './battleFx'

/**
 * Pokémon-style battle presentation. The store resolves a whole turn
 * instantly; this screen replays `battle.events` one by one — arena
 * animations, sounds, HP drain and log lines stay in sync.
 */

const EVENT_STEP_MS = 650
const INTRO_MS = 1000

const infoBox: CSSProperties = {
  ...paper,
  padding: '9px 15px',
  minWidth: 235,
}

const commandButton: CSSProperties = {
  ...paper,
  padding: '12px 12px',
  borderRadius: 10,
  fontSize: 15,
  fontWeight: 600,
  cursor: 'pointer',
  textAlign: 'left',
  boxShadow: '0 2px 6px rgba(20, 16, 8, 0.22)',
}

const OUTCOME_TEXT: Record<string, string> = {
  win: 'You won the battle!',
  lose: 'Your companion is exhausted... you carry it back to rest.',
  recruited: 'A new friend joins your party!',
  fled: 'You got away safely.',
}

function HpBar({ hp, maxHp }: { hp: number; maxHp: number }) {
  const ratio = Math.max(0, hp / maxHp)
  return (
    <div
      style={{
        height: 10,
        background: '#d9d2bf',
        borderRadius: 5,
        marginTop: 6,
        border: `1px solid rgba(51, 46, 38, 0.5)`,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${ratio * 100}%`,
          height: '100%',
          background: hpColor(ratio),
          borderRadius: 4,
          transition: 'width 0.45s ease-out',
        }}
      />
    </div>
  )
}

function InfoBox({
  name,
  level,
  hp,
  maxHp,
  showNumbers,
}: {
  name: string
  level: number
  hp: number
  maxHp: number
  showNumbers: boolean
}) {
  return (
    <div style={infoBox}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15 }}>
        <strong>{name}</strong>
        <span>Lv.{level}</span>
      </div>
      <HpBar hp={hp} maxHp={maxHp} />
      {showNumbers && (
        <div style={{ textAlign: 'right', fontSize: 13, marginTop: 3 }}>
          {Math.max(0, Math.round(hp))} / {maxHp}
        </div>
      )}
    </div>
  )
}

/** Types its log line character by character (remounted via key per line). */
function TypedLine({ text }: { text: string }) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => {
      setCount((c) => {
        if (c >= text.length) {
          clearInterval(timer)
          return c
        }
        return c + 2
      })
    }, 24)
    return () => clearInterval(timer)
  }, [text])
  return <div>{text.slice(0, count)}</div>
}

/** Sequenced replay of one action's events: fx + sfx + hp + log reveal. */
function playEvents(
  events: BattleEvent[],
  setDispHp: (updater: (prev: { player: number; wild: number }) => { player: number; wild: number }) => void,
  revealLine: () => void,
  timers: ReturnType<typeof setTimeout>[],
): number {
  events.forEach((event, i) => {
    timers.push(
      setTimeout(() => {
        revealLine()
        switch (event.kind) {
          case 'hit': {
            const attacker = event.target === 'wild' ? 'player' : 'wild'
            emitFx({ type: 'lunge', side: attacker })
            timers.push(
              setTimeout(() => {
                emitFx({ type: 'flinch', side: event.target })
                sfx.hit(event.effective)
                setDispHp((prev) => ({ ...prev, [event.target]: event.hp }))
              }, 240),
            )
            break
          }
          case 'miss': {
            emitFx({ type: 'lunge', side: event.attacker })
            timers.push(
              setTimeout(() => {
                emitFx({ type: 'dodge', side: event.attacker === 'player' ? 'wild' : 'player' })
                sfx.miss()
              }, 240),
            )
            break
          }
          case 'faint':
            emitFx({ type: 'faint', side: event.target })
            sfx.faint()
            break
          case 'link':
            if (event.success) {
              emitFx({ type: 'hop', side: 'wild' })
              sfx.linkSuccess()
            } else {
              sfx.linkFail()
            }
            break
          case 'flee':
            if (event.success) sfx.fleeSuccess()
            else sfx.fleeFail()
            break
          case 'xp':
            sfx.xp()
            break
          case 'levelup':
            sfx.levelup()
            break
        }
      }, i * EVENT_STEP_MS),
    )
  })
  return events.length * EVENT_STEP_MS + 250
}

function BattleInner({ battle }: { battle: BattleState }) {
  const battleAction = useGameStore((s) => s.battleAction)
  const closeBattle = useGameStore((s) => s.closeBattle)

  const [busy, setBusy] = useState(true)
  const [showOutcome, setShowOutcome] = useState(false)
  const [shownLines, setShownLines] = useState(1)
  const [dispHp, setDispHp] = useState({ player: battle.player.hp, wild: battle.wild.hp })
  const [introDone, setIntroDone] = useState(false)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  // intro: flash transition + encounter sting, then enable commands
  useEffect(() => {
    const pending = timers.current
    sfx.encounter()
    const t1 = setTimeout(() => setIntroDone(true), 700)
    const t2 = setTimeout(() => setBusy(false), INTRO_MS)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      for (const t of pending) clearTimeout(t)
    }
  }, [])

  const act = (action: BattleAction) => {
    if (busy) return
    setBusy(true)
    battleAction(action)
    const fresh = useGameStore.getState().battle
    if (!fresh) return
    const total = playEvents(
      fresh.events,
      setDispHp,
      () => setShownLines((n) => Math.min(n + 1, fresh.log.length)),
      timers.current,
    )
    timers.current.push(
      setTimeout(() => {
        setDispHp({ player: fresh.player.hp, wild: fresh.wild.hp })
        setShownLines(fresh.log.length)
        if (fresh.outcome === 'ongoing') {
          setBusy(false)
        } else {
          if (fresh.outcome === 'win') sfx.winFanfare()
          if (fresh.outcome === 'lose') sfx.loseSting()
          setShowOutcome(true)
        }
      }, total),
    )
  }

  const visibleLog = battle.log.slice(0, shownLines).slice(-3)
  const wildSpecies = getSpecies(battle.wild.speciesId)

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <BattleArena
        playerSpeciesId={battle.player.speciesId}
        wildSpeciesId={battle.wild.speciesId}
      />

      {/* wild info — top left, like the classic enemy box */}
      <div style={{ position: 'absolute', top: 18, left: 18 }}>
        <InfoBox
          name={battle.wild.name}
          level={battle.wild.level}
          hp={dispHp.wild}
          maxHp={battle.wild.maxHp}
          showNumbers={false}
        />
        <div
          style={{
            marginTop: 4,
            fontSize: 12,
            color: '#fff',
            textShadow: '0 1px 2px rgba(0,0,0,0.6)',
            paddingLeft: 4,
          }}
        >
          <span
            style={{
              background: ELEMENT_COLORS[wildSpecies.element],
              borderRadius: 6,
              padding: '1px 8px',
            }}
          >
            {wildSpecies.element}
          </span>
        </div>
      </div>

      {/* player info — above the message box on the right */}
      <div style={{ position: 'absolute', right: 18, bottom: 170 }}>
        <InfoBox
          name={battle.player.name}
          level={battle.player.level}
          hp={dispHp.player}
          maxHp={battle.player.maxHp}
          showNumbers
        />
      </div>

      {/* bottom panel: message box + commands */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          gap: 12,
          padding: 14,
          background: 'rgba(36, 30, 23, 0.92)',
          borderTop: `3px solid ${INK}`,
          minHeight: 130,
          boxSizing: 'border-box',
        }}
      >
        <div
          style={{
            ...paper,
            flex: 1.4,
            padding: '10px 16px',
            fontSize: 15,
            lineHeight: 1.55,
          }}
        >
          {visibleLog.map((line, i) =>
            i === visibleLog.length - 1 ? (
              <TypedLine key={`${shownLines}-${i}`} text={line} />
            ) : (
              <div key={`${shownLines}-${i}`} style={{ opacity: 0.65 }}>
                {line}
              </div>
            ),
          )}
        </div>

        {!showOutcome ? (
          <div
            style={{
              flex: 1,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
            }}
          >
            {battle.player.moveIds.map((moveId) => {
              const move = MOVES[moveId]
              return (
                <button
                  key={moveId}
                  className="qw-btn"
                  style={{ ...commandButton, opacity: busy ? 0.55 : 1 }}
                  disabled={busy}
                  onClick={() => act({ type: 'move', moveId })}
                >
                  {move.name}
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: ELEMENT_COLORS[move.element],
                    }}
                  >
                    {move.element} · pw {move.power}
                  </div>
                </button>
              )
            })}
            <button
              className="qw-btn"
              style={{
                ...commandButton,
                background: 'rgba(219, 235, 207, 0.96)',
                opacity: busy ? 0.55 : 1,
              }}
              disabled={busy}
              onClick={() => act({ type: 'link' })}
            >
              Friend Link
              <div style={{ fontSize: 11, fontWeight: 600, color: ACCENT_DARK }}>befriend</div>
            </button>
            <button
              className="qw-btn"
              style={{
                ...commandButton,
                background: 'rgba(238, 224, 205, 0.96)',
                opacity: busy ? 0.55 : 1,
              }}
              disabled={busy}
              onClick={() => act({ type: 'flee' })}
            >
              Run
              <div style={{ fontSize: 11, fontWeight: 600, color: '#9a6a3c' }}>escape</div>
            </button>
          </div>
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              gap: 10,
            }}
          >
            <strong style={{ color: '#f5f1e6', fontSize: 16 }}>
              {OUTCOME_TEXT[battle.outcome] ?? ''}
            </strong>
            <button
              className="qw-btn"
              style={{ ...commandButton, textAlign: 'center', fontSize: 16 }}
              onClick={closeBattle}
            >
              Continue
            </button>
          </div>
        )}
      </div>

      {/* encounter transition: white flash + closing iris feel */}
      {!introDone && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: '#fff',
            animation: 'qw-battle-flash 0.7s ease-out forwards',
            pointerEvents: 'none',
          }}
        />
      )}
      <style>{`
        @keyframes qw-battle-flash {
          0% { opacity: 1; }
          35% { opacity: 0.2; }
          55% { opacity: 0.85; }
          100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}

export function BattleScreen() {
  const battle = useGameStore((s) => s.battle)
  const battleSpawnKey = useGameStore((s) => s.battleSpawnKey)
  if (!battle) return null
  // remount per encounter so presentation state resets
  return <BattleInner key={battleSpawnKey ?? 0} battle={battle} />
}
