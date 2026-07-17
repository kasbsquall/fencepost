# Fencepost — demo film, v4

**Target 2:24.** Rules cap under 3:00. Audio must name **Codex** and **GPT-5.6**.

**v4 changes came from two agnostic judges who read v3 cold.** Every change below is theirs,
not taste. What they found:

- **The film asserted a green it never checked.** v3 said two prior systems "neither read
  git history, neither run anything." We verified that for the NYU paper. ACM blocked us on
  the Dartmouth paper, so we never confirmed its method — and the README correctly says so.
  The skeptic: *"That is the film doing the thing it accuses the student's test suite of."*
  He was right. The claim is gone.
- **The synthetic fixture was undisclosed.** Both judges called it the film's biggest
  liability. *"A team member reading their own fixture aloud in a voice of discovery."*
  It is now said out loud, early, and it becomes the point instead of the risk.
- **There was no instructor in the film.** Both scored Impact 4–5 for it. *"I can name the
  mechanism. I cannot name the person."* Fixed in scenes 2 and 9.
- **The 403 contradicted the copy.** *"You built an anti-cheating lockout and then told me
  there are no stakes. Nobody cheats on a worksheet with no consequences."* Cut.
- **The Codex beat bragged instead of proving.** *"Twenty-two commits is a productivity
  brag. 'Codex refused to fake the count' is a story only a real build produces."* Rewritten.

**Every number is verified against `.fp_demo` and the repo at the final commit.**

---

## SCENES — narration for `audio_gen.py`

≈310 words ≈ **2:00 spoken**, ~2:24 with pauses. Voice: Will (`bIHbv24MWmeRgasZH58o`).

### 1 — The green lie · 0:00–0:12 · 24 words
> A student hands in their assignment. Every test passes. Green across the board.
> So — did they understand it? Or did an agent write it while they watched?

**Visual:** `pytest -q` → `10 passed in 0.05s`. **Hold 1s, not 2** — the seller judge:
*"a green terminal is the most common opening image in a hackathon reel; if my thumb is
hovering, it hovers there."* Get the words on screen fast.
**SFX:** whoosh f1, pop per dot.

### 2 — The person · 0:12–0:26 · 33 words
> Detection can't answer that, so Fencepost doesn't try. Every instructor already knows
> some of the class used an agent. None of them can prove which — so they grade like
> nobody did. That's the problem.

**Visual:** no papers. A CS2 course, a stack of submissions, one instructor. This is the
beat that buys the Impact score both judges scored at 4–5.
**SFX:** whoosh; alert on "grade like nobody did".

*(The prior-art comparison moves to on-screen text in scene 8, where the viewer has the
context to grade it — and it now claims only what we verified.)*

### 3 — Synthetic, and say so · 0:26–0:46 · 38 words
> This repo is synthetic. We built the student so you can check our work.
>
> Fencepost reads the lines Git attributes to them, then changes one. One character.
> Line thirty-nine, from their own commit. And their ten tests still pass.

**Visual:** `VideoShot3D` of the real report. The diff, big, centered:
`39 −  if k >= len(ordered):` / `+  if k > len(ordered):`
**SFX:** whoosh; stamp on the `−` row.

*Both judges, independently: say it here or the film's best beat becomes its worst. "A
fixture with documented ground truth is how you make execution falsifiable. Right now you
are hiding the thing that proves you were honest."*

### 4 — THE FLIP · 0:46–1:02 · 28 words
> Then GPT-5.6 writes a test that tells the two apart. A sandbox runs it.
>
> Their suite says passed. The generated test says failed. The assertion is the answer key.

**Visual:** the two run rows land **inside 4 seconds** — the seller judge: *"if the
animation eats 4 seconds and the hold eats 2, the scene is all waiting. Land the rows fast
so the silence is on comprehension, not on animation."*
`Their submitted suite — passed · 10 tests · 0.95s`
`Test written by gpt-5.6-terra — failed · 0.60s`
then the quotation: `IndexError: list index out of range`
**### HOLD 2 SECONDS ON THE RED. NO VO, NO MUSIC. Nothing after it — the silence ends the scene.**
**SFX:** chime on `passed`. `error` on the red, alone, in the silence.

### 5 — The receipt · 1:02–1:18 · 31 words
> Here's the part that gets me. Their own commit is titled: fix percentile index out of
> range when p equals one hundred. They fixed it. And their tests never checked it.

**Visual:** the provenance line, isolated:
`c59d8e6 · "fix percentile index out of range when p=100"`
then: **"and their tests never checked it."**
**SFX:** alert on the commit title.

*The seller judge called this the strongest ten seconds in the film — stronger than the
flip. "Scene 4 proves your tool works. Scene 5 proves the problem is real, using the
student's own words as evidence." Keep "here's the part that gets me": it is the only
moment a human appears to be speaking.*

### 6 — The student · 1:18–1:30 · 24 words
> The student answers before they see anything. Then they see what their tests missed.
> They keep their answer. Their instructor sees the same evidence they do.

**Visual:** the real probe: grounding → question → typing → reveal.
**SFX:** pop per screen; soft chime on the reveal.

