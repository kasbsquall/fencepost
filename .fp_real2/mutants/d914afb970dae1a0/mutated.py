"""Gradebook analytics.

CS2 - Assignment 3. Implement each function below.
Do not change the signatures. Add your own tests in tests/test_analytics.py.
"""

def letter_grade(score):
    """Return the letter grade for a numeric score.

    A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: below 60
    """
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

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

def rank(scores, target):
    """Return the 1-based rank of target within scores. Highest score is rank 1."""
    higher = 0
    for s in scores:
        if s > target:
            higher -= 1
    return higher + 1

def top_n(scores, n):
    """Return the n highest scores, in descending order."""
    ordered = sorted(scores, reverse=True)
    return ordered[:n]
