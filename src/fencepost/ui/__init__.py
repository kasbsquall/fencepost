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
<a class="brand" href="/" aria-label="Fencepost report home">
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
        label = f"Their {count} tests"
    elif status == "survived":
        label = "Their submitted tests"
    elif status is not None:
        label = "Their submitted tests"
    else:
        return ""
    outcome = "passed" if status == "survived" else str(status)
    artifact = mutant.get("submitted_suite_artifact_ref")
    return f"""
<section class="run-state run-state-pass" aria-label="Student test suite passed">
  <span class="state-icon" aria-hidden="true">✓</span>
  <div>
    <p class="state-result"><span>{_text(label)}</span> <strong>— {_text(outcome)}</strong></p>
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
    unified_diff = mutation.get("unified_diff")
    return f"""
<article class="mutation-story">
  <section class="change-considered">
    <p class="step-label"><span>2</span> Change considered</p>
    {f'<div class="change-line">{change}</div>' if change else ''}
    {f'<details class="unified-diff"><summary>Full source diff</summary><pre><code>{_text(unified_diff)}</code></pre></details>' if unified_diff else ''}
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
    explanation = assessment.get("evidence_explanation")
    citations = [_mapping(item) for item in _sequence(assessment.get("citations"))]
    if verdict is not None:
        parts.append(f'<p class="verdict">{_text(verdict)}</p>')
    if feedback is not None:
        parts.append(f"<p>{_text(feedback)}</p>")
    if explanation is not None:
        parts.append(f'<p class="evidence-explanation">{_text(explanation)}</p>')
    if citations:
        parts.append('<h5>Execution evidence used for this assessment</h5><ul class="citations">')
        for citation in citations:
            nodeid = citation.get("nodeid")
            message = citation.get("message")
            detail = citation.get("detail")
            artifact = citation.get("artifact_ref")
            parts.append(
                "<li>"
                + (f"<p>{_code(nodeid)}</p>" if nodeid else "")
                + (f"<pre><code>{_text(message)}</code></pre>" if message else "")
                + (f"<p class=\"artifact-ref\">{_code(artifact)}</p>" if artifact else "")
                + (f"<details><summary>Full assertion trace</summary><pre><code>{_text(detail)}</code></pre></details>" if detail else "")
                + "</li>"
            )
        parts.append("</ul>")
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
    plain_reason = item.get("plain_language_reason") or reason
    return f"""
<article class="shielded-card">
  <div class="shielded-body">
    <p class="shielded-label">withheld from probes · {_code(location, 'location')}</p>
    {f'<p class="shielded-lead">{_text(plain_reason)}</p>' if plain_reason else ''}
    {f'<div class="change-line">{change}</div>' if change else ''}
    <details class="technical-evidence">
      <summary>Technical evidence for audit</summary>
      {f'<p>{_text(reason)}</p>' if reason and reason != plain_reason else ''}
      {f'<p class="step-label">STRICT-mode killing test</p><pre class="test-code"><code>{_text(test.get("source"))}</code></pre>' if test.get('source') is not None else ''}
      {f'<div class="strict-failure"><p>{_code(failure.get("nodeid"))}</p><pre><code>{_text(failure.get("message"))}</code></pre></div>' if failure else ''}
    </details>
  </div>
</article>""".strip()


def _pedagogically_withheld_item(item: Mapping[str, Any]) -> str:
    mutant = _mapping(item.get("mutant"))
    mutation = _mapping(mutant.get("mutation"))
    evidence = _mapping(mutant.get("evidence"))
    candidate = _mapping(_mapping(mutant.get("mutant")).get("candidate"))
    path = candidate.get("path")
    anchor = _mapping(candidate.get("anchor"))
    line = anchor.get("line")
    location = ":".join(_text(value) for value in (path, line) if value is not None)
    codes = set(str(code) for code in _sequence(item.get("reason_codes")))
    if "implicit_bool_as_number" in codes:
        lead = (
            "We found a difference only by treating a boolean as a number even "
            "though the function does not declare a boolean input. That is not a "
            "fair CS2 question, so we dropped it."
        )
    elif "implementation_introspection" in codes:
        lead = (
            "We found a difference only by inspecting Python implementation details, "
            "not the function's ordinary result. That is not a fair CS2 question, so "
            "we dropped it."
        )
    else:
        lead = (
            "Execution found a technical difference, but its witness would make a "
            "poor CS2 question. We dropped it from the conversation guide."
        )
    change = _change_line(mutation)
    test = _mapping(evidence.get("adversarial_test"))
    failure = _mapping(evidence.get("failing_assertion"))
    reasons = _sequence(item.get("reasons"))
    return f"""
<article class="shielded-card">
  <div class="shielded-body">
    <p class="shielded-label">withheld from probes {f'· {_code(location, "location")}' if location else ''}</p>
    <p class="shielded-lead">{_text(lead)}</p>
    {f'<div class="change-line">{change}</div>' if change else ''}
    <details class="technical-evidence">
      <summary>Technical evidence for audit</summary>
      {''.join(f'<p>{_text(reason)}</p>' for reason in reasons)}
      {f'<pre class="test-code"><code>{_text(test.get("source"))}</code></pre>' if test.get('source') is not None else ''}
      {f'<div class="strict-failure"><p>{_code(failure.get("nodeid"))}</p><pre><code>{_text(failure.get("message"))}</code></pre></div>' if failure else ''}
    </details>
  </div>
</article>""".strip()