*Cut: the 403. The skeptic: "you built an anti-cheating lockout and then told me there are
no stakes — both on screen at once." Cut: "No score. No verdict." — an assertion where the
screen already shows the absence.*

### 7 — Codex inside · 1:30–1:56 · 47 words
> Codex wrote this engine. And when it reported a passing gate it hadn't actually run, it
> owned that. But Codex isn't only what built it — it's inside it. Fencepost shells out to
> Codex with GPT-5.6 to write those adversarial tests at runtime, on the instructor's own
> plan. No API key.

**Visual:** live `codex exec -m gpt-5.6-terra` firing, uncut, model flag visible. The
generated test appearing as text nobody typed. Then `killed`. Then the sandbox flags:
`--network none · read-only · no /out mount`.
**SFX:** whoosh; pop per flag; chime on `killed`.

*The skeptic: "the film spends its Codex beat on a productivity brag instead of the story
only a real build produces." The honest beat is better and it is the same length.*

### 8 — Judgment · 1:56–2:10 · 27 words
> It stays quiet on the two functions they got right. And on one change it refused to ask
> about, because the only way to break it was to break the program.

**Visual:** the flow bar `30 caught · 20 to discuss · 1 withheld`, then the rejected test
on screen with the AST rule that killed it. Small on-screen text: *"Two published systems
give AI oral exams over student code. The one we could verify reads no git history and runs
nothing."*
**SFX:** pop per segment; stamp on the withheld block.

*"Unfair" was doing the work of an auditable AST policy. Show the rule. And the prior-art
line now claims only what we checked.*

### 9 — Close · 2:10–2:24 · 30 words
> An instructor points this at one repo. Twenty minutes later, eight questions come back.
> They read them. Nobody else does. That's not a grade. It's a reason to talk to your student.

**Visual:** the report, wide. The wordmark. `pytest tests/integration → 2 passed`. Repo URL.
End card: fence·post, a fan of report / probe / method.
**SFX:** chime on the close.

*The skeptic wrote this beat. "Same length. It names the user, the cost, the cadence, and
the fact that this output does not leave the instructor's hands — which answers the FERPA
question I didn't get to ask."*

---

## Music

Instrumental. Upbeat, warm, forward — *someone found a way through*, not *danger detected*.
Underscore ~0.18, ducked hard under VO, **silent for the 2-second hold in scene 4.**

**No lyrics under the VO.** The rules require the audio to explain Codex and GPT-5.6; a
vocal hook landing on "GPT-5.6" trades a rule for a groove. Lyrics only on the end card,
after the voice stops.

## Shot list

| # | Shot | Source |
|---|---|---|
| 1 | `pytest -q` → 10 passed | terminal |
| 2 | Report: headline + flow bar | `/report` |
| 3 | **The diff rows** | `/report` |
| 4 | **The two run rows + assertion** | `/report` |
| 5 | The provenance line, tight | `/report` |
| 6 | Probe: grounding → question → type → reveal | `:8766` |
| 7 | **The rejected test + the AST rule** | `/report` withheld block |
| 8 | Live `codex exec` firing, uncut | terminal |
| 9 | `pytest tests/integration` → 2 passed | terminal |
| 10 | Landing / report / probe trio | all |

1920x1080. Warm the server; cut from first paint, never a loading state.

## Compliance

**Read against the rules verbatim, not from memory.** An earlier draft of this checklist said
"audio names Codex" and "audio names GPT-5.6". That was the wrong bar. The rule asks for
explanation, not mention:

> "must include a clear demo with audio that covers what you built and how you used Codex
> and GPT-5.6" — [official rules](https://openai.devpost.com/rules)

> "it needs a voiceover which can be recorded yourself or AI-assisted, either works."
> "A screencast with music won't meet the requirement." — [submissions update](https://openai.devpost.com/updates/45282-openai-build-week-submissions-are-open-plugin-launch)

> "must not include third party trademarks, or copyrighted music or other material unless
> the Entrant has permission to use such material" — official rules

- [x] Under 3:00 — ~2:24. *"Judges are not required to watch beyond three minutes."*
- [ ] Public YouTube, link on the submission form
- [x] **Audio covers HOW Codex was used** — scene 7: it wrote the engine, it owned a false
      passing gate, and it runs *inside* the product at runtime. Not a name-drop.
- [x] **Audio covers HOW GPT-5.6 was used** — scene 4 (writes the distinguishing test) and
      scene 7 (the runtime call, on the instructor's own plan).
- [x] **Audio covers what was built** — scenes 1–3.
- [x] AI-assisted voiceover — explicitly allowed. Cartesia `sonic-2`.
- [x] **Music cleared** — Suno Pro grants commercial rights *for songs generated while the
      paid plan is active*. Rights attach at generation time; free-tier songs never convert.
      The track was generated under Pro. This rule is why that mattered.
- [x] Not a screencast with music — there is a voiceover throughout.
- [x] Shows it working — scenes 3–8, real recorded UI
- [x] **Says the repo is synthetic** — scene 3, first line
- [x] Prior-art claim limited to what we verified — scene 8
- [x] Commit count matches the repo (22) and the README
- [x] An instructor is in the film — scenes 2 and 9
