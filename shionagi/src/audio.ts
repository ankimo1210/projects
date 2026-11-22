type VoiceKind = 'radio' | 'handset';
export type HarborSound = 'step' | 'run' | 'shot' | 'empty' | 'hit' | 'death' | 'pickup'
  | 'door' | 'bridge' | 'shutter' | 'drag' | 'clear' | VoiceKind;

const voiceFiles: Record<VoiceKind, string> = { radio: 'municipal-broadcast.mp3', handset: 'station-handset.mp3' };
const between = (min: number, max: number) => min + Math.random() * (max - min);
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

type Recording = { output: GainNode; buffer?: AudioBuffer; media?: HTMLAudioElement };
type ActiveVoice = { kind: VoiceKind; source?: AudioBufferSourceNode; media?: HTMLAudioElement };

interface SoundShape {
  hz: number;
  to?: number;
  bends?: readonly [number, number][];
  at?: number;
  length: number;
  volume: number;
  attack?: number;
  release?: number;
}

// Every layer in a cue shares a clock and a position. Short-lived nodes disconnect at their end.
class Cue {
  private readonly time: number;

  constructor(private readonly context: AudioContext, private readonly noiseBuffer: AudioBuffer,
    private readonly output: AudioNode, private readonly live: Set<AudioScheduledSourceNode>, private readonly level = 1) {
    this.time = context.currentTime + 0.004;
  }

  private tune(frequency: AudioParam, shape: SoundShape, start: number) {
    frequency.setValueAtTime(shape.hz, start);
    for (const [time, hz] of shape.bends ?? []) {
      frequency.exponentialRampToValueAtTime(hz, start + time);
    }
    if (shape.to !== undefined) frequency.exponentialRampToValueAtTime(shape.to, start + shape.length);
  }

  private envelope(shape: SoundShape, start: number) {
    const gain = this.context.createGain();
    const attack = Math.min(shape.attack ?? 0.004, shape.length * 0.7);
    const releaseAt = Math.max(attack, shape.length - (shape.release ?? shape.length));
    const peak = Math.max(0.0001, shape.volume * this.level);
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(peak, start + attack);
    if (releaseAt > attack) gain.gain.exponentialRampToValueAtTime(peak * 0.9, start + releaseAt);
    gain.gain.exponentialRampToValueAtTime(0.00004, start + shape.length);
    gain.connect(this.output);
    return gain;
  }

  private releaseOnEnd(source: AudioScheduledSourceNode, ...nodes: AudioNode[]) {
    this.live.add(source);
    source.onended = () => {
      this.live.delete(source);
      source.disconnect();
      for (const node of nodes) node.disconnect();
    };
  }

  tone(wave: OscillatorType, shape: SoundShape) {
    const start = this.time + (shape.at ?? 0);
    const source = this.context.createOscillator();
    source.type = wave;
    this.tune(source.frequency, shape, start);
    const gain = this.envelope(shape, start);
    source.connect(gain);
    this.releaseOnEnd(source, gain);
    source.start(start);
    source.stop(start + shape.length + 0.006);
  }

  noise(type: BiquadFilterType, shape: SoundShape, resonance = 0.7) {
    const start = this.time + (shape.at ?? 0);
    const source = this.context.createBufferSource();
    source.buffer = this.noiseBuffer;
    source.loop = true;
    source.playbackRate.value = between(0.89, 1.13);
    const filter = this.context.createBiquadFilter();
    filter.type = type;
    filter.Q.value = resonance;
    this.tune(filter.frequency, shape, start);
    const gain = this.envelope(shape, start);
    source.connect(filter).connect(gain);
    this.releaseOnEnd(source, filter, gain);
    source.start(start, between(0, this.noiseBuffer.duration));
    source.stop(start + shape.length + 0.006);
  }
}

