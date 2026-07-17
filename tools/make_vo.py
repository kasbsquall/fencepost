"""Generate the film's voiceover, one file per scene, then verify it out loud.

The rules do not ask the audio to name Codex and GPT-5.6. They ask it to cover "what you
built and how you used Codex and GPT-5.6". Scene 7 carries that weight, so if the model
mangles "GPT-5.6" into something a listener cannot parse, the submission's headline
requirement is the thing that breaks.

So this does not trust the synthesis. It transcribes the generated audio back with Whisper
and checks that the model names survived the round trip. If Whisper cannot hear them, a
judge cannot either. The same pass returns word-level timings, which is what Remotion needs
to hang text off the voice.

One file per scene, not one long take: scene boundaries are fixed by the beat grid, and a
single take would force the edit to chase the voice instead of the bar.

Usage:
    CARTESIA_API_KEY=... python tools/make_vo.py [--voice <id>] [--outdir docs/video/audio/vo]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

API = "https://api.cartesia.ai/tts/bytes"
MODEL = "sonic-2"
MARVIN = "49808e4c-998a-40a8-b2ea-8ac8e8ce779e"   # Steady Ally

# v5. Three agnostic reviewers read the rendered cut and the client watched it and said he
# did not understand it. They independently landed on the same failure: across 2:24 nobody
# ever says what Fencepost does. The film showed a diff and assumed the viewer would infer
# mutation-based probing from it. Scene 3 below is that missing sentence, and it is why the
# other scenes got shorter.
#
# What paid for it, per the reviewers: scene 2 spent 14s on a grid of tiles measured at
# 1.05:1 contrast (invisible), scene 7 spent 5s on a JSON dump that proves nothing to a
# human, and scene 8 spent 4s on 20px prior-art text nobody reads in three seconds.
#
# The ceiling is 2:28, not the 2:52 a reviewer wanted: the track is 152.3s and the last
# usable bar-aligned cut with a two-bar fade is 148.90s. Music decides the runtime.
#
# Em dashes become commas: the synthesiser reads punctuation literally and an em dash lands
# as an odd stall.
SCENES = {
    1: "A student hands in their assignment. Every test passes. So, did they understand "
       "it? Or did an agent write it while they watched?",
    2: "Detection can't answer that. Every instructor already knows some of the class used "
       "an agent. None of them can prove which, so they grade like nobody did.",
    # THE MISSING BEAT. Says the mechanism as one causal sentence, then puts the real report
    # on screen at 0:24 instead of 1:18. "Git blame" not "Git attributes": the latter
    # synthesised close enough to "get attributes" that Whisper heard the latter, and it is
    # also the command the tool actually runs.
    # "Git" lost to "get" across two takes and two Whisper models. They are a minimal pair
    # (/ɡɪt/ vs /ɡɛt/) and the language model wins every time on the commoner word. Two
    # rewrites bought nothing, so the jargon moves to where jargon belongs: the screen shows
    # `git blame -M -C -C -w` in scene 4, and the voice says the thing a judge actually needs
    # to understand, which is that the line is the student's own. Same claim, no minimal pair.
    3: "So Fencepost doesn't detect. It takes a line from the student's own commit, changes "
       "one character, and runs their own tests against it. If their tests don't notice, "
       "they never checked it. Here's what an instructor gets back.",
    4: "Here. Line thirty-nine, from their own commit. Greater-or-equal becomes greater. "
       "One character. And their ten tests still pass.",
    5: "So GPT-5.6 writes a test that tells the original and the mutant apart. A sandbox "
       "runs both. Their suite says passed. The generated test says failed. The assertion "
       "is the answer key.",
    # Relocated from 0:26. Early, it apologised before the viewer knew what for. Here, the
    # judge has just watched the flip and is asking whether it was rigged.
    6: "This student is synthetic. We built them, with documented ground truth, so you can "
       "check every number in this film without an API key.",
    7: "Here's the part that gets me. Their own commit is titled: fix percentile index out "
       "of range when p equals one hundred. They fixed it. And their tests never checked it.",
    8: "The student answers before they see anything. Then they see what their tests missed. "
       "They keep their answer. Their instructor sees the same evidence they do.",
    # "a passing gate" slurred into one word, "passengate". Whisper could not split it and a
    # listener would not either. Saying the gate passed, as a clause, forces the break.
    9: "Codex wrote this engine. And when it told us a test gate had passed, without ever "
       "running it, Codex owned that. But Codex isn't only what built it. It's inside it. "
       "Fencepost shells out to Codex with GPT-5.6 to write those adversarial tests at "
       "runtime, on the instructor's own plan. No API key.",
    # The proof beat. The reviewers all flagged that the strongest evidence in the README —
    # the model refuting its own authors — never reached the film.
    10: "Fifty-one changes. Thirty caught by their own tests, and we stay silent on those. "
        "One we refused to ask about, because the only way to break it was to break the "
        "program. GPT-5.6 refuted us twice on that, and we printed both.",
    # "nothing leaves your hands" was false: the student's code is sent to a hosted GPT-5.6
    # to write the test, which scene 9 shows. A judge flagged the contradiction. The honest
    # claim, still strong: the report and the student's answers stay local; only the code
    # they already submitted crosses to the model.
    11: "It's MIT. It runs on your own plan, and the report never leaves your hands. We want "
        "one CS2 section this fall. That's not a grade. It's a reason to talk to your student.",
}

# The submission lives or dies on these surviving synthesis intelligibly. Each entry is a
# list of acceptable spellings; any one of them passes.
#
# "5.6" is checked separately from "gpt": the rule names the version, and an earlier pass
# went green on "GPT" alone while saying nothing about whether the number survived.
# "blame" and "gate" are here because both failed a round trip once already.
#
# "kodex" counts as Codex. base.en has no such token and spells the product name from the
# phonemes, and phonemes are precisely what this checks — a listener who knows the product
# hears it. That is a different event from "passing gate" collapsing into "passengate",
# where the phonemes merged and no listener could split them. That one still fails.
MUST_HEAR = {
    # scene 3 no longer says "Git blame" — see the note on its text. The screen carries it.
    3: [["own commit"]],
    5: [["gpt"], ["5.6"]],
    9: [["codex", "kodex"], ["gpt"], ["5.6"], ["gate"]],
    10: [["gpt"], ["5.6"]],
}


def synth(text, voice, key, out):
    r = requests.post(
        API,
        headers={"X-API-Key": key, "Cartesia-Version": "2024-06-10",
                 "Content-Type": "application/json"},
        json={"model_id": MODEL, "transcript": text,
              "voice": {"mode": "id", "id": voice},
              "output_format": {"container": "mp3", "sample_rate": 44100,
                                "bit_rate": 128000},
              "language": "en"},
        timeout=120,
    )
    if r.status_code != 200:
        raise SystemExit(f"cartesia {r.status_code}: {r.text[:200]}")
    out.write_bytes(r.content)
    return len(r.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=MARVIN)
    ap.add_argument("--outdir", default="docs/video/audio/vo")
    ap.add_argument("--no-verify", action="store_true")
    # Re-synthesising to re-check moves the target: sonic-2 is not deterministic, so the
    # audio under test changes every run. Verify the take you actually have.
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    d = Path(args.outdir)
    d.mkdir(parents=True, exist_ok=True)

    import librosa
    if not args.verify_only:
        key = os.environ.get("CARTESIA_API_KEY")
        if not key:
            raise SystemExit("set CARTESIA_API_KEY")
        total = 0.0
        for n, text in SCENES.items():
            p = d / f"scene{n:02d}.mp3"
            synth(text, args.voice, key, p)
            dur = librosa.get_duration(path=str(p))
            total += dur
            words = len(text.split())
            print(f"  scene {n}  {dur:5.2f}s  {words:3d} words  {dur/words:.3f} s/word")
        print(f"\n  spoken total {total:.1f}s = {int(total//60)}:{total%60:04.1f}")
        print(f"  script budget 2:00 spoken -> 2:24 with pauses")

    if args.no_verify:
        return

    print("\n  transcribing back (the model names must survive synthesis)...")
    from faster_whisper import WhisperModel
    # small.en, not base.en. Not because it agrees with us — because base.en was shown to
    # be the unreliable instrument. Over the full film it transcribed "Codex" as "codecs"
    # (a near-homophone and a commoner word) at every occurrence. Given the same audio in
    # isolation, base.en itself hears "CodeX", with no priming. The difference is Whisper
    # conditioning on its own prior text over a long take: once it commits to "codecs" it
    # repeats it. small.en gets it right either way. Four of five measurements agreed, and
    # the outlier has a known failure mode.
    w = WhisperModel("small.en", device="cpu", compute_type="int8")

    timings = {}
    ok = True
    for n in SCENES:
        segs, _ = w.transcribe(str(d / f"scene{n:02d}.mp3"), word_timestamps=True)
        words = [{"w": x.word.strip(), "start": round(x.start, 3), "end": round(x.end, 3)}
                 for s in segs for x in s.words]
        timings[n] = words
        heard = " ".join(x["w"] for x in words).lower()
        # Whisper returns "GPT -5 .6" — spaced and hyphenated. Searching the raw string for
        # "5.6" would report a miss on audio that says it perfectly.
        flat = re.sub(r"[\s\-]", "", heard)
        for spellings in MUST_HEAR.get(n, []):
            hit = next((s for s in spellings
                        if re.sub(r"[\s\-]", "", s) in flat), None)
            if hit is None:
                print(f"    scene {n}: FAIL, {spellings} not heard -> {heard[:90]}")
                ok = False
            else:
                note = "" if hit == spellings[0] else f"  (heard as '{hit}')"
                print(f"    scene {n}: '{spellings[0]}' ok{note}")

    (d / "word_timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
    print(f"\n  word timings -> {d / 'word_timings.json'}")
    if not ok:
        print("\n  A required model name did not survive. Rewrite it phonetically and rerun.")
        sys.exit(1)


if __name__ == "__main__":
    main()
