# Fencepost comprehension report

This report is formative and advisory. It identifies behavior changes the submitted tests did not distinguish; it is not a verdict, accusation, or standalone score. An instructor should review the evidence and decide whether a conversation would be useful.

## Summary

Diego Ramos's 10 tests pass.

We made 51 small changes to code they wrote; their tests caught 30. Of the 21 changes they missed, 20 are fair to discuss. We withheld 1 that would not make a fair question.

Authored-line coverage: **22 of 24 (92%)**. The minimum for an assessable zero-finding report is 50%.

Analyzed repository commit: `3a93a3eb3a34e04aed55c7761d7c8d1cf0ec414c`.

## What their tests already protect

- `rank` — all 10 of 10 changes caught.
- `top_n` — all 4 of 4 changes caught.
- `clamp_percent` — 6 verified behavior changes among 11 changes; 2 fair question site(s).
- `letter_grade` — 12 verified behavior changes among 20 changes; 4 fair question site(s).
- `percentile` — 2 verified behavior changes among 6 changes; 2 fair question site(s).

## Deliberately not asked

### gradebook/analytics.py:38

We found a way to break this, but only by feeding the function a fake object no ordinary caller would write. That is not a fair question, so we dropped it.

`len(ordered) * p / 100` -> `len(ordered) * p // 100`

<details><summary>Technical evidence for audit</summary>

```python
from gradebook.analytics import percentile

class DivergentDivision:
    def __lt__(self, other):
        return False
    def __gt__(self, other):
        return False
    def __rmul__(self, other):
        return self
    def __truediv__(self, other):
        return 1
    def __floordiv__(self, other):
        return 0

def test_custom_division_protocol():
    assert percentile([10, 20], DivergentDivision()) == 20

```

`.fencepost-generated-0018.test_adversarial::test_custom_division_protocol`: assert 10 == 20
 +  where 10 = percentile([10, 20], <test_adversarial.DivergentDivision object at 0x7168582de1e0>)
 +    where <test_adversarial.DivergentDivision object at 0x7168582de1e0> = DivergentDivision()

</details>

## Conversations worth having

### `percentile`

2 source site(s); 2 surviving change(s).

**Why this comes first.** Commit c59d8e6 says “fix percentile index out of range when p=100,” but execution shows the submitted tests did not protect that claimed behavior.

#### gradebook/analytics.py:38

line 38, commit dceec68 on 2026-07-09 (implement percentile).

```python
  38 |     k = int(len(ordered) * p / 100)
```

**Question:** What result changes at this boundary, and why?

- `100` -> `99`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0018.test_adversarial::test_upper_numeric_boundaries`: assert 30 == 20
 +  where 30 = percentile([30, 10, 20], 66)

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -2,7 +2,7 @@
     """Return the p-th percentile of scores (p between 0 and 100)."""
     p = clamp_percent(p)
     ordered = sorted(scores)
-    k = int(len(ordered) * p / 100)
+    k = int(len(ordered) * p / 99)
     if k >= len(ordered):
         k = len(ordered) - 1
     return ordered[k]
  ```

  </details>

#### gradebook/analytics.py:39

line 39, commit c59d8e6 on 2026-07-09 (fix percentile index out of range when p=100).

```python
  39 |     if k >= len(ordered):
```

**Question:** What result changes at this boundary, and why?

- `k >= len(ordered)` -> `k > len(ordered)`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0019.test_adversarial::test_percentile_one_hundred_returns_maximum`: IndexError: list index out of range

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -3,6 +3,6 @@
     p = clamp_percent(p)
     ordered = sorted(scores)
     k = int(len(ordered) * p / 100)
-    if k >= len(ordered):
+    if k > len(ordered):
         k = len(ordered) - 1
     return ordered[k]
  ```

  </details>

### `letter_grade`

4 source site(s); 12 surviving change(s).

#### gradebook/analytics.py:13

line 13, commit a0f7cba on 2026-07-07 (implement letter_grade).

```python
  13 |     if score >= 90:
```

**Question:** What result changes at this boundary, and why?

