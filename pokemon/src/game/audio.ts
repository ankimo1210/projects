/**
 * Procedural audio for Quokka Wilds — no audio assets, everything is
 * synthesized with the Web Audio API.
 *
 * - Two looping chiptune-ish themes (field / battle) driven by a small
 *   lookahead step sequencer.
 * - One-shot SFX for battle events (hit / miss / faint / level-up / link /
 *   flee / heal / encounter).
 * - Mute state persists in localStorage. The AudioContext is created lazily
 *   on the first user gesture (browser autoplay policy), so every public
 *   function is safe to call any time — including from node/vitest, where
 *   everything is a no-op.
 */

const MUTE_KEY = 'quokka-wilds-muted'

type ThemeName = 'field' | 'battle'

/** [step, midiNote, durationInSteps] */
type Note = [number, number, number]

interface Track {
  wave: OscillatorType
  gain: number
  notes: Note[]
}

interface Theme {
  bpm: number
  /** loop length in 8th-note steps */
  steps: number
  tracks: Track[]
  /** noise hat on these steps (mod 8) */
  hatSteps?: number[]
}

// midi helpers: C4 = 60
const FIELD_THEME: Theme = {
  bpm: 104,
  steps: 64,
  tracks: [
    {
      // gentle pentatonic melody
      wave: 'triangle',
      gain: 0.055,
      notes: [
        [0, 64, 2], [2, 67, 2], [4, 69, 2], [6, 67, 2],
        [8, 64, 2], [10, 62, 2], [12, 60, 4],
        [16, 62, 2], [18, 64, 2], [20, 67, 2], [22, 69, 2],
        [24, 67, 6],
        [32, 76, 2], [34, 74, 2], [36, 72, 2], [38, 67, 2],
        [40, 69, 2], [42, 72, 2], [44, 69, 4],
        [48, 67, 2], [50, 64, 2], [52, 62, 2], [54, 64, 2],
        [56, 62, 5],
      ],
    },
    {
      // soft bass roots: C / Am / F / G, twice
      wave: 'sine',
      gain: 0.09,
      notes: [
        [0, 48, 3], [4, 48, 3], [8, 45, 3], [12, 45, 3],
        [16, 41, 3], [20, 41, 3], [24, 43, 3], [28, 43, 3],
        [32, 48, 3], [36, 48, 3], [40, 45, 3], [44, 45, 3],
        [48, 41, 3], [52, 41, 3], [56, 43, 3], [60, 43, 3],
      ],
    },
  ],
}

const BATTLE_THEME: Theme = {
  bpm: 152,
  steps: 32,
  tracks: [
    {
      // driving minor lead riff
      wave: 'square',
      gain: 0.035,
      notes: [
        [0, 69, 1], [2, 72, 1], [4, 76, 2], [7, 74, 1],
        [8, 72, 1], [10, 71, 1], [12, 69, 2],
        [16, 65, 1], [18, 69, 1], [20, 72, 2], [23, 71, 1],
        [24, 67, 1], [26, 71, 1], [28, 76, 3],
      ],
    },
    {
      // pumping eighth-note bass with octave pops: Am Am F G
      wave: 'sawtooth',
      gain: 0.05,
      notes: [
        [0, 45, 1], [1, 45, 1], [2, 57, 1], [3, 45, 1],
        [4, 45, 1], [5, 57, 1], [6, 45, 1], [7, 45, 1],
        [8, 45, 1], [9, 45, 1], [10, 57, 1], [11, 45, 1],
        [12, 45, 1], [13, 57, 1], [14, 45, 1], [15, 45, 1],
        [16, 41, 1], [17, 41, 1], [18, 53, 1], [19, 41, 1],
        [20, 41, 1], [21, 53, 1], [22, 41, 1], [23, 41, 1],
        [24, 43, 1], [25, 43, 1], [26, 55, 1], [27, 43, 1],
        [28, 43, 1], [29, 45, 1], [30, 47, 1], [31, 48, 1],
      ],
    },
  ],
  hatSteps: [0, 2, 4, 6],
}

const THEMES: Record<ThemeName, Theme> = { field: FIELD_THEME, battle: BATTLE_THEME }