def _coverage_section(report: Mapping[str, Any]) -> str:
    coverage = _mapping(report.get("authored_line_coverage"))
    total = coverage.get("authored_mutatable_line_count")
    covered = coverage.get("covered_authored_mutatable_line_count")
    rate = coverage.get("rate")
    minimum = coverage.get("minimum_rate")
    sufficient = coverage.get("sufficient_for_assessment")
    if not coverage:
        return ""
    parts = []
    if isinstance(covered, int) and isinstance(total, int):
        parts.append(f"Their suite executes <strong>{covered} of {total}</strong> mutatable lines they authored.")
    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
        parts.append(f"Coverage: <strong>{rate:.0%}</strong>.")
    if sufficient is False:
        parts.append(
            "Fencepost cannot assess understanding of code their tests never run."
        )
        if isinstance(minimum, (int, float)) and not isinstance(minimum, bool):
            parts.append(
                f"Assessment requires at least {minimum:.0%} authored-line coverage."
            )
    class_name = "coverage-context coverage-low" if sufficient is False else "coverage-context"
    return f'<aside class="{class_name}"><p class="eyebrow">Authored-line coverage</p><p>{" ".join(parts)}</p></aside>'


def _instructor_headline(report: Mapping[str, Any]) -> tuple[str, str]:
    student = report.get("student_name") or report.get("student_email") or "The student"
    coverage = _mapping(report.get("authored_line_coverage"))
    sufficient = coverage.get("sufficient_for_assessment")
    covered = coverage.get("covered_authored_mutatable_line_count")
    authored = coverage.get("authored_mutatable_line_count")
    tests = report.get("submitted_suite_tests_passed")
    test_phrase = (
        f"{tests} tests pass"
        if isinstance(tests, int) and not isinstance(tests, bool)
        else "submitted tests pass"
    )
    if sufficient is False:
        if isinstance(covered, int) and isinstance(authored, int):
            headline = (
                f"{student}'s {test_phrase}, but they execute {covered} of {authored} "
                "mutatable lines they wrote."
            )
        else:
            headline = f"{student}'s {test_phrase}, but coverage is too low to assess."
        return (
            headline,
            "Fencepost cannot assess understanding of code their tests never run.",
        )

    mutation = _mapping(report.get("mutation_summary"))
    total = mutation.get("total_mutants")
    killed = mutation.get("killed_by_submitted_tests")
    survived = mutation.get("survived_submitted_tests")
    fair = report.get("question_mutant_count")
    withheld = report.get("not_questioned_mutant_count")
    headline = f"{student}'s {test_phrase}."
    detail = []
    if isinstance(total, int) and isinstance(killed, int):
        detail.append(
            f"We made {total} small changes to code they wrote; their tests caught {killed}."
        )
    if isinstance(survived, int) and isinstance(fair, int):
        detail.append(
            f"Of the {survived} changes they missed, {fair} are fair to discuss."
        )
    if isinstance(withheld, int) and withheld:
        noun = "change" if withheld == 1 else "changes"
        detail.append(
            f"We withheld {withheld} {noun} that would not make a fair question."
        )
    return headline, " ".join(detail)


