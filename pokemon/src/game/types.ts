/** Keyboard control names shared between App (mapping) and Player (reading). */
export const Controls = {
  forward: 'forward',
  back: 'back',
  left: 'left',
  right: 'right',
  interact: 'interact',
} as const

export type ControlName = (typeof Controls)[keyof typeof Controls]
