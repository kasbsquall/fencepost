"""Read-only report v2 renderer for the local instructor UI."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


SUPPORTED_REPORT_SCHEMA = "2.0"


class ReportUiError(ValueError):
    """The selected artifact cannot be rendered by this viewer."""


def resolve_report_path(artifact: Path) -> Path:
    """Locate report.json without exposing arbitrary artifact files."""
    root = artifact.expanduser().resolve()
    if root.is_file():
        return root
    candidates = (root / "report" / "report.json", root / "report.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ReportUiError(
        f"No report.json was found under {root}. Run Fencepost through Stage 7 "
        "and serve the resulting artifact directory."
    )


def load_report(report_path: Path) -> dict[str, Any]:
    """Load and minimally validate the versioned UI contract."""
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportUiError(f"report.json is missing: {report_path}") from exc
    except OSError as exc:
        raise ReportUiError(f"report.json could not be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReportUiError(
            f"report.json is not valid JSON (line {exc.lineno}, column {exc.colno})."
        ) from exc
    if not isinstance(payload, dict):
        raise ReportUiError("report.json must contain a JSON object.")
    schema = payload.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        rendered = "missing" if schema is None else repr(schema)
        raise ReportUiError(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the artifact declares {rendered}. Re-run Fencepost to produce a "
            "current report."
        )
    return payload


def render_artifact_page(artifact: Path) -> str:
    """Render either the report or a complete, human-readable error page."""
    try:
        report_path = resolve_report_path(artifact)
        report = load_report(report_path)
    except ReportUiError as exc:
        return render_error_document(str(exc))
    return render_report_document(report)


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    return value if isinstance(value, list) else ()


def _code(value: object, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<code{class_attr}>{_text(value)}</code>"


def _logo() -> str:
    return """
<a class="brand" href="#top" aria-label="Fencepost report home">
  <svg class="brand-mark" viewBox="0 0 100 100" fill="none" aria-hidden="true">
    <rect x="12" y="30" width="9" height="54" rx="2" fill="currentColor"/>
    <rect x="30" y="30" width="9" height="54" rx="2" fill="currentColor"/>
    <rect x="48" y="44" width="9" height="40" rx="2" fill="#B24A3C"/>
    <rect x="66" y="30" width="9" height="54" rx="2" fill="currentColor"/>
    <rect x="84" y="30" width="9" height="54" rx="2" fill="currentColor"/>
  </svg>
  <span class="wordmark"><span>fence</span><span class="wordmark-post">post</span></span>
</a>""".strip()


def _rate_card(report: Mapping[str, Any], mode: str) -> str:
    lower = mode.casefold()
    rate_key = f"equivalent_rate_{lower}"
    count_keys = (
        (f"probable_equivalent_count_{lower}", "probable equivalent"),
        (f"real_gap_count_{lower}", "real gap"),
        (f"unresolved_count_{lower}", "unresolved"),
    )
    if rate_key not in report and not any(key in report for key, _ in count_keys):
        return ""
    rate = report.get(rate_key)
    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
        rate_html = f'<strong class="rate-value">{_text(f"{rate:.3f}")}</strong>'
    elif rate is None:
        rate_html = '<strong class="rate-value rate-unavailable">unavailable</strong>'
    else:
        rate_html = ""
    counts = []
    for key, label in count_keys:
        value = report.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            counts.append(f"<li><strong>{value}</strong> {_text(label)}</li>")
    explanation = (
        "Upper bound under all behavior Python permits."
        if mode == "STRICT"
        else "Evidence under the stated plain-caller contract."
    )
    return f"""
<article class="rate-card" aria-labelledby="rate-{lower}">
  <p class="eyebrow" id="rate-{lower}">{mode} equivalent rate</p>
  {rate_html}
  <p class="rate-note">{_text(explanation)}</p>
  {f'<ul class="rate-counts">{"".join(counts)}</ul>' if counts else ''}
</article>""".strip()


def _source_section(grounding: Mapping[str, Any]) -> str:
    authored = [
        _mapping(item) for item in _sequence(grounding.get("authored_lines"))
    ]
    if not authored:
        return ""
    provenance = []
    source_lines = []
    for line in authored:
        number = line.get("line")
        text = line.get("text")
        if number is not None and text is not None:
            source_lines.append(
                '<span class="source-line">'
                f'<span class="line-number" aria-label="line {_text(number)}">'
                f"{_text(number)}</span>"
                f'<span class="source-code">{_text(text)}</span>'
                "</span>"
            )
        pieces = []
        if number is not None:
            pieces.append(f"line {_text(number)}")
        commit = line.get("commit")
        if commit:
            pieces.append(f"commit {_code(commit)}")
        date = line.get("author_date")
        if date:
            pieces.append(
                f'<time datetime="{_text(date)}">{_text(date)}</time>'
            )
        summary = line.get("commit_summary")
        if summary:
            pieces.append(_text(summary))
        if pieces:
            provenance.append(f"<li>{' · '.join(pieces)}</li>")
    return f"""
