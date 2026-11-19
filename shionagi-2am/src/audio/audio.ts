// Everything you hear is synthesised here with the Web Audio API: there are no
// sample files. Sounds made by the drowned are placed in the world (panned,
// attenuated with distance and muffled when a wall is in the way) because the
// game leans on hearing them before seeing them.

import type { Sim } from "../sim/sim";
import type { SimEvent, Surface, VocalKind } from "../sim/types";

export interface Listener {
  /** camera position */
  x: number;
  y: number;
  z: number;
  yaw: number;
  /** 0 outdoors .. 1 under a roof */
  indoor: number;
}

interface Pos {
  x: number;
  y: number;
  z: number;
}

type NoiseKind = "white" | "pink" | "brown";

const MASTS: Pos[] = [
  { x: 12.9, y: 7, z: -18.2 },
  { x: -4.45, y: 7, z: -104.9 },
];

/** The announcement, spelt so that a speech synthesiser reads the town's name correctly. */
const ANNOUNCE = "こちらは、防災しおなぎです。高潮と大雨のため、避難指示が出ています。避難先は、しおなぎ警察署です。";

/** Levels of the rain beds. Everything else is balanced against these. */
const RAIN = { hiss: 0.05, roar: 0.12, drips: 0.075, roof: 0.07, pane: 0.035 };

function hash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return ((h >>> 0) % 1000) / 1000;
}

const rnd = (a: number, b: number): number => a + Math.random() * (b - a);

export class AudioEngine {
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private tone!: BiquadFilterNode;
  private dry!: GainNode;
  private world!: GainNode;
  private amb!: GainNode;
  private revOut!: ConvolverNode;
  private revIn!: ConvolverNode;
  private sendOut!: GainNode;
  private sendIn!: GainNode;
  private analyser!: AnalyserNode;
  private buffers: Partial<Record<NoiseKind, AudioBuffer>> = {};
  private drips: AudioBuffer | null = null;
  private scope: Float32Array<ArrayBuffer> | null = null;

  private rainOut!: GainNode;
  private rainIn!: GainNode;
  private rainTone!: BiquadFilterNode;
  private windGain!: GainNode;
  private floodGain!: GainNode;
  private sluiceGain!: GainNode;
  private sirenGain!: GainNode;
  private droneGain!: GainNode;
  private dreadGain!: GainNode;

  private lis: Listener = { x: 0, y: 1.6, z: 0, yaw: 0, indoor: 1 };
  private started = false;
  private paused = false;
  private ended = false;
  private time = 0;
  private sirenT = 14;
  private sirenOn = false;
  private radioT = 5;
  private creakT = 9;
  private beatT = 0;
  private danger = 0;
  private bridge: { stop: () => void } | null = null;
  private bridgeTick = 0;
  private voice: SpeechSynthesisVoice | null = null;
  private tts = true;
  private ttsVolume = 1;
  private peakHold = 0;
  private recentSteps: number[] = [];
  /** how many times each kind of sound was started (tests read this) */
  readonly counts: Record<string, number> = {};

  constructor() {
    try {
      const q = new URLSearchParams(location.search);
      if (q.get("tts") === "0") this.tts = false;
      if (q.get("tts") === "silent") this.ttsVolume = 0; // goes through the motions, for tests
    } catch {
      // not in a browser
    }
  }

  // ------------------------------------------------------------ set-up

  start(): void {
    if (this.started) {
      void this.ctx?.resume();
      return;
    }
    const AC: typeof AudioContext | undefined =
      window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return;
    let ctx: AudioContext;
    try {
      ctx = new AC({ latencyHint: "interactive" });
    } catch {
      return;
    }
    this.ctx = ctx;
    this.started = true;

    this.master = ctx.createGain();
    this.master.gain.value = 0.9;
    this.tone = ctx.createBiquadFilter();
    this.tone.type = "lowpass";
    this.tone.frequency.value = 20000;
    // a safety limiter rather than a leveller: quiet things must stay quiet.
    // (The node adds make-up gain of its own, about +4 dB at these settings,
    // which `post` takes back out.)
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -8;
    comp.knee.value = 6;
    comp.ratio.value = 12;
    comp.attack.value = 0.003;
    comp.release.value = 0.15;
    const post = ctx.createGain();
    post.gain.value = 0.6;
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 2048;
    this.scope = new Float32Array(this.analyser.fftSize);
    this.master.connect(this.tone);
    this.tone.connect(comp);
    comp.connect(post);
    post.connect(this.analyser);
    this.analyser.connect(ctx.destination);

    this.dry = ctx.createGain();
    this.world = ctx.createGain();
    this.amb = ctx.createGain();
    this.dry.connect(this.master);
    this.world.connect(this.master);
    this.amb.connect(this.master);

    // two rooms: the wet street (slap-back off shop fronts) and a tiled hall
    this.revOut = ctx.createConvolver();
    this.revOut.buffer = this.impulse(2.3, 2.2, 0.035);
    this.revIn = ctx.createConvolver();
    this.revIn.buffer = this.impulse(0.75, 3.2, 0.006);
    this.sendOut = ctx.createGain();
    this.sendIn = ctx.createGain();
    this.sendOut.gain.value = 0;
    this.sendIn.gain.value = 0.3;
    const wetOut = ctx.createGain();
    wetOut.gain.value = 0.5;
    const wetIn = ctx.createGain();
    wetIn.gain.value = 0.45;
    this.sendOut.connect(this.revOut);
    this.revOut.connect(wetOut);
    wetOut.connect(this.master);
    this.sendIn.connect(this.revIn);
    this.revIn.connect(wetIn);
    wetIn.connect(this.master);
    this.dry.connect(this.sendOut);
    this.dry.connect(this.sendIn);
    this.world.connect(this.sendOut);
    this.world.connect(this.sendIn);

    this.buffers.white = this.noiseBuffer("white", 3);
    this.buffers.pink = this.noiseBuffer("pink", 4);
    this.buffers.brown = this.noiseBuffer("brown", 5);
    this.drips = this.dripBuffer();
    this.ambience();
    this.pickVoice();
    if (typeof speechSynthesis !== "undefined") {
      speechSynthesis.addEventListener?.("voiceschanged", () => this.pickVoice());
    }
    void ctx.resume();
  }

  private pickVoice(): void {
    if (typeof speechSynthesis === "undefined") return;
    const all = speechSynthesis.getVoices();
    const ja = all.filter((v) => v.lang.toLowerCase().startsWith("ja"));
    // a plain announcer's voice if the system has one, not a novelty voice
    const plain = /kyoko|o-?ren|otoya|hattori|nanami|haruka|ayumi|google 日本語/i;
    this.voice = ja.find((v) => plain.test(v.name)) ?? ja.find((v) => v.localService) ?? ja[0] ?? null;
  }

