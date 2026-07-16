# Fencepost comprehension report

This report is formative and advisory. It identifies behavior changes the submitted tests did not distinguish; it is not a verdict, accusation, or standalone score. An instructor should review the evidence and decide whether a conversation would be useful.

## Summary

Diego Ramos's submitted pytest suite passed. Fencepost found 8 execution-grounded source sites where understanding remains unverified.

Analyzed repository commit: `3a93a3eb3a34e04aed55c7761d7c8d1cf0ec414c`.

## Places to discuss

### 1. gradebook/analytics.py:13

line 13, commit a0f7cba on 2026-07-07 (implement letter_grade).

Authored source:

```python
  13 |     if score >= 90:
```

Question:

What observable grading behavior would break at the A/B cutoff if its threshold were shifted or made exclusive, and why must that boundary use the correct inclusive comparison?

Supporting execution evidence (3 surviving mutations):

1. `score >= 90` -> `score > 90`

   Original passed; mutant failed at `.fencepost-generated-0000.test_adversarial::test_letter_grade_assigns_a_at_inclusive_ninety_boundary`: AssertionError: assert 'B' == 'A'
  
  - A
  + B

   Artifact: `triage/contract/86e0917e5c6bf1d8/attempt-01/attempt.json`.

2. `90` -> `89`

   Original passed; mutant failed at `.fencepost-generated-0001.test_adversarial::test_letter_grade_89_is_b`: AssertionError: assert 'A' == 'B'
  
  - B
  + A

   Artifact: `triage/contract/2e231a949dfe891d/attempt-01/attempt.json`.

3. `90` -> `91`

   Original passed; mutant failed at `.fencepost-generated-0002.test_adversarial::test_letter_grade_includes_ninety_in_a_range`: AssertionError: assert 'B' == 'A'
  
  - A
  + B

   Artifact: `triage/contract/1d2de104b4e2ea87/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 2. gradebook/analytics.py:15

line 15, commit a0f7cba on 2026-07-07 (implement letter_grade).

Authored source:

```python
  15 |     elif score >= 80:
```

Question:

What letter grade should scores at the B/C cutoff and immediately next to it receive, and why would making the B threshold exclusive or shifting it change that behavior?

Supporting execution evidence (3 surviving mutations):

1. `score >= 80` -> `score > 80`

   Original passed; mutant failed at `.fencepost-generated-0003.test_adversarial::test_letter_grade_includes_80_in_b_range`: AssertionError: assert 'C' == 'B'
  
  - B
  + C

   Artifact: `triage/contract/bc57b02d4b5d32a1/attempt-01/attempt.json`.

2. `80` -> `79`

   Original passed; mutant failed at `.fencepost-generated-0004.test_adversarial::test_letter_grade_79_is_c`: AssertionError: assert 'B' == 'C'
  
  - C
  + B

   Artifact: `triage/contract/de6e7433e88c46a6/attempt-01/attempt.json`.

3. `80` -> `81`

   Original passed; mutant failed at `.fencepost-generated-0005.test_adversarial::test_letter_grade_awards_b_at_inclusive_lower_boundary`: AssertionError: assert 'C' == 'B'
  
  - B
  + C

   Artifact: `triage/contract/ce1508b29bd64233/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 3. gradebook/analytics.py:17

line 17, commit a0f7cba on 2026-07-07 (implement letter_grade).

Authored source:

```python
  17 |     elif score >= 70:
```

Question:

What grade should `letter_grade` return for a score of 70, and why must the C-grade condition include that boundary exactly?

Supporting execution evidence (3 surviving mutations):

1. `score >= 70` -> `score > 70`

   Original passed; mutant failed at `.fencepost-generated-0006.test_adversarial::test_letter_grade_assigns_c_at_inclusive_lower_boundary`: AssertionError: assert 'D' == 'C'
  
  - C
  + D

   Artifact: `triage/contract/75b9f689f32ac45a/attempt-01/attempt.json`.