<section class="authored-source">
  <p class="step-label"><span>1</span> Student-authored source</p>
  {f'<ul class="provenance">{"".join(provenance)}</ul>' if provenance else ''}
  {f'<pre class="source-block"><code>{chr(10).join(source_lines)}</code></pre>' if source_lines else ''}
</section>""".strip()


def _change_line(mutation: Mapping[str, Any]) -> str:
    original = mutation.get("original_segment")
    changed = mutation.get("mutated_segment")
    if original is None and changed is None:
        return ""
    if original is None:
        return _code(changed)
    if changed is None:
        return _code(original)
    return (
        f'<span class="change-before">{_code(original)}</span>'
        '<span class="change-arrow" aria-label="changed to">→</span>'
        f'<span class="change-after">{_code(changed)}</span>'
    )


def _suite_state(mutant: Mapping[str, Any]) -> str:
    result = _mapping(_mapping(mutant.get("mutant")).get("execution"))
    status = result.get("status")
    count = mutant.get("submitted_suite_tests_passed")
    if status is None and count is None:
        return ""
    if isinstance(count, int) and not isinstance(count, bool):
        outcome = f"{count} passed"
    elif status == "survived":
        outcome = "passed"
    elif status is not None:
        outcome = str(status)
    else:
        return ""
    artifact = mutant.get("submitted_suite_artifact_ref")
    raw_output = result.get("stdout") if count is None else None
    return f"""
<section class="run-state run-state-pass" aria-label="Student test suite passed">
  <span class="state-icon" aria-hidden="true">✓</span>
  <div>
    <p class="state-name">Student's own suite</p>
    <p class="state-result">{_text(outcome)}</p>
    {f'<pre class="suite-output"><code>{_text(raw_output)}</code></pre>' if raw_output else ''}
    {f'<p class="artifact-ref">{_code(artifact)}</p>' if artifact else ''}
  </div>
</section>""".strip()


def _adversarial_section(evidence: Mapping[str, Any]) -> str:
    test = _mapping(evidence.get("adversarial_test"))
    source = test.get("source")
    behavior = test.get("targeted_behavior")
    original = _mapping(evidence.get("original_execution"))
    if source is None and behavior is None:
        return ""
    validated = (
        '<span class="validation-pass">✓ passed on original</span>'
        if original.get("status") == "passed"
        else ""
    )
    return f"""
<section class="adversarial-test">
  <div class="section-heading-row">
    <p class="step-label"><span>4</span> Adversarial test</p>
    {validated}
  </div>
  {f'<p class="targeted-behavior">{_text(behavior)}</p>' if behavior else ''}
  {f'<pre class="test-code"><code>{_text(source)}</code></pre>' if source is not None else ''}
</section>""".strip()


def _failure_section(evidence: Mapping[str, Any]) -> str:
    failure = _mapping(evidence.get("failing_assertion"))
    execution = _mapping(evidence.get("mutant_execution"))
    message = failure.get("message")
    nodeid = failure.get("nodeid")
    detail = failure.get("detail")
    if not failure and not execution:
        return ""
    status = execution.get("status")
    return f"""
<section class="run-state run-state-fail" aria-label="Adversarial test failed on mutant">
  <span class="state-icon" aria-hidden="true">×</span>
  <div class="failure-body">
    <p class="step-label"><span>5</span> Result on changed code</p>
    {f'<p class="state-result">{_text(status)}</p>' if status is not None else ''}
    {f'<p class="failure-node">{_code(nodeid)}</p>' if nodeid else ''}
    {f'<pre class="failure-message"><code>{_text(message)}</code></pre>' if message is not None else ''}
    {f'<details class="trace"><summary>Full assertion trace</summary><pre><code>{_text(detail)}</code></pre></details>' if detail else ''}
  </div>
</section>""".strip()


def _mutation_story(mutant: Mapping[str, Any]) -> str:
    mutation = _mapping(mutant.get("mutation"))
    evidence = _mapping(mutant.get("evidence"))
    change = _change_line(mutation)
    suite = _suite_state(mutant)
    adversarial = _adversarial_section(evidence)
    failure = _failure_section(evidence)
    artifact = evidence.get("triage_artifact_ref")
    return f"""