function rainTexture(context: AudioContext) {
  const rate = 24000;
  const seconds = 6.47;
  const buffer = context.createBuffer(2, Math.round(rate * seconds), rate);
  for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
    const samples = buffer.getChannelData(channel);
    let wash = 0;
    for (let i = 0; i < samples.length; i++) {
      const grain = between(-1, 1);
      wash += (grain - wash) * 0.097;
      samples[i] = 0.34 * grain + 0.91 * wash;
    }
    // Small resonant impacts are embedded at independent positions on each side of the street.
    for (let drop = 0; drop < 173; drop++) {
      const start = Math.floor(between(0, samples.length));
      const length = Math.ceil(between(0.023, 0.084) * rate);
      let phase = 0;
      let step = 2 * Math.PI * between(940, 4380) / rate;
      let energy = between(0.045, 0.22);
      const falloff = Math.exp(-5.1 / length);
      const pitch = Math.exp(-0.51 / length);
      for (let i = 0; i < length; i++) {
        phase += step;
        step *= pitch;
        samples[(start + i) % samples.length] += Math.sin(phase) * energy * Math.min(i / 8, 1);
        energy *= falloff;
      }
    }
  }
  return buffer;
}

function buildRig(context: AudioContext, audible: boolean) {
  const master = context.createGain();
  master.gain.value = audible ? 0.87 : 0;
  const limiter = context.createDynamicsCompressor();
  limiter.threshold.value = -13;
  limiter.knee.value = 10;
  limiter.ratio.value = 4;
  limiter.attack.value = 0.003;
  limiter.release.value = 0.14;
  limiter.connect(master).connect(context.destination);

  const panners = Array.from({ length: 15 }, (_, index) => {
    const pan = context.createStereoPanner();
    pan.pan.value = index / 7 - 1;
    pan.connect(limiter);
    return pan;
  });
  const noise = context.createBuffer(1, 56273, 24000);
  const random = noise.getChannelData(0);
  for (let i = 0; i < random.length; i++) random[i] = between(-1, 1);

  const rain = context.createBufferSource();
  rain.buffer = rainTexture(context);
  rain.loop = true;
  const rainFilter = context.createBiquadFilter();
  rainFilter.type = 'lowpass';
  rainFilter.Q.value = 0.55;
  rainFilter.frequency.value = 1100;
  const rainGain = context.createGain();
  rainGain.gain.value = 0.20;
  rain.connect(rainFilter).connect(rainGain).connect(limiter);
  const gust = context.createOscillator();
  const depth = context.createGain();
  gust.frequency.value = 0.079;
  depth.gain.value = 130;
  gust.connect(depth).connect(rainFilter.detune);
  rain.start();
  gust.start();

  return { context, master, panners, noise, rainFilter, rainGain, effects: new Set<AudioScheduledSourceNode>() };
}

function wetFootfall(cue: Cue, run: boolean, outside: number) {
  const weight = run ? 1.28 : 0.90;
  const wet = 0.17 + outside * 0.83;
  cue.tone('sine', { hz: between(106, 142), to: 49, length: 0.12, volume: 0.22 * weight });
  cue.noise('lowpass', { hz: between(620, 1010), to: 210, length: 0.13, volume: 0.52 * weight });
  cue.noise('bandpass', { at: 0.021, hz: between(1660, 2440), to: 930, length: 0.14, volume: (0.17 + wet * 0.30) * weight }, 0.65);
  cue.noise('highpass', { at: 0.060, hz: 2850, to: 5400, length: run ? 0.19 : 0.14, volume: wet * 0.23 * weight, attack: 0.016 });
  cue.tone('sine', { at: between(0.065, 0.090), hz: between(490, 820), to: 280, length: 0.063, volume: wet * 0.07 });
}

function metalTap(cue: Cue, at: number, hz: number, volume: number) {
  cue.noise('bandpass', { at, hz: hz * 3.6, to: hz * 1.85, length: 0.088, volume: volume * 1.9 }, 0.8);
  cue.tone('triangle', { at, hz, to: hz * 0.95, length: 0.16, volume });
  cue.tone('sine', { at, hz: hz * 2.74, length: 0.091, volume: volume * 0.54 });
}

