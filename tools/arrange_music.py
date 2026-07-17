"""Build the film's dynamic arc out of a flat generated track.

Suno gave us the tempo we asked for (161.5 BPM against a requested 162) and ignored
every structural instruction in the prompt. Measured, the body of the track lives inside
3 dB from 0:08 to 2:24 — a wall, not an arrangement. Drums enter at 2.5s, so there is no
sparse open, and the "lift" sits 2.5 dB over the mean, which is inaudible under a voice.

The film needs an arc the track does not have, and one thing the track cannot give at all:
two seconds of silence on the red assertion in scene 4. You cannot carve silence out of a
mix with a fader without it sounding like a mistake. You can carve it out of stems.

So: separate, then automate per stem. Every boundary snaps to a real downbeat from the
grid, which is why the drop lands as a decision instead of a dropout.

Usage:
    python tools/arrange_music.py --stems <demucs_out_dir> --grid beatgrid_punk.json \
        --out docs/video/audio/punk_arranged.mp3
"""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
BAR = None  # filled from the grid

# Per-section stem gains, aligned to the 11-scene layout. Each start snaps to the nearest
# downbeat before use; a crossfade over one bar reads as arrangement.
#
# There is no SILENCE section anymore. The first cut dropped every stem to zero on the red
# assertion, and the client asked why the film went quiet — a question that is the verdict.
# Over a red error, total silence reads as an encode dropout. So the flip (scene 5) keeps
# the bed alive; the voice stops there and the band does not, which reads as emphasis. The
# voice-out hold is handled by the VO track and the duck in mix_audio.py, not by killing
# the music here.
#
# The lift lands under scene 9 (Codex, 98.8s), the film's biggest beat, which is where the
# measured grid put the track's loudest sustained stretch anyway.
SECTIONS = [
    (0.0,   "intro",    {"other": 1.00, "bass": 0.00, "drums": 0.00}, False),
    (22.3,  "explain",  {"other": 1.00, "bass": 0.70, "drums": 0.25}, False),
    (37.0,  "mutation", {"other": 1.00, "bass": 0.90, "drums": 0.55}, False),
    (47.3,  "flip",     {"other": 1.00, "bass": 1.00, "drums": 1.00}, False),
    (65.0,  "synth",    {"other": 0.95, "bass": 0.75, "drums": 0.35}, False),
    (75.3,  "receipt",  {"other": 1.00, "bass": 0.95, "drums": 0.70}, False),
    (88.5,  "student",  {"other": 0.92, "bass": 0.75, "drums": 0.30}, False),
    (98.8,  "lift",     {"other": 1.00, "bass": 1.00, "drums": 1.00}, False),
    (119.4, "proof",    {"other": 0.95, "bass": 0.90, "drums": 0.65}, False),
    (135.7, "close",    {"other": 1.00, "bass": 0.90, "drums": 0.80}, False),
]

STEMS = ("drums", "bass", "other")


def snap(t, downbeats):
    return min(downbeats, key=lambda d: abs(d - t))


def load_stems(d):
    """Load demucs output. The vocals stem is folded into `other`: on an instrumental
    track it should be near-silent, and whatever it did catch is guitar we still want."""
    out, sr = {}, None
    for name in ("drums", "bass", "other", "vocals"):
        p = Path(d) / f"{name}.wav"
        if not p.exists():
            raise SystemExit(f"missing stem: {p}")
        y, sr = sf.read(str(p), always_2d=True)
        out[name] = y.mean(axis=1)  # mono; the film's bed is mono anyway
    n = min(len(v) for v in out.values())
    out = {k: v[:n] for k, v in out.items()}

    voc_db = 20 * np.log10(max(np.sqrt(np.mean(out["vocals"] ** 2)), 1e-9))
    oth_db = 20 * np.log10(max(np.sqrt(np.mean(out["other"] ** 2)), 1e-9))
    print(f"  vocals stem RMS {voc_db:6.1f} dB   (other {oth_db:.1f} dB) "
          f"-> {voc_db - oth_db:+.1f} dB relative")
    if voc_db - oth_db > -12:
        print("  WARNING: the vocals stem carries real energy. Either the track is not")
        print("           instrumental, or demucs put guitar there. Listen before trusting.")

    out["other"] = out["other"] + out["vocals"]
    return {k: out[k] for k in STEMS}, sr


def envelope(n, sr, bounds, gains, hard_flags):
    """Piecewise gain over n samples with a one-bar ramp into each section."""
    env = np.zeros(n)
    for i, (start, g) in enumerate(zip(bounds, gains)):
        end = bounds[i + 1] if i + 1 < len(bounds) else n / sr
        s, e = int(start * sr), int(min(end * sr, n))
        if e <= s:
            continue
        env[s:e] = g
        ramp = int((0.02 if hard_flags[i] else BAR) * sr)
        ramp = min(ramp, e - s)
        if ramp > 1 and i > 0:
            env[s:s + ramp] = np.linspace(gains[i - 1], g, ramp)
    return env


def main():
    global BAR
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems", required=True)
    ap.add_argument("--grid", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=144.47)
    args = ap.parse_args()

    grid = json.load(open(args.grid))
    fps = grid["fps"]
    downbeats = [f / fps for f in grid["downbeatFrames"]]
    BAR = 60.0 / grid["tempo"] * 4
    print(f"  tempo {grid['tempo']:.1f} BPM   bar {BAR:.3f}s   downbeats {len(downbeats)}\n")

    stems, sr = load_stems(args.stems)
    if sr != SR:
        print(f"  note: stems are {sr} Hz")
    n = len(next(iter(stems.values())))

    bounds = [snap(t, downbeats) for t, *_ in SECTIONS]
    hard = [h for *_, h in SECTIONS]
    print("\n  arreglo:")
    for (t, name, g, h), b in zip(SECTIONS, bounds):
        mark = "  <- corte duro" if h else ""
        print(f"    {b:7.3f}s  {name:9s}  drums {g['drums']:.2f}  bass {g['bass']:.2f}  "
              f"other {g['other']:.2f}{mark}")

    mix = np.zeros(n)
    for stem in STEMS:
        env = envelope(n, sr, bounds, [g[stem] for _, _, g, _ in SECTIONS], hard)
        mix += stems[stem] * env

    # cut on the bar the fit chose, then fade two bars so the film ends, not stops
    cut = snap(args.seconds, downbeats)
    mix = mix[:int(cut * sr)]
    fade = int(BAR * 2 * sr)
    mix[-fade:] *= np.linspace(1, 0, fade)

    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.89
    print(f"\n  corte {cut:.3f}s   fundido {BAR * 2:.2f}s = 2 compases")

    raw = Path(args.out).with_suffix(".raw")
    (np.clip(mix, -1, 1) * 32767).astype(np.int16).tofile(str(raw))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", str(raw),
         "-codec:a", "libmp3lame", "-b:a", "192k", args.out],
        check=True, capture_output=True,
    )
    raw.unlink()
    print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