interface Engine {
  ctx: AudioContext
  music: GainNode
  sfx: GainNode
  noiseBuffer: AudioBuffer
}

let engine: Engine | null = null
let muted = false
let currentTheme: ThemeName | null = null
let schedulerTimer: ReturnType<typeof setInterval> | null = null
let stepIndex = 0
let nextStepTime = 0

if (typeof window !== 'undefined') {
  try {
    muted = window.localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    muted = false
  }
}

function midiToFreq(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}

function getEngine(): Engine | null {
  return engine
}

/** Create the AudioContext. Call from a user-gesture handler. */
export function unlockAudio(): void {
  if (typeof window === 'undefined' || engine) return
  const Ctx = window.AudioContext
  if (!Ctx) return
  try {
    const ctx = new Ctx()
    const music = ctx.createGain()
    const sfx = ctx.createGain()
    music.gain.value = muted ? 0 : 1
    sfx.gain.value = muted ? 0 : 1
    music.connect(ctx.destination)
    sfx.connect(ctx.destination)
    // 1s of white noise, reused by hats / hit bursts
    const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate)
    const data = noiseBuffer.getChannelData(0)
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1
    engine = { ctx, music, sfx, noiseBuffer }
    if (currentTheme) startScheduler()
  } catch {
    engine = null
  }
}

export function isMuted(): boolean {
  return muted
}

export function setMuted(value: boolean): void {
  muted = value
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(MUTE_KEY, value ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  }
  const e = getEngine()
  if (e) {
    e.music.gain.setTargetAtTime(value ? 0 : 1, e.ctx.currentTime, 0.05)
    e.sfx.gain.value = value ? 0 : 1
  }
}

export function toggleMuted(): boolean {
  setMuted(!muted)
  return muted
}

// ---------------------------------------------------------------- sequencer

function scheduleNote(
  e: Engine,
  wave: OscillatorType,
  freq: number,
  gain: number,
  start: number,
  duration: number,
  dest: GainNode,
): void {
  const osc = e.ctx.createOscillator()
  const g = e.ctx.createGain()
  osc.type = wave
  osc.frequency.value = freq
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(gain, start + 0.01)
  g.gain.setValueAtTime(gain, Math.max(start + 0.01, start + duration - 0.04))
  g.gain.linearRampToValueAtTime(0, start + duration)
  osc.connect(g)
  g.connect(dest)
  osc.start(start)
  osc.stop(start + duration + 0.02)
}

function scheduleHat(e: Engine, start: number): void {
  const src = e.ctx.createBufferSource()
  src.buffer = e.noiseBuffer
  const g = e.ctx.createGain()
  const filter = e.ctx.createBiquadFilter()
  filter.type = 'highpass'
  filter.frequency.value = 6000
  g.gain.setValueAtTime(0.025, start)
  g.gain.exponentialRampToValueAtTime(0.001, start + 0.04)
  src.connect(filter)
  filter.connect(g)
  g.connect(e.music)
  src.start(start)
  src.stop(start + 0.05)
}

function scheduleStep(e: Engine, theme: Theme, step: number, time: number, stepDur: number): void {
  for (const track of theme.tracks) {
    for (const [noteStep, midi, dur] of track.notes) {
      if (noteStep === step) {
        scheduleNote(e, track.wave, midiToFreq(midi), track.gain, time, dur * stepDur * 0.92, e.music)
      }
    }
  }
  if (theme.hatSteps?.includes(step % 8)) scheduleHat(e, time)
}

function startScheduler(): void {
  const e = getEngine()
  if (!e || !currentTheme || schedulerTimer !== null) return
  stepIndex = 0
  nextStepTime = e.ctx.currentTime + 0.1
  schedulerTimer = setInterval(() => {
    const eng = getEngine()
    if (!eng || !currentTheme) return
    const theme = THEMES[currentTheme]
    const stepDur = 60 / theme.bpm / 2 // 8th notes
    while (nextStepTime < eng.ctx.currentTime + 0.3) {
      scheduleStep(eng, theme, stepIndex % theme.steps, nextStepTime, stepDur)
      nextStepTime += stepDur
      stepIndex++
    }
  }, 120)
}

