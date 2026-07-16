# Fencepost comprehension report

This report is formative and advisory\. It identifies behavior changes the submitted tests did not distinguish; it is not a verdict, accusation, or standalone score\. An instructor should review the evidence and decide whether a conversation would be useful\.

## Summary

Diego Ramos's submitted pytest suite passed. Fencepost found 21 execution-grounded places where understanding remains unverified.

Analyzed repository commit: `3a93a3eb3a34e04aed55c7761d7c8d1cf0ec414c`.

## Places to discuss

### 1. gradebook/analytics\.py:13

line 13: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        if score &gt;= 90:

Change considered: `score &gt;= 90` → `score &gt; 90`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 13 of gradebook/analytics\.py: 13:     if score &gt;= 90:  Consider changing \`score &gt;= 90\` to \`score &gt; 90\`\.  After changing the first condition from \`score &gt;= 90\` to \`score &gt; 90\`, what observable grade assignment changes at the documented lower boundary of the A range, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0000\.test\_adversarial::test\_letter\_grade\_assigns\_a\_at\_inclusive\_ninety\_boundary`: AssertionError: assert 'B' == 'A'      \- A   \+ B

Artifact: `triage/contract/86e0917e5c6bf1d8/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 2. gradebook/analytics\.py:13

line 13: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        if score &gt;= 90:

Change considered: `90` → `89`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 13 of gradebook/analytics\.py: 13:     if score &gt;= 90:  Consider changing \`90\` to \`89\`\.  After changing the first cutoff from 90 to 89, which score is now classified differently from the documented grade ranges, and why does the order of the conditions produce that result?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0001\.test\_adversarial::test\_letter\_grade\_89\_is\_b`: AssertionError: assert 'A' == 'B'      \- B   \+ A

Artifact: `triage/contract/2e231a949dfe891d/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 3. gradebook/analytics\.py:13

line 13: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        if score &gt;= 90:

Change considered: `90` → `91`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 13 of gradebook/analytics\.py: 13:     if score &gt;= 90:  Consider changing \`90\` to \`91\`\.  After changing the A\-grade condition from \`score &gt;= 90\` to \`score &gt;= 91\`, what behavior breaks at the documented lower boundary of the A range, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0002\.test\_adversarial::test\_letter\_grade\_assigns\_a\_at\_exact\_lower\_boundary`: AssertionError: assert 'B' == 'A'      \- A   \+ B

Artifact: `triage/contract/1d2de104b4e2ea87/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 4. gradebook/analytics\.py:15

line 15: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 80:

Change considered: `score &gt;= 80` → `score &gt; 80`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 15 of gradebook/analytics\.py: 15:     elif score &gt;= 80:  Consider changing \`score &gt;= 80\` to \`score &gt; 80\`\.  After changing \`elif score &gt;= 80\` to \`elif score &gt; 80\`, what observable behavior breaks at the B\-grade lower boundary, and why does the next condition determine the returned grade?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0003\.test\_adversarial::test\_letter\_grade\_includes\_b\_lower\_boundary`: AssertionError: assert 'C' == 'B'      \- B   \+ C

Artifact: `triage/contract/bc57b02d4b5d32a1/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 5. gradebook/analytics\.py:15

line 15: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 80:

Change considered: `80` → `79`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 15 of gradebook/analytics\.py: 15:     elif score &gt;= 80:  Consider changing \`80\` to \`79\`\.  After changing the B threshold from \`score &gt;= 80\` to \`score &gt;= 79\`, what grade is returned for a score of 79, what should it be under the documented ranges, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0004\.test\_adversarial::test\_letter\_grade\_79\_is\_c`: AssertionError: assert 'B' == 'C'      \- C   \+ B

Artifact: `triage/contract/de6e7433e88c46a6/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 6. gradebook/analytics\.py:15

line 15: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 80:

Change considered: `80` → `81`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 15 of gradebook/analytics\.py: 15:     elif score &gt;= 80:  Consider changing \`80\` to \`81\`\.  After changing \`elif score &gt;= 80\` to \`elif score &gt;= 81\` in \`letter\_grade\`, which score range now receives a different letter grade, what does it receive, and why does execution reach that branch?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0005\.test\_adversarial::test\_letter\_grade\_assigns\_b\_at\_inclusive\_lower\_boundary`: AssertionError: assert 'C' == 'B'      \- B   \+ C

