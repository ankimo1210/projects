#!/usr/bin/env python3
"""Generate NeonThread placeholder audio assets (synth SFX + synthwave BGM loop).

Stdlib only. Writes 16-bit .wav files to Tools/build_audio/.
Convert to .caf for the app bundle (gapless, small) with:

    afconvert -f caff -d ima4 in.wav out.caf

Assets:
    sfx_button.wav    short UI blip
    sfx_start.wav     rising sweep (game start)
    sfx_hit.wav       noise burst + pitch drop (obstacle hit)
    sfx_gameover.wav  descending minor arpeggio
    bgm_loop.wav      8-bar synthwave loop in A minor, 110 BPM (stereo)
"""

import math
import os
import random
import struct
import wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_audio")

random.seed(1210)  # reproducible noise


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def zeros(dur):
    return [0.0] * int(dur * SR)


def add(dst, src, at=0.0):
    i0 = int(at * SR)
    for i, v in enumerate(src):
        j = i0 + i
        if 0 <= j < len(dst):
            dst[j] += v


def lowpass(x, fc):
    a = 1 - math.exp(-2 * math.pi * fc / SR)
    y = 0.0
    out = []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def normalize(x, peak=0.9):
    m = max(1e-9, max(abs(v) for v in x))
    return [v * peak / m for v in x]


def sine(p):
    return math.sin(2 * math.pi * p)


def saw(p):
    return 2 * (p % 1.0) - 1


def square(p, duty=0.5):
    return 1.0 if (p % 1.0) < duty else -1.0


def sq30(p):
    return square(p, 0.3)


def tone(freq, dur, wave_fn, attack=0.005, decay=8.0, freq_end=None):
    n = int(dur * SR)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = freq if freq_end is None else freq + (freq_end - freq) * (t / dur)
        phase += f / SR
        env = min(1.0, t / attack) * math.exp(-t * decay)
        out.append(wave_fn(phase) * env)
    return out


def pad_tone(freq, dur, attack=0.4):
    """Detuned saw pair with slow attack, for chord pads."""
    n = int(dur * SR)
    out = []
    p1 = p2 = 0.0
    release = dur - 0.3
    for i in range(n):
        t = i / SR
        p1 += freq * 1.004 / SR
        p2 += freq / 1.004 / SR
        env = min(1.0, t / attack)
        if t > release:
            env *= max(0.0, 1 - (t - release) / 0.3)
        out.append((saw(p1) + saw(p2)) * 0.5 * env)
    return out


def noise_burst(dur, decay):
    return [random.uniform(-1, 1) * math.exp(-i / SR * decay) for i in range(int(dur * SR))]


def write_wav(name, mono=None, stereo=None):
    path = os.path.join(OUT, name)
    with wave.open(path, "w") as w:
        w.setsampwidth(2)
        w.setframerate(SR)
        if mono is not None:
            w.setnchannels(1)
            data = b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in mono
            )
        else:
            w.setnchannels(2)
            left, right = stereo
            data = b"".join(
                struct.pack(
                    "<hh",
                    int(max(-1.0, min(1.0, l)) * 32767),
                    int(max(-1.0, min(1.0, r)) * 32767),
                )
                for l, r in zip(left, right)
            )
        w.writeframes(data)
    print("wrote", path)


# ---------------------------------------------------------------- SFX

def gen_button():
    blip = tone(1500, 0.07, lambda p: square(p, 0.4), decay=45, freq_end=1900)
    write_wav("sfx_button.wav", mono=normalize(blip, 0.7))


def gen_start():
    sweep = tone(250, 0.35, saw, attack=0.01, decay=6, freq_end=950)
    shimmer = tone(500, 0.35, sq30, attack=0.01, decay=8, freq_end=1900)
    mix = [a + 0.3 * b for a, b in zip(sweep, shimmer)]
    write_wav("sfx_start.wav", mono=normalize(mix, 0.8))