  private noiseBuffer(kind: NoiseKind, seconds: number): AudioBuffer {
    const ctx = this.ctx as AudioContext;
    const n = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(1, n, ctx.sampleRate);
    const d = buf.getChannelData(0);
    if (kind === "white") {
      for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    } else if (kind === "pink") {
      // Paul Kellet's economy filter
      let b0 = 0;
      let b1 = 0;
      let b2 = 0;
      for (let i = 0; i < n; i++) {
        const w = Math.random() * 2 - 1;
        b0 = 0.99765 * b0 + w * 0.099046;
        b1 = 0.963 * b1 + w * 0.2965164;
        b2 = 0.57 * b2 + w * 1.0526913;
        d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.22;
      }
    } else {
      let v = 0;
      for (let i = 0; i < n; i++) {
        v = (v + (Math.random() * 2 - 1) * 0.02) / 1.02;
        d[i] = v * 3.4;
      }
    }
    // make the loop seamless
    const fade = Math.floor(ctx.sampleRate * 0.05);
    for (let i = 0; i < fade; i++) {
      const k = i / fade;
      d[i] = (d[i] as number) * k + (d[n - fade + i] as number) * (1 - k);
    }
    return buf;
  }

  /** A loop of individual drops hitting puddles and sills, in stereo. */
  private dripBuffer(): AudioBuffer {
    const ctx = this.ctx as AudioContext;
    const sr = ctx.sampleRate;
    const n = Math.floor(sr * 6);
    const buf = ctx.createBuffer(2, n, sr);
    const l = buf.getChannelData(0);
    const r = buf.getChannelData(1);
    for (let k = 0; k < 150; k++) {
      const at = Math.floor(Math.random() * (n - sr * 0.1));
      const f = rnd(1400, 5200);
      const len = Math.floor(sr * rnd(0.012, 0.04));
      const pan = Math.random();
      const amp = rnd(0.1, 0.5) * (Math.random() < 0.15 ? 2 : 1);
      for (let i = 0; i < len; i++) {
        const e = Math.exp((-5 * i) / len);
        const v = Math.sin((2 * Math.PI * f * i) / sr + (i / len) * 3) * e * amp;
        l[at + i] = (l[at + i] as number) + v * (1 - pan);
        r[at + i] = (r[at + i] as number) + v * pan;
      }
    }
    return buf;
  }