Artifact: `triage/contract/ce1508b29bd64233/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 7. gradebook/analytics\.py:17

line 17: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 70:

Change considered: `score &gt;= 70` → `score &gt; 70`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 17 of gradebook/analytics\.py: 17:     elif score &gt;= 70:  Consider changing \`score &gt;= 70\` to \`score &gt; 70\`\.  After changing the C\-grade condition from \`score &gt;= 70\` to \`score &gt; 70\`, what happens for a score at the lower C\-grade boundary, and why does the condition sequence produce that result?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0006\.test\_adversarial::test\_letter\_grade\_assigns\_c\_at\_inclusive\_70\_boundary`: AssertionError: assert 'D' == 'C'      \- C   \+ D

Artifact: `triage/contract/75b9f689f32ac45a/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 8. gradebook/analytics\.py:17

line 17: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 70:

Change considered: `70` → `69`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 17 of gradebook/analytics\.py: 17:     elif score &gt;= 70:  Consider changing \`70\` to \`69\`\.  After changing \`elif score &gt;= 70\` to \`elif score &gt;= 69\` in \`letter\_grade\`, what observable boundary behavior changes, and why does the order of the conditions cause it?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0007\.test\_adversarial::test\_letter\_grade\_69\_is\_d`: AssertionError: assert 'C' == 'D'      \- D   \+ C

Artifact: `triage/contract/dbb83dad668b1b68/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 9. gradebook/analytics\.py:17

line 17: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 70:

Change considered: `70` → `71`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 17 of gradebook/analytics\.py: 17:     elif score &gt;= 70:  Consider changing \`70\` to \`71\`\.  After changing the C\-grade cutoff from \`score &gt;= 70\` to \`score &gt;= 71\`, what observable behavior breaks at the C/D boundary, and why does the condition order produce that result?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0008\.test\_adversarial::test\_letter\_grade\_includes\_seventy\_in\_c\_range`: AssertionError: assert 'D' == 'C'      \- C   \+ D

Artifact: `triage/contract/8e3bb3b74b5e7623/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 10. gradebook/analytics\.py:19

line 19: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 60:

Change considered: `score &gt;= 60` → `score &gt; 60`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 19 of gradebook/analytics\.py: 19:     elif score &gt;= 60:  Consider changing \`score &gt;= 60\` to \`score &gt; 60\`\.  After changing \`score &gt;= 60\` to \`score &gt; 60\` in \`letter\_grade\`, what observable grade\-assignment behavior changes at the boundary between D and F, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0009\.test\_adversarial::test\_letter\_grade\_includes\_sixty\_in\_d\_range`: AssertionError: assert 'F' == 'D'      \- D   \+ F

Artifact: `triage/contract/9e215f782bcfc8e3/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 11. gradebook/analytics\.py:19

line 19: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 60:

Change considered: `60` → `59`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 19 of gradebook/analytics\.py: 19:     elif score &gt;= 60:  Consider changing \`60\` to \`59\`\.  What observable grading behavior changes for a score at the boundary just below 60 after the D\-grade condition changes from \`&gt;= 60\` to \`&gt;= 59\`, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0010\.test\_adversarial::test\_score\_59\_is\_failing\_grade`: AssertionError: assert 'D' == 'F'      \- F   \+ D

Artifact: `triage/contract/db66414d596970b4/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 12. gradebook/analytics\.py:19

line 19: commit a0f7cba on 2026\-07\-07 \(implement letter\_grade\).

Authored source:

        elif score &gt;= 60:

Change considered: `60` → `61`.

Question:

In commit a0f7cba on 2026\-07\-07, you wrote line 19 of gradebook/analytics\.py: 19:     elif score &gt;= 60:  Consider changing \`60\` to \`61\`\.  After changing the D\-grade cutoff from \`score &gt;= 60\` to \`score &gt;= 61\`, which input's letter\-grade result changes, what result does it produce, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0011\.test\_adversarial::test\_letter\_grade\_includes\_sixty\_in\_d\_range`: AssertionError: assert 'F' == 'D'      \- D   \+ F

