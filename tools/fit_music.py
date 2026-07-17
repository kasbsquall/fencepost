"""Fit a generated music track to the film, musically.

Suno has no exact-duration control — you get what it gives you. So the track is always
the wrong length, and cutting it at an arbitrary second sounds like the tape ran out.

This finds the bar boundary nearest the target and fades over two bars, so the ear reads
an ending instead of a cut. It also reports the beat grid in frames, which is what the
Remotion scenes hang their motion off: an element that appears on frame 47 lands on the
beat because 47 is where the beat is.

Usage:
    python tools/fit_music.py <track.mp3> [--seconds 144] [--fps 30] [--out fitted.mp3]
    python tools/fit_music.py <track.mp3> --report        # analyse only, cut nothing
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np


def analyse(path, fps=30):
    y, sr = librosa.load(str(path), sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(beat_frames, sr=sr)
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")

    # Where the track opens up: the loudest sustained stretch. A generated underscore
    # usually has one lift, and the film wants it under its own strongest beat.
    rms = librosa.feature.rms(y=y)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    win = max(1, int(len(rms) * 0.05))
    smooth = np.convolve(rms, np.ones(win) / win, mode="same")
    lift = float(times[int(np.argmax(smooth))])

    return {
        "duration": len(y) / sr,
        "tempo": tempo,
        "seconds_per_bar": 60.0 / tempo * 4,
        "beats": beats,
        "downbeats": beats[::4],
        "onsets": onsets,
        "lift_at": lift,
        "beat_frames": [round(float(t) * fps) for t in beats],
        "downbeat_frames": [round(float(t) * fps) for t in beats[::4]],
    }


def fit(path, out, seconds, fps=30):
    a = analyse(path, fps)
    bar = a["seconds_per_bar"]

    if a["duration"] < seconds:
        raise SystemExit(
            f"track is {a['duration']:.1f}s, shorter than the {seconds:.0f}s film. "
            "Generate a longer one — do not stretch it."
        )

    cut = min(a["downbeats"], key=lambda t: abs(t - seconds))
    fade = bar * 2
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-t", f"{cut:.3f}",
         "-af", f"afade=t=out:st={cut - fade:.3f}:d={fade:.3f}",
         "-codec:a", "libmp3lame", "-b:a", "192k", str(out)],
        check=True, capture_output=True,
    )
    return a, cut, fade


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    ap.add_argument("--seconds", type=float, default=144.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json", default=None, help="write the beat grid for Remotion")
    args = ap.parse_args()

    a = analyse(args.track, args.fps)
    print(f"  duration   {a['duration']:.1f}s")
    print(f"  tempo      {a['tempo']:.1f} BPM   (bar = {a['seconds_per_bar']:.2f}s)")
    print(f"  beats      {len(a['beats'])}   onsets {len(a['onsets'])}")
    print(f"  lift at    {a['lift_at']:.1f}s  ({a['lift_at'] / a['duration'] * 100:.0f}% in)")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "tempo": a["tempo"],
            "fps": args.fps,
            "beatFrames": a["beat_frames"],
            "downbeatFrames": a["downbeat_frames"],
            "liftFrame": round(a["lift_at"] * args.fps),
        }, indent=2), encoding="utf-8")
        print(f"  beat grid -> {args.json}")

    if args.report:
        return

    out = args.out or str(Path(args.track).with_name(Path(args.track).stem + "_fitted.mp3"))
    a, cut, fade = fit(args.track, out, args.seconds, args.fps)
    print(f"\n  cut at     {cut:.2f}s  (target {args.seconds:.0f}s, off by {cut - args.seconds:+.2f}s)")
    print(f"  fade       {fade:.2f}s = 2 bars")
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
