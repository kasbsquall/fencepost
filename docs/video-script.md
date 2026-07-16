# Fencepost — demo video script (v2)

**Hard constraint:** under 3:00. Public YouTube. Audio must cover Codex AND GPT-5.6.

**v1 was 641 words = 3:43 at a normal read.** Two judges counted it independently and both
called it disqualifying. This is **~490 words = 2:45 at 165 wpm, with two real pauses
budgeted.** Every cut below came from a judge, not from taste.

---

## 0:00–0:14 · Open on green

**Screen:** `pytest -q` → `10 passed in 0.05s`. Hold two seconds before speaking.

> A student hands this in. Every test passes.
>
> Detection can't tell you whether they understood it. So Fencepost doesn't try. It assumes
> they used an agent, and asks the one question detection can't: **does this student
> understand the code in their repo?**

*(v1 spent 32 words rebutting AI detection. Every judge in this track already agrees.
Six words now.)*

---

## 0:14–0:26 · The prior art, before they think it

**Screen:** the two papers, side by side, one beat each.

> Two published systems already give AI oral exams over student code. Neither reads git
> history. Neither runs anything.
>
> Fencepost changes the student's own line and asks what breaks — **and the answer isn't in
> the file, so you can't paste it into a chatbot.**

*(All three judges: without this, a reviewer finds NYU and Dartmouth in thirty seconds and
concludes we don't know the field. Five seconds fixes it.)*

---

## 0:26–1:00 · The mechanism, on a synthetic repo we say is synthetic

**Screen:** the report. The proportional bar, then site 1 — open by default.

> This is a synthetic student repo with known ground truth, so you can check every number.
>
> Fencepost uses git blame to keep only the lines this student wrote. Then it changes one.

**Screen:** the diff. `score >= 90` → `score > 90`. Let it sit.

> One character, on line 13, from their own commit.
>
> Their ten tests still pass.

**Screen:** green "10 passed", then — say the line first —

> **A student who scores exactly ninety now gets a B.**

**Screen:** the red assertion appears. `assert 'B' == 'A'`

> Their tests never noticed.

**### PAUSE — two full seconds on the red. Say nothing.**

> GPT-5.6 wrote that test. A sandbox ran it. The failing assertion **is** the answer key —
> no model decided it.

---

## 1:00–1:22 · The student side

**Screen:** probe — grounding, question, typing, submit, reveal.

> The student sees their line and their commit, then the question. They answer before they
> see anything — skip ahead and you get a 403.
>
> Then they see what their tests never checked. No score. No verdict. The red is on the
> assertion, never on the student.

---

## 1:22–1:47 · The refutation — one round, not three

**Screen:** the clamp code, then GPT-5.6's killing test.

> We planted a mutant we could prove was equivalent — at exactly a hundred, both return a
> hundred. We were wrong.
>
> GPT-5.6 killed it with **negative zero**.

**Screen:** `str(clamp_percent(-0.0)) == "-0.0"`

> Then we caught it cheating — monkeypatching our own clamp away to fake a difference that
> can't happen in real code.

**Screen:** `INVALID_CONTRACT` firing, rejecting the model's test in real time.

> So we banned that. An AST rule, not a prompt. **The tool rejects its own model's test.**

**Screen:** the "Deliberately not asked" section.

> That's the question Fencepost decided not to ask. A tool that flags everything found
> nothing.

*(v1 spent 50s and three refutations here. Judges: keep negative zero and the monkeypatch,
cut the Decimal round and the 36,180 — that number belongs in the README.)*

---

## 1:47–2:30 · Codex and GPT-5.6 — slow down, this is the criterion

**Screen:** the live `codex exec -m gpt-5.6-terra` call firing inside the triage loop. Real,
uncut. Then the generated test appearing as text nobody typed. Then `killed`.

> Codex wrote this engine — eighteen commits, one session, feedback ID in the submission.
>
> But Codex isn't only what built it. **It's inside it.** Fencepost shells out to `codex
> exec` with GPT-5.6 to write the adversarial tests at runtime.
>
> **No API key.** It runs on the instructor's own ChatGPT plan — which is the only way a
> tool like this gets installed in a department.

**Screen:** the sandbox flags.

> The generated code runs with no network, a read-only filesystem, and no way to write its
> own results. Two audits; both findings fixed.

*(v1 ran this at 280 wpm — the mandatory disclosure, compressed into the least deliverable
30 seconds. It now gets 43 seconds and the terminal actually fires on screen.)*

---

## 2:30–2:45 · Close

**Screen:** the report summary line, then `rank` and `top_n` clean.

> Their tests caught thirty of fifty-one changes. It stays silent on the two functions they
> got right, and turns what's left into **eight conversations** — not twenty.
>
> That's not a grade. It's a reason to talk to your student.

**Screen:** `pytest tests/integration` → 2 passed. Then the repo URL.

> Two hermetic gates, no model calls, two minutes. Check it yourself.

---

## Shot list

| # | Shot | Why it's here |
|---|---|---|
| 1 | `pytest -q` → 10 passed | the green that gets broken |
| 2 | The two papers | pre-empts the killer objection |
| 3 | Report top: bar + summary | the visual anchor |
| 4 | Site 1: diff → green → **red assertion** | the moment; needs 2s of silence |
| 5 | Probe: grounding → question → reveal | the student side |
| 6 | **`INVALID_CONTRACT` rejecting a model test** | the money shot — judge's words |
| 7 | "Deliberately not asked" | judgment made visible |
| 8 | **Live `codex exec` + generated test + `killed`** | the Codex claim, proven not asserted |
| 9 | Sandbox flags | the IT question every department asks |
| 10 | `pytest tests/integration` → 2 passed | falsifiable |

**Cut from v1:** `git log --oneline` ("proves nothing"), the detection rebuttal, the Decimal
round, "thirty-six thousand combinations", the fixture-flaw and passing-gate honesty beats
(they're the 4th and 5th honesty beats — they live in the README).

## Compliance

- [ ] Under 3:00 — **~490 words ≈ 2:45 at 165 wpm**
- [ ] Public YouTube
- [ ] Audio covers **Codex** — built it, and runs inside it at runtime
- [ ] Audio covers **GPT-5.6** — the model writing the adversarial tests
- [ ] Shows the project working
- [ ] Says the demo repo is synthetic
- [ ] Numbers match the README exactly