Artifact: `triage/contract/7d45e006f2ec7b27/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 13. gradebook/analytics\.py:27

line 27: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &lt; 0:

Change considered: `p &lt; 0` → `p &lt;= 0`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 27 of gradebook/analytics\.py: 27:     if p &lt; 0:  Consider changing \`p &lt; 0\` to \`p &lt;= 0\`\.  After changing \`if p &lt; 0\` to \`if p &lt;= 0\`, what observable behavior can change for an input that compares equal to zero but has a distinct representation or type, and why does the reassignment matter?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0012\.test\_adversarial::test\_clamp\_percent\_preserves\_negative\_zero\_float`: AttributeError: 'int' object has no attribute 'hex'

Artifact: `triage/contract/67c52a2840605244/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 14. gradebook/analytics\.py:27

line 27: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &lt; 0:

Change considered: `0` → `\-1`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 27 of gradebook/analytics\.py: 27:     if p &lt; 0:  Consider changing \`0\` to \`\-1\`\.  After changing \`if p &lt; 0\` to \`if p &lt; \-1\`, what observable behavior breaks for negative percentages closest to zero, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0013\.test\_adversarial::test\_clamp\_percent\_clamps\_negative\_one\_to\_zero`: AssertionError: assert \-1 == 0  \+  where \-1 = &lt;function clamp\_percent at 0x7aa2dae04040&gt;\(\-1\)  \+    where &lt;function clamp\_percent at 0x7aa2dae04040&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0013\-oegrhbew/mutant/tree/gradebook/analytics\.py'&gt;\.clamp\_percent  \+      where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0013\-oegrhbew/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/ab756a31efd05a69/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 15. gradebook/analytics\.py:27

line 27: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &lt; 0:

Change considered: `0` → `1`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 27 of gradebook/analytics\.py: 27:     if p &lt; 0:  Consider changing \`0\` to \`1\`\.  After changing the lower\-bound check in \`clamp\_percent\` from \`p &lt; 0\` to \`p &lt; 1\`, what happens to inputs strictly between 0 and 1, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0014\.test\_adversarial::test\_clamp\_percent\_preserves\_positive\_fraction\_below\_one`: AssertionError: assert 0 == 0\.5  \+  where 0 = &lt;function clamp\_percent at 0x79689c0ec040&gt;\(0\.5\)  \+    where &lt;function clamp\_percent at 0x79689c0ec040&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0014\-ntmrl96d/mutant/tree/gradebook/analytics\.py'&gt;\.clamp\_percent  \+      where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0014\-ntmrl96d/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/44bc84979be41b9d/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 16. gradebook/analytics\.py:29

line 29: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &gt; 100:

Change considered: `p &gt; 100` → `p &gt;= 100`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 29 of gradebook/analytics\.py: 29:     if p &gt; 100:  Consider changing \`p &gt; 100\` to \`p &gt;= 100\`\.  For an input exactly equal to 100\.0, what observable difference in \`clamp\_percent\`’s returned value results from changing \`p &gt; 100\` to \`p &gt;= 100\`, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0015\.test\_adversarial::test\_clamp\_percent\_preserves\_upper\_boundary\_float\_representation`: AssertionError: assert '100' == '100\.0'      \- 100\.0   ?    \-\-   \+ 100

Artifact: `triage/contract/92261c57ed4e3d56/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 17. gradebook/analytics\.py:29

line 29: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &gt; 100:

Change considered: `100` → `99`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 29 of gradebook/analytics\.py: 29:     if p &gt; 100:  Consider changing \`100\` to \`99\`\.  After changing the upper\-bound check from \`p &gt; 100\` to \`p &gt; 99\`, what observable behavior changes for a fractional input strictly between 99 and 100, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0016\.test\_adversarial::test\_clamp\_percent\_preserves\_fraction\_below\_upper\_bound`: AssertionError: assert 100 == 99\.5  \+  where 100 = &lt;function clamp\_percent at 0x76b2b6fac040&gt;\(99\.5\)  \+    where &lt;function clamp\_percent at 0x76b2b6fac040&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0016\-yhdo\_a7e/mutant/tree/gradebook/analytics\.py'&gt;\.clamp\_percent  \+      where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0016\-yhdo\_a7e/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/086eee6e74bf01f0/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 18. gradebook/analytics\.py:29