function stopScheduler(): void {
  if (schedulerTimer !== null) {
    clearInterval(schedulerTimer)
    schedulerTimer = null
  }
}

/** Switch the background music (no-op until audio is unlocked). */
export function playTheme(name: ThemeName | null): void {
  if (currentTheme === name) return
  currentTheme = name
  stopScheduler()
  if (name) startScheduler()
}

// --------------------------------------------------------------------- sfx

function blip(
  wave: OscillatorType,
  fromFreq: number,
  toFreq: number,
  duration: number,
  gain = 0.08,
  delay = 0,
): void {
  const e = getEngine()
  if (!e || muted) return
  const start = e.ctx.currentTime + delay
  const osc = e.ctx.createOscillator()
  const g = e.ctx.createGain()
  osc.type = wave
  osc.frequency.setValueAtTime(fromFreq, start)
  osc.frequency.exponentialRampToValueAtTime(Math.max(20, toFreq), start + duration)
  g.gain.setValueAtTime(gain, start)
  g.gain.exponentialRampToValueAtTime(0.001, start + duration)
  osc.connect(g)
  g.connect(e.sfx)
  osc.start(start)
  osc.stop(start + duration + 0.02)
}

function noiseBurst(duration: number, filterFreq: number, gain = 0.12, delay = 0): void {
  const e = getEngine()
  if (!e || muted) return
  const start = e.ctx.currentTime + delay
  const src = e.ctx.createBufferSource()
  src.buffer = e.noiseBuffer
  const filter = e.ctx.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.value = filterFreq
  const g = e.ctx.createGain()
  g.gain.setValueAtTime(gain, start)
  g.gain.exponentialRampToValueAtTime(0.001, start + duration)
  src.connect(filter)
  filter.connect(g)
  g.connect(e.sfx)
  src.start(start)
  src.stop(start + duration + 0.02)
}

function jingle(midis: number[], stepSec: number, wave: OscillatorType = 'square', gain = 0.05): void {
  midis.forEach((midi, i) => {
    blip(wave, midiToFreq(midi), midiToFreq(midi), stepSec * 1.6, gain, i * stepSec)
  })
}

export const sfx = {
  /** wild creature appears — descending alarm sweep */
  encounter(): void {
    blip('sawtooth', 880, 220, 0.3, 0.06)
    blip('sawtooth', 660, 165, 0.3, 0.06, 0.12)
  },
  hit(effective: 'strong' | 'weak' | 'normal'): void {
    if (effective === 'strong') {
      noiseBurst(0.22, 1400, 0.16)
      blip('square', 220, 55, 0.22, 0.1)
    } else if (effective === 'weak') {
      noiseBurst(0.1, 700, 0.07)
    } else {
      noiseBurst(0.14, 1000, 0.11)
      blip('square', 180, 70, 0.16, 0.06)
    }
  },
  miss(): void {
    blip('sine', 300, 700, 0.18, 0.04)
  },
  faint(): void {
    blip('square', 330, 50, 0.5, 0.08)
  },
  xp(): void {
    jingle([76, 79], 0.07, 'square', 0.04)
  },
  levelup(): void {
    jingle([60, 64, 67, 72, 76], 0.09, 'square', 0.05)
  },
  linkSuccess(): void {
    jingle([67, 72, 76, 79, 84], 0.11, 'triangle', 0.08)
  },
  linkFail(): void {
    blip('triangle', 500, 240, 0.3, 0.05)
  },
  fleeSuccess(): void {
    blip('sine', 240, 960, 0.25, 0.06)
  },
  fleeFail(): void {
    blip('square', 200, 140, 0.18, 0.05)
  },
  heal(): void {
    jingle([72, 76, 79, 84], 0.13, 'sine', 0.07)
  },
  winFanfare(): void {
    jingle([72, 72, 72, 76, 79, 84], 0.1, 'square', 0.05)
  },
  loseSting(): void {
    jingle([64, 60, 57, 52], 0.16, 'triangle', 0.06)
  },
}