function shutter(cue: Cue) {
  const pitch = between(235, 305);
  cue.noise('bandpass', { hz: 440, to: 310, length: 0.68, volume: 0.22, attack: 0.06 });
  for (const [at, level] of [[0, 0.16], [0.095, 0.108], [0.17, 0.076], [0.34, 0.12], [0.44, 0.067]]) {
    metalTap(cue, at, pitch * between(0.87, 1.12), level);
  }
}

function bridge(cue: Cue) {
  metalTap(cue, 0, 229, 0.28);
  cue.tone('sine', { at: 0.12, hz: 48, bends: [[0.75, 80], [6.55, 83]], to: 44, length: 7.54, attack: 0.68, release: 0.80, volume: 0.19 });
  cue.tone('triangle', { at: 0.14, hz: 95, bends: [[0.79, 158], [6.58, 162]], to: 80, length: 7.50, attack: 0.74, release: 0.78, volume: 0.069 });
  cue.noise('bandpass', { at: 0.17, hz: 340, bends: [[0.84, 730], [6.33, 690]], to: 240, length: 7.45, attack: 0.73, release: 0.82, volume: 0.22 }, 1.2);
  for (const [at, pitch] of [[1.11, 293], [3.17, 377], [5.64, 319]]) {
    cue.tone('triangle', { at, hz: pitch, bends: [[0.33, pitch * 1.37], [0.60, pitch * 1.21]], to: pitch * 0.92, length: 0.93, volume: 0.086, attack: 0.22, release: 0.32 });
    cue.noise('bandpass', { at: at + 0.05, hz: pitch * 3.95, to: pitch * 2.2, length: 0.74, volume: 0.18, attack: 0.13 }, 3);
  }
  for (let tooth = 0; tooth < 8; tooth++) metalTap(cue, 0.69 + tooth * 0.78, 143 + tooth * 2, 0.044);
  metalTap(cue, 7.55, 167, 0.30);
  metalTap(cue, 7.77, 262, 0.13);
  cue.tone('sine', { at: 7.57, hz: 112, to: 41, length: 0.45, volume: 0.30 });
}

export class HarborAudio {
  onBroadcast?: () => void;
  private rig?: ReturnType<typeof buildRig>;
  private paused = false;
  private muted = false;
  private suspendTimer?: number;
  private outside = 0;
  private leftFoot = false;
  private dropIn = 1;
  private sirenIn = 12;
  private shutterIn = 18;
  private heartbeatIn = 0;
  private radioIn = 2.7;
  private radioGuard = 0;
  private readonly recordings: Partial<Record<VoiceKind, Recording | null>> = {};
  private activeVoice?: ActiveVoice;
  private handsetPending = false;
  private bridgeUntil = -1;
  private dragAfter = -1;