line 29: commit 1fe8a85 on 2026\-07\-10 \(clamp percentile inputs to the valid interval\).

Authored source:

        if p &gt; 100:

Change considered: `100` → `101`.

Question:

In commit 1fe8a85 on 2026\-07\-10, you wrote line 29 of gradebook/analytics\.py: 29:     if p &gt; 100:  Consider changing \`100\` to \`101\`\.  After changing the upper\-bound check from \`p &gt; 100\` to \`p &gt; 101\`, what observable behavior does \`clamp\_percent\` exhibit for values just above the documented inclusive 0–100 range, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0017\.test\_adversarial::test\_clamp\_percent\_clamps\_first\_integer\_above\_upper\_bound`: AssertionError: assert 101 == 100  \+  where 101 = &lt;function clamp\_percent at 0x77db36eec040&gt;\(101\)  \+    where &lt;function clamp\_percent at 0x77db36eec040&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0017\-\_swpm8gf/mutant/tree/gradebook/analytics\.py'&gt;\.clamp\_percent  \+      where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0017\-\_swpm8gf/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/2e3d6e7b8bdac2ad/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 19. gradebook/analytics\.py:38

line 38: commit dceec68 on 2026\-07\-09 \(implement percentile\).

Authored source:

        k = int(len(ordered) * p / 100)

Change considered: `len\(ordered\) \* p / 100` → `len\(ordered\) \* p // 100`.

Question:

In commit dceec68 on 2026\-07\-09, you wrote line 38 of gradebook/analytics\.py: 38:     k = int\(len\(ordered\) \* p / 100\)  Consider changing \`len\(ordered\) \* p / 100\` to \`len\(ordered\) \* p // 100\`\.  After changing \`len\(ordered\) \* p / 100\` to \`len\(ordered\) \* p // 100\`, what percentile results break when that calculation has a fractional value, and why does applying \`int\(\)\` afterward no longer preserve the original index?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0000\.test\_adversarial::test\_percentile\_index\_uses\_true\_division\_opcode`: assert '7a0b0000' in '9700740100000000000000007c01ab010000000000007d01740300000000000000007c00ab010000000000007d027405000000000000000074070\.\.\.00000000007c02ab010000000000006b5c0000720e740700000000000000007c02ab0100000000000064027a0a00007d037c027c03190000005300'  \+  where '9700740100000000000000007c01ab010000000000007d01740300000000000000007c00ab010000000000007d027405000000000000000074070\.\.\.00000000007c02ab010000000000006b5c0000720e740700000000000000007c02ab0100000000000064027a0a00007d037c027c03190000005300' = &lt;built\-in method hex of bytes object at 0x7e0e11e36db0&gt;\(\)  \+    where &lt;built\-in method hex of bytes object at 0x7e0e11e36db0&gt; = b'\\x97\\x00t\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\|\\x01\\xab\\x01\\x00\\x00\\x00\\x00\\x00\\x00\}\\x01t\\x03\\x00\\x00\\x00\\x00\\x00\\x00\.\.\.0\\x00\\x00\\x00\\x00\\x00\\x00\\x00\|\\x02\\xab\\x01\\x00\\x00\\x00\\x00\\x00\\x00d\\x02z\\n\\x00\\x00\}\\x03\|\\x02\|\\x03\\x19\\x00\\x00\\x00S\\x00'\.hex  \+      where b'\\x97\\x00t\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\|\\x01\\xab\\x01\\x00\\x00\\x00\\x00\\x00\\x00\}\\x01t\\x03\\x00\\x00\\x00\\x00\\x00\\x00\.\.\.0\\x00\\x00\\x00\\x00\\x00\\x00\\x00\|\\x02\\xab\\x01\\x00\\x00\\x00\\x00\\x00\\x00d\\x02z\\n\\x00\\x00\}\\x03\|\\x02\|\\x03\\x19\\x00\\x00\\x00S\\x00' = &lt;code object percentile at 0x7e0e11fff280, file "/work/jobs/triage\-0000\-g3y1p2j0/mutant/tree/gradebook/analytics\.py", line 31&gt;\.co\_code  \+        where &lt;code object percentile at 0x7e0e11fff280, file "/work/jobs/triage\-0000\-g3y1p2j0/mutant/tree/gradebook/analytics\.py", line 31&gt; = &lt;function percentile at 0x7e0e11d50360&gt;\.\_\_code\_\_  \+          where &lt;function percentile at 0x7e0e11d50360&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0000\-g3y1p2j0/mutant/tree/gradebook/analytics\.py'&gt;\.percentile  \+            where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0000\-g3y1p2j0/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/bb49d21e0537bf13/attempt\-02/attempt\.json`.