  /** Exponentially decaying noise: a cheap room. */
  private impulse(seconds: number, decay: number, predelay: number): AudioBuffer {
    const ctx = this.ctx as AudioContext;
    const sr = ctx.sampleRate;
    const n = Math.floor(sr * seconds);
    const pre = Math.floor(sr * predelay);
    const buf = ctx.createBuffer(2, n, sr);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      let lp = 0;
      for (let i = pre; i < n; i++) {
        const t = (i - pre) / (n - pre);
        const w = Math.random() * 2 - 1;
        // the tail loses its top end as it dies
        const k = 0.25 + 0.7 * t;
        lp = lp * k + w * (1 - k);
        d[i] = lp * Math.pow(1 - t, decay) * (1 + 0.5 * Math.sin(i * 0.0007 * (c + 1)));
      }
      // a few distinct slaps off the buildings across the street
      for (let e = 0; e < 5; e++) {
        const at = pre + Math.floor(sr * rnd(0.02, 0.22));
        if (at < n) d[at] = (d[at] as number) + rnd(-0.6, 0.6);
      }
    }
    return buf;
  }

  private loop(kind: NoiseKind): AudioBufferSourceNode {
    const ctx = this.ctx as AudioContext;
    const src = ctx.createBufferSource();
    src.buffer = this.buffers[kind] as AudioBuffer;
    src.loop = true;
    src.start(0, Math.random() * 2);
    return src;
  }

  private filter(type: BiquadFilterType, freq: number, q = 0.7): BiquadFilterNode {
    const f = (this.ctx as AudioContext).createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    f.Q.value = q;
    return f;
  }

  private gain(v: number): GainNode {
    const g = (this.ctx as AudioContext).createGain();
    g.gain.value = v;
    return g;
  }

  private lfo(freq: number, depth: number, target: AudioParam): void {
    const ctx = this.ctx as AudioContext;
    const o = ctx.createOscillator();
    o.frequency.value = freq;
    const g = ctx.createGain();
    g.gain.value = depth;
    o.connect(g);
    g.connect(target);
    o.start();
  }

  /** The beds that never stop: rain, wind, water, a siren somewhere, and unease. */
  private ambience(): void {
    const ctx = this.ctx as AudioContext;

    // rain in the open: hiss, a body of roar underneath, and single drops on top
    this.rainOut = this.gain(0);
    const hiss = this.loop("white");
    const hissHp = this.filter("highpass", 1100, 0.4);
    const hissLp = this.filter("lowpass", 9500, 0.4);
    const hissG = this.gain(RAIN.hiss);
    hiss.connect(hissHp);
    hissHp.connect(hissLp);
    hissLp.connect(hissG);
    hissG.connect(this.rainOut);
    const roar = this.loop("pink");
    const roarBp = this.filter("bandpass", 520, 0.45);
    const roarG = this.gain(RAIN.roar);
    roar.connect(roarBp);
    roarBp.connect(roarG);
    roarG.connect(this.rainOut);
    const drip = ctx.createBufferSource();
    drip.buffer = this.drips;
    drip.loop = true;
    drip.start();
    const dripG = this.gain(RAIN.drips);
    drip.connect(dripG);
    dripG.connect(this.rainOut);
    this.lfo(0.09, RAIN.hiss * 0.25, hissG.gain); // gusts
    this.rainOut.connect(this.amb);

    // rain heard from under a roof: the same storm with the top taken off
    this.rainIn = this.gain(0);
    this.rainTone = this.filter("lowpass", 620, 0.5);
    const roof = this.loop("pink");
    const roofG = this.gain(RAIN.roof);
    roof.connect(this.rainTone);
    this.rainTone.connect(roofG);
    roofG.connect(this.rainIn);
    const pane = ctx.createBufferSource();
    pane.buffer = this.drips;
    pane.loop = true;
    pane.playbackRate.value = 0.7;
    pane.start(0, 2);
    const paneLp = this.filter("lowpass", 2600, 0.5);
    const paneG = this.gain(RAIN.pane);
    pane.connect(paneLp);
    paneLp.connect(paneG);
    paneG.connect(this.rainIn);
    this.rainIn.connect(this.amb);

    // wind in the wires
    const wind = this.loop("pink");
    const windBp = this.filter("bandpass", 420, 1.3);
    this.windGain = this.gain(0.05);
    wind.connect(windBp);
    windBp.connect(this.windGain);
    this.windGain.connect(this.amb);
    this.lfo(0.07, 180, windBp.frequency);
    this.lfo(0.113, 0.03, this.windGain.gain);

    // flood water lapping at the shutters
    const lap = this.loop("brown");
    const lapBp = this.filter("bandpass", 340, 0.8);
    this.floodGain = this.gain(0);
    lap.connect(lapBp);
    lapBp.connect(this.floodGain);
    this.floodGain.connect(this.amb);
    this.lfo(0.31, 90, lapBp.frequency);

    // the canal going through the sluice
    const rush = this.loop("brown");
    const rushLp = this.filter("lowpass", 260, 0.6);
    const rush2 = this.loop("white");
    const rush2Bp = this.filter("bandpass", 1300, 0.5);
    const rush2G = this.gain(0.035);
    this.sluiceGain = this.gain(0);
    rush.connect(rushLp);
    rushLp.connect(this.sluiceGain);
    rush2.connect(rush2Bp);
    rush2Bp.connect(rush2G);
    rush2G.connect(this.sluiceGain);
    this.sluiceGain.connect(this.amb);

    // a hand-cranked siren a long way off, rising and falling
    const siren = ctx.createOscillator();
    siren.type = "sawtooth";
    siren.frequency.value = 520;
    this.lfo(0.085, 150, siren.frequency);
    const sirenLp = this.filter("lowpass", 760, 1.2);
    this.sirenGain = this.gain(0);
    siren.connect(sirenLp);
    sirenLp.connect(this.sirenGain);
    this.sirenGain.connect(this.amb);
    this.sirenGain.connect(this.sendOut);
    siren.start();

    // unease: two sines that never quite agree
    this.droneGain = this.gain(0);
    for (const f of [43, 46.6]) {
      const o = ctx.createOscillator();
      o.frequency.value = f;
      o.connect(this.droneGain);
      o.start();
    }
    const air = this.loop("brown");
    const airBp = this.filter("bandpass", 170, 2.5);
    const airG = this.gain(0.5);
    air.connect(airBp);
    airBp.connect(airG);
    airG.connect(this.droneGain);
    this.droneGain.connect(this.amb);

    // being hunted: a thin dissonance with a shiver in it
    this.dreadGain = this.gain(0);
    const shiver = this.gain(0.6);
    this.lfo(6.3, 0.4, shiver.gain);
    for (const f of [1244.5, 1318.5, 932.3]) {
      const o = ctx.createOscillator();
      o.type = "triangle";
      o.frequency.value = f;
      o.connect(shiver);
      o.start();
    }
    shiver.connect(this.dreadGain);
    this.dreadGain.connect(this.amb);
    this.dreadGain.connect(this.sendOut);
  }

  // ------------------------------------------------------------ plumbing for one-shots

  private count(name: string): void {
    this.counts[name] = (this.counts[name] ?? 0) + 1;
  }

  /** Is there a wall between the listener and a point? */
  private occluded(sim: Sim | null, p: Pos): boolean {
    if (!sim) return false;
    const pl = sim.s.player;
    return !sim.los(pl.x, pl.z, p.x, p.z);
  }

  /**
   * A bus input for one sound. With a position the sound is placed in the
   * world; `muffled` puts a wall in front of it.
   */
  private voiceOut(pos: Pos | null, level: number, muffled = false, ref = 3.5): GainNode {
    const ctx = this.ctx as AudioContext;
    const g = ctx.createGain();
    g.gain.value = level * (muffled ? 0.62 : 1);
    if (!pos) {
      g.connect(this.dry);
      return g;
    }
    const pan = ctx.createPanner();
    pan.panningModel = "HRTF";
    pan.distanceModel = "inverse";
    pan.refDistance = ref;
    pan.rolloffFactor = 1.05;
    pan.maxDistance = 90;
    pan.positionX.value = pos.x;
    pan.positionY.value = pos.y;
    pan.positionZ.value = pos.z;
    if (muffled) {
      const lp = this.filter("lowpass", 780, 0.6);
      g.connect(lp);
      lp.connect(pan);
    } else {
      g.connect(pan);
    }
    pan.connect(this.world);
    return g;
  }

  private burst(
    out: AudioNode,
    kind: NoiseKind,
    t: number,
    attack: number,
    decay: number,
    peak: number,
    type: BiquadFilterType,
    f0: number,
    f1 = f0,
    q = 0.8,
  ): void {
    const ctx = this.ctx as AudioContext;
    const src = ctx.createBufferSource();
    const buf = this.buffers[kind] as AudioBuffer;
    src.buffer = buf;
    const flt = ctx.createBiquadFilter();
    flt.type = type;
    flt.Q.value = q;
    flt.frequency.setValueAtTime(Math.max(20, f0), t);
    if (f1 !== f0) flt.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + attack + decay);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + Math.max(attack, 0.002));
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    src.connect(flt);
    flt.connect(g);
    g.connect(out);
    const dur = attack + decay + 0.05;
    src.start(t, Math.random() * Math.max(0.01, buf.duration - dur - 0.05), dur);
  }

  private blip(
    out: AudioNode,
    type: OscillatorType,
    t: number,
    f0: number,
    f1: number,
    attack: number,
    decay: number,
    peak: number,
  ): void {
    const ctx = this.ctx as AudioContext;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(Math.max(20, f0), t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + attack + decay);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + Math.max(attack, 0.002));
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    o.connect(g);
    g.connect(out);
    o.start(t);
    o.stop(t + attack + decay + 0.05);
  }

  // ------------------------------------------------------------ feet

  private footstep(surface: Surface, run: boolean): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.005;
    const lvl = (run ? 0.5 : 0.3) * rnd(0.85, 1.1);
    const out = this.voiceOut(null, lvl);
    this.count("step");
    switch (surface) {
      case "tile":
        this.blip(out, "sine", t, rnd(105, 125), 58, 0.004, 0.07, 0.55);
        this.burst(out, "white", t, 0.002, 0.03, 0.5, "bandpass", rnd(2100, 2700), undefined, 2.5);
        if (Math.random() < 0.3) this.blip(out, "sine", t + 0.03, rnd(1500, 2100), 2600, 0.01, 0.05, 0.05); // wet sole
        break;
      case "water":
        this.burst(out, "white", t, 0.012, rnd(0.2, 0.3), 0.9, "bandpass", rnd(1100, 1500), 700, 0.6);
        this.burst(out, "brown", t, 0.01, 0.16, 0.9, "lowpass", 380);
        for (let k = 0; k < 3; k++) {
          this.blip(out, "sine", t + rnd(0.09, 0.3), rnd(1600, 3200), rnd(2400, 4200), 0.004, 0.035, 0.07);
        }
        break;
      case "metal": {
        const base = rnd(290, 340);
        for (const [m, d, a] of [
          [1, 0.2, 0.3],
          [1.69, 0.15, 0.22],
          [3.77, 0.1, 0.14],
          [6.06, 0.07, 0.08],
        ] as const) {
          this.blip(out, "sine", t, base * m, base * m * 0.995, 0.002, d, a);
        }
        this.burst(out, "white", t, 0.001, 0.025, 0.4, "bandpass", 3200, undefined, 1.5);
        break;
      }
      default:
        // wet asphalt and concrete: a soft scuff and the slap of a wet sole
        this.burst(out, "pink", t, 0.004, rnd(0.06, 0.09), 0.9, "bandpass", rnd(600, 850), undefined, 0.8);
        this.blip(out, "sine", t, 92, 50, 0.004, 0.055, 0.4);
        this.burst(out, "white", t + 0.012, 0.003, 0.045, 0.22, "highpass", 3000);
        break;
    }
  }

  /** One of the drowned taking a step: a thud and then the foot it drags. */
  private dragStep(pos: Pos, surface: Surface, fast: boolean, sim: Sim): void {
    const ctx = this.ctx as AudioContext;
    const d = Math.hypot(pos.x - this.lis.x, pos.z - this.lis.z);
    if (d > 42) return;
    // a crowd is heard as its nearest few: thin out the far ones when it is busy
    const nowT = ctx.currentTime;
    this.recentSteps = this.recentSteps.filter((q) => nowT - q < 0.3);
    if (this.recentSteps.length >= 3 && d > 9) return;
    if (this.recentSteps.length >= 6) return;
    this.recentSteps.push(nowT);
    const t = ctx.currentTime + 0.005;
    const out = this.voiceOut(pos, fast ? 1.45 : 1.25, this.occluded(sim, pos), 4);
    this.count("estep");
    if (surface === "water") {
      this.burst(out, "white", t, 0.03, fast ? 0.25 : 0.42, 0.8, "bandpass", rnd(800, 1100), 500, 0.6);
      this.burst(out, "brown", t, 0.02, 0.2, 0.9, "lowpass", 300);
    } else {
      this.blip(out, "sine", t, 72, 44, 0.006, 0.09, 0.8);
      const metal = surface === "metal";
      this.burst(
        out,
        "pink",
        t + 0.05,
        0.07,
        fast ? 0.18 : 0.36,
        0.75,
        "bandpass",
        metal ? rnd(900, 1300) : rnd(360, 520),
        metal ? 700 : 300,
        metal ? 3 : 0.9,
      );
    }
  }

  // ------------------------------------------------------------ throats

  private vocal(id: string, kind: VocalKind, pos: Pos, sim: Sim, boost = 1): void {
    const ctx = this.ctx as AudioContext;
    const d = Math.hypot(pos.x - this.lis.x, pos.z - this.lis.z);
    if (d > 60) return;
    const t = ctx.currentTime + 0.01;
    const pitch = 0.85 + hash(id) * 0.4;
    // [length, f0 start, f0 end, formant 1, formant 2, level, growl rate, breath]
    const shape: Record<VocalKind, [number, number, number, number, number, number, number, number]> = {
      idle: [rnd(1.3, 2.1), 88, 68, 480, 900, 1.3, 0, 0.12],
      suspicious: [0.55, 86, 124, 520, 1100, 1.5, 0, 0.1],
      search: [0.95, 78, 72, 420, 820, 1.5, 23, 0.14],
      alert: [1.05, 150, 310, 820, 1750, 3.4, 31, 0.2],
      attack: [0.36, 210, 105, 760, 1500, 2.6, 38, 0.22],
      hurt: [0.3, 260, 170, 700, 1650, 2.2, 0, 0.18],
      die: [1.7, 150, 44, 520, 900, 2.2, 13, 0.25],
    };
    const [len, f0, f1, fa, fb, lvl, growl, breath] = shape[kind];
    const out = this.voiceOut({ x: pos.x, y: 1.5, z: pos.z }, lvl * boost, this.occluded(sim, pos), 4.5);
    this.count(`vocal:${kind}`);

    const o = ctx.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(f0 * pitch, t);
    if (kind === "alert") {
      o.frequency.exponentialRampToValueAtTime(f1 * pitch, t + len * 0.45);
      o.frequency.exponentialRampToValueAtTime(f1 * pitch * 0.72, t + len);
    } else {
      o.frequency.exponentialRampToValueAtTime(f1 * pitch, t + len);
    }
    // an unsteady throat
    const wob = ctx.createOscillator();
    wob.frequency.value = rnd(4.5, 7);
    const wobG = this.gain(f0 * pitch * 0.045);
    wob.connect(wobG);
    wobG.connect(o.frequency);

    const mix = this.gain(1);
    for (const [f, q, g] of [
      [fa, 5, 1],
      [fb, 7, 0.6],
      [fb * 2.4, 6, 0.18],
    ] as const) {
      const bp = this.filter("bandpass", f * (0.9 + hash(id + "f") * 0.25), q);
      const bg = this.gain(g);
      o.connect(bp);
      bp.connect(bg);
      bg.connect(mix);
    }
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(1, t + Math.min(0.12, len * 0.25));
    env.gain.setValueAtTime(1, t + len * 0.6);
    env.gain.exponentialRampToValueAtTime(0.0001, t + len);
    mix.connect(env);
    if (growl > 0) {
      const am = this.gain(0.55);
      const lf = ctx.createOscillator();
      lf.type = "square";
      lf.frequency.value = growl * rnd(0.9, 1.1);
      const lg = this.gain(0.45);
      lf.connect(lg);
      lg.connect(am.gain);
      env.connect(am);
      am.connect(out);
      lf.start(t);
      lf.stop(t + len + 0.1);
    } else {
      env.connect(out);
    }
    this.burst(out, "pink", t, len * 0.3, len * 0.7, breath, "bandpass", 1700, 1100, 0.7);
    o.start(t);
    wob.start(t);
    o.stop(t + len + 0.1);
    wob.stop(t + len + 0.1);
  }

  // ------------------------------------------------------------ the revolver, doors, things

  private gunshot(ev: Extract<SimEvent, { t: "shot" }>): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.003;
    const out = this.voiceOut(null, 1);
    this.count("shot");
    this.burst(out, "white", t, 0.001, 0.04, 1.0, "highpass", 1800);
    this.burst(out, "white", t, 0.002, 0.22, 0.9, "lowpass", 3400, 260);
    this.blip(out, "sine", t, 150, 42, 0.002, 0.16, 1.0);
    // the report comes back off the shop fronts
    this.burst(out, "pink", t + 0.11, 0.02, 0.5, 0.22, "bandpass", 900, 400, 0.5);
    // the rest of the world goes quiet for a moment
    this.amb.gain.cancelScheduledValues(t);
    this.amb.gain.setValueAtTime(0.35, t);
    this.amb.gain.linearRampToValueAtTime(1, t + 1.1);

    const hit: Pos = { x: ev.hx, y: ev.hy, z: ev.hz };
    const th = t + Math.min(0.12, Math.hypot(ev.hx - ev.x, ev.hz - ev.z) / 340) + 0.02;
    if (ev.hit === "world") {
      const o = this.voiceOut(hit, 0.6, false, 3);
      this.burst(o, "white", th, 0.001, 0.05, 0.8, "bandpass", 4200, undefined, 1.2);
      if (Math.random() < 0.5) this.blip(o, "sine", th, rnd(2600, 3400), rnd(1100, 1500), 0.002, 0.16, 0.25); // ricochet
    } else if (ev.hit !== "none") {
      const o = this.voiceOut(hit, 0.9, false, 3);
      this.burst(o, "brown", th, 0.003, 0.09, 1.0, "lowpass", 520);
      this.burst(o, "white", th + 0.01, 0.01, 0.08, 0.3, "bandpass", 1400, 600, 0.8);
    }
  }

  private dryFire(): void {
    const t = (this.ctx as AudioContext).currentTime + 0.003;
    const out = this.voiceOut(null, 0.5);
    this.count("dry");
    this.blip(out, "square", t, 2100, 1900, 0.001, 0.012, 0.3);
    this.blip(out, "sine", t + 0.012, 880, 760, 0.001, 0.03, 0.3);
    this.burst(out, "white", t, 0.001, 0.015, 0.3, "highpass", 4000);
  }

  private pickup(kind: "gun" | "ammo" | "medkit"): void {
    const t = (this.ctx as AudioContext).currentTime + 0.01;
    const out = this.voiceOut(null, 1.0);
    this.count(`pickup:${kind}`);
    if (kind === "gun") {
      // steel dragged off a wet bonnet, then the cylinder checked
      this.burst(out, "white", t, 0.03, 0.12, 0.35, "bandpass", 2600, 3600, 2);
      this.blip(out, "sine", t + 0.02, 1240, 1180, 0.002, 0.09, 0.2);
      this.burst(out, "white", t + 0.26, 0.001, 0.02, 0.5, "bandpass", 3400, undefined, 3);
      this.blip(out, "square", t + 0.3, 1650, 1500, 0.001, 0.02, 0.18);
    } else if (kind === "ammo") {
      for (let k = 0; k < 4; k++) {
        this.blip(out, "sine", t + k * rnd(0.045, 0.07), rnd(3000, 4400), rnd(2900, 4300), 0.001, 0.05, 0.16);
      }
      this.burst(out, "white", t + 0.02, 0.01, 0.1, 0.2, "bandpass", 2400, undefined, 1.5);
    } else {
      this.burst(out, "white", t, 0.05, 0.22, 0.3, "bandpass", 1100, 3800, 1.8); // zip
      this.burst(out, "pink", t + 0.35, 0.08, 0.5, 0.25, "bandpass", 900, 500, 0.7); // a breath let go
    }
  }

  /** Dry hinges: stick, slip, stick. */
  private creak(pos: Pos | null, t: number, len: number, f: number, level: number, muffled = false): void {
    const ctx = this.ctx as AudioContext;
    const out = this.voiceOut(pos, level, muffled, 5);
    const o = ctx.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(f, t);
    let tt = t;
    let cur = f;
    while (tt < t + len) {
      tt += rnd(0.08, 0.22);
      cur = f * rnd(0.82, 1.25);
      o.frequency.linearRampToValueAtTime(cur, tt);
    }
    const bp = this.filter("bandpass", f * 3.1, 11);
    bp.frequency.setValueAtTime(f * 2.6, t);
    bp.frequency.linearRampToValueAtTime(f * 4.4, t + len);
    const bp2 = this.filter("bandpass", f * 7.3, 9);
    const g2 = this.gain(0.4);
    // stick-slip: the sound comes in grains
    const gate = this.gain(0.5);
    const lf = ctx.createOscillator();
    lf.type = "sawtooth";
    lf.frequency.setValueAtTime(rnd(22, 34), t);
    lf.frequency.linearRampToValueAtTime(rnd(9, 16), t + len);
    const lg = this.gain(0.5);
    lf.connect(lg);
    lg.connect(gate.gain);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(1, t + len * 0.25);
    env.gain.setValueAtTime(1, t + len * 0.7);
    env.gain.exponentialRampToValueAtTime(0.0001, t + len);
    o.connect(bp);
    o.connect(bp2);
    bp2.connect(g2);
    bp.connect(gate);
    g2.connect(gate);
    gate.connect(env);
    env.connect(out);
    o.start(t);
    lf.start(t);
    o.stop(t + len + 0.05);
    lf.stop(t + len + 0.05);
  }

  private door(pos: Pos, sim: Sim): void {
    const t = (this.ctx as AudioContext).currentTime + 0.01;
    const out = this.voiceOut(pos, 0.9, false, 4);
    this.count("door");
    this.burst(out, "white", t, 0.001, 0.02, 0.6, "bandpass", 1800, undefined, 2.5); // latch
    this.blip(out, "sine", t, 300, 220, 0.002, 0.06, 0.5);
    this.creak(pos, t + 0.06, rnd(0.7, 0.95), rnd(150, 190), 0.9, this.occluded(sim, pos));
    this.burst(out, "brown", t + 0.85, 0.005, 0.14, 0.8, "lowpass", 340); // it meets the stop
  }

  private lockedDoor(pos: Pos): void {
    const t = (this.ctx as AudioContext).currentTime + 0.01;
    const out = this.voiceOut(pos, 0.8, false, 4);
    this.count("locked");
    for (const dt of [0, 0.17]) {
      this.burst(out, "brown", t + dt, 0.003, 0.09, 0.9, "lowpass", 420);
      for (let k = 0; k < 3; k++) this.blip(out, "sine", t + dt + 0.01, rnd(1700, 3300), rnd(1700, 3300), 0.001, 0.09, 0.06);
    }
  }

  /** Something on the inside leaning on a shutter. */
  rattle(x: number, y: number, z: number): void {
    const ctx = this.ctx;
    if (!ctx || this.ended) return;
    const t = ctx.currentTime + 0.02;
    const len = rnd(0.7, 1.3);
    const out = this.voiceOut({ x, y, z }, 0.8, false, 4);
    this.count("rattle");
    this.blip(out, "sine", t, 84, 48, 0.004, 0.12, 0.9);
    const src = ctx.createBufferSource();
    src.buffer = this.buffers.white as AudioBuffer;
    const a = this.filter("bandpass", rnd(1100, 1500), 2.2);
    const b = this.filter("bandpass", rnd(2600, 3300), 3.2);
    const bg = this.gain(0.6);
    const gate = this.gain(0);
    // the slats chatter and settle
    let tt = t + 0.03;
    while (tt < t + len) {
      const k = 1 - (tt - t) / len;
      gate.gain.setValueAtTime(rnd(0.3, 0.8) * k, tt);
      gate.gain.exponentialRampToValueAtTime(0.01, tt + rnd(0.02, 0.04));
      tt += rnd(0.04, 0.085);
    }
    src.connect(a);
    src.connect(b);
    b.connect(bg);
    a.connect(gate);
    bg.connect(gate);
    gate.connect(out);
    src.start(t, Math.random(), len + 0.2);
  }

  thunder(delay: number, near: boolean): void {
    const ctx = this.ctx;
    if (!ctx || this.ended) return;
    const t = ctx.currentTime + Math.max(0.02, delay);
    const inside = this.lis.indoor;
    const out = this.voiceOut(null, (near ? 1 : 0.5) * (1 - inside * 0.45));
    this.count(near ? "thunder:near" : "thunder:far");
    if (near) {
      this.burst(out, "white", t, 0.002, 0.14, 0.8 * (1 - inside * 0.6), "highpass", 1300);
      this.burst(out, "white", t + 0.09, 0.002, 0.2, 0.5 * (1 - inside * 0.6), "bandpass", 2200, 600, 0.5);
    }
    // the roll: brown noise that tumbles downhill for seconds
    const src = ctx.createBufferSource();
    src.buffer = this.buffers.brown as AudioBuffer;
    src.loop = true;
    const lp = this.filter("lowpass", near ? 520 : 260, 0.5);
    const len = near ? rnd(5.5, 7) : rnd(4, 6);
    lp.frequency.setValueAtTime(near ? 520 : 260, t);
    lp.frequency.exponentialRampToValueAtTime(70, t + len);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(1.0, t + (near ? 0.08 : 0.5));
    let tt = t + 0.4;
    while (tt < t + len - 0.6) {
      g.gain.linearRampToValueAtTime(rnd(0.25, 0.9) * (1 - (tt - t) / len), tt);
      tt += rnd(0.18, 0.5);
    }
    g.gain.exponentialRampToValueAtTime(0.0001, t + len);
    src.connect(lp);
    lp.connect(g);
    g.connect(out);
    src.start(t, Math.random() * 2);
    src.stop(t + len + 0.1);
    this.blip(out, "sine", t, near ? 58 : 44, 30, 0.05, near ? 1.6 : 1.0, near ? 0.8 : 0.4);
  }

  // ------------------------------------------------------------ the footbridge

  private bridgeStart(sim: Sim): void {
    const ctx = this.ctx as AudioContext;
    this.bridgeStop();
    this.count("bridge:start");
    const t = ctx.currentTime + 0.02;
    const w = sim.level.winch;
    const winch: Pos = { x: w.x, y: 2, z: w.z };
    const head: Pos = { x: 24.25, y: 3, z: -132.5 };

    // the motor in the winch house
    const mOut = this.voiceOut(winch, 0.0001, false, 9);
    mOut.gain.exponentialRampToValueAtTime(0.45, t + 0.8);
    const lp = this.filter("lowpass", 520, 1.2);
    const oscs: OscillatorNode[] = [];
    for (const [f, type, g] of [
      [49, "sawtooth", 0.6],
      [98.6, "square", 0.25],
      [147, "sawtooth", 0.2],
    ] as const) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.setValueAtTime(f * 0.5, t);
      o.frequency.exponentialRampToValueAtTime(f, t + 1.2); // it winds up
      const og = this.gain(g);
      o.connect(og);
      og.connect(lp);
      o.start(t);
      oscs.push(o);
    }
    lp.connect(mOut);
    const whine = this.loop("pink");
    const whineBp = this.filter("bandpass", 1900, 6);
    const whineG = this.gain(0.35);
    whine.connect(whineBp);
    whineBp.connect(whineG);
    whineG.connect(mOut);

    // the warning buzzer at the bridge head: two harsh notes, on and off
    const bOut = this.voiceOut(head, 0.36, false, 7);
    const buzz = ctx.createOscillator();
    buzz.type = "square";
    const buzzLp = this.filter("bandpass", 1500, 1.4);
    const buzzG = this.gain(0);
    buzz.connect(buzzLp);
    buzzLp.connect(buzzG);
    buzzG.connect(bOut);
    for (let k = 0; k < 40; k++) {
      const at = t + k * 0.5;
      buzz.frequency.setValueAtTime(k % 2 === 0 ? 740 : 587, at);
      buzzG.gain.setValueAtTime(0.5, at);
      buzzG.gain.setValueAtTime(0.0, at + 0.3);
    }
    buzz.start(t);

    this.bridgeTick = 0;
    const stopAt = (when: number): void => {
      for (const o of oscs) o.stop(when);
      whine.stop(when);
      buzz.stop(when);
    };
    this.bridge = {
      stop: () => {
        const now = ctx.currentTime;
        mOut.gain.cancelScheduledValues(now);
        mOut.gain.setTargetAtTime(0.0001, now, 0.12);
        buzzG.gain.cancelScheduledValues(now);
        buzzG.gain.setValueAtTime(0, now);
        stopAt(now + 0.8);
      },
    };
  }

  private bridgeStop(): void {
    this.bridge?.stop();
    this.bridge = null;
  }

  private bridgeDown(): void {
    const ctx = this.ctx as AudioContext;
    this.bridgeStop();
    this.count("bridge:down");
    const t = ctx.currentTime + 0.02;
    const out = this.voiceOut({ x: 24.25, y: 0.5, z: -145 }, 1, false, 12);
    for (const [f, d, a] of [
      [97, 1.9, 0.6],
      [151, 1.4, 0.45],
      [233, 1.0, 0.35],
      [389, 0.7, 0.25],
      [571, 0.5, 0.2],
      [887, 0.35, 0.12],
      [1310, 0.22, 0.08],
    ] as const) {
      this.blip(out, "sine", t, f * rnd(0.98, 1.02), f * 0.99, 0.003, d, a);
    }
    this.burst(out, "brown", t, 0.004, 0.35, 1.0, "lowpass", 240);
    this.burst(out, "white", t, 0.002, 0.12, 0.5, "bandpass", 2400, 900, 0.8);
    // the deck settles
    this.creak({ x: 24.25, y: 0.5, z: -139 }, t + 0.5, 1.4, 120, 1.0);
  }

  // ------------------------------------------------------------ the body

  private hurt(): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.003;
    const out = this.voiceOut(null, 1);
    this.count("hurt");
    this.blip(out, "sine", t, 125, 48, 0.003, 0.17, 1.0);
    this.burst(out, "brown", t, 0.003, 0.11, 0.9, "lowpass", 900);
    this.burst(out, "pink", t + 0.07, 0.03, 0.2, 0.4, "bandpass", 1250, 800, 0.8); // the breath knocked out
    this.blip(out, "sine", t + 0.05, 3400, 3380, 0.05, 1.3, 0.03); // ears
    // the world dulls for a moment
    this.tone.frequency.cancelScheduledValues(t);
    this.tone.frequency.setValueAtTime(900, t);
    this.tone.frequency.exponentialRampToValueAtTime(20000, t + 1.0);
  }

  private swipe(pos: Pos): void {
    const t = (this.ctx as AudioContext).currentTime + 0.003;
    const out = this.voiceOut({ x: pos.x, y: 1.3, z: pos.z }, 1.0, false, 3);
    this.count("swipe");
    this.burst(out, "white", t, 0.05, 0.13, 1.0, "bandpass", 500, 1700, 1.2);
  }

  private heartbeat(t: number, level: number): void {
    const out = this.voiceOut(null, level);
    this.blip(out, "sine", t, 62, 40, 0.012, 0.11, 1.0);
    this.blip(out, "sine", t + 0.17, 54, 36, 0.012, 0.13, 0.7);
  }

  private death(): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.01;
    this.count("death");
    const out = this.voiceOut(null, 1);
    this.blip(out, "sine", t, 64, 27, 0.02, 1.9, 1.0);
    this.burst(out, "brown", t, 0.02, 1.2, 0.8, "lowpass", 300, 60);
    this.tone.frequency.cancelScheduledValues(t);
    this.tone.frequency.setValueAtTime(Math.min(this.tone.frequency.value, 6000), t);
    this.tone.frequency.exponentialRampToValueAtTime(320, t + 1.4);
    this.master.gain.setTargetAtTime(0.5, t, 0.8);
    this.stopSpeech();
    this.bridgeStop();
  }

  private revive(): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime;
    this.tone.frequency.cancelScheduledValues(t);
    this.tone.frequency.setTargetAtTime(20000, t, 0.3);
    this.master.gain.cancelScheduledValues(t);
    this.master.gain.setTargetAtTime(0.9, t, 0.3);
    this.amb.gain.cancelScheduledValues(t);
    this.amb.gain.setTargetAtTime(1, t, 0.2);
    this.world.gain.setTargetAtTime(1, t, 0.1);
    this.ended = false;
    this.bridgeStop();
    this.radioT = 8;
  }

  /** The door handle gives, and the night is shut out all at once. */
  private clear(): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.01;
    this.count("clear");
    this.ended = true;
    this.stopSpeech();
    this.bridgeStop();
    const out = this.voiceOut(null, 1);
    this.burst(out, "brown", t, 0.002, 0.09, 1.0, "lowpass", 520);
    this.blip(out, "sine", t, 96, 70, 0.003, 0.22, 0.9);
    this.blip(out, "sine", t + 0.02, 410, 400, 0.002, 0.07, 0.25);
    for (const g of [this.amb, this.world]) {
      g.gain.cancelScheduledValues(t);
      g.gain.setValueAtTime(g.gain.value, t + 0.07);
      g.gain.linearRampToValueAtTime(0, t + 0.11);
    }
    // inside: the storm is somewhere else now
    this.burst(out, "pink", t + 1.0, 1.5, 9, 0.05, "lowpass", 300);
  }

  // ------------------------------------------------------------ the loudspeakers

  private stopSpeech(): void {
    try {
      if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    } catch {
      // ignore
    }
  }

  /** How loud the masts are from where we stand. */
  private mastLevel(): number {
    let d = Infinity;
    for (const m of MASTS) d = Math.min(d, Math.hypot(m.x - this.lis.x, m.z - this.lis.z));
    return Math.max(0.3, Math.min(1, 1.15 - d / 75)) * (1 - this.lis.indoor * 0.45);
  }

  private announce(): void {
    const ctx = this.ctx as AudioContext;
    const t = ctx.currentTime + 0.05;
    const level = this.mastLevel();
    this.count("radio");
    // horn loudspeakers, and the same message arriving late from the far mast
    const horn = this.filter("bandpass", 1350, 0.75);
    const out = this.gain(0.2 * level);
    const delay = ctx.createDelay(1.5);
    delay.delayTime.value = 0.43;
    const fb = this.gain(0.42);
    horn.connect(out);
    out.connect(delay);
    delay.connect(fb);
    fb.connect(delay);
    delay.connect(this.amb);
    out.connect(this.amb);
    out.connect(this.sendOut);

    // chime: four struck notes up, one down
    const notes = [587.3, 740, 880, 1174.7, 880];
    notes.forEach((f, k) => {
      const at = t + k * 0.62;
      this.blip(horn, "sine", at, f, f, 0.006, 1.5, 0.8);
      this.blip(horn, "sine", at, f * 3.01, f * 3.01, 0.004, 0.5, 0.12);
    });
    const speakAt = notes.length * 0.62 + 1.2;

    const spoken = this.tts && this.voice !== null && typeof SpeechSynthesisUtterance !== "undefined";
    if (spoken) {
      window.setTimeout(
        () => {
          if (this.paused || this.ended || !this.voice) return;
          try {
            const u = new SpeechSynthesisUtterance(ANNOUNCE);
            u.voice = this.voice;
            u.lang = this.voice.lang;
            u.rate = 0.74;
            u.pitch = 0.85;
            u.volume = Math.min(1, 0.5 * this.mastLevel()) * this.ttsVolume;
            u.onstart = () => this.count("radio:speech-started");
            u.onend = () => this.count("radio:speech-ended");
            u.onerror = () => this.count("radio:speech-error");
            speechSynthesis.speak(u);
            this.count("radio:spoken");
          } catch {
            // no speech on this machine: the murmur below is used next time
            this.voice = null;
          }
        },
        speakAt * 1000,
      );
      return;
    }
    // no voice available: a public-address murmur, the words lost in the rain
    this.count("radio:murmur");
    const vt = t + speakAt;
    const len = 8.5;
    const o = ctx.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(205, vt);
    const f1 = this.filter("bandpass", 600, 6);
    const f2 = this.filter("bandpass", 1500, 8);
    const syl = this.gain(0);
    const vowels: [number, number][] = [
      [800, 1250],
      [320, 2300],
      [360, 1150],
      [520, 1900],
      [500, 900],
    ];
    let tt = vt;
    while (tt < vt + len) {
      const d = rnd(0.13, 0.24);
      const v = vowels[Math.floor(Math.random() * vowels.length)] as [number, number];
      f1.frequency.setTargetAtTime(v[0], tt, 0.02);
      f2.frequency.setTargetAtTime(v[1], tt, 0.02);
      o.frequency.setTargetAtTime(rnd(185, 235), tt, 0.05);
      const phraseEnd = Math.random() < 0.12;
      syl.gain.setTargetAtTime(0.9, tt, 0.015);
      syl.gain.setTargetAtTime(0.05, tt + d * 0.75, 0.02);
      tt += d + (phraseEnd ? rnd(0.35, 0.6) : 0);
    }
    syl.gain.setTargetAtTime(0, vt + len, 0.05);
    const push = this.gain(2.4);
    o.connect(f1);
    o.connect(f2);
    f1.connect(syl);
    f2.connect(syl);
    syl.connect(push);
    push.connect(horn);
    o.start(vt);
    o.stop(vt + len + 0.5);
  }

  // ------------------------------------------------------------ public

  setPaused(paused: boolean): void {
    this.paused = paused;
    const ctx = this.ctx;
    if (!ctx) return;
    if (paused) {
      this.stopSpeech();
      void ctx.suspend();
    } else {
      void ctx.resume();
    }
  }

  onEvent(ev: SimEvent, sim: Sim): void {
    const ctx = this.ctx;
    if (!ctx) return;
    if (ev.t === "retry") {
      this.revive();
      return;
    }
    if (this.ended) return;
    switch (ev.t) {
      case "step":
        this.footstep(ev.surface, ev.run);
        break;
      case "estep":
        this.dragStep({ x: ev.x, y: 0.2, z: ev.z }, ev.surface, ev.fast, sim);
        break;
      case "vocal":
        this.vocal(ev.id, ev.kind, { x: ev.x, y: 1.5, z: ev.z }, sim);
        break;
      case "shot":
        this.gunshot(ev);
        break;
      case "dry":
        this.dryFire();
        break;
      case "swipe":
        this.swipe({ x: ev.x, y: 1.3, z: ev.z });
        break;
      case "hurt":
        this.hurt();
        break;
      case "death":
        this.death();
        break;
      case "pickup":
        this.pickup(ev.kind);
        break;
      case "door":
        this.door({ x: ev.x, y: 1.2, z: ev.z }, sim);
        break;
      case "locked":
        this.lockedDoor({ x: ev.x, y: 1.2, z: ev.z });
        break;
      case "bridge":
        if (ev.phase === "start") this.bridgeStart(sim);
        else this.bridgeDown();
        break;
      case "thunder":
        this.thunder(0.25, ev.near);
        break;
      case "cue":
        if (ev.id === "final") {
          // heard before it is seen: something in the dark ahead clears its throat
          this.count("cue:final");
          this.vocal("F2", "search", { x: ev.x, y: 1.5, z: ev.z }, sim, 2.2);
          window.setTimeout(() => {
            if (!this.ended && this.ctx) this.vocal("F1", "suspicious", { x: ev.x + 6, y: 1.5, z: ev.z + 6 }, sim, 1.8);
          }, 450);
        } else if (ev.id === "glass") {
          // a wet hand trails along the outside of the glass
          this.count("cue:glass");
          const t = ctx.currentTime + 0.3;
          const out = this.voiceOut({ x: ev.x - 2, y: 1.2, z: -14.3 }, 1.5, true, 6);
          this.burst(out, "pink", t, 0.3, 1.5, 0.9, "bandpass", 500, 320, 2.5);
          this.creak({ x: ev.x - 2, y: 1.4, z: -14.3 }, t + 0.5, 1.1, 210, 0.8, true);
        }
        break;
      case "clear":
        this.clear();
        break;
      default:
        break;
    }
  }

  update(dt: number, sim: Sim, cam: Listener): void {
    const ctx = this.ctx;
    this.lis = cam;
    if (!ctx || this.paused || ctx.state !== "running") return;
    const now = ctx.currentTime;
    this.time += dt;
    const s = sim.s;
    const p = s.player;

    // ears: at the camera, turned with the view
    const L = ctx.listener;
    const fx = -Math.sin(cam.yaw);
    const fz = -Math.cos(cam.yaw);
    if (L.positionX) {
      L.positionX.value = cam.x;
      L.positionY.value = cam.y;
      L.positionZ.value = cam.z;
      L.forwardX.value = fx;
      L.forwardY.value = 0;
      L.forwardZ.value = fz;
      L.upX.value = 0;
      L.upY.value = 1;
      L.upZ.value = 0;
    } else {
      L.setPosition(cam.x, cam.y, cam.z);
      L.setOrientation(fx, 0, fz, 0, 1, 0);
    }
    if (this.ended) return;

    const inside = cam.indoor;
    const k = 0.25;
    this.rainOut.gain.setTargetAtTime(1 - inside, now, k);
    this.rainIn.gain.setTargetAtTime(inside, now, k);
    this.sendOut.gain.setTargetAtTime(0.32 * (1 - inside), now, k);
    this.sendIn.gain.setTargetAtTime(0.34 * inside, now, k);
    this.windGain.gain.setTargetAtTime(0.05 * (1 - inside * 0.8), now, 0.6);
    const onFlood = p.surface === "water" || (p.x > -6 && p.x < 6 && p.z < -26 && p.z > -101);
    this.floodGain.gain.setTargetAtTime(onFlood ? 0.22 : 0, now, 0.9);
    const toCanal = Math.abs(p.z + 139);
    this.sluiceGain.gain.setTargetAtTime(Math.max(0, 1 - toCanal / 34) * 0.5 * (1 - inside), now, 0.6);

    // how much trouble we are in, from what the drowned are doing nearby
    let danger = 0;
    let hunted = 0;
    for (const e of s.enemies) {
      if (e.mode === "dead" || e.mode === "dormant") continue;
      const d = Math.hypot(e.x - p.x, e.z - p.z);
      const near = Math.max(0, 1 - d / 26);
      const hunting = e.mode === "chase" || e.mode === "windup" || e.mode === "recover";
      if (hunting) hunted = Math.max(hunted, Math.max(near, 0.35));
      danger = Math.max(danger, near * (hunting ? 1 : 0.35 + e.aware * 0.4));
    }
    this.danger += (danger - this.danger) * Math.min(1, dt * 0.9);
    this.droneGain.gain.setTargetAtTime(0.006 + this.danger * 0.05, now, 0.5);
    this.dreadGain.gain.setTargetAtTime(hunted * 0.014, now, hunted > 0 ? 0.3 : 1.6);

    // heart in the ears when hurt
    if (s.phase === "play" && p.hp <= 50) {
      this.beatT -= dt;
      if (this.beatT <= 0) {
        const bpm = 72 + (50 - p.hp) * 1.1 + hunted * 26;
        this.beatT = 60 / bpm;
        this.heartbeat(now + 0.02, p.hp <= 25 ? 0.42 : 0.26);
        this.count("heartbeat");
      }
    }

    // the siren comes and goes with the wind
    this.sirenT -= dt;
    if (this.sirenT <= 0) {
      this.sirenOn = !this.sirenOn;
      this.sirenT = this.sirenOn ? rnd(16, 26) : rnd(18, 34);
      this.sirenGain.gain.setTargetAtTime(this.sirenOn ? 0.014 * (1 - inside * 0.5) : 0, now, this.sirenOn ? 2.5 : 3.5);
      if (this.sirenOn) this.count("siren");
    }

    // the loudspeakers repeat themselves
    this.radioT -= dt;
    if (this.radioT <= 0 && s.phase === "play") {
      this.radioT = rnd(44, 56);
      this.announce();
    }

    // iron working in the swell: pontoons by the terminal, the sluice, the footbridge
    this.creakT -= dt;
    if (this.creakT <= 0) {
      this.creakT = rnd(7, 15);
      const spots: Pos[] =
        p.z > -30
          ? [
              { x: -18, y: 1, z: 6 },
              { x: 6, y: 1, z: 8 },
            ]
          : p.z < -100
            ? [
                { x: 24.25, y: 2, z: -137 },
                { x: -10, y: 4, z: -138 },
                { x: 16.5, y: 4, z: -121 },
              ]
            : [{ x: p.x + rnd(-14, 14), y: 5, z: p.z + rnd(-22, -8) }];
      const spot = spots[Math.floor(Math.random() * spots.length)] as Pos;
      this.creak(spot, now + 0.05, rnd(1.2, 2.6), rnd(70, 130), p.z < -100 ? 1.6 : 1.1, this.occluded(sim, spot));
      this.count("creak");
    }

    // while the bridge comes down: the chain ratchets and the deck complains
    if (this.bridge && s.bridge.state === "lowering") {
      this.bridgeTick -= dt;
      if (this.bridgeTick <= 0) {
        this.bridgeTick = 0.16;
        const w = sim.level.winch;
        const out = this.voiceOut({ x: w.x, y: 1.5, z: w.z }, 0.55, false, 7);
        this.burst(out, "white", now + 0.01, 0.001, 0.03, 0.8, "bandpass", rnd(2000, 2600), undefined, 4);
        if (Math.random() < 0.09) this.creak({ x: 24.25, y: 3, z: -136 }, now + 0.02, rnd(0.8, 1.6), rnd(90, 150), 1.5);
      }
    } else if (this.bridge && s.bridge.state !== "lowering") {
      this.bridgeStop();
    }
  }

  /** The final mix, so a test can record what a player would hear. */
  get output(): AudioNode | null {
    return this.ctx ? this.analyser : null;
  }

  get context(): AudioContext | null {
    return this.ctx;
  }

  /** Output level right now, for tests and the dev overlay (there are no ears in CI). */
  levels(): Record<string, number> {
    const ctx = this.ctx;
    if (!ctx || !this.scope) return { running: 0 };
    this.analyser.getFloatTimeDomainData(this.scope);
    let peak = 0;
    let sum = 0;
    for (const v of this.scope) {
      const a = Math.abs(v);
      if (a > peak) peak = a;
      sum += v * v;
    }
    this.peakHold = Math.max(this.peakHold * 0.98, peak);
    return {
      running: ctx.state === "running" ? 1 : 0,
      time: ctx.currentTime,
      peak,
      peakHold: this.peakHold,
      rms: Math.sqrt(sum / this.scope.length),
      voice: this.voice ? 1 : 0,
    };
  }
}
