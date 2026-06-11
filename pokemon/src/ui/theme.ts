import type { CSSProperties } from 'react'

/**
 * Shared design tokens — "field guide" look: warm cream paper, dark ink
 * borders, one green accent. Every UI surface (HUD, dialog, collection,
 * battle) draws from here so the game reads as one object.
 */

export const INK = '#332e26'
export const INK_SOFT = 'rgba(51, 46, 38, 0.55)'
export const PAPER = 'rgba(249, 245, 235, 0.96)'
export const PAPER_SOLID = '#f9f5eb'
export const PAPER_SHADE = '#efe8d6'
export const ACCENT = '#5a8a3c'
export const ACCENT_DARK = '#46702e'
export const GOLD = '#c9971f'
export const DANGER = '#c4453c'
export const SCRIM = 'rgba(28, 23, 16, 0.55)'

export const ELEMENT_COLORS: Record<string, string> = {
  leaf: '#5a8a3c',
  ember: '#c05a32',
  tide: '#3a6ea5',
  spark: '#b8941c',
  stone: '#7a6a55',
  breeze: '#4f9494',
  neutral: '#777067',
}

/** Cream panel with ink border — the base surface for every UI box. */
export const paper: CSSProperties = {
  background: PAPER,
  border: `2px solid ${INK}`,
  borderRadius: 12,
  color: INK,
  boxShadow: '0 4px 14px rgba(20, 16, 8, 0.28)',
}

/** Standard button on paper. Pair with className="qw-btn" for hover. */
export const button: CSSProperties = {
  ...paper,
  padding: '9px 14px',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 2px 6px rgba(20, 16, 8, 0.22)',
}

/** Floating chip for prompts / hints over the 3D field. */
export const chip: CSSProperties = {
  background: 'rgba(38, 33, 26, 0.72)',
  borderRadius: 10,
  padding: '7px 14px',
  color: '#f5f1e6',
  fontSize: 13.5,
  backdropFilter: 'blur(4px)',
  userSelect: 'none',
}

/** Keyboard key cap, e.g. the E in "Press E to talk". */
export const keycap: CSSProperties = {
  display: 'inline-block',
  background: PAPER_SOLID,
  color: INK,
  border: `1px solid ${INK}`,
  borderBottomWidth: 2.5,
  borderRadius: 5,
  padding: '0 7px',
  margin: '0 2px',
  fontWeight: 700,
  fontSize: 12.5,
  lineHeight: '18px',
}

export function hpColor(ratio: number): string {
  return ratio > 0.5 ? '#56a04c' : ratio > 0.25 ? '#d9a52c' : DANGER
}