No student answer was supplied in this run.

### 20. gradebook/analytics\.py:38

line 38: commit dceec68 on 2026\-07\-09 \(implement percentile\).

Authored source:

        k = int(len(ordered) * p / 100)

Change considered: `100` → `99`.

Question:

In commit dceec68 on 2026\-07\-09, you wrote line 38 of gradebook/analytics\.py: 38:     k = int\(len\(ordered\) \* p / 100\)  Consider changing \`100\` to \`99\`\.  After changing the percentile index calculation’s divisor from 100 to 99, which percentile requests can return a different sorted score, and why does that altered denominator shift the computed index?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0019\.test\_adversarial::test\_percentile\_uses\_hundred\_based\_indexing`: AssertionError: assert 30 == 20  \+  where 30 = &lt;function percentile at 0x7951c4b60220&gt;\(\[10, 20, 30\], 66\)  \+    where &lt;function percentile at 0x7951c4b60220&gt; = &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0019\-bn6fgxh0/mutant/tree/gradebook/analytics\.py'&gt;\.percentile  \+      where &lt;module 'gradebook\.analytics' from '/work/jobs/triage\-0019\-bn6fgxh0/mutant/tree/gradebook/analytics\.py'&gt; = gradebook\.analytics

Artifact: `triage/contract/764a18c525e359d6/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

### 21. gradebook/analytics\.py:39

line 39: commit c59d8e6 on 2026\-07\-09 \(fix percentile index out of range when p=100\).

Authored source:

        if k &gt;= len(ordered):

Change considered: `k &gt;= len\(ordered\)` → `k &gt; len\(ordered\)`.

Question:

In commit c59d8e6 on 2026\-07\-09, you wrote line 39 of gradebook/analytics\.py: 39:     if k &gt;= len\(ordered\):  Consider changing \`k &gt;= len\(ordered\)\` to \`k &gt; len\(ordered\)\`\.  How does changing the bounds check from \`k &gt;= len\(ordered\)\` to \`k &gt; len\(ordered\)\` affect \`percentile\` when \`p\` is 100 for a non\-empty score list, and why?

Execution evidence:

Original passed; mutant failed at `\.fencepost\-generated\-0020\.test\_adversarial::test\_percentile\_at\_100\_returns\_largest\_score`: IndexError: list index out of range

Artifact: `triage/contract/ebad6149cee857c9/attempt\-01/attempt\.json`.

No student answer was supplied in this run.

## Deliberately not asked

No strict-only, contract-shielded mutants were found.

## Equivalence triage

STRICT equivalent rate: **0.000** (0 probable equivalent, 21 real gap, 0 unresolved).

CONTRACT equivalent rate: **0.000** (0 probable equivalent, 21 real gap, 0 unresolved).

CONTRACT limitation: CONTRACT mode can hide a genuine behavioral gap when the only witness uses type, identity, a custom object, or another excluded input\. This deliberate false\-negative risk means its rate is execution\-grounded only under the stated caller contract, not universal truth\.

## Traceability

Every behavioral statement above points to an execution artifact. Core artifacts:

- `run\.json`
- `baseline/result\.json`
- `selection\.json`
- `triage/summary\.json`
- `probe/summary\.json`