def gen_hit():
    crunch = noise_burst(0.25, 30)
    thud = tone(380, 0.22, square, decay=14, freq_end=110)
    mix = zeros(0.25)
    add(mix, [v * 0.8 for v in crunch])
    add(mix, thud)
    write_wav("sfx_hit.wav", mono=normalize(mix, 0.95))


def gen_coin():
    voice = lambda p: 0.5 * sine(p) + 0.5 * square(p, 0.4)
    mix = zeros(0.22)
    add(mix, tone(1318, 0.07, voice, decay=20))       # E6
    add(mix, tone(1976, 0.14, voice, decay=16), 0.06)  # B6
    write_wav("sfx_coin.wav", mono=normalize(mix, 0.75))


def gen_gameover():
    voice = lambda p: 0.6 * saw(p) + 0.4 * square(p)
    mix = zeros(1.3)
    for i, m in enumerate([69, 64, 60]):  # A4 E4 C4
        add(mix, tone(midi(m), 0.18, voice, decay=12), i * 0.14)
    add(mix, tone(midi(57), 0.85, voice, decay=4), 3 * 0.14)  # A3 with tail
    write_wav("sfx_gameover.wav", mono=normalize(mix, 0.85))


# ---------------------------------------------------------------- BGM

BPM = 110
BEAT = 60.0 / BPM
BARS = 8
TOTAL = BARS * 4 * BEAT
CHORDS = [  # (bass midi, chord tone midis) — Am F C G, 2 bars each
    (45, [57, 60, 64]),
    (41, [53, 57, 60]),
    (48, [60, 64, 67]),
    (43, [55, 59, 62]),
]


def chord_at(t):
    bar = int(t // (4 * BEAT)) % BARS
    return CHORDS[bar // 2]


def gen_bgm():
    bass = zeros(TOTAL)
    for e in range(BARS * 8):  # eighth notes
        t = e * BEAT / 2
        root, _ = chord_at(t)
        add(bass, tone(midi(root), BEAT / 2 * 0.9, saw, decay=6), t)
    bass = lowpass(bass, 350)

    kick = zeros(TOTAL)
    hat = zeros(TOTAL)
    for b in range(BARS * 4):
        add(kick, tone(120, 0.09, sine, attack=0.001, decay=28, freq_end=45), b * BEAT)
        add(hat, noise_burst(0.04, 90), b * BEAT + BEAT / 2)

    pad = zeros(TOTAL)
    for seg in range(4):
        t = seg * 2 * 4 * BEAT
        _, tones = CHORDS[seg]
        for m in tones:
            add(pad, pad_tone(midi(m), 2 * 4 * BEAT), t)
    pad = lowpass(pad, 900)

    arp = zeros(TOTAL)
    sixteenth = BEAT / 4
    for k in range(BARS * 16):
        t = k * sixteenth
        _, tones = chord_at(t)
        note = tones[k % 4 % 3] + (12 if (k // 8) % 2 else 0)
        add(arp, tone(midi(note), sixteenth * 0.95, sq30, decay=20), t)

    delay = int(3 * sixteenth * SR)
    echo_l = zeros(TOTAL)
    echo_r = zeros(TOTAL)
    for i, v in enumerate(arp):
        if i + delay < len(echo_l):
            echo_l[i + delay] += v * 0.4
        if i + 2 * delay < len(echo_r):
            echo_r[i + 2 * delay] += v * 0.28

    n = len(bass)

    def mix(echo):
        out = []
        for i in range(n):
            v = (
                bass[i] * 0.5
                + kick[i] * 0.85
                + hat[i] * 0.15
                + pad[i] * 0.22
                + arp[i] * 0.3
                + echo[i] * 0.25
            )
            out.append(math.tanh(1.4 * v))
        return out

    left, right = mix(echo_l), mix(echo_r)
    peak = max(max(abs(v) for v in left), max(abs(v) for v in right))
    left = [v * 0.85 / peak for v in left]
    right = [v * 0.85 / peak for v in right]
    write_wav("bgm_loop.wav", stereo=(left, right))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    gen_button()
    gen_start()
    gen_hit()
    gen_coin()
    gen_gameover()
    gen_bgm()
