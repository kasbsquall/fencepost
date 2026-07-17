"""Synthesize the film's SFX and music bed. No vendor, no key, no licence question.

Micro-interaction SFX are short transients — a pop is an enveloped sine, a whoosh is
filtered noise with a sweep. Synthesizing them is cheaper and more controllable than
generating them, and every parameter is tuned to the beat it lands on.

The music bed is a warm pad on a slow progression. It sits at ~18% under the voiceover
and goes silent for the hold in scene 4, so it is a cushion, not a composition.

Usage:  python tools/make_audio.py [outdir]
"""

import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 44100


def _env(n, attack, decay, sustain=0.0, release=None):
    """ADSR-ish envelope over n samples, times in seconds."""
    a, d = int(attack * SR), int(decay * SR)
    r = int((release if release is not None else 0.0) * SR)
    s = max(0, n - a - d - r)
    return np.concatenate([
        np.linspace(0, 1, a) ** 0.5 if a else np.array([]),
        np.linspace(1, sustain, d) if d else np.array([]),
        np.full(s, sustain),
        np.linspace(sustain, 0, r) if r else np.array([]),
    ])[:n]


def _sine(f, n, phase=0.0):
    return np.sin(2 * np.pi * f * np.arange(n) / SR + phase)


def _write(path, x, peak=0.7):
    """Normalize to a peak and write a 16-bit mp3 via ffmpeg."""
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * peak
    # tiny fade in/out so nothing clicks
    f = min(256, len(x) // 8)
    if f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    raw = path.with_suffix(".raw")
    raw.write_bytes(pcm.tobytes())
    subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", str(raw),
         "-codec:a", "libmp3lame", "-b:a", "192k", str(path)],
        check=True, capture_output=True,
    )
    raw.unlink()
    return path


# ---------------------------------------------------------------- SFX

def pop(dur=0.09):
    """A soft element-reveal tick. Pitched blip, fast decay, no click."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 880 * np.exp(-t * 14) + 320          # a quick downward chirp
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return x * _env(n, 0.002, dur - 0.002, 0.0)


def whoosh(dur=0.42):
    """Scene transition. Filtered noise swept up then away."""
    n = int(dur * SR)
    noise = np.random.default_rng(7).normal(0, 1, n)
    # cheap one-pole lowpass whose cutoff sweeps: emulate by cumulative smoothing
    out, y = np.zeros(n), 0.0
    cut = np.linspace(0.02, 0.35, n) * np.linspace(1.0, 0.25, n)
    for i in range(n):
        y += cut[i] * (noise[i] - y)
        out[i] = y
    body = out * _env(n, 0.10, 0.32, 0.0)
    return body + 0.25 * _sine(70, n) * _env(n, 0.05, 0.30, 0.0)


def chime(dur=1.1):
    """Success / close. A clean fifth, bell-like decay."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    parts = [(880, 1.0), (1320, 0.55), (1760, 0.28), (2640, 0.12)]
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * (2.2 + i * 1.1))
            for i, (f, a) in enumerate(parts))
    return x * _env(n, 0.003, dur - 0.003, 0.0)


def stamp(dur=0.3):
    """A hit landing. Low thud with a short body."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 180 * np.exp(-t * 30) + 55
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    click = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t * 90) * 0.35
    return (body + click) * _env(n, 0.001, dur - 0.001, 0.0)


def alert(dur=0.5):
    """Emphasis on a headline fact. Two rising notes."""
    n = int(dur * SR)
    h = n // 2
    a = _sine(660, h) * _env(h, 0.004, h / SR - 0.004, 0.0)
    b = _sine(990, n - h) * _env(n - h, 0.004, (n - h) / SR - 0.004, 0.0)
    return np.concatenate([a, b]) * 0.9


def error(dur=0.6):
    """The red assertion. Falling minor second, no cartoon buzz."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 400 * np.exp(-t * 1.6) + 150
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    x += 0.3 * np.sin(2 * np.pi * np.cumsum(f * 0.995) / SR)   # slight beating
    return x * _env(n, 0.006, dur - 0.006, 0.0)


# ---------------------------------------------------------------- music bed

def bed(dur=150.0):
    """A warm pad under the voice. Slow progression, no drums, nothing to compete with.

    Am - F - C - G, four bars each, detuned saws through a soft filter, plus a
    quiet sub pulse so it moves forward without a beat.
    """
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(11)

    roots = [220.00, 174.61, 261.63, 196.00]        # A3 F3 C4 G3
    chords = [[1.0, 1.2, 1.5], [1.0, 1.26, 1.5], [1.0, 1.26, 1.5], [1.0, 1.26, 1.5]]
    bar = dur / 8                                    # two passes over four chords

    out = np.zeros(n)
    for k in range(8):
        r, ratios = roots[k % 4], chords[k % 4]
        s, e = int(k * bar * SR), int(min((k + 1) * bar * SR, n))
        m = e - s
        if m <= 0:
            continue
        seg = np.zeros(m)
        tt = np.arange(m) / SR
        for ratio in ratios:
            f = r * ratio
            for det in (-0.6, 0.0, 0.6):             # three detuned voices
                ph = rng.uniform(0, 2 * np.pi)
                seg += np.sin(2 * np.pi * (f + det) * tt + ph) / 9
        # soften: one-pole lowpass
        y, lp = 0.0, np.zeros(m)
        for i in range(m):
            y += 0.06 * (seg[i] - y)
            lp[i] = y
        seg = lp * _env(m, bar * 0.28, bar * 0.30, 0.85, bar * 0.34)
        out[s:e] += seg

    sub = 0.10 * np.sin(2 * np.pi * 55 * t) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 3.2))
    air = 0.012 * rng.normal(0, 1, n)
    return out * 0.9 + sub + air


def main(outdir="docs/video/audio"):
    d = Path(outdir)
    (d / "sfx").mkdir(parents=True, exist_ok=True)
    for name, fn, peak in [
        ("pop", pop, 0.55), ("whoosh", whoosh, 0.5), ("chime", chime, 0.6),
        ("stamp", stamp, 0.7), ("alert", alert, 0.6), ("error", error, 0.65),
    ]:
        p = _write(d / "sfx" / f"{name}.mp3", fn(), peak=peak)
        print(f"  {p}")
    p = _write(d / "bed.mp3", bed(), peak=0.5)
    print(f"  {p}")


if __name__ == "__main__":
    main(*sys.argv[1:])
