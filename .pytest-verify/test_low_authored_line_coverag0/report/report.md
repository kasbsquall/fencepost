# Fencepost comprehension report

This report is formative and advisory. It identifies behavior changes the submitted tests did not distinguish; it is not a verdict, accusation, or standalone score. An instructor should review the evidence and decide whether a conversation would be useful.

## Summary

Diego Ramos's 10 tests pass.

We made 3 small changes to code they wrote; their tests caught 0. Of the 3 changes they missed, 2 are fair to discuss. We withheld 1 that would not make a fair question.

Authored-line coverage: **1 of 1 (100%)**. The minimum for an assessable zero-finding report is 50%.

Analyzed repository commit: `fixture-commit`.

## What their tests already protect

- `f` — 2 fair gaps among 3 changes.

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

## Conversations worth having

### `f`

1 source site(s); 2 surviving change(s).

#### pkg/analytics.py:2

line 2, commit 4a3f000 on 2026-07-07 (implement boundary).

```python
   2 |     return value >= 1
```

**Question:** What result changes at this boundary, and why?

- `value >= 1` -> `value > 1`

  Their 10 tests passed; the adversarial test failed at `test_probe.py::test_boundary`: assert False

  <details><summary>Full source diff</summary>

  ```diff
-    return value >= 1
+    return value > 1
  ```

  </details>

- `1` -> `2`

  Their 10 tests passed; the adversarial test failed at `test_probe.py::test_boundary`: assert False

  <details><summary>Full source diff</summary>

  ```diff
-    return value >= 1
+    return value >= 2
  ```

  </details>

Student answer:

I don't know

Formative assessment: **INSUFFICIENT**

Review the answer against the execution-grounded boundary behavior.

Execution evidence cited:

- `test_probe.py::test_boundary` — assert False (`triage/contract/contract-gap/attempt-01/attempt.json`)
- `test_probe.py::test_boundary` — assert False (`triage/contract/contract-gap-2/attempt-01/attempt.json`)

## Method: equivalence triage

STRICT equivalent rate: **0.000** (0 probable equivalent, 3 real gap, 0 unresolved).

CONTRACT equivalent rate: **0.500** (1 probable equivalent, 2 real gap, 0 unresolved).

CONTRACT limitation: CONTRACT can hide a genuine type-only gap.

## Traceability

Every behavioral statement above points to an execution artifact. Core artifacts:

- `run.json`
- `baseline/result.json`
- `selection.json`
- `triage/summary.json`
- `probe/summary.json`
