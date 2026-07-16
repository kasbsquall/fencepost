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

   Selection also records an **authored-line coverage precondition**: the fraction
   of unique student-authored production lines that contain a supported mutation
   site and were executed by the submitted suite. The current minimum is 50%.
   This deliberately simple floor requires evidence from at least a majority of
   the student's authored, mutatable lines before silence can be summarized as an
   assessable zero-finding result; it is a product policy, not a statistical
   confidence claim.
   Below that threshold, a report must say that Fencepost cannot assess code the
   tests never run; zero eligible mutants is never a clean bill of health. The
   coverage count and threshold appear in every report.

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

5. **Triage the survivors in two modes.** This is the core of the project and
   the hardest part. Equivalence is meaningful only relative to a domain
   contract, so every survivor is tested independently through both lenses:

   - **STRICT** gives Codex all behavior Python permits, including custom
     objects, dunder protocols, identity, and type behavior. This is the honest
     upper bound on technical distinguishability.
   - **CONTRACT** permits only tests a plain caller could write. Generated tests
     are statically validated from their AST: no classes or nested helpers, no
     identity or type-inspection operations, no imports beyond pytest and the
     module under test, only builtin scalar/container literal inputs, and no
     monkeypatch, mocks, attribute rebinding, or other replacement of the
     program under test. A test that replaces part of the program is no longer
     evidence about the program.

   In both modes, a test must pass on the original before it can kill a mutant.
   A CONTRACT violation is `INVALID_CONTRACT`: it never executes, never counts
   as a kill or valid attempt, consumes the separate invalid-retry budget, and
   its exact rule violations are fed back to the generator. After N valid tests:
   - Strong test kills it -> **real gap** under that mode.
   - Nothing kills it -> **probable equivalent** under that mode.

   Report both `equivalent_rate_strict` and `equivalent_rate_contract`, their
   raw counts, and every per-survivor label. Never present either as "the"
   equivalent rate. A strict real gap that is contract probable-equivalent is
   `contract_shielded`; retain its strict killing test as evidence of the
   behavior deliberately excluded from student probes.

6. **Probe.** GPT-5.6 generates questions only from CONTRACT-mode real gaps,
   using the surviving gap mutant plus
   diff context and blame metadata. It grades the student's answer against the
   execution result we already computed. The model phrases and evaluates; it does
   not decide truth. Questions are one or two plain-language sentences (at most
   32 words), designed to be read aloud by an instructor; the report already
   supplies location and attribution, so the question must not repeat them.

   A final pedagogical filter applies only to the question layer, never to
   mutation execution or either equivalence rate. A verified CONTRACT witness is
   withheld when it inspects implementation details (dunder metadata or
   reflection), or when it relies on an implicit `bool`-as-number quirk for a
   parameter that the function does not declare as boolean. These are generic,
   auditable rules for avoiding technically real but poor CS2 conversations, not
   fixture exceptions. The evidence remains in the artifact under
   **Deliberately not asked**. This is a deliberately conservative false-negative
   trade: a withheld witness can still describe a genuine Python behavior.

7. **Report.** Formative. "Here are the N places your understanding is
   unverified, and here is what breaks." Human in the loop. Never a verdict,
   never an accusation, never a score that stands on its own. It leads with what
   the submitted tests already protect as well as the fair gaps, groups related
   sites by function, and ranks conversations from execution and commit-message
   evidence. The instructor view keeps the two equivalence rates out of the
   student-facing headline; a separate Method view retains both rates, raw counts,
   and the CONTRACT limitation for audit.

## Non-negotiables

- **Formative, not summative.** No AI-detection framing anywhere in the product,
  the copy, or the report. Output is advisory and assumes an instructor reads it.
- **Python + pytest only.** Multi-language support is out of scope and will kill
  the timeline. One language done properly beats three done badly.
- **Execution is the ground truth.** If a claim in the report is not backed by a
  test run we performed, it does not go in the report.
- **Equivalent mutants must be handled explicitly**, not ignored. Asking a student
  about a behaviorally-identical mutant is a question with no correct answer.
- **CONTRACT is a stated trade, not universal truth.** It can hide a genuine
  behavioral gap whose only witness requires type, identity, custom objects, or
  another excluded input. This is a deliberate false-negative risk and must be
  stated beside the contract rate in every artifact.

## Scope

In: the six stages above, a CLI entry point, a minimal web UI showing the diff,
the mutant, and the test going red.

Out: VS Code extension, LMS integration, auth, multi-language, user accounts,
persistence beyond a run artifact.

## Sample data

`python demo/build_demo_repo.py` builds a synthetic student submission with
realistic git history: an instructor scaffold commit, then a week of student
commits. The student's 10 tests all pass. Known ground truth in that repo:

- `letter_grade`: `score >= 90` -> `score > 90` **survives**. Consequence: a
  student scoring exactly 90 receives a B. Same for the 80/70/60 boundaries.
- `percentile`: `k >= len(ordered)` -> `k > len(ordered)` **survives**, and
  `percentile(scores, 100)` then raises IndexError. The student's own commit
  c59d8e6 is titled "fix percentile index out of range when p=100". They wrote
  the fence and never verified it.
- `rank`, `top_n`: their mutants are **killed**. The tool must not flag these.
  A tool that flags everything is a tool that found nothing.
- `clamp_percent`: `p < 0` -> `p <= 0` and `p > 100` -> `p >= 100`
  **survive** the submitted suite and are real gaps in both modes. Our original
  claim that they were universally equivalent was wrong twice: a plain caller
  can distinguish the upper boundary with `str(clamp_percent(100.0)) ==
  "100.0"`, because the mutant returns integer `100`; and it can distinguish the
  lower boundary with `str(clamp_percent(-0.0)) == "-0.0"`, because `-0.0 < 0`
  is false while `-0.0 <= 0` is true. These require neither custom objects nor
  type/identity inspection, so they are legitimate CONTRACT real gaps.
- Because `percentile` now clamps `p` before computing its index, its surviving
  `/` -> `//` arithmetic mutant is a STRICT real gap through a custom object
  whose true-division and floor-division protocols differ. A first CONTRACT
  witness monkeypatched out `clamp_percent` to expose a negative numerator, but
  that replaces the program and is `INVALID_CONTRACT`. With the clamp intact,
  exhaustive verification over about 36,180 combinations (list lengths 0..59;
  percentages -50..150 as integers, halves, and quarter fractions) found zero
  differences between `int(n * p / 100)` and `int(n * p // 100)`. It is therefore
  expected to become a CONTRACT probable-equivalent after three valid plain
  attempts, but the label remains execution-decided rather than hardcoded. The
  real unrestricted run found all 21 survivors to be STRICT real gaps; the gap
  between modes is the finding, not an error to collapse away.

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
