# Fencepost

A comprehension probe for programming courses, for the era where a coding agent
can complete the assignment for the student.

Named after Chesterton's Fence (don't remove a fence until you know why it's
there) and the fencepost error (off-by-one), which is the bug class this thing
is best at surfacing.

## The thesis

Detecting AI-written code does not work and is not worth doing. Fencepost does
not try. It assumes the student may have used an agent, and asks a different
question that detection cannot answer: **does this student understand the code
in their repo?**

The answer is grounded in execution, never in a model's opinion. Every question
Fencepost asks has a ground truth we obtained by running code.

## The mechanism

1. **Attribute.** `git blame -M -C -C -w` over the student's repo. Keep only
   lines the student authored. Instructor scaffold is out of scope. Move/copy
   detection matters: grounding a question in a line the student did not write
   destroys credibility instantly.

2. **Select.** Of those lines, keep the ones covered by the student's own tests.
   An uncovered line has nothing to survive.

3. **Mutate.** AST-level operators via the `ast` module (`ast.unparse`, py3.9+).
   One node change per mutant. Text substitution is not acceptable: it produces
   invalid code and cannot be reasoned about. Operator families: comparison
   (`<`/`<=`, `>`/`>=`, `==`/`!=`), boundary (`n` -> `n±1`), arithmetic,
   boolean (`and`/`or`, drop `not`), return (`return x` -> `return None`),
   constants.

4. **Execute.** Run the student's pytest suite against each mutant in a Docker
   sandbox. Classify:
   - `killed`   - a student test failed. Their tests cover this. Not interesting.
   - `survived` - all tests pass. Either a comprehension gap or an equivalent mutant.
   - `broken`   - syntax/import error. Discard, it is a bug in our operator.

5. **Triage the survivors.** This is the core of the project and the hardest part.
   A survivor is either a real gap (behavior changed, tests do not check it) or
   equivalent (behavior genuinely unchanged). Distinguishing them is undecidable
   in general, so we resolve it empirically:

   Ask Codex to write an aggressive adversarial test targeting that specific
   function, then re-run.
   - Strong test kills it -> **real gap**. Best probe target. We now know exactly
     what breaks, which is the ground truth for grading the answer.
   - Nothing kills it after N attempts -> **probable equivalent**. Discard.

   This must emit a **measurable equivalent rate**. That number is the project's
   credibility. If we cannot state it, we do not have a system.

6. **Probe.** GPT-5.6 generates the question from the surviving gap mutant plus
   diff context and blame metadata. It grades the student's answer against the
   execution result we already computed. The model phrases and evaluates; it does
   not decide truth.

7. **Report.** Formative. "Here are the N places your understanding is
   unverified, and here is what breaks." Human in the loop. Never a verdict,
   never an accusation, never a score that stands on its own.

## Non-negotiables

- **Formative, not summative.** No AI-detection framing anywhere in the product,
  the copy, or the report. Output is advisory and assumes an instructor reads it.
- **Python + pytest only.** Multi-language support is out of scope and will kill
  the timeline. One language done properly beats three done badly.
- **Execution is the ground truth.** If a claim in the report is not backed by a
  test run we performed, it does not go in the report.
- **Equivalent mutants must be handled explicitly**, not ignored. Asking a student
  about a behaviorally-identical mutant is a question with no correct answer.

## Scope

In: the six stages above, a CLI entry point, a minimal web UI showing the diff,
the mutant, and the test going red.

Out: VS Code extension, LMS integration, auth, multi-language, user accounts,
persistence beyond a run artifact.

## Sample data

`python demo/build_demo_repo.py` builds a synthetic student submission with
realistic git history: an instructor scaffold commit, then a week of student
commits. The student's 9 tests all pass. Known ground truth in that repo:

- `letter_grade`: `score >= 90` -> `score > 90` **survives**. Consequence: a
  student scoring exactly 90 receives a B. Same for the 80/70/60 boundaries.
- `percentile`: `k >= len(ordered)` -> `k > len(ordered)` **survives**, and
  `percentile(scores, 100)` then raises IndexError. The student's own commit
  c59d8e6 is titled "fix percentile index out of range when p=100". They wrote
  the fence and never verified it.
- `rank`, `top_n`: their mutants are **killed**. The tool must not flag these.
  A tool that flags everything is a tool that found nothing.

Use this repo as the fixture. If Fencepost cannot reproduce the classifications
above, it is wrong.

Note on the `score >= 60` boundary: the only test that reaches that line is
`test_letter_grade_f`, which comes from the instructor's starter commit. The
student's own tests all return before it. This is deliberate and must not be
"fixed" in the fixture. It encodes the rule: **blame filters what we mutate, not
which tests we run**. Attribution answers "did the student write this code", and
the suite runs exactly as submitted. Filtering the test suite by authorship would
drop this mutant and would also be conceptually wrong.

## Division of labour

Codex builds the engine (stages 1-7) and the interfaces. The spec, the demo
fixture, the README narrative and the video are the human's.
