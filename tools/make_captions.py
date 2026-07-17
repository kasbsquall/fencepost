"""Burn-ready captions: the real script text on the ASR's timings.

The word timings in word_timings.json are good — they are where Whisper heard each word. The
TEXT is not: it says "Kodex" in the Codex scene, splits "GPT -5 .6" across three tokens, and
carries a stray "//". Burning it verbatim would put "Kodex" on screen in the exact beat the
rules require to name Codex, and YouTube's auto-caption is the same class of model that will
make the same mistake — which is the whole reason to burn our own.

So this keeps the timings and replaces the text. Each scene's ASR tokens are aligned against
the true script with difflib: on a match, copy the timing; on a replacement, spread the ASR
span across the script tokens by length; on a deletion, drop it; on an insertion, borrow from
the neighbour. Times become absolute via layout.json's voAt, the one source the mix and the
picture also read.

Emits captions.json for the burned overlay and fencepost.srt to suppress YouTube's auto-CC.

Usage:  python tools/make_captions.py
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from make_vo import SCENES  # the true script, one entry per scene

FPS = 30
LAYOUT = json.loads(Path("video/src/layout.json").read_text("utf-8"))
VO_AT = {s["n"]: s["voAt"] for s in LAYOUT["scenes"]}
TIMINGS = json.loads(Path("video/public/casts/word_timings.json").read_text("utf-8"))

norm = lambda w: re.sub(r"[^a-z0-9.]", "", w.lower())


def align(script_text, asr):
    """Return [(word, start, end)] for the script words, borrowing ASR timings."""
    script = script_text.split()
    a = [norm(w) for w in script]
    b = [norm(x["w"]) for x in asr]
    out = [None] * len(script)

    sm = SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = (asr[j1 + k]["start"], asr[j1 + k]["end"])
        elif tag in ("replace", "delete"):
            # Spread the matched ASR span (if any) across the script words by count.
            if j2 > j1:
                s, e = asr[j1]["start"], asr[j2 - 1]["end"]
            else:
                # deletion with no ASR span: borrow the gap around it later
                s = e = None
            span = (i2 - i1)
            for k in range(span):
                if s is None:
                    out[i1 + k] = None
                else:
                    out[i1 + k] = (s + (e - s) * k / span, s + (e - s) * (k + 1) / span)
        # 'insert' means ASR heard words the script does not have -> ignore them

    # Fill any gaps by interpolating from known neighbours, so no word is timeless.
    known = [(i, t) for i, t in enumerate(out) if t]
    for i, t in enumerate(out):
        if t:
            continue
        prev = max((k for k, _ in known if k < i), default=None)
        nxt = min((k for k, _ in known if k > i), default=None)
        if prev is not None and nxt is not None:
            ps, pe = out[prev]
            ns, ne = out[nxt]
            frac = (i - prev) / (nxt - prev)
            mid = pe + (ns - pe) * frac
            out[i] = (mid, mid + 0.3)
        elif prev is not None:
            pe = out[prev][1]
            out[i] = (pe, pe + 0.3)
        elif nxt is not None:
            ns = out[nxt][0]
            out[i] = (max(0, ns - 0.3), ns)
        else:
            out[i] = (0.0, 0.3)
    return [(script[i], out[i][0], out[i][1]) for i in range(len(script))]


def group_lines(words, max_chars=42):
    """Pack words into caption lines of at most max_chars."""
    lines, cur, start = [], [], None
    for w, s, e in words:
        if not cur:
            start = s
        if sum(len(x) + 1 for x in cur) + len(w) > max_chars and cur:
            lines.append((" ".join(cur), start, prev_e))
            cur, start = [w], s
        else:
            cur.append(w)
        prev_e = e
    if cur:
        lines.append((" ".join(cur), start, prev_e))
    return lines


def srt_time(t):
    h, m = divmod(int(t) // 60, 60)
    s = t - int(t) // 60 * 60
    return f"{h:02d}:{m % 60:02d}:{s:06.3f}".replace(".", ",")


def main():
    caption_words = []   # for the burned karaoke overlay
    srt_lines = []       # for YouTube

    idx = 1
    for n, text in SCENES.items():
        asr = TIMINGS.get(str(n), [])
        if not asr:
            continue
        base = VO_AT[n] / FPS
        aligned = [(w, base + s, base + e) for w, s, e in align(text, asr)]
        caption_words.extend({"w": w, "t": round(s, 3), "e": round(e, 3)} for w, s, e in aligned)

        for line, s, e in group_lines(aligned):
            srt_lines.append(f"{idx}\n{srt_time(s)} --> {srt_time(e)}\n{line}\n")
            idx += 1

    Path("video/public/casts/captions.json").write_text(
        json.dumps(caption_words, indent=2), encoding="utf-8")
    Path("out").mkdir(exist_ok=True)
    Path("out/fencepost.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    print(f"  {len(caption_words)} palabras, {idx - 1} lineas de subtitulo")
    print(f"  -> video/public/casts/captions.json")
    print(f"  -> out/fencepost.srt")
    # Show that the traps are fixed: these must read the SCRIPT text, not the ASR.
    joined = " ".join(w["w"] for w in caption_words).lower()
    for bad, why in [("kodex", "Codex misheard"), ("//", "stray token"), ("getblame", "git merge")]:
        print(f"    '{bad}' ({why}): {'PRESENTE, mal' if bad in joined else 'ausente, ok'}")
    print(f"    'codex' presente: {'si' if 'codex' in joined else 'NO'}")
    print(f"    'gpt-5.6' presente: {'si' if 'gpt-5.6' in joined else 'NO'}")


if __name__ == "__main__":
    main()
