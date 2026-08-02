import { clamp, type AircraftState } from '@b737/shared';

/**
 * State-driven cockpit soundscape (spec §17).
 * Phase 2: when the converted GPL sound set (737-800YV, see
 * THIRD_PARTY_ASSETS.md) is served under /cockpit/sounds/, real samples are
 * used (engine loops, levers, wind, GPWS callouts); otherwise everything
 * falls back to the Milestone-1 synthesized sounds. Levels always follow
 * aircraft state, not UI clicks.
 */

/** Sample files (basenames under /cockpit/sounds/). */
const SAMPLES = {
  click: 'click.wav',
  flaps: 'flaps.wav',
  gear: 'gear.wav',
  wind: 'Wind.wav',
  engineIdle: 'cfm11a.wav',
  engineFull: 'cfm14a.wav',
  apDisconnect: 'Apdisco.wav',
} as const;

const CALLOUT_ALTS = [10, 20, 30, 40, 50, 100, 200, 300, 400, 500, 1000, 2500] as const;

class AudioEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private engineOsc: OscillatorNode | null = null;
  private engineOsc2: OscillatorNode | null = null;
  private engineGain: GainNode | null = null;
  private engineFilter: BiquadFilterNode | null = null;
  private windNoise: AudioBufferSourceNode | null = null;
  private windGain: GainNode | null = null;
  private windFilter: BiquadFilterNode | null = null;
  private rollNoise: AudioBufferSourceNode | null = null;
  private rollGain: GainNode | null = null;
  private prevWow = true;
  private prevGearPos = 1;
  enabled = false;

  // sample-based playback (Phase 2, optional)
  private samples = new Map<string, AudioBuffer>();
  private engineIdleGain: GainNode | null = null;
  private engineFullGain: GainNode | null = null;
  private engineIdleSrc: AudioBufferSourceNode | null = null;
  private engineFullSrc: AudioBufferSourceNode | null = null;
  private windSampleGain: GainNode | null = null;
  private gearSamplePlaying = false;

  /** Must be called from a user gesture (browser autoplay policy). */
  start(): void {
    if (this.ctx) {
      this.enabled = true;
      void this.ctx.resume();
      return;
    }
    const ctx = new AudioContext();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0.5;
    this.master.connect(ctx.destination);

    // Engine: two detuned saws through a lowpass
    this.engineOsc = ctx.createOscillator();
    this.engineOsc.type = 'sawtooth';
    this.engineOsc2 = ctx.createOscillator();
    this.engineOsc2.type = 'sawtooth';
    this.engineFilter = ctx.createBiquadFilter();
    this.engineFilter.type = 'lowpass';
    this.engineFilter.frequency.value = 400;
    this.engineGain = ctx.createGain();
    this.engineGain.gain.value = 0;
    this.engineOsc.connect(this.engineFilter);
    this.engineOsc2.connect(this.engineFilter);
    this.engineFilter.connect(this.engineGain);
    this.engineGain.connect(this.master);
    this.engineOsc.start();
    this.engineOsc2.start();

    // Wind + ground roll: looped noise buffers with filters
    const noiseBuffer = this.makeNoiseBuffer(ctx);
    this.windFilter = ctx.createBiquadFilter();
    this.windFilter.type = 'bandpass';
    this.windFilter.frequency.value = 700;
    this.windGain = ctx.createGain();
    this.windGain.gain.value = 0;
    this.windNoise = this.loopNoise(ctx, noiseBuffer, this.windFilter, this.windGain);

    const rollFilter = ctx.createBiquadFilter();
    rollFilter.type = 'lowpass';
    rollFilter.frequency.value = 140;
    this.rollGain = ctx.createGain();
    this.rollGain.gain.value = 0;
    this.rollNoise = this.loopNoise(ctx, noiseBuffer, rollFilter, this.rollGain);

    this.enabled = true;
    void this.loadSamples(ctx);
  }

  /** Fetch + decode the optional GPL sample set; missing files are fine. */
  private async loadSamples(ctx: AudioContext): Promise<void> {
    const names = [
      ...Object.values(SAMPLES),
      ...CALLOUT_ALTS.map((a) => `altitude-${a}.wav`),
    ];
    await Promise.all(
      names.map(async (name) => {
        try {
          const res = await fetch(`/cockpit/sounds/${name}`);
          if (!res.ok) return;
          const buf = await ctx.decodeAudioData(await res.arrayBuffer());
          this.samples.set(name, buf);
        } catch {
          /* keep synth fallback */
        }
      }),
    );
    this.startSampleLoops(ctx);
  }

  /** Swap synth engine/wind loops for real recordings when available. */
  private startSampleLoops(ctx: AudioContext): void {
    const idle = this.samples.get(SAMPLES.engineIdle);
    const full = this.samples.get(SAMPLES.engineFull);
    if (idle && full && this.master && !this.engineIdleSrc) {
      this.engineIdleGain = ctx.createGain();
      this.engineIdleGain.gain.value = 0.25;
      this.engineFullGain = ctx.createGain();
      this.engineFullGain.gain.value = 0;
      this.engineIdleSrc = this.loopSample(ctx, idle, this.engineIdleGain);
      this.engineFullSrc = this.loopSample(ctx, full, this.engineFullGain);
      this.engineGain?.gain.setValueAtTime(0, ctx.currentTime); // silence synth
    }
    const wind = this.samples.get(SAMPLES.wind);
    if (wind && this.master && !this.windSampleGain) {
      this.windSampleGain = ctx.createGain();
      this.windSampleGain.gain.value = 0;
      this.loopSample(ctx, wind, this.windSampleGain);
      this.windGain?.gain.setValueAtTime(0, ctx.currentTime);
    }
  }

  private loopSample(ctx: AudioContext, buffer: AudioBuffer, gain: GainNode): AudioBufferSourceNode {
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    src.connect(gain);
    gain.connect(this.master!);
    src.start();
    return src;
  }

  /** One-shot sample; returns false when unavailable (caller uses synth). */
  private playSample(name: string, gainValue = 0.6, rate = 1): boolean {
    if (!this.ctx || !this.master || !this.enabled) return false;
    const buffer = this.samples.get(name);
    if (!buffer) return false;
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.playbackRate.value = rate;
    const gain = this.ctx.createGain();
    gain.gain.value = gainValue;
    src.connect(gain).connect(this.master);
    src.start();
    return true;
  }

  /** Radio-altitude callout (GPWS voice) — returns false if no sample. */
  playAltitudeCallout(altFt: number): boolean {
    return this.playSample(`altitude-${altFt}.wav`, 0.9);
  }

  stop(): void {
    this.enabled = false;
    if (this.ctx) void this.ctx.suspend();
  }

  /** Called on every state sample (spec §17 level rules). */
  update(state: AircraftState): void {
    if (!this.enabled || !this.ctx) return;
    const t = this.ctx.currentTime;
    const n1 = (state.engines.left.n1Pct + state.engines.right.n1Pct) / 2;
    const n1Norm = clamp((n1 - 20) / 80, 0, 1);
    const reverse = Math.max(state.engines.left.reverserNorm, state.engines.right.reverserNorm);

    if (this.engineIdleSrc && this.engineIdleGain && this.engineFullGain) {
      // real CFM56 loops: crossfade + pitch by N1
      this.engineIdleGain.gain.setTargetAtTime((1 - n1Norm) * 0.4, t, 0.25);
      this.engineFullGain.gain.setTargetAtTime(n1Norm * (0.5 + reverse * 0.2), t, 0.25);
      this.engineIdleSrc.playbackRate.setTargetAtTime(0.85 + n1Norm * 0.3, t, 0.25);
      this.engineFullSrc?.playbackRate.setTargetAtTime(0.8 + n1Norm * 0.45, t, 0.25);
    } else if (this.engineOsc && this.engineOsc2 && this.engineGain && this.engineFilter) {
      this.engineOsc.frequency.setTargetAtTime(35 + n1Norm * 95, t, 0.2);
      this.engineOsc2.frequency.setTargetAtTime(36.5 + n1Norm * 99, t, 0.2);
      this.engineFilter.frequency.setTargetAtTime(200 + n1Norm * 900 + reverse * 500, t, 0.2);
      this.engineGain.gain.setTargetAtTime(0.05 + n1Norm * 0.3 + reverse * 0.15, t, 0.2);
    }
    const windNorm = clamp(state.speeds.iasKt / 250, 0, 1);
    if (this.windSampleGain) {
      this.windSampleGain.gain.setTargetAtTime(windNorm * windNorm * 0.5, t, 0.3);
    } else if (this.windGain && this.windFilter) {
      this.windGain.gain.setTargetAtTime(windNorm * windNorm * 0.25, t, 0.3);
      this.windFilter.frequency.setTargetAtTime(400 + windNorm * 1200, t, 0.3);
    }
    if (this.rollGain) {
      const rollNorm = state.weightOnWheels ? clamp(state.speeds.gsKt / 150, 0, 1) : 0;
      this.rollGain.gain.setTargetAtTime(rollNorm * 0.35, t, 0.15);
    }
    // touchdown thump on WOW transition
    if (state.weightOnWheels && !this.prevWow && state.speeds.gsKt > 30) {
      this.thump();
    }
    this.prevWow = state.weightOnWheels;
    // gear transit sound (sample once per transit; synth fallback is silent)
    const gearMoving = Math.abs(state.controls.gearPositionNorm - this.prevGearPos) > 0.001;
    if (gearMoving && !this.gearSamplePlaying) {
      this.gearSamplePlaying = this.playSample(SAMPLES.gear, 0.5);
    } else if (!gearMoving) {
      this.gearSamplePlaying = false;
    }
    this.prevGearPos = state.controls.gearPositionNorm;
  }

  /** Switch/lever interaction click (only called after backend accepts). */
  click(kind: 'click' | 'lever' | 'rotary' | 'flap_lever' | 'gear_lever' = 'click'): void {
    if (!this.ctx || !this.master || !this.enabled) return;
    // real samples when available
    if (kind === 'flap_lever' && this.playSample(SAMPLES.flaps, 0.5)) return;
    if (kind === 'gear_lever' && this.playSample(SAMPLES.gear, 0.4, 1.4)) return;
    if (this.playSample(SAMPLES.click, kind === 'rotary' ? 0.35 : 0.5)) return;
    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'square';
    osc.frequency.value = kind === 'click' ? 2200 : kind === 'rotary' ? 1400 : 700;
    gain.gain.setValueAtTime(0.12, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    osc.connect(gain).connect(this.master);
    osc.start(t);
    osc.stop(t + 0.06);
  }

  /** Advisory / warning chime (rule events). */
  chime(severity: 'advisory' | 'warning'): void {
    if (!this.ctx || !this.master || !this.enabled) return;
    const t0 = this.ctx.currentTime;
    const count = severity === 'warning' ? 3 : 1;
    for (let i = 0; i < count; i++) {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 620;
      const t = t0 + i * 0.25;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
      osc.connect(gain).connect(this.master);
      osc.start(t);
      osc.stop(t + 0.24);
    }
  }

  private thump(): void {
    if (!this.ctx || !this.master) return;
    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(80, t);
    osc.frequency.exponentialRampToValueAtTime(35, t + 0.25);
    gain.gain.setValueAtTime(0.6, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
    osc.connect(gain).connect(this.master);
    osc.start(t);
    osc.stop(t + 0.35);
  }

  private gearWhir(): void {
    // subtle: reuse click at low rate — full servo loop omitted in M1
  }

  private makeNoiseBuffer(ctx: AudioContext): AudioBuffer {
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) {
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02; // pinkish
      data[i] = last * 3.5;
    }
    return buffer;
  }

  private loopNoise(
    ctx: AudioContext,
    buffer: AudioBuffer,
    filter: BiquadFilterNode,
    gain: GainNode,
  ): AudioBufferSourceNode {
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    src.connect(filter);
    filter.connect(gain);
    gain.connect(this.master!);
    src.start();
    return src;
  }
}

export const audioEngine = new AudioEngine();
