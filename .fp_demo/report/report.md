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
import gradebook.analytics as analytics


class _DivisionSensitiveProduct:
    def __truediv__(self, divisor):
        assert divisor == 100
        return 1

    def __floordiv__(self, divisor):
        assert divisor == 100
        return 0


class _DivisionSensitivePercent:
    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __gt__(self, other):
        return other == 0

    def __ge__(self, other):
        return other == 0

    def __rmul__(self, other):
        assert other == 2
        return _DivisionSensitiveProduct()


def test_percentile_uses_true_division_before_integer_conversion():
    assert analytics.percentile([10, 20], _DivisionSensitivePercent()) == 20
```

`.fencepost-generated-0018.test_adversarial::test_percentile_uses_true_division_before_integer_conversion`: assert 10 == 20
 +  where 10 = <function percentile at 0x7bc628ff02c0>([10, 20], <test_adversarial._DivisionSensitivePercent object at 0x7bc6292e5b20>)
 +    where <function percentile at 0x7bc628ff02c0> = analytics.percentile
 +    and   <test_adversarial._DivisionSensitivePercent object at 0x7bc6292e5b20> = _DivisionSensitivePercent()

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

**Question:** How can a divisor of 99 cause percentile to return the next higher score instead of the intended one for a percentage like 66, and why?

- `100` -> `99`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0019.test_adversarial::test_percentile_uses_hundred_based_rank_for_three_values`: assert 30 == 20
 +  where 30 = percentile([10, 20, 30], 66)

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

**Question:** At p = 100, what should `percentile` return, and why can’t it use an index equal to the number of scores?

- `k >= len(ordered)` -> `k > len(ordered)`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0020.test_adversarial::test_percentile_at_100_returns_highest_score`: IndexError: list index out of range

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

**Question:** What grade should letter_grade return at the A/B cutoff, and why does including or excluding that boundary change the result?

- `score >= 90` -> `score > 90`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0000.test_adversarial::test_letter_grade_includes_ninety_in_a_range`: AssertionError: assert 'B' == 'A'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0001.test_adversarial::test_letter_grade_89_is_b`: AssertionError: assert 'A' == 'B'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0002.test_adversarial::test_letter_grade_assigns_a_at_inclusive_lower_boundary`: AssertionError: assert 'B' == 'A'
  
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

**Question:** What result does letter_grade give 80 and 79, and why does changing the B cutoff or dropping equality put one of them in the wrong grade?

- `score >= 80` -> `score > 80`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0003.test_adversarial::test_letter_grade_includes_80_in_b_range`: AssertionError: assert 'C' == 'B'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0004.test_adversarial::test_letter_grade_79_is_c`: AssertionError: assert 'B' == 'C'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0005.test_adversarial::test_letter_grade_assigns_b_at_inclusive_lower_boundary`: AssertionError: assert 'C' == 'B'
  
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

**Question:** What should letter_grade return for scores 69 and 70, and why does changing the C cutoff or making it exclusive put one of them in the wrong grade?

- `score >= 70` -> `score > 70`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0006.test_adversarial::test_letter_grade_includes_seventy_in_c_range`: AssertionError: assert 'D' == 'C'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0007.test_adversarial::test_letter_grade_69_is_d`: AssertionError: assert 'C' == 'D'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0008.test_adversarial::test_letter_grade_includes_70_in_c_range`: AssertionError: assert 'D' == 'C'
  
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

**Question:** All right, in letter_grade, what grade should a score of 60 receive, and why must the comparison include that boundary?

- `score >= 60` -> `score > 60`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0009.test_adversarial::test_letter_grade_assigns_d_at_inclusive_lower_boundary`: AssertionError: assert 'F' == 'D'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0010.test_adversarial::test_letter_grade_59_is_failing`: AssertionError: assert 'D' == 'F'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0011.test_adversarial::test_letter_grade_includes_sixty_in_d_range`: AssertionError: assert 'F' == 'D'
  
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

**Question:** In clamp_percent, if you move or include the zero lower boundary, which percentages get clamped or left unchanged incorrectly, and why?

- `p < 0` -> `p <= 0`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0012.test_adversarial::test_clamp_percent_preserves_negative_zero`: AssertionError: assert '0' == '-0.0'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0013.test_adversarial::test_clamp_percent_clamps_negative_one_to_zero`: AssertionError: assert -1 == 0
 +  where -1 = <function clamp_percent at 0x73cf73ef0040>(-1)
 +    where <function clamp_percent at 0x73cf73ef0040> = <module 'gradebook.analytics' from '/work/jobs/triage-0013-ev0x7dt5/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0013-ev0x7dt5/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0014.test_adversarial::test_clamp_percent_preserves_positive_fraction_below_one`: assert 0 == 0.5
 +  where 0 = <function clamp_percent at 0x790f73548180>(0.5)
 +    where <function clamp_percent at 0x790f73548180> = analytics.clamp_percent

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

**Question:** If clamp_percent changes its upper check, what happens to a value at 100, just below it, or just above it—and why?

- `p > 100` -> `p >= 100`

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0015.test_adversarial::test_clamp_percent_preserves_float_at_inclusive_upper_boundary`: AssertionError: assert '100' == '100.0'
  
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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0016.test_adversarial::test_clamp_percent_preserves_fraction_just_below_upper_bound`: AssertionError: assert 100 == 99.5
 +  where 100 = <function clamp_percent at 0x7cd011eec040>(99.5)
 +    where <function clamp_percent at 0x7cd011eec040> = <module 'gradebook.analytics' from '/work/jobs/triage-0016-5zimpfpb/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0016-5zimpfpb/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

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

  Their 10 tests passed; the adversarial test failed at `.fencepost-generated-0017.test_adversarial::test_clamp_percent_clamps_101_to_100`: assert 101 == 100
 +  where 101 = <function clamp_percent at 0x7045654d4180>(101)
 +    where <function clamp_percent at 0x7045654d4180> = analytics.clamp_percent

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
