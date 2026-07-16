"""Build a synthetic student submission with realistic git history.

Fencepost needs a repo where `git blame` can separate instructor scaffold from
student work. This script creates one: an instructor commit with stubs, then a
week of student commits implementing them.

The student's code contains genuine comprehension gaps at boundary conditions,
and the student's tests pass while never exercising those boundaries. That is
the whole point: the tests are green, the understanding is not verified.

Usage:  python demo/build_demo_repo.py [output_dir]
"""

import subprocess
import sys
from pathlib import Path

INSTRUCTOR = ("Ana Martinez", "a.martinez@ejemplo.edu")
STUDENT = ("Diego Ramos", "d.ramos@alumnos.ejemplo.edu")

STARTER_ANALYTICS = '''"""Gradebook analytics.

CS2 - Assignment 3. Implement each function below.
Do not change the signatures. Add your own tests in tests/test_analytics.py.
"""


def letter_grade(score):
    """Return the letter grade for a numeric score.

    A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
    """
    raise NotImplementedError


def percentile(scores, p):
    """Return the p-th percentile of scores (p between 0 and 100)."""
    raise NotImplementedError


def rank(scores, target):
    """Return the 1-based rank of target within scores. Highest score is rank 1."""
    raise NotImplementedError


def top_n(scores, n):
    """Return the n highest scores, in descending order."""
    raise NotImplementedError
'''

STARTER_TESTS = '''from gradebook.analytics import letter_grade


def test_letter_grade_f():
    assert letter_grade(12) == "F"
'''

STEP_LETTER_GRADE = '''
def letter_grade(score):
    """Return the letter grade for a numeric score.

    A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
'''

STEP_PERCENTILE_V1 = '''
def percentile(scores, p):
    """Return the p-th percentile of scores (p between 0 and 100)."""
    ordered = sorted(scores)
    k = int(len(ordered) * p / 100)
    return ordered[k]
'''

STEP_PERCENTILE_V2 = '''
def percentile(scores, p):
    """Return the p-th percentile of scores (p between 0 and 100)."""
    ordered = sorted(scores)
    k = int(len(ordered) * p / 100)
    if k >= len(ordered):
        k = len(ordered) - 1
    return ordered[k]
'''

STEP_PERCENTILE_V3 = '''
def clamp_percent(p):
    """Clamp a percentage to the inclusive 0-100 interval."""
    if p < 0:
        p = 0
    if p > 100:
        p = 100
    return p


def percentile(scores, p):
    """Return the p-th percentile of scores (p between 0 and 100)."""
    p = clamp_percent(p)
    ordered = sorted(scores)
    k = int(len(ordered) * p / 100)
    if k >= len(ordered):
        k = len(ordered) - 1
    return ordered[k]
'''

STEP_RANK_TOPN = '''
def rank(scores, target):
    """Return the 1-based rank of target within scores. Highest score is rank 1."""
    higher = 0
    for s in scores:
        if s > target:
            higher += 1
    return higher + 1


def top_n(scores, n):
    """Return the n highest scores, in descending order."""
    ordered = sorted(scores, reverse=True)
    return ordered[:n]
'''

TESTS_LETTER_GRADE = '''from gradebook.analytics import letter_grade


def test_letter_grade_f():
    assert letter_grade(12) == "F"


def test_letter_grade_a():
    assert letter_grade(95) == "A"


def test_letter_grade_b():
    assert letter_grade(85) == "B"


def test_letter_grade_c():
    assert letter_grade(72) == "C"
'''

TESTS_FULL = '''from gradebook.analytics import clamp_percent, letter_grade, percentile, rank, top_n


def test_letter_grade_f():
    assert letter_grade(12) == "F"


def test_letter_grade_a():
    assert letter_grade(95) == "A"


def test_letter_grade_b():
    assert letter_grade(85) == "B"


def test_letter_grade_c():
    assert letter_grade(72) == "C"


def test_percentile_median():
    assert percentile([10, 20, 30, 40, 50], 50) == 30


def test_percentile_low():
    assert percentile([10, 20, 30, 40, 50], 20) == 20


def test_clamp_percent_outside_interval():
    assert clamp_percent(-5) == 0
    assert clamp_percent(50) == 50
    assert clamp_percent(120) == 100


def test_rank_middle():
    assert rank([90, 80, 70], 80) == 2


def test_rank_highest():
    assert rank([90, 80, 70], 90) == 1


def test_top_n():
    assert top_n([50, 90, 70, 60], 2) == [90, 70]
'''

