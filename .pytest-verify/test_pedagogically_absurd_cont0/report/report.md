# Fencepost comprehension report

This report is formative and advisory. It identifies behavior changes the submitted tests did not distinguish; it is not a verdict, accusation, or standalone score. An instructor should review the evidence and decide whether a conversation would be useful.

## Summary

Diego Ramos's 10 tests pass.

We made 2 small changes to code they wrote; their tests caught 0. Of the 2 changes they missed, 0 are fair to discuss. We withheld 2 that would not make a fair question.

Authored-line coverage: **1 of 1 (100%)**. The minimum for an assessable zero-finding report is 50%.

Analyzed repository commit: `fixture-commit`.

## What their tests already protect

- `f` — 1 fair gaps among 2 changes.

## Deliberately not asked

### pkg/analytics.py:2

We found a technical way to distinguish this change, but it falls outside the plain-caller contract used for student questions. We dropped it rather than ask about an artificial edge case.

`value >= 1` -> `value > 1`

<details><summary>Technical evidence for audit</summary>

```python
from pkg.analytics import f

def test_boundary():
    assert f(1)

```

`test_probe.py::test_boundary`: assert False

</details>

### pkg/analytics.py:2

This execution witness was withheld because it would make a poor CS2 question.

A boolean may be used as a numeric argument only when the function signature explicitly declares or defaults that parameter as boolean. Treating False as integer zero is otherwise a Python quirk, not evidence of the assignment's intended numeric contract. Witness: passes a boolean literal to a parameter that is not explicitly boolean.

`value >= 1` -> `value > 1`

## Conversations worth having

## Method: equivalence triage

STRICT equivalent rate: **0.000** (0 probable equivalent, 2 real gap, 0 unresolved).

CONTRACT equivalent rate: **0.500** (1 probable equivalent, 1 real gap, 0 unresolved).

CONTRACT limitation: CONTRACT can hide a genuine type-only gap.

## Traceability

Every behavioral statement above points to an execution artifact. Core artifacts:

- `run.json`
- `baseline/result.json`
- `selection.json`
- `triage/summary.json`
- `probe/summary.json`
