# fencepost

**A comprehension probe for programming courses, for the era where a coding agent can do the assignment.**

Fencepost reads the lines a student actually wrote, mutates them, runs the mutants against the student's own tests, and interrogates what survives. Every question it asks is grounded in a test run we performed — never in a model's opinion.

Built for OpenAI Build Week (Education track) with Codex and GPT-5.6.

---

## The problem

A student's submission passes all its tests. Did they understand it, or did an agent write it?

Detection is the wrong question. AI-detection for code does not work, it is adversarial toward students, and it fails the honest student who used an agent well. Every semester more instructors quietly stop assigning take-home programming work because they cannot trust it, and they have nothing to replace it with.

Fencepost does not detect. It assumes the student may have used an agent, and asks something detection cannot answer: **does this student understand the code in their repo?**

That question is answerable, defensible in an academic hearing, and useful even for the student who wrote every line themselves.

## How it works

```
1  Attribute   git blame -M -C -C -w  → keep only lines the student authored
2  Select      → keep the ones their own tests actually execute
3  Mutate      AST-level operators (ast.unparse), one node change per mutant
4  Execute     run their pytest suite against each mutant in a Docker sandbox
                 killed   → their tests caught it. We stay silent.
                 survived → a comprehension gap, or an equivalent mutant.
5  Triage      GPT-5.6 (via Codex) writes adversarial tests to distinguish each survivor
                 kills it  → REAL GAP, and we now know exactly what breaks
                 can't     → PROBABLE EQUIVALENT. We stay silent.
6  Probe       one question per site, grounded in the authored line and its commit
7  Report      formative, human in the loop, every claim backed by an execution artifact
```

The interesting part is stage 5, and the number it produces.

## What makes this different from prior work

Two systems already do AI oral examination of student code, and a reviewer will find them in thirty seconds. We did too:

