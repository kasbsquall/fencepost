"""Capture a real terminal run with real timings, for the film to replay.

The film asserts that every claim traces back to a run. Three of its shots are terminal
shots, so recreating them in a text editor would be the film doing the exact thing it
accuses the student's green suite of doing.

Screen-recording a terminal window is honest but ugly: it drags Windows Terminal's chrome
into a film that has a design system. So this captures what asciinema captures — the real
bytes with the real timestamps — and Remotion replays them inside the film's own type. The
data is the run. The presentation is the film.

The output timings are wall-clock. If a capture is longer than its scene, that is a fact
about the run, not a rendering knob: trim the scene or speed the replay explicitly and say
so, rather than quietly regenerating a shorter take.

Usage:
    python tools/capture_term.py --out docs/video/casts/pytest.json \
        --cwd demo/student-repo -- python -m pytest -q
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def capture(cmd, cwd, display=None):
    """Run cmd, streaming stdout+stderr, recording (elapsed, text) per chunk."""
    t0 = time.monotonic()
    events = []
    p = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, universal_newlines=True, encoding="utf-8", errors="replace",
    )
    for line in p.stdout:
        events.append({"t": round(time.monotonic() - t0, 3), "s": line.rstrip("\n")})
        sys.stdout.write(line)
        sys.stdout.flush()
    p.wait()
    return {
        "cmd": display or " ".join(cmd),
        "cwd": str(cwd),
        "exit": p.returncode,
        "duration": round(time.monotonic() - t0, 3),
        "events": events,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--display", help="command line to show on screen, if different")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        raise SystemExit("give a command after --")

    cast = capture(cmd, args.cwd, args.display)
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cast, indent=2), encoding="utf-8")

    print(f"\n  -> {p}")
    print(f"     exit {cast['exit']}   {cast['duration']:.2f}s   {len(cast['events'])} lines")


if __name__ == "__main__":
    main()
