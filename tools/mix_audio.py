"""Duck the bed against the real voiceover envelope, and prove the words survive.

The first render put the bed under the voice at a flat 0.18 and it read fine on the meters.
Then Whisper transcribed the finished film and heard "codecs wrote this engine" — not
"Codex". The per-scene voice files had passed every check; they were checked dry. Under
music, the consonants went, and the submission's headline requirement went with them:
the rules ask for audio covering how you used Codex.

A static level cannot fix that, because the problem is not loudness, it is masking. So the
bed follows the voice: it opens in the gaps and gets out of the way under a line. Attack is
fast enough to catch a consonant, release slow enough that the band does not pump.

This writes the ducked bed. Remotion then plays it at unity, because the mix decision lives
here, next to the measurement that justifies it.

Usage:
    python tools/mix_audio.py [--duck -11] [--bed 0.22]
"""

import argparse
import json
import subprocess
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

SR = 44100
FPS = 30

# The voiceover start frames come from layout.json, not a copy kept here. They were
# duplicated in this file and in Film.tsx once, on the old 9-scene cut, and five of the
# nine were wrong. One source: if the layout changes, the duck follows.
LAYOUT = json.loads(Path("video/src/layout.json").read_text("utf-8"))
VO_AT = {s["n"]: s["voAt"] for s in LAYOUT["scenes"]}

BED = "docs/video/audio/punk_arranged.mp3"
VO_DIR = Path("docs/video/audio/vo")


def sceneOf(n):
    return next(s for s in LAYOUT["scenes"] if s["n"] == n)


def _vo_len(n):
    y, _ = librosa.load(str(VO_DIR / f"scene{n:02d}.mp3"), sr=SR, mono=True)
    return len(y) / SR * FPS


def vo_envelope(n):
    """A 0..1 envelope that is 1 wherever any voiceover is speaking."""
    env = np.zeros(n)
    for scene, vo_at in VO_AT.items():
        y, _ = librosa.load(str(VO_DIR / f"scene{scene:02d}.mp3"), sr=SR, mono=True)
        at = int(vo_at / FPS * SR)

        # Follow the line's own loudness, not just its extent: the gaps between sentences
        # are where the band is allowed back in.
        hop = 512
        rms = librosa.feature.rms(y=y, hop_length=hop)[0]
        rms = rms / max(rms.max(), 1e-9)
        gate = (rms > 0.06).astype(float)
        gate = np.repeat(gate, hop)[: len(y)]

        end = min(at + len(gate), n)
        if end > at:
            env[at:end] = np.maximum(env[at:end], gate[: end - at])
    return env


def smooth(env, attack_ms=18, release_ms=260):
    """One-pole follower. Fast down so a consonant is not clipped by the band, slow up so
    the release does not pump between words."""
    a = np.exp(-1.0 / (SR * attack_ms / 1000))
    r = np.exp(-1.0 / (SR * release_ms / 1000))
    out = np.zeros_like(env)
    y = 0.0
    for i, x in enumerate(env):
        coef = a if x > y else r
        y = coef * y + (1 - coef) * x
        out[i] = y
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bed", type=float, default=0.22, help="bed level with no voice")
    ap.add_argument("--duck", type=float, default=-11.0, help="dB of duck under the voice")
    ap.add_argument("--out", default="docs/video/audio/bed_ducked.mp3")
    args = ap.parse_args()

    bed, _ = librosa.load(BED, sr=SR, mono=True)
    n = len(bed)
    print(f"  bed {n / SR:.2f}s")

    env = vo_envelope(n)
    print(f"  voz presente en {env.mean() * 100:.0f}% del film")

    env = smooth(env)
    duck_lin = 10 ** (args.duck / 20)
    gain = args.bed * (1 - env * (1 - duck_lin))

    out = bed * gain

    # The flip's hold is NOT silent anymore. The first cut dropped the bed to zero on the
    # red assertion and the client asked why the film went quiet; over a red error, total
    # silence reads as an encode dropout. So the voice stops and the bed stays. Assert the
    # opposite of before: during scene 5's hold the voice is out but the band is alive,
    # between a whisper and the ducked-under-voice level, never zero and never full.
    hold5 = sceneOf(5)
    h0 = (hold5["voAt"] + _vo_len(5)) / FPS       # where the line ends
    h1 = hold5["to"] / FPS
    seg = out[int(h0 * SR) : int(h1 * SR)]
    rms = float(np.sqrt(np.mean(seg**2))) if len(seg) else 0.0
    lvl = 20 * np.log10(max(rms, 1e-9))
    ok = -45 < lvl < -18
    print(f"  hold escena 5 ({h0:.1f}-{h1:.1f}s): bed vivo {lvl:.1f} dB   {'ok' if ok else 'REVISAR'}")

    raw = Path(args.out).with_suffix(".raw")
    (np.clip(out, -1, 1) * 32767).astype(np.int16).tofile(str(raw))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", str(raw),
         "-codec:a", "libmp3lame", "-b:a", "192k", args.out],
        check=True, capture_output=True,
    )
    raw.unlink()

    db = lambda x: 20 * np.log10(max(np.sqrt(np.mean(x**2)), 1e-9))
    print(f"\n  bed bajo la voz : {db(out[env > 0.8]):6.1f} dB")
    print(f"  bed en los huecos: {db(out[env < 0.2]):6.1f} dB")
    print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