def _function_outcomes(report: Mapping[str, Any]) -> str:
    assessments = [
        _mapping(item) for item in _sequence(report.get("function_assessments"))
    ]
    if not assessments:
        return ""
    clean = [item for item in assessments if item.get("status") == "CLEAN"]
    gaps = [item for item in assessments if item.get("status") == "GAPS_FOUND"]
    other = [item for item in assessments if item not in clean and item not in gaps]

    def items(values, *, positive: bool) -> str:
        rendered = []
        for item in values:
            name = item.get("qualified_function_name")
            killed = item.get("killed_by_submitted_tests")
            total = item.get("total_mutants")
            gaps_count = item.get("contract_real_gap_mutants")
            question_sites = item.get("question_site_count")
            detail = ""
            if positive and isinstance(killed, int) and isinstance(total, int):
                detail = f"all {killed} of {total} changes caught"
            elif isinstance(gaps_count, int) and isinstance(total, int):
                detail = f"{gaps_count} verified behavior changes among {total} changes"
                if isinstance(question_sites, int):
                    detail += (
                        f"; {question_sites} fair question "
                        f"{'site' if question_sites == 1 else 'sites'}"
                    )
            rendered.append(
                f'<li><span>{_code(name or "<unknown>")}</span>{f"<small>{_text(detail)}</small>" if detail else ""}</li>'
            )
        return "".join(rendered)

    columns = []
    if clean:
        columns.append(
            '<div class="function-column function-clean"><h3>Protected by their tests</h3>'
            f'<ul>{items(clean, positive=True)}</ul></div>'
        )
    if gaps:
        columns.append(
            '<div class="function-column"><h3>Worth discussing</h3>'
            f'<ul>{items(gaps, positive=False)}</ul></div>'
        )
    if other:
        columns.append(
            '<div class="function-column"><h3>No fair conclusion yet</h3>'
            f'<ul>{items(other, positive=False)}</ul></div>'
        )
    return f"""
<section class="function-outcomes" aria-labelledby="outcomes-heading">
  <div class="section-intro"><p class="eyebrow">Both sides of the evidence</p><h2 id="outcomes-heading">What their tests already protect</h2></div>
  <div class="function-columns">{''.join(columns)}</div>
</section>""".strip()


def _conversation_groups(report: Mapping[str, Any]) -> str:
    places = {
        item.get("site_id"): item
        for item in (_mapping(value) for value in _sequence(report.get("places")))
        if item.get("site_id")
    }
    groups = [
        _mapping(item) for item in _sequence(report.get("function_groups"))
    ]
    if not groups and places:
        return "".join(_site_card(place) for place in places.values())
    rendered = []
    for group in groups:
        name = group.get("qualified_function_name")
        path = group.get("path")
        site_count = group.get("site_count")
        mutant_count = group.get("mutant_count")
        reason = group.get("priority_reason")
        metadata = []
        if isinstance(site_count, int):
            metadata.append(f"{site_count} source {'site' if site_count == 1 else 'sites'}")
        if isinstance(mutant_count, int):
            metadata.append(f"{mutant_count} surviving {'change' if mutant_count == 1 else 'changes'}")
        cards = "".join(
            _site_card(places[site_id])
            for site_id in _sequence(group.get("site_ids"))
            if site_id in places
        )
        rendered.append(
            f"""<section class="conversation-group">
  <header class="conversation-header">
    <p class="eyebrow">{_text(path) if path else 'Source function'}</p>
    <h3>{_code(name or '<unknown>')}</h3>
    {f'<p class="group-meta">{" · ".join(metadata)}</p>' if metadata else ''}
    {f'<p class="priority-reason"><strong>Why this comes first.</strong> {_text(reason)}</p>' if reason else ''}
  </header>
  {cards}
</section>"""
        )
    return "".join(rendered)