  unlock(): void {
    if (!this.rig) {
      const Context = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Context) return;
      let context: AudioContext;
      try { context = new Context({ latencyHint: 'interactive' }); } catch { return; }
      // Request playback during the trusted gesture, before any fetch or decode can yield.
      void context.resume().catch(() => {});
      this.rig = buildRig(context, !this.paused && !this.muted);
      const prime = context.createBufferSource();
      prime.buffer = context.createBuffer(1, 1, context.sampleRate);
      prime.connect(context.destination);
      prime.onended = () => prime.disconnect();
      prime.start();
      void this.loadVoice('radio', this.rig);
      void this.loadVoice('handset', this.rig);
      this.mixRain();
    } else if (!this.paused && this.rig.context.state !== 'running') {
      void this.rig.context.resume().catch(() => {});
    }
  }

  setMuted(muted: boolean): void {
    if (muted === this.muted) return;
    this.muted = muted;
    if (!muted && !this.paused) this.unlock();
    this.setMaster();
  }

  reset(): void {
    if (this.rig) {
      for (const effect of this.rig.effects) effect.stop();
      this.rig.effects.clear();
    }
    this.activeVoice?.source?.stop();
    this.activeVoice?.media?.pause();
    this.activeVoice = undefined;
    this.handsetPending = false;
    this.radioGuard = 0;
    this.radioIn = 2.7;
    this.dropIn = 1;
    this.sirenIn = 12;
    this.shutterIn = 18;
    this.heartbeatIn = 0;
    this.bridgeUntil = -1;
    this.dragAfter = -1;
    this.leftFoot = false;
    this.outside = 0;
    this.mixRain();
  }

  setPaused(paused: boolean): void {
    if (paused === this.paused) return;
    this.paused = paused;
    if (!this.rig) return;
    const { context } = this.rig;
    window.clearTimeout(this.suspendTimer);
    this.setMaster();
    if (paused) {
      this.activeVoice?.media?.pause();
      this.suspendTimer = window.setTimeout(() => {
        if (this.paused) void context.suspend().catch(() => {});
      }, 70);
    } else {
      void context.resume().catch(() => {});
      const voice = this.activeVoice;
      if (voice?.media) void voice.media.play().catch(() => this.endVoice(voice));
    }
  }

  private setMaster() {
    if (!this.rig) return;
    this.rig.master.gain.setTargetAtTime(this.paused || this.muted ? 0 : 0.87, this.rig.context.currentTime, 0.013);
  }

  private mixRain() {
    if (!this.rig) return;
    const { context, rainFilter, rainGain } = this.rig;
    rainFilter.frequency.setTargetAtTime(1100 + this.outside ** 1.2 * 8200, context.currentTime, 0.24);
    rainGain.gain.setTargetAtTime((0.20 + 0.34 * this.outside) * (this.activeVoice ? 0.36 : 1), context.currentTime, this.activeVoice ? 0.10 : 0.35);
  }

  private cue(pan = 0, level = 1) {
    const { context, noise, panners, effects } = this.rig!;
    return new Cue(context, noise, panners[Math.round((clamp(pan, -1, 1) + 1) * 7)], effects, level);
  }

  private async loadVoice(kind: VoiceKind, rig: ReturnType<typeof buildRig>) {
    const file = `${import.meta.env.BASE_URL}audio/${voiceFiles[kind]}`;
    const output = rig.context.createGain();
    output.connect(rig.panners[kind === 'radio' ? 6 : 7]);
    try {
      const result = await fetch(file);
      if (!result.ok) throw new Error('Broadcast unavailable');
      const buffer = await rig.context.decodeAudioData(await result.arrayBuffer());
      this.recordings[kind] = { buffer, output };
    } catch {
      // A native media decoder can still play the packaged recording on some Web Audio implementations.
      const media = new Audio(file);
      media.preload = 'auto';
      try { rig.context.createMediaElementSource(media).connect(output); } catch {
        this.recordings[kind] = null;
        if (kind === 'handset') this.handsetPending = false;
        return;
      }
      this.recordings[kind] = { media, output };
      media.onerror = () => {
        this.recordings[kind] = null;
        if (this.activeVoice?.kind === kind) this.endVoice(this.activeVoice);
        if (kind === 'handset') this.handsetPending = false;
      };
    }
  }

  private endVoice(voice: ActiveVoice) {
    if (this.activeVoice !== voice) return;
    this.activeVoice = undefined;
    this.mixRain();
  }

  private startVoice(kind: VoiceKind) {
    const clip = this.recordings[kind];
    if (!this.rig || !clip || this.rig.context.state !== 'running' || this.paused || this.muted || this.activeVoice?.kind === kind) return;
    const { context } = this.rig;
    if (this.activeVoice) {
      // The officer on the handheld takes priority over the street loudspeaker.
      if (kind === 'radio') return;
      const previous = this.activeVoice;
      this.recordings[previous.kind]?.output.gain.setTargetAtTime(0, context.currentTime, 0.007);
      previous.source?.stop(context.currentTime + 0.035);
      previous.media?.pause();
    }
    const voice: ActiveVoice = { kind };
    this.activeVoice = voice;
    clip.output.gain.cancelScheduledValues(context.currentTime);
    clip.output.gain.setValueAtTime(0.9, context.currentTime);
    if (kind === 'radio') {
      this.radioGuard = 15;
      this.radioIn = between(63, 76);
    } else {
      this.handsetPending = false;
      this.radioIn = Math.max(this.radioIn, 18);
    }
    this.mixRain();
    if (clip.buffer) {
      const source = context.createBufferSource();
      voice.source = source;
      source.buffer = clip.buffer;
      source.connect(clip.output);
      source.onended = () => { source.disconnect(); this.endVoice(voice); };
      source.start();
      if (kind === 'radio') this.onBroadcast?.();
    } else if (clip.media) {
      const media = clip.media;
      voice.media = media;
      media.onended = () => this.endVoice(voice);
      media.currentTime = 0;
      void media.play().then(() => {
        if (kind === 'radio' && this.activeVoice === voice) this.onBroadcast?.();
      }).catch(() => this.endVoice(voice));
    }
  }

  tick(dt: number, outside: number, danger: number): void {
    if (!this.rig || this.paused) return;
    const elapsed = clamp(dt, 0, 1);
    const exposure = clamp(outside, 0, 1);
    if (Math.abs(exposure - this.outside) > 0.012) {
      this.outside = exposure;
      this.mixRain();
    }
    if (this.muted || this.rig.context.state !== 'running') return;
    this.radioGuard = Math.max(this.radioGuard - elapsed, 0);
    this.radioIn -= elapsed;
    if (this.handsetPending) this.startVoice('handset');
    if (this.radioIn <= 0) this.startVoice('radio');
    this.dropIn -= elapsed;
    if (this.dropIn <= 0) {
      this.dropIn = between(0.57, 1.64) * (1.45 - exposure * 0.44);
      const drip = this.cue(between(-0.93, 0.93), 0.49 + exposure * 0.44);
      drip.tone('sine', { hz: between(650, 1640), to: between(340, 510), length: 0.083, volume: between(0.028, 0.067) });
      drip.noise('bandpass', { hz: between(1900, 3650), to: 1080, length: 0.055, volume: 0.105 }, 1.4);
    }
    this.sirenIn -= elapsed;
    if (this.sirenIn <= 0) {
      this.sirenIn = between(42, 57);
      const far = this.cue(-0.68, (0.40 + exposure * 0.60) * (this.activeVoice ? 0.48 : 1));
      far.tone('triangle', { hz: 239, bends: [[1.84, 379], [2.9, 394], [4.08, 300]], to: 226, length: 5.8, volume: 0.072, attack: 1.5, release: 2.4 });
      far.tone('sine', { at: 0.14, hz: 475, bends: [[1.84, 752], [2.92, 781]], to: 455, length: 5.7, volume: 0.028, attack: 1.6, release: 2.3 });
    }
    this.shutterIn -= elapsed;
    if (this.shutterIn <= 0 && exposure > 0.56) {
      shutter(this.cue(Math.random() < 0.5 ? -0.84 : 0.84, 0.39));
      this.shutterIn = between(17, 29);
    }
    this.heartbeatIn -= elapsed;
    if (danger > 0.51 && this.heartbeatIn <= 0) {
      const threat = clamp(danger, 0, 1);
      this.heartbeatIn = 1.44 - threat * 0.65;
      const beat = this.cue(0, (threat - 0.42) * 1.1);
      beat.tone('sine', { hz: 84, to: 44, length: 0.16, volume: 0.28, attack: 0.018 });
      beat.tone('sine', { at: 0.17, hz: 65, to: 38, length: 0.17, volume: 0.17, attack: 0.019 });
    }
  }

  play(event: HarborSound, pan?: number): void {
    if (event === 'radio') {
      if (!this.activeVoice && this.radioGuard <= 0) { this.radioIn = 0; this.startVoice('radio'); }
      return;
    }
    if (event === 'handset') {
      if (this.activeVoice?.kind !== 'handset' && !this.muted && this.recordings.handset !== null) {
        this.handsetPending = true;
        this.startVoice('handset');
      }
      return;
    }
    if (!this.rig || this.paused || this.muted) return;
    if (event === 'step' || event === 'run') {
      this.leftFoot = !this.leftFoot;
      wetFootfall(this.cue(pan ?? (this.leftFoot ? -0.12 : 0.12)), event === 'run', this.outside);
      return;
    }
    const cue = this.cue(pan);
    const now = this.rig.context.currentTime;
    switch (event) {
      case 'shot':
        cue.noise('lowpass', { hz: 9100, to: 350, length: 0.20, volume: 1.36, attack: 0.001 });
        cue.tone('triangle', { hz: 181, to: 43, length: 0.23, volume: 0.61, attack: 0.002 });
        cue.noise('bandpass', { at: 0.072, hz: 1810, to: 575, length: 0.24, volume: 0.43, attack: 0.008 }, 0.68);
        this.cue(-0.57).noise('bandpass', { at: 0.178, hz: 1160, to: 460, length: 0.32, volume: 0.22 }, 0.78);
        break;
      case 'empty':
        metalTap(cue, 0, between(720, 820), 0.092);
        cue.noise('highpass', { at: 0.026, hz: 2200, length: 0.038, volume: 0.13 });
        break;
      case 'hit':
        cue.noise('lowpass', { hz: 960, to: 145, length: 0.27, volume: 0.79 });
        cue.tone('sine', { hz: 140, to: 42, length: 0.31, volume: 0.48 });
        cue.tone('sine', { at: 0.045, hz: 1780, to: 1520, length: 0.43, volume: 0.045, attack: 0.035 });
        break;
      case 'death':
        cue.noise('lowpass', { hz: 1200, to: 140, length: 1.42, volume: 0.64, attack: 0.04 });
        cue.tone('triangle', { hz: 131, to: 38, length: 1.61, volume: 0.30, attack: 0.08 });
        cue.tone('sine', { at: 0.20, hz: 193, to: 79, length: 1.54, volume: 0.11, attack: 0.15 });
        break;
      case 'pickup':
        cue.noise('bandpass', { hz: 1350, to: 700, length: 0.13, volume: 0.24 }, 1.1);
        metalTap(cue, 0.066, 581, 0.13);
        metalTap(cue, 0.15, 832, 0.080);
        break;
      case 'door':
        metalTap(cue, 0.00, 312, 0.20);
        cue.noise('bandpass', { at: 0.10, hz: 628, to: 980, length: 0.62, volume: 0.29, attack: 0.075 }, 1.8);
        cue.tone('triangle', { at: 0.13, hz: 240, bends: [[0.19, 357]], to: 246, length: 0.46, volume: 0.090, attack: 0.075 });
        cue.noise('lowpass', { at: 0.68, hz: 620, to: 170, length: 0.24, volume: 0.58 });
        break;
      case 'bridge':
        if (now < this.bridgeUntil) return;
        this.bridgeUntil = now + 8.03;
        bridge(cue);
        break;
      case 'shutter':
        shutter(cue);
        this.shutterIn = between(17, 29);
        break;
      case 'drag':
        if (now < this.dragAfter) return;
        this.dragAfter = now + 0.32;
        cue.noise('bandpass', { hz: between(590, 820), to: 293, length: 0.58, volume: 0.42, attack: 0.085, release: 0.29 }, 1.1);
        cue.noise('bandpass', { at: 0.09, hz: 1810, to: 1170, length: 0.37, volume: 0.19, attack: 0.055 }, 2.1);
        cue.tone('triangle', { at: 0.08, hz: between(170, 207), to: 103, length: 0.36, volume: 0.083, attack: 0.08 });
        metalTap(cue, 0.49, 239, 0.082);
        break;
      case 'clear':
        for (const [at, hz] of [[0, 294], [0.36, 392], [0.79, 440]]) {
          cue.tone('sine', { at, hz, length: 1.47, volume: 0.18, attack: 0.06 });
          cue.tone('sine', { at, hz: hz * 2.01, length: 0.80, volume: 0.036, attack: 0.035 });
        }
        break;
    }
  }
}
