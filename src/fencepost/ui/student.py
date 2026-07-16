"""Server-rendered student probe screens with evidence withheld until answer commit."""

from __future__ import annotations

import ast
import difflib
from collections.abc import Mapping, Sequence
from typing import Any

from . import _icon, _icon_sprite, _logo, _mapping, _sequence, _text


def _page(
    *,
    title: str,
    body: str,
    current: int | None = None,
    total: int | None = None,
) -> str:
    progress = ""
    if current is not None and total:
        progress = (
            '<p class="probe-progress" aria-label="Question progress">'
            f'<span class="data-value">{current}</span> / '
            f'<span class="data-value">{total}</span></p>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{_text(title)}</title>
  <link rel="stylesheet" href="/assets/ledger.css">
</head>
<body class="probe-body">
  {_icon_sprite()}
  <a class="skip-link" href="#main">Skip to question</a>
  <header class="masthead"><div class="shell masthead-inner">{_logo(linked=False)}{progress}</div></header>
  <main class="shell probe-main" id="main">{body}</main>
</body>
</html>"""


def _count_word(value: int) -> str:
    words = (
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
    )
    return words[value] if 0 <= value < len(words) else str(value)


def _csrf(token: str) -> str:
    return f'<input type="hidden" name="csrf_token" value="{_text(token)}">'


def _source_grounding(place: Mapping[str, Any]) -> str:
    grounding = _mapping(place.get("grounding"))
    authored = [_mapping(item) for item in _sequence(grounding.get("authored_lines"))]
    path = grounding.get("path")
    line = grounding.get("start_line")
    location = ":".join(
        _text(value) for value in (path, line) if value is not None
    )
    first = authored[0] if authored else {}
    provenance = []
    commit = first.get("commit")
    if commit:
        provenance.append(f"<code>{_text(str(commit)[:7])}</code>")
    date = first.get("author_date")
    if date:
        provenance.append(f'<time datetime="{_text(date)}">{_text(date)}</time>')
    summary = first.get("commit_summary")
    if summary:
        provenance.append(f'“{_text(summary)}”')
    source_lines = []
    for authored_line in authored:
        number = authored_line.get("line")
        source = authored_line.get("text")
        if number is None or source is None:
            continue
        source_lines.append(
            '<span class="source-line">'
            f'<span class="line-number" aria-label="line {_text(number)}">{_text(number)}</span>'
            f'<span class="source-code">{_text(source)}</span>'
            "</span>"
        )
    return f"""
<section class="probe-grounding" aria-labelledby="grounding-heading">
  <p class="eyebrow" id="grounding-heading">Code you authored</p>
  {f'<p class="probe-location">{location}</p>' if location else ''}
  {f'<p class="probe-provenance">{" · ".join(provenance)}</p>' if provenance else ''}
  {f'<pre class="source-block"><code>{chr(10).join(source_lines)}</code></pre>' if source_lines else ''}
</section>""".strip()


def render_probe_start(report: Mapping[str, Any], *, total: int, token: str) -> str:
    tests_pass = report.get("submitted_suite_tests_passed")
    count = _count_word(total).capitalize()
    suite_sentence = (
        "Your tests pass. "
        if isinstance(tests_pass, int) and not isinstance(tests_pass, bool)
        else ""
    )
    body = f"""
<section class="probe-intro probe-panel">
  <p class="eyebrow">A conversation about your code</p>
  <h1>{_text(count)} questions about code you wrote.</h1>
  <p class="probe-lead">{suite_sentence}These questions are about behaviour your tests do not check.</p>
  <p>There is no score and no time limit. Your instructor sees your answers and the same evidence you will see.</p>
  <form method="post" action="/begin">{_csrf(token)}<button class="probe-button" type="submit">Begin</button></form>
</section>"""
    return _page(
        title="Fencepost student probe",
        body=body,
        current=1 if total else None,
        total=total,
    )


def render_probe_question(
    place: Mapping[str, Any],
    *,
    index: int,
    total: int,
    token: str,
    validation_message: str | None = None,
) -> str:
    question = _mapping(place.get("question")).get("question_text")
    site_id = place.get("site_id")
    body = f"""
{_source_grounding(place)}
<section class="probe-question" aria-labelledby="question-heading">
  <p class="eyebrow">Question</p>
  {f'<h1 class="probe-question-text" id="question-heading">{_text(question)}</h1>' if question else ''}
  <form method="post" action="/answer/{index}" class="probe-answer-form">
    {_csrf(token)}
    <input type="hidden" name="site_id" value="{_text(site_id)}">
    <label for="answer">Your answer</label>
    <textarea id="answer" name="answer" rows="8" autofocus></textarea>
    {f'<p class="probe-choice-message" role="status">{_text(validation_message)}</p>' if validation_message else ''}
    <div class="probe-commit-actions">
      <button class="probe-button" type="submit" name="commitment" value="answer">Submit answer</button>
      <button class="probe-button probe-button-secondary" type="submit" name="commitment" value="unknown">I donâ€™t know</button>
    </div>
    <p class="probe-choice-note">Either choice records your response before the evidence is shown.</p>
  </form>
</section>"""
    return _page(
        title=f"Question {index + 1} · Fencepost",
        body=body,
        current=index + 1,
        total=total,
    )


def _primary_mutant(place: Mapping[str, Any]) -> Mapping[str, Any]:
    mutants = [_mapping(item) for item in _sequence(place.get("mutants"))]
    return mutants[0] if mutants else {}


def _assertion_line(test_source: object) -> str | None:
    if not isinstance(test_source, str):
        return None
    return next(
        (line.strip() for line in test_source.splitlines() if line.strip().startswith("assert ")),
        None,
    )


def _edit_size(before: object, after: object) -> int | None:
    if not isinstance(before, str) or not isinstance(after, str):
        return None
    size = 0
    for tag, left_start, left_end, right_start, right_end in difflib.SequenceMatcher(
        None, before, after
    ).get_opcodes():
        if tag != "equal":
            size += max(left_end - left_start, right_end - right_start)
    return size


def _equality_parts(expression: ast.AST) -> tuple[ast.AST, ast.AST] | None:
    if not isinstance(expression, ast.Compare) or len(expression.ops) != 1:
        return None
    if not isinstance(expression.ops[0], ast.Eq) or len(expression.comparators) != 1:
        return None
    return expression.left, expression.comparators[0]


def _consequence_from_assertion(
    test_source: object, failure_message: object
) -> str | None:
    """Derive a narrow equality consequence without evaluating generated code."""
    if not isinstance(test_source, str) or not isinstance(failure_message, str):
        return None
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return None
    asserted = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.Assert)),
        None,
    )
    if asserted is None:
        return None
    expected_parts = _equality_parts(asserted.test)
    if expected_parts is None or not isinstance(expected_parts[0], ast.Call):
        return None
    call, expected = expected_parts

    observed_parts = None
    for line in failure_message.splitlines():
        marker = line.find("assert ")
        if marker < 0:
            continue
        try:
            observed = ast.parse(line[marker + len("assert ") :], mode="eval")
        except SyntaxError:
            continue
        observed_parts = _equality_parts(observed.body)
        if observed_parts is not None:
            break
    if observed_parts is None:
        return None
    actual, observed_expected = observed_parts
    if ast.dump(expected, include_attributes=False) != ast.dump(
        observed_expected, include_attributes=False
    ):
        return None
    call_source = ast.get_source_segment(test_source, call) or ast.unparse(call)
    return (
        f"Calling <code>{_text(call_source)}</code> returns "
        f"<code>{_text(ast.unparse(actual))}</code> instead of "
        f"<code>{_text(ast.unparse(expected))}</code>."
    )


def _reveal_evidence(place: Mapping[str, Any]) -> str:
    mutant = _primary_mutant(place)
    mutation = _mapping(mutant.get("mutation"))
    evidence = _mapping(mutant.get("evidence"))
    test = _mapping(evidence.get("adversarial_test"))
    failure = _mapping(evidence.get("failing_assertion"))
    diff = mutation.get("unified_diff")
    assertion = _assertion_line(test.get("source"))
    failure_message = failure.get("message")
    assertion_text = "\n".join(
        str(item) for item in (assertion, failure_message) if item
    )
    tests = mutant.get("submitted_suite_tests_passed")
    execution = _mapping(_mapping(mutant.get("mutant")).get("execution"))
    suite_passed = execution.get("status") == "survived"
    consequence = _consequence_from_assertion(
        test.get("source"), failure.get("message")
    )
    caption = (
        "One character. Here is what your submitted suite said about it."
        if _edit_size(
            mutation.get("original_segment"), mutation.get("mutated_segment")
        )
        == 1
        else "Here is what your submitted suite said about this change."
    )
    beats = []
    if diff is not None:
        beats.append(
            '<section class="reveal-beat reveal-change">'
            '<p class="eyebrow">The change</p>'
            f'<pre><code>{_text(diff)}</code></pre>'
            f'<p class="reveal-caption">{_text(caption)}</p>'
            "</section>"
        )
    if (
        suite_passed
        and isinstance(tests, int)
        and not isinstance(tests, bool)
    ):
        beats.append(
            '<section class="reveal-beat reveal-suite" aria-label="Submitted tests passed">'
            f'<span class="state-icon">{_icon("check")}</span>'
            f'<p>Your <span class="data-value">{tests}</span> tests — <strong>passed</strong></p>'
            "</section>"
        )
    if assertion_text:
        beats.append(
            '<section class="reveal-beat reveal-failure" aria-label="Assertion failed on changed code">'
            '<p class="eyebrow">What breaks</p>'
            f'<pre><code>{_text(assertion_text)}</code></pre>'
            "</section>"
        )
    if consequence:
        beats.append(f'<p class="reveal-consequence">{consequence}</p>')
    return "".join(beats)


def render_probe_reveal(
    place: Mapping[str, Any],
    *,
    answer: str,
    index: int,
    total: int,
    token: str,
    previous_index: int | None,
) -> str:
    answer_text = answer if answer else "No answer given."
    previous = (
        f'<a class="probe-back" href="/reveal/{previous_index}">Previous reveal</a>'
        if previous_index is not None
        else ""
    )
    body = f"""
<section class="probe-answer-committed">
  <p class="eyebrow">Your recorded answer</p>
  <blockquote>{_text(answer_text)}</blockquote>
</section>
<section class="probe-reveal" aria-labelledby="reveal-heading">
  <h1 id="reveal-heading">Now see what changed.</h1>
  <div class="reveal-sequence">{_reveal_evidence(place)}</div>
</section>
<nav class="probe-actions" aria-label="Probe navigation">
  {previous}
  <form method="post" action="/continue/{index}">{_csrf(token)}<button class="probe-button" type="submit">Continue</button></form>
</nav>"""
    return _page(
        title=f"Evidence for question {index + 1} · Fencepost",
        body=body,
        current=index + 1,
        total=total,
    )


def render_probe_between(
    *,
    index: int,
    total: int,
    next_url: str,
) -> str:
    body = f"""
<section class="probe-panel probe-between">
  <p class="eyebrow">Answer recorded</p>
  <h1>Ready for the next question.</h1>
  <p>Your answers are recorded as you gave them, before you saw the evidence. That is what makes them worth anything.</p>
  <div class="probe-actions">
    <a class="probe-back" href="/reveal/{index}">Re-read this reveal</a>
    <a class="probe-button" href="{_text(next_url)}">Next question</a>
  </div>
</section>"""
    return _page(
        title="Answer recorded · Fencepost",
        body=body,
        current=min(index + 2, total) if total else None,
        total=total,
    )


def render_probe_end(*, total: int, token: str) -> str:
    count = _count_word(total).capitalize()
    body = f"""
<section class="probe-panel probe-end">
  <p class="eyebrow">Complete</p>
  <h1>{_text(count)} answers recorded.</h1>
  <p>Your instructor will see them alongside the same runs you saw.</p>
  <form method="post" action="/download">{_csrf(token)}<button class="probe-button" type="submit">Download answers.json</button></form>
</section>"""
    return _page(title="Answers recorded · Fencepost", body=body)


def render_probe_error(message: str) -> str:
    body = f"""
<section class="probe-panel error-panel" role="alert">
  <p class="eyebrow">Probe unavailable</p>
  <h1>This student probe cannot continue.</h1>
  <p>{_text(message)}</p>
</section>"""
    return _page(title="Fencepost probe unavailable", body=body)


__all__ = [
    "render_probe_between",
    "render_probe_end",
    "render_probe_error",
    "render_probe_question",
    "render_probe_reveal",
    "render_probe_start",
]