def render_report_document(report: Mapping[str, Any]) -> str:
    """Render schema 2.0 as a self-contained semantic HTML document."""
    schema = report.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        return render_error_document(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the supplied data declares {schema!r}."
        )
    commit = report.get("repository_commit")
    student = report.get("student_name") or report.get("student_email")
    headline, summary = _instructor_headline(report)
    run_meta = []
    if student:
        run_meta.append(f'<span class="student-name">{_text(student)}</span>')
    if commit:
        run_meta.append(f'<span>repository commit {_code(commit)}</span>')
    shielded = [
        _mapping(item)
        for item in _sequence(report.get("deliberately_not_asked"))
    ]
    shielded_cards = "".join(_shielded_item(item) for item in shielded)
    pedagogical = [
        _mapping(item)
        for item in _sequence(report.get("pedagogically_not_asked"))
    ]
    pedagogical_cards = "".join(
        _pedagogically_withheld_item(item) for item in pedagogical
    )
    coverage = _mapping(report.get("authored_line_coverage"))
    if coverage.get("sufficient_for_assessment") is False:
        empty_conversations = (
            "Question generation is inconclusive because the submitted tests do "
            "not execute enough student-authored code."
        )
    else:
        empty_conversations = "No fair question sites are present in this report."
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
    <div class="shell masthead-inner">{_logo()}<nav aria-label="Report navigation"><a href="/method">Method</a></nav></div>
  </header>
  <main class="shell" id="main">
    {f'<aside class="formative-notice"><strong>Formative, human-reviewed.</strong><span>{_text(formative)}</span></aside>' if formative else ''}
    <section class="run-header" aria-labelledby="run-title">
      {f'<p class="run-meta">{" · ".join(run_meta)}</p>' if run_meta else ''}
      <h1 id="run-title">{_text(headline)}</h1>
      {f'<p class="headline-detail">{_text(summary)}</p>' if summary else ''}
    </section>
    {_coverage_section(report)}
    {_function_outcomes(report)}
    <section class="shielded" aria-labelledby="shielded-heading">
      <div class="section-intro"><p class="eyebrow">Evidence of restraint</p><h2 id="shielded-heading">Deliberately not asked</h2><p>We keep technical distinctions visible for audit without turning them into unfair student questions.</p></div>
      {shielded_cards + pedagogical_cards if shielded_cards or pedagogical_cards else '<p class="empty-state">No changes were withheld from student questions in this report.</p>'}
    </section>
    <section class="places" aria-labelledby="places-heading">
      <div class="section-intro"><p class="eyebrow">Instructor conversation guide</p><h2 id="places-heading">Conversations worth having</h2><p>Related sites are grouped by function and ordered by the strength of their execution and commit evidence.</p></div>
      {_conversation_groups(report) or f'<p class="empty-state">{empty_conversations}</p>'}
    </section>
  </main>
  <footer class="shell"><span class="wordmark small"><span>fence</span><span class="wordmark-post">post</span></span><span>Execution-grounded. Advisory, never a verdict.</span></footer>
</body>
</html>"""


def render_method_document(report: Mapping[str, Any]) -> str:
    """Render the technical rates and contract tradeoffs away from the student view."""
    schema = report.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        return render_error_document(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the supplied data declares {schema!r}."
        )
    rates = "".join(
        card
        for card in (_rate_card(report, "STRICT"), _rate_card(report, "CONTRACT"))
        if card
    )
    limitation = report.get("contract_limitation")
    coverage = _mapping(report.get("authored_line_coverage"))
    minimum = coverage.get("minimum_rate")
    title = report.get("title") or "Fencepost comprehension report"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Method · {_text(title)}</title>
  <link rel="stylesheet" href="/assets/ledger.css">
</head>
<body id="top">
  <a class="skip-link" href="#main">Skip to method</a>
  <header class="masthead"><div class="shell masthead-inner">{_logo()}<nav aria-label="Report navigation"><a href="/">Instructor report</a></nav></div></header>
  <main class="shell method-main" id="main">
    <section class="run-header"><p class="eyebrow">Technical appendix</p><h1>How Fencepost decides what is fair to ask.</h1><p class="headline-detail">These rates describe mutation triage, not the student. They are kept here so an instructor or reviewer can audit the method without mistaking them for a score.</p></section>
    {f'<section class="rates" aria-label="Equivalent mutant rates">{rates}</section>' if rates else ''}
    {f'<p class="contract-limitation"><strong>CONTRACT limitation.</strong> {_text(limitation)}</p>' if limitation else ''}
    <section class="method-copy"><h2>Coverage precondition</h2><p>Fencepost measures the unique student-authored lines that contain mutation sites and were executed by the submitted suite. {f"At least {minimum:.0%} must be covered before the report presents zero findings as assessable." if isinstance(minimum, (int, float)) and not isinstance(minimum, bool) else "A run below the configured threshold is marked as not assessable."}</p></section>
    <section class="method-copy"><h2>Two lenses, both retained</h2><p><strong>STRICT</strong> permits every distinction Python can express. <strong>CONTRACT</strong> admits only plain-caller evidence and drives student questions. Technical or pedagogically inappropriate witnesses are retained under “Deliberately not asked,” never silently deleted.</p></section>
    <section class="method-copy"><h2>Execution trail</h2><p>Fencepost combines AST mutation, Git-blame attribution, Docker sandbox execution, and dual-mode equivalence triage. GPT-5.6 generates adversarial tests inside the product; it phrases tests and questions, while executed results remain the ground truth.</p></section>
  </main>
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
    "render_method_document",
    "render_report_document",
    "resolve_report_path",
]
