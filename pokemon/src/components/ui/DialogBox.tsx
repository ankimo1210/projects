import { NPC_BY_ID } from '../../game/data/npcs'
import { useGameStore } from '../../game/state/gameStore'
import { ACCENT_DARK, INK_SOFT, keycap, paper } from '../../ui/theme'

export function DialogBox() {
  const mode = useGameStore((s) => s.mode)
  const dialogNpcId = useGameStore((s) => s.dialogNpcId)
  const dialogLineIndex = useGameStore((s) => s.dialogLineIndex)
  const advanceDialog = useGameStore((s) => s.advanceDialog)
  if (mode !== 'dialog' || !dialogNpcId) return null

  const npc = NPC_BY_ID[dialogNpcId]
  const line = npc.lines[dialogLineIndex]
  const isLast = dialogLineIndex === npc.lines.length - 1

  return (
    <div
      style={{
        ...paper,
        position: 'absolute',
        left: '50%',
        bottom: 30,
        transform: 'translateX(-50%)',
        width: 'min(640px, 92vw)',
        padding: '14px 20px',
        cursor: 'pointer',
        userSelect: 'none',
        animation: 'qw-rise-in 0.22s ease-out',
      }}
      onClick={advanceDialog}
    >
      <strong style={{ color: ACCENT_DARK, fontSize: 14, letterSpacing: 0.3 }}>
        {npc.name}
      </strong>
      <div style={{ marginTop: 6, fontSize: 15.5, lineHeight: 1.55 }}>{line}</div>
      <div style={{ textAlign: 'right', fontSize: 12, color: INK_SOFT, marginTop: 8 }}>
        <span style={keycap}>E</span> {isLast ? 'close' : 'continue ▾'}
      </div>
    </div>
  )
}