2. `70` -> `69`

   Original passed; mutant failed at `.fencepost-generated-0007.test_adversarial::test_score_69_is_a_d`: AssertionError: assert 'C' == 'D'
  
  - D
  + C

   Artifact: `triage/contract/dbb83dad668b1b68/attempt-01/attempt.json`.

3. `70` -> `71`

   Original passed; mutant failed at `.fencepost-generated-0008.test_adversarial::test_letter_grade_assigns_c_at_inclusive_lower_boundary`: AssertionError: assert 'D' == 'C'
  
  - C
  + D

   Artifact: `triage/contract/8e3bb3b74b5e7623/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 4. gradebook/analytics.py:19

line 19, commit a0f7cba on 2026-07-07 (implement letter_grade).

Authored source:

```python
  19 |     elif score >= 60:
```

Question:

What observable grading behavior would break if this condition used a strict comparison or shifted its cutoff by one point, and why does the stated grade range require its current inclusive boundary?

Supporting execution evidence (3 surviving mutations):

1. `score >= 60` -> `score > 60`

   Original passed; mutant failed at `.fencepost-generated-0009.test_adversarial::test_letter_grade_awards_d_at_inclusive_lower_boundary`: AssertionError: assert 'F' == 'D'
  
  - D
  + F

   Artifact: `triage/contract/9e215f782bcfc8e3/attempt-01/attempt.json`.

2. `60` -> `59`

   Original passed; mutant failed at `.fencepost-generated-0010.test_adversarial::test_letter_grade_59_is_f`: AssertionError: assert 'D' == 'F'
  
  - F
  + D

   Artifact: `triage/contract/db66414d596970b4/attempt-01/attempt.json`.

3. `60` -> `61`

   Original passed; mutant failed at `.fencepost-generated-0011.test_adversarial::test_letter_grade_includes_sixty_in_d_range`: AssertionError: assert 'F' == 'D'
  
  - D
  + F

   Artifact: `triage/contract/7d45e006f2ec7b27/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 5. gradebook/analytics.py:27

line 27, commit 1fe8a85 on 2026-07-10 (clamp percentile inputs to the valid interval).

Authored source:

```python
  27 |     if p < 0:
```

Question:

Under the function’s inclusive 0–100 contract, what observable behavior would change at the lower boundary if the guard were inclusive or its threshold shifted, and why must it distinguish values below 0 from those equal to or above 0?

Supporting execution evidence (3 surviving mutations):

1. `p < 0` -> `p <= 0`

   Original passed; mutant failed at `.fencepost-generated-0012.test_adversarial::test_clamp_percent_preserves_false_at_zero_boundary`: AssertionError: assert '0' == 'False'
  
  - False
  + 0

   Artifact: `triage/contract/67c52a2840605244/attempt-01/attempt.json`.

2. `0` -> `-1`

   Original passed; mutant failed at `.fencepost-generated-0013.test_adversarial::test_clamp_percent_clamps_negative_one_to_zero`: AssertionError: assert -1 == 0
 +  where -1 = <function clamp_percent at 0x731b9e790040>(-1)
 +    where <function clamp_percent at 0x731b9e790040> = <module 'gradebook.analytics' from '/work/jobs/triage-0013-k2ds4ddo/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0013-k2ds4ddo/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

   Artifact: `triage/contract/ab756a31efd05a69/attempt-01/attempt.json`.

3. `0` -> `1`

   Original passed; mutant failed at `.fencepost-generated-0014.test_adversarial::test_clamp_percent_preserves_positive_fraction_below_one`: AssertionError: assert 0 == 0.5
 +  where 0 = <function clamp_percent at 0x7bdccf914040>(0.5)
 +    where <function clamp_percent at 0x7bdccf914040> = <module 'gradebook.analytics' from '/work/jobs/triage-0014-twbwgtty/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0014-twbwgtty/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

   Artifact: `triage/contract/44bc84979be41b9d/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 6. gradebook/analytics.py:29

line 29, commit 1fe8a85 on 2026-07-10 (clamp percentile inputs to the valid interval).

Authored source:

```python
  29 |     if p > 100:
```

Question:

What observable behavior would break at and around the maximum percentage if the upper-bound check included the limit or moved it by one, and why should values at or below the maximum be returned unchanged while only larger values are clamped?

Supporting execution evidence (3 surviving mutations):

1. `p > 100` -> `p >= 100`

   Original passed; mutant failed at `.fencepost-generated-0015.test_adversarial::test_clamp_percent_preserves_float_at_inclusive_upper_bound`: AssertionError: assert '100' == '100.0'
  
  - 100.0
  ?    --
  + 100

   Artifact: `triage/contract/92261c57ed4e3d56/attempt-01/attempt.json`.

2. `100` -> `99`

   Original passed; mutant failed at `.fencepost-generated-0016.test_adversarial::test_clamp_percent_preserves_fraction_below_upper_bound`: AssertionError: assert 100 == 99.5
 +  where 100 = <function clamp_percent at 0x7342cebb4040>(99.5)
 +    where <function clamp_percent at 0x7342cebb4040> = <module 'gradebook.analytics' from '/work/jobs/triage-0016-nfthugae/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0016-nfthugae/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

   Artifact: `triage/contract/086eee6e74bf01f0/attempt-01/attempt.json`.

3. `100` -> `101`

   Original passed; mutant failed at `.fencepost-generated-0017.test_adversarial::test_clamp_percent_clamps_first_integer_above_upper_bound`: AssertionError: assert 101 == 100
 +  where 101 = <function clamp_percent at 0x74b7e889c040>(101)
 +    where <function clamp_percent at 0x74b7e889c040> = <module 'gradebook.analytics' from '/work/jobs/triage-0017-5ox08170/mutant/tree/gradebook/analytics.py'>.clamp_percent
 +      where <module 'gradebook.analytics' from '/work/jobs/triage-0017-5ox08170/mutant/tree/gradebook/analytics.py'> = gradebook.analytics

   Artifact: `triage/contract/2e3d6e7b8bdac2ad/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 7. gradebook/analytics.py:38

line 38, commit dceec68 on 2026-07-09 (implement percentile).

Authored source:

```python
  38 |     k = int(len(ordered) * p / 100)
```

Question:

How does the percentile calculation map a percentage to an index in the sorted scores, and what results would become incorrect if its divisor did not preserve the 0–100 percentage scale?

Supporting execution evidence (1 surviving mutation):

1. `100` -> `99`

   Original passed; mutant failed at `.fencepost-generated-0019.test_adversarial::test_percentile_uses_hundred_based_rank_scale`: assert 30 == 20
 +  where 30 = <function percentile at 0x739c89670220>([10, 20, 30], 66)
 +    where <function percentile at 0x739c89670220> = analytics.percentile

   Artifact: `triage/contract/764a18c525e359d6/attempt-01/attempt.json`.

No student answer was supplied in this run.

### 8. gradebook/analytics.py:39

line 39, commit c59d8e6 on 2026-07-09 (fix percentile index out of range when p=100).

Authored source:

```python
  39 |     if k >= len(ordered):
```

Question:

What observable behavior breaks when the computed percentile index equals the number of sorted scores, and why must that boundary be handled before indexing the list?

Supporting execution evidence (1 surviving mutation):

1. `k >= len(ordered)` -> `k > len(ordered)`

   Original passed; mutant failed at `.fencepost-generated-0020.test_adversarial::test_percentile_at_100_returns_largest_score`: IndexError: list index out of range

   Artifact: `triage/contract/ebad6149cee857c9/attempt-01/attempt.json`.

No student answer was supplied in this run.

## Deliberately not asked

### gradebook/analytics.py:38

`len(ordered) * p / 100` -> `len(ordered) * p // 100`

STRICT execution found a technical distinction, but CONTRACT execution did not find a caller-conforming distinction. Fencepost therefore withholds this question from the student.

STRICT evidence retained: `.fencepost-generated-0018.test_adversarial::test_percentile_uses_true_division_before_integer_conversion` -- AssertionError: percentile must use true division.

## Equivalence triage

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