STUDENT_README = """# Assignment 3 - Gradebook Analytics

CS2, Prof. Martinez.

Implemented `letter_grade`, `percentile`, `clamp_percent`, `rank` and `top_n`.
All tests pass: `pytest -q`
"""

# (message, author, iso_date, [(path, content), ...])
HISTORY = [
    (
        "Assignment 3 starter: gradebook analytics",
        INSTRUCTOR,
        "2026-07-06T09:15:00",
        [
            ("gradebook/__init__.py", ""),
            ("gradebook/analytics.py", STARTER_ANALYTICS),
            ("tests/test_analytics.py", STARTER_TESTS),
            ("pytest.ini", "[pytest]\ntestpaths = tests\n"),
        ],
    ),
    (
        "implement letter_grade",
        STUDENT,
        "2026-07-07T21:42:00",
        [("gradebook/analytics.py", None)],  # placeholder, filled by _apply
    ),
    (
        "add tests for letter_grade",
        STUDENT,
        "2026-07-07T22:10:00",
        [("tests/test_analytics.py", TESTS_LETTER_GRADE)],
    ),
    (
        "implement percentile",
        STUDENT,
        "2026-07-09T20:05:00",
        [("gradebook/analytics.py", None)],
    ),
    (
        "fix percentile index out of range when p=100",
        STUDENT,
        "2026-07-09T20:31:00",
        [("gradebook/analytics.py", None)],
    ),
    (
        "implement rank and top_n",
        STUDENT,
        "2026-07-10T01:47:00",
        [("gradebook/analytics.py", None)],
    ),
    (
        "clamp percentile inputs to the valid interval",
        STUDENT,
        "2026-07-10T01:55:00",
        [("gradebook/analytics.py", None)],
    ),
    (
        "add remaining tests, all green",
        STUDENT,
        "2026-07-10T02:03:00",
        [("tests/test_analytics.py", TESTS_FULL)],
    ),
    (
        "add readme",
        STUDENT,
        "2026-07-10T02:08:00",
        [("README.md", STUDENT_README)],
    ),
]


def _run(args, cwd, env=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, env=env)


def _write(root: Path, rel: str, content: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _analytics_at(step: int) -> str:
    """Rebuild analytics.py as it looked after each student commit."""
    header = STARTER_ANALYTICS.split("\n\ndef letter_grade")[0]
    stub_pct = '\n\ndef percentile(scores, p):\n    """Return the p-th percentile of scores (p between 0 and 100)."""\n    raise NotImplementedError\n'
    stub_rank = '\n\ndef rank(scores, target):\n    """Return the 1-based rank of target within scores. Highest score is rank 1."""\n    raise NotImplementedError\n\n\ndef top_n(scores, n):\n    """Return the n highest scores, in descending order."""\n    raise NotImplementedError\n'

    if step == 1:  # letter_grade implemented, rest still stubs
        return header + "\n" + STEP_LETTER_GRADE + stub_pct + stub_rank
    if step == 3:  # percentile v1 (no guard)
        return header + "\n" + STEP_LETTER_GRADE + "\n" + STEP_PERCENTILE_V1 + stub_rank
    if step == 4:  # percentile v2 (guard added)
        return header + "\n" + STEP_LETTER_GRADE + "\n" + STEP_PERCENTILE_V2 + stub_rank
    if step == 5:  # rank + top_n
        return (
            header
            + "\n"
            + STEP_LETTER_GRADE
            + "\n"
            + STEP_PERCENTILE_V2
            + "\n"
            + STEP_RANK_TOPN
        )
    if step == 6:  # clamp is wired into percentile
        return (
            header
            + "\n"
            + STEP_LETTER_GRADE
            + "\n"
            + STEP_PERCENTILE_V3
            + "\n"
            + STEP_RANK_TOPN
        )
    raise ValueError(step)


def build(out: Path):
    if out.exists():
        print(f"error: {out} already exists, remove it first", file=sys.stderr)
        return 1

    out.mkdir(parents=True)
    _run(["git", "init", "-q", "-b", "main"], out)

    for i, (msg, (name, email), date, files) in enumerate(HISTORY):
        for rel, content in files:
            if content is None:
                content = _analytics_at(i)
            _write(out, rel, content)

        env = {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_COMMITTER_DATE": date,
            "PATH": __import__("os").environ.get("PATH", ""),
            "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
        }
        _run(["git", "add", "-A"], out)
        _run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", msg], out, env)

    print(f"built {out} with {len(HISTORY)} commits")
    print(f"  instructor: {INSTRUCTOR[0]}   student: {STUDENT[0]}")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo/student-repo")
    sys.exit(build(target.resolve()))