- `score >= 90` -> `score > 90`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0000.test_adversarial::test_letter_grade_boundary_90`: AssertionError: assert 'B' == 'A'
  
  - A
  + B

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -3,13 +3,13 @@
 
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
-    if score >= 90:
-        return "A"
+    if score > 90:
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `90` -> `89`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0001.test_adversarial::test_letter_grade_numeric_boundary_90_89`: AssertionError: assert 'A' == 'B'
  
  - B
  + A

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -3,13 +3,13 @@
 
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
-    if score >= 90:
-        return "A"
+    if score >= 89:
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `90` -> `91`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0002.test_adversarial::test_letter_grade_numeric_boundary_90_91`: AssertionError: assert 'B' == 'A'
  
  - A
  + B

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -3,13 +3,13 @@
 
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
-    if score >= 90:
-        return "A"
+    if score >= 91:
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

#### gradebook/analytics.py:15

line 15, commit a0f7cba on 2026-07-07 (implement letter_grade).

```python
  15 |     elif score >= 80:
```

**Question:** What result changes at this boundary, and why?

- `score >= 80` -> `score > 80`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0003.test_adversarial::test_letter_grade_boundary_80`: AssertionError: assert 'C' == 'B'
  
  - B
  + C

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
-    elif score >= 80:
-        return "B"
+        return 'A'
+    elif score > 80:
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `80` -> `79`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0004.test_adversarial::test_letter_grade_numeric_boundary_80_79`: AssertionError: assert 'B' == 'C'
  
  - C
  + B

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
-    elif score >= 80:
-        return "B"
+        return 'A'
+    elif score >= 79:
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `80` -> `81`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0005.test_adversarial::test_letter_grade_numeric_boundary_80_81`: AssertionError: assert 'C' == 'B'
  
  - B
  + C

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
-    elif score >= 80:
-        return "B"
+        return 'A'
+    elif score >= 81:
+        return 'B'
     elif score >= 70:
-        return "C"
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

#### gradebook/analytics.py:17

line 17, commit a0f7cba on 2026-07-07 (implement letter_grade).

```python
  17 |     elif score >= 70:
```

**Question:** What result changes at this boundary, and why?

- `score >= 70` -> `score > 70`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0006.test_adversarial::test_letter_grade_boundary_70`: AssertionError: assert 'D' == 'C'
  
  - C
  + D

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
-    elif score >= 70:
-        return "C"
+        return 'B'
+    elif score > 70:
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `70` -> `69`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0007.test_adversarial::test_letter_grade_numeric_boundary_70_69`: AssertionError: assert 'C' == 'D'
  
  - D
  + C

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
-    elif score >= 70:
-        return "C"
+        return 'B'
+    elif score >= 69:
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `70` -> `71`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0008.test_adversarial::test_letter_grade_numeric_boundary_70_71`: AssertionError: assert 'D' == 'C'
  
  - C
  + D

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
-    elif score >= 70:
-        return "C"
+        return 'B'
+    elif score >= 71:
+        return 'C'
     elif score >= 60:
-        return "D"
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

#### gradebook/analytics.py:19

line 19, commit a0f7cba on 2026-07-07 (implement letter_grade).

```python
  19 |     elif score >= 60:
```

**Question:** What result changes at this boundary, and why?

- `score >= 60` -> `score > 60`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0009.test_adversarial::test_letter_grade_boundary_60`: AssertionError: assert 'F' == 'D'
  
  - D
  + F

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
-    elif score >= 60:
-        return "D"
+        return 'C'
+    elif score > 60:
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `60` -> `59`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0010.test_adversarial::test_letter_grade_numeric_boundary_60_59`: AssertionError: assert 'D' == 'F'
  
  - F
  + D

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
-    elif score >= 60:
-        return "D"
+        return 'C'
+    elif score >= 59:
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

- `60` -> `61`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0011.test_adversarial::test_letter_grade_numeric_boundary_60_61`: AssertionError: assert 'F' == 'D'
  
  - D
  + F

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -4,12 +4,12 @@
     A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
     """
     if score >= 90:
-        return "A"
+        return 'A'
     elif score >= 80:
-        return "B"
+        return 'B'
     elif score >= 70:
-        return "C"
-    elif score >= 60:
-        return "D"
+        return 'C'
+    elif score >= 61:
+        return 'D'
     else:
-        return "F"
+        return 'F'
  ```

  </details>

### `clamp_percent`

2 source site(s); 6 surviving change(s).

#### gradebook/analytics.py:27

line 27, commit 1fe8a85 on 2026-07-10 (clamp percentile inputs to the valid interval).

```python
  27 |     if p < 0:
```

**Question:** What result changes at this boundary, and why?

- `p < 0` -> `p <= 0`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0012.test_adversarial::test_lower_boundary_preserves_negative_zero`: AssertionError: assert '0' == '-0.0'
  
  - -0.0
  + 0

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -1,6 +1,6 @@
 def clamp_percent(p):
     """Clamp a percentage to the inclusive 0-100 interval."""
-    if p < 0:
+    if p <= 0:
         p = 0
     if p > 100:
         p = 100
  ```

  </details>

- `0` -> `-1`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0013.test_adversarial::test_clamp_percent_clamps_negative_one`: assert -1 == 0
 +  where -1 = clamp_percent(-1)

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -1,6 +1,6 @@
 def clamp_percent(p):
     """Clamp a percentage to the inclusive 0-100 interval."""
-    if p < 0:
+    if p < -1:
         p = 0
     if p > 100:
         p = 100
  ```

  </details>

- `0` -> `1`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0014.test_adversarial::test_clamp_percent_preserves_positive_fraction`: assert 0 == 0.5
 +  where 0 = clamp_percent(0.5)

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -1,6 +1,6 @@
 def clamp_percent(p):
     """Clamp a percentage to the inclusive 0-100 interval."""
-    if p < 0:
+    if p < 1:
         p = 0
     if p > 100:
         p = 100
  ```

  </details>

#### gradebook/analytics.py:29

line 29, commit 1fe8a85 on 2026-07-10 (clamp percentile inputs to the valid interval).

```python
  29 |     if p > 100:
```

**Question:** What result changes at this boundary, and why?

- `p > 100` -> `p >= 100`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0015.test_adversarial::test_upper_boundary_preserves_float_representation`: AssertionError: assert '100' == '100.0'
  
  - 100.0
  ?    --
  + 100

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -2,6 +2,6 @@
     """Clamp a percentage to the inclusive 0-100 interval."""
     if p < 0:
         p = 0
-    if p > 100:
+    if p >= 100:
         p = 100
     return p
  ```

  </details>

- `100` -> `99`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0016.test_adversarial::test_upper_numeric_boundaries`: assert 100 == 99.5
 +  where 100 = clamp_percent(99.5)

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -2,6 +2,6 @@
     """Clamp a percentage to the inclusive 0-100 interval."""
     if p < 0:
         p = 0
-    if p > 100:
+    if p > 99:
         p = 100
     return p
  ```

  </details>

- `100` -> `101`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0017.test_adversarial::test_clamp_percent_clamps_one_hundred_one`: assert 101 == 100
 +  where 101 = clamp_percent(101)

  <details><summary>Full source diff</summary>

  ```diff
--- original
+++ mutant
@@ -2,6 +2,6 @@
     """Clamp a percentage to the inclusive 0-100 interval."""
     if p < 0:
         p = 0
-    if p > 100:
+    if p > 101:
         p = 100
     return p
  ```

  </details>

## Method: equivalence triage

STRICT equivalent rate: **0.000** (0 probable equivalent, 21 real gap, 0 unresolved).

CONTRACT equivalent rate: **0.048** (1 probable equivalent, 20 real gap, 0 unresolved).

CONTRACT limitation: CONTRACT mode can hide a genuine behavioral gap when the only witness uses type, identity, a custom object, or another excluded input. This deliberate false-negative risk means its rate is execution-grounded only under the stated caller contract, not universal truth.

## Traceability

Every behavioral statement above points to an execution artifact. Core artifacts:

- `run.json`
- `baseline/result.json`
- `selection.json`
- `triage/summary.json`
- `probe/summary.json`
