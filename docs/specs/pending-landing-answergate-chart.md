The student view works and I verified its integrity myself: no mutant/assertion/test in the
pre-answer HTML, /reveal/N returns 403 without an answer, zero JS. Repo is public at
github.com/kasbsquall/fencepost.

The user walked the product and gave three findings. All three are right. Fix them.

## 1. There is no home. Nobody knows what views exist.

Right now there are two disconnected commands and no way in. The user's words: "should
there be a home page or something, where I decide where to go? I don't know how many views
exist or from what angle you can see this." A judge clones this and has the same problem,
and so does anyone who might one day pay for it.

Build a landing route. It must:
- Name the two views and who each is for, in one line each. Instructor: read the report,
  decide whether to have a conversation. Student: answer questions about your own code and
  see what your tests never checked.
- Link to: the instructor report, the student probe, and /method.
- State what this run is: which repo, which commit, which student, when it ran — all from
  the artifact.
- Show the CLI commands that produce and open each view, because half the audience lives
  in a terminal and the README's commands should be discoverable from the product too.
- Be the default route of `fencepost serve`. The instructor report moves to /report.

## 2. The empty answer lets you skip the whole instrument.

The user pressed Continue without typing and got the full reveal. My spec allowed empty
answers; I did not think through that this defeats the instrument. If a student can see the
evidence without committing an answer, the exam measures nothing.

Fix: to reach the reveal the student must either write something, or explicitly press a
distinct "I don't know" control. Both are recorded, and recorded DIFFERENTLY — a deliberate
"I don't know" is honest data an instructor can use; a reflexive Continue is not. An empty
textarea + Continue is no longer a path to the reveal.

Do not make it punitive. "I don't know" must be one click, not buried, and the copy must
not shame. The point is that the student chose.

## 3. The page has no visual anchor. It reads as a wall of prose.

The user: "I only see plain text, no visual elements that catch my attention. Big engraved
text. Everything very old." He is right, and the earlier rounds fixed measurable defects
(contrast, surfaces, icons) without giving the page any structure to look at.

The report already contains a numeric FLOW that is sitting in prose:

    51 changes made -> 30 caught by their own tests -> 21 missed -> 20 fair to ask -> 1 withheld

That is the whole story of the run in five numbers, and it should be the visual anchor at
the top of the report. Build it as a proportional bar, and build the per-function status
(rank 10/10 caught, top_n 4/4, letter_grade 12/20, clamp_percent 6/11, percentile ...) as
small multiples of the same form underneath.

### The chart rules — these are not stylistic, they came from a validator

I ran the palette validator on our three status colours (#3E6E52 caught, #B24A3C gap,
#8C7B5A withheld) against the Ledger surface. Results:

    [PASS] lightness band
    [FAIL] chroma floor        green (0.07) and tan (0.052) read as gray
    [WARN] CVD separation      red<->green worst adjacent dE 8.6 under protan
    [PASS] contrast vs surface

dE 8.6 between red and green under protanopia means a red-green colourblind instructor
CANNOT distinguish "their tests caught it" from "this is a gap". That is ~8% of men, and
this product's whole claim is that it does not make assertions it cannot support.

So the encoding rules are mandatory, not optional:
- **Every segment is directly labelled** with its number and its noun ("30 caught",
  "20 to discuss", "1 withheld"). The label carries the meaning; the colour only
  reinforces it. Never colour alone.
- **2px surface gap between adjacent segments** so the boundary is geometric, not chromatic.
- A table view / the existing prose sentence stays as the text equivalent.
- Status colours stay reserved for status. Do not introduce a fourth hue.
- No dual axis, no rainbow, no decoration. Every pixel comes from report.json; if a number
  is missing, omit the segment rather than infer it.
- The bar is one row, thin, with the segments in narrative order (caught -> to discuss ->
  withheld). It is a part-to-whole of the 51 changes, not a chart for its own sake.
- Keep the JS budget at zero. If you want a hover tooltip, it must be CSS-only or omitted;
  the direct labels already do the job the tooltip would.

Small multiples: one thin bar per function, same encoding, sorted so the clean ones read as
clean at a glance. `rank` and `top_n` being fully caught should be visible in one second —
that is the "what the student got right" evidence the instructor asked for, made visual.

## Constraints

- Ledger stays. --tan-strong for text, the SVG sprite, no emoji, offline, zero JS.
- Every number from the artifact. A fabricated default is a defect.
- Keep 66 unit + 2 Docker gates green.
- Do not touch triage, the rates, the contract policy, or any measurement.

Run the non-Docker tests. Tell me the commands to see the landing page and the probe.