<article class="mutation-story">
  <section class="change-considered">
    <p class="step-label"><span>2</span> Change considered</p>
    {f'<div class="change-line">{change}</div>' if change else ''}
  </section>
  <div class="state-sequence">
    <div>
      <p class="step-label"><span>3</span> Submitted tests</p>
      {suite}
    </div>
    {adversarial}
    {failure}
  </div>
  {f'<p class="evidence-ref">Execution artifact {_code(artifact)}</p>' if artifact else ''}
</article>""".strip()


def _assessment(place: Mapping[str, Any]) -> str:
    answer = place.get("answer")
    assessment = _mapping(place.get("assessment"))
    if answer is None and not assessment:
        return ""
    parts = ['<section class="answer-section"><h4>Student response</h4>']
    if answer is not None:
        parts.append(f'<blockquote>{_text(answer)}</blockquote>')
    verdict = assessment.get("verdict")
    feedback = assessment.get("feedback")
    if verdict is not None:
        parts.append(f'<p class="verdict">{_text(verdict)}</p>')
    if feedback is not None:
        parts.append(f"<p>{_text(feedback)}</p>")
    parts.append("</section>")
    return "".join(parts)


def _site_card(place: Mapping[str, Any]) -> str:
    grounding = _mapping(place.get("grounding"))
    path = grounding.get("path")
    line = grounding.get("start_line")
    authored = [_mapping(item) for item in _sequence(grounding.get("authored_lines"))]
    first = authored[0] if authored else {}
    commit = first.get("commit")
    date = first.get("author_date")
    question = _mapping(place.get("question")).get("question_text")
    survivor_count = place.get("survivor_count")
    location = ":".join(
        _text(value) for value in (path, line) if value is not None
    )
    metadata = []
    if commit:
        metadata.append(f"commit {_code(str(commit)[:7])}")
    if date:
        metadata.append(f'<time datetime="{_text(date)}">{_text(date)}</time>')
    count_text = ""
    if isinstance(survivor_count, int) and not isinstance(survivor_count, bool):
        noun = "mutation" if survivor_count == 1 else "mutations"
        count_text = (
            f'<span class="survivor-count">{survivor_count} surviving {noun}</span>'
        )
    mutants = [
        _mapping(item) for item in _sequence(place.get("mutants"))
    ]
    stories = "".join(_mutation_story(mutant) for mutant in mutants)
    return f"""
<details class="site-card">
  <summary>
    <span class="summary-copy">
      <span class="site-meta">{_code(location, 'location')} {f'<span>{" · ".join(metadata)}</span>' if metadata else ''}</span>
      {f'<span class="question">{_text(question)}</span>' if question else ''}
    </span>
    {count_text}
    <span class="disclosure-label" aria-hidden="true">view evidence</span>
  </summary>
  <div class="site-evidence">
    {_source_section(grounding)}
    <div class="mutation-list">{stories}</div>
    {_assessment(place)}
  </div>
</details>""".strip()


def _shielded_item(item: Mapping[str, Any]) -> str:
    path = item.get("path")
    line = item.get("line")
    location = ":".join(
        _text(value) for value in (path, line) if value is not None
    )
    change = _change_line(
        {
            "original_segment": item.get("original_segment"),
            "mutated_segment": item.get("mutated_segment"),
        }
    )
    test = _mapping(item.get("strict_test"))
    failure = _mapping(item.get("strict_failure_evidence"))
    reason = item.get("reason")
    return f"""
<details class="shielded-card">
  <summary>
    <span>{_code(location, 'location')}</span>
    <span class="shielded-label">withheld from probes</span>
  </summary>
  <div class="shielded-body">
    {f'<div class="change-line">{change}</div>' if change else ''}
    {f'<p>{_text(reason)}</p>' if reason else ''}
    <p class="shielded-explanation">The unrestricted STRICT witness is retained for audit, but CONTRACT did not justify a student-facing question.</p>
    {f'<p class="step-label">STRICT-mode killing test</p><pre class="test-code"><code>{_text(test.get("source"))}</code></pre>' if test.get('source') is not None else ''}
    {f'<div class="strict-failure"><p>{_code(failure.get("nodeid"))}</p><pre><code>{_text(failure.get("message"))}</code></pre></div>' if failure else ''}
  </div>