- **[Scalable and Personalized Oral Assessments Using Voice AI](https://arxiv.org/abs/2603.18221)** (Ipeirotis & Rizakos, NYU). Voice oral exams graded by a panel of three LLMs. Deployed on two real cohorts. Their system is also called *Viva*. It does **not** read git history, and it does **not** execute code.
- **[AI-Driven Oral Examinations for Code Assessment: Evaluating Understanding Beyond the Commit](https://dl.acm.org/doi/10.1145/3770761.3777032)** (Tregubov & Sow Traore, Dartmouth, SIGCSE 2026). AI-driven oral exams over student submissions.

Fencepost does three things neither does:

1. **Line-level attribution.** `git blame -M -C -C -w` isolates the lines *this student* authored. A question grounded in the instructor's scaffold destroys credibility instantly. Ours cite the commit and the date.
2. **Mutation as an active probe.** We do not ask the student to explain their code. We *change* it and ask what breaks. A question about a mutant that does not exist on disk cannot be answered by pasting the file into a chatbot.
3. **Execution as ground truth.** Codex runs the mutant against the real suite. The failing assertion *is* the answer key. The model phrases the question and grades the reply; it never decides what is true.

## The finding: equivalence is relative to a contract

A surviving mutant is either a real gap or an *equivalent mutant* — behavior genuinely unchanged, so there is nothing to catch. Telling them apart is undecidable in general. It is also the first thing a skeptical reviewer asks about, because a tool that flags equivalents is a tool that asks students unanswerable questions.

We resolved it empirically, and the result surprised us.

We planted a mutant we believed was **provably equivalent** — in a clamp, `if p > 100: p = 100` mutated to `p >= 100`. At exactly 100 both return 100. We checked. We were wrong: GPT-5.6 killed it with `str(clamp_percent(-0.0)) == "-0.0"`. Negative zero. `-0.0 < 0` is false, so the original returns `-0.0`; the mutant's `<=` fires and returns the int `0`. **`p = 100` is never a no-op — it replaces the caller's object with an int literal**, and that is observable with plain values and no introspection.

So under unrestricted Python semantics, our equivalent rate is **0%**. The generator can distinguish everything.

Then it killed the arithmetic mutant (`/` → `//`) by monkeypatching the clamp away, letting a negative numerator reach the division. But `percentile` always clamps first — that state is unreachable in the real program. We verified exhaustively: with the clamp intact, `int(n*p/100)` and `int(n*p//100)` differ **zero times** across ~36,180 combinations. **A test that replaces part of the program is no longer evidence about the program.**

That is the finding: **equivalence is only meaningful relative to a domain contract.** So Fencepost reports two rates, and never presents one as the truth:

| mode | what the generator may use | fixture result |
|---|---|---|
| **strict** | anything Python allows | 21 real gaps, 0 equivalent — rate **0.000** |
| **contract** | what a real caller could write, enforced by an auditable AST policy | 20 real gaps, 1 equivalent — rate **0.048** |

The difference is the set of questions we chose *not* to ask. Probe questions come only from contract-mode gaps. The report has a **"Deliberately not asked"** section showing exactly what we suppressed and why — that section is the evidence the tool has judgment.

**Honest limitation:** contract mode can hide a genuine gap when the only possible witness is a type or identity check. That is a deliberate false-negative trade, stated beside the number, not buried.

## Setup

Requirements: **Python 3.12+**, **Docker** (running), and **Codex CLI** authenticated with a ChatGPT plan.

```bash
pip install -e .
npm install -g @openai/codex && codex login    # if you don't have it
docker build -f docker/runner.Dockerfile -t fencepost-runner:local .
```

## Run it

Build the sample student submission (synthetic, with realistic git history):

```bash
python demo/build_demo_repo.py demo/student-repo
```

Analyze it:

```bash
fencepost demo/student-repo \
  --student-email d.ramos@alumnos.ejemplo.edu \
  --output .fp_run \
  --generator codex \
  --adversarial-model gpt-5.6-terra
```

A full real run takes ~20 minutes and ~45 Codex calls (each survivor is triaged in both modes). Read the report:

```bash
fencepost serve .fp_run          # the instructor UI
cat .fp_run/report/report.md     # or the markdown rendering
```

**To evaluate without spending Codex calls**, the hermetic gates run the whole pipeline with a deterministic generator in ~2 minutes:

```bash
pytest tests/integration    # 2 Docker gates, no model calls
pytest tests --ignore=tests/integration   # 66 unit tests, no Docker
```

## The sample data

`demo/build_demo_repo.py` builds a CS2 gradebook assignment: an instructor scaffold commit, then a week of student commits. **The student's 10 tests all pass.** Known ground truth (documented in `AGENTS.md`, verified by the gates):

- `letter_grade`: the boundary mutants survive. A student scoring exactly **90 gets a B**.
- `percentile`: the student's commit is literally titled *"fix percentile index out of range when p=100"*. Remove their fix and **their tests never notice**. They built the fence and never checked it.
- `rank`, `top_n`: their mutants are **killed**. Fencepost stays silent. A tool that flags everything found nothing.

On this fixture: 51 eligible mutants → 30 killed by the student's own suite → 21 survivors → 8 sites → 8 questions.

## How Codex and GPT-5.6 were used

**Codex wrote the engine.** As measured at the final project commit: 8,120 lines across 18 modules and 18 commits, in one Codex session (`gpt-5.6-terra` for mechanical work, `gpt-5.6-sol` for design and the hard reasoning). The spec (`AGENTS.md`), the demo fixture, this README, and the video are the human's.

**Codex is also *inside* the product.** Stage 5 and stage 6 shell out to `codex exec -m gpt-5.6-terra` with structured output to generate adversarial tests and probe questions at runtime. The credential stays host-only; only the generated test string crosses into the sandbox. Codex is not just the tool that built Fencepost — it is the agent that runs it.

Where the decisions were made, honestly:

- Codex proposed the architecture and **solved the hardest design problem correctly**: `ast.unparse` reformats the file, so mutant line numbers cannot map back to blame. It refused to try, and used two independent coordinate systems joined by a structural AST path.
- Codex **caught a flaw in the human's fixture** that the human missed: the `score >= 60` boundary is only covered by the instructor's starter test. Its rule — *blame filters what we mutate, not which tests we run* — is now spec.
- The human **caught Codex's sandbox contradiction**: it mounted `/workspace` read-only and then ran a syntax check that writes `__pycache__`, so all 287 mutants came back `broken`. Codex reported the gate as failing but blamed Docker; running the gate ourselves found the real cause.
- Codex **reported a count of 287 mutants as a passing assertion without verifying it**. The honest number is 40 (later 51). It owned the mistake and refused to fabricate a post-hoc explanation for where 287 came from.
- **GPT-5.6 refuted the humans twice** on equivalence, once with `Decimal` identity and once with negative zero, and then tried to cheat with monkeypatch. Execution was the only party that never lied.

That last one is the project in miniature: a human and two models were confident and wrong, and the test run settled it. That is exactly what Fencepost does to a student's green test suite.

## What this is not

- Not a detector. There is no AI-detection anywhere in the product, the copy, or the report.
- Not summative. The output is advisory and assumes an instructor reads it. It is not a grade and must not be used as one.
- Not multi-language. Python + pytest only. One language done properly beats three done badly.
- Not a replacement for talking to your students. It is a reason to.

## Security

The student's repo and every model-generated test are untrusted input. They run in Docker with `--network none`, a read-only root filesystem, a read-only source mount, all capabilities dropped, `no-new-privileges`, a non-root user, and memory/CPU/PID limits. Two independent audits reviewed this codebase; both findings they raised are fixed:

- a TOCTOU tar-slip in archive extraction that ran **on the host** (a crafted symlink in a student repo could write outside the sandbox),
- and untrusted code sharing write access to the results directory, which would have let the code under test **forge the ground truth**. `/out` is no longer mounted; results return through the trusted driver.

## License

MIT.