</details>""".strip()


def render_report_document(report: Mapping[str, Any]) -> str:
    """Render schema 2.0 as a self-contained semantic HTML document."""
    schema = report.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        return render_error_document(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the supplied data declares {schema!r}."
        )
    student = report.get("student_name") or report.get("student_email")
    commit = report.get("repository_commit")
    status = report.get("submitted_suite_status")
    sites = report.get("unverified_place_count")
    if status == "PASSED" and isinstance(sites, int) and not isinstance(sites, bool):
        noun = "site" if sites == 1 else "sites"
        headline = f"Their suite passed; {sites} {noun} where understanding is unverified."
    elif status is not None and isinstance(sites, int) and not isinstance(sites, bool):
        noun = "site" if sites == 1 else "sites"
        headline = f"Submitted suite: {status}. {sites} unverified {noun}."
    elif status is not None:
        headline = f"Submitted suite: {status}."
    elif isinstance(sites, int) and not isinstance(sites, bool):
        noun = "site" if sites == 1 else "sites"
        headline = f"{sites} {noun} where understanding is unverified."
    else:
        headline = "Comprehension report"
    run_meta = []
    if student:
        run_meta.append(f'<span class="student-name">{_text(student)}</span>')
    if commit:
        run_meta.append(f'<span>repository commit {_code(commit)}</span>')
    rates = "".join(
        card for card in (_rate_card(report, "STRICT"), _rate_card(report, "CONTRACT")) if card
    )
    limitation = report.get("contract_limitation")
    places = [_mapping(item) for item in _sequence(report.get("places"))]
    place_cards = "".join(_site_card(place) for place in places)
    shielded = [
        _mapping(item)
        for item in _sequence(report.get("deliberately_not_asked"))
    ]
    shielded_cards = "".join(_shielded_item(item) for item in shielded)
    formative = report.get("formative_notice")
    title = report.get("title") or "Fencepost comprehension report"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{_text(title)}</title>
  <link rel="stylesheet" href="/assets/ledger.css">
</head>
<body id="top">
  <a class="skip-link" href="#main">Skip to report</a>
  <header class="masthead">
    <div class="shell masthead-inner">{_logo()}<span class="schema-tag">report v{_text(schema)}</span></div>
  </header>
  <main class="shell" id="main">
    {f'<aside class="formative-notice"><strong>Formative, human-reviewed.</strong><span>{_text(formative)}</span></aside>' if formative else ''}
    <section class="run-header" aria-labelledby="run-title">
      {f'<p class="run-meta">{" · ".join(run_meta)}</p>' if run_meta else ''}
      <h1 id="run-title">{_text(headline)}</h1>
    </section>
    {f'<section class="rates" aria-label="Equivalent mutant rates">{rates}</section>' if rates else ''}
    {f'<p class="contract-limitation"><strong>CONTRACT limitation.</strong> {_text(limitation)}</p>' if limitation else ''}
    <section class="places" aria-labelledby="places-heading">
      <div class="section-intro"><p class="eyebrow">Instructor conversation guide</p><h2 id="places-heading">Places to discuss</h2></div>
      {place_cards if place_cards else '<p class="empty-state">No question sites are present in this report.</p>'}
    </section>
    <section class="shielded" aria-labelledby="shielded-heading">
      <div class="section-intro"><p class="eyebrow">Evidence of restraint</p><h2 id="shielded-heading">Deliberately not asked</h2><p>Technical distinctions excluded by the caller contract remain visible for instructor audit.</p></div>
      {shielded_cards if shielded_cards else '<p class="empty-state">No contract-shielded mutations are present in this report.</p>'}
    </section>
  </main>
  <footer class="shell"><span class="wordmark small"><span>fence</span><span class="wordmark-post">post</span></span><span>Execution-grounded. Advisory, never a verdict.</span></footer>
</body>
</html>"""


def render_error_document(message: str) -> str:
    """Render a complete page when an artifact is missing or incompatible."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Fencepost report unavailable</title>
  <link rel="stylesheet" href="/assets/ledger.css">
</head>
<body id="top">
  <header class="masthead"><div class="shell masthead-inner">{_logo()}</div></header>
  <main class="shell error-main" id="main">
    <section class="error-panel" role="alert">
      <p class="eyebrow">Report unavailable</p>
      <h1>This artifact cannot be displayed.</h1>
      <p>{_text(message)}</p>
      <p>No partial report has been rendered.</p>
    </section>
  </main>
</body>
</html>"""


__all__ = [
    "ReportUiError",
    "SUPPORTED_REPORT_SCHEMA",
    "load_report",
    "render_artifact_page",
    "render_error_document",
    "render_report_document",
    "resolve_report_path",
]
