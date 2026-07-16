"""Read-only report v2 renderer for the local instructor UI."""

from __future__ import annotations

import json
import re
from datetime import datetime
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


def _human_timestamp(value: object) -> str:
    """Format an artifact timestamp for reading without altering its audit value."""
    if not isinstance(value, str):
        return _text(value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return _text(value)
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    return value if isinstance(value, list) else ()


def _code(value: object, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<code{class_attr}>{_text(value)}</code>"


def _data_text(value: object) -> str:
    """Escape prose while marking numeric data for deterministic mono figures."""
    escaped = _text(value)
    return re.sub(
        r"(?<![\w])([0-9]+(?:\.[0-9]+)?%?)(?![\w])",
        r'<span class="data-value">\1</span>',
        escaped,
    )


def _prose_with_code(value: object) -> str:
    """Render backtick-delimited identifiers without accepting arbitrary markup."""
    parts = str(value).split("`")
    return "".join(
        _code(part) if index % 2 else _text(part)
        for index, part in enumerate(parts)
    )


def _icon(name: str, class_name: str = "") -> str:
    classes = "icon" + (f" {class_name}" if class_name else "")
    return (
        f'<svg class="{classes}" aria-hidden="true" focusable="false">'
        f'<use href="#icon-{name}"></use></svg>'
    )


def _icon_sprite() -> str:
    """Definitions for the few disclosures and links that need an icon."""
    return """
<svg class="icon-sprite" aria-hidden="true" focusable="false">
  <symbol id="icon-chevron" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></symbol>
  <symbol id="icon-check" viewBox="0 0 24 24"><path d="m4 12 5 5L20 6"/></symbol>
  <symbol id="icon-cross" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></symbol>
  <symbol id="icon-arrow" viewBox="0 0 24 24"><path d="M4 12h16M14 6l6 6-6 6"/></symbol>
</svg>""".strip()


def _inline_disclosure(label: str) -> str:
    return f'<summary>{_text(label)}{_icon("chevron", "disclosure-icon")}</summary>'


def _logo(*, linked: bool = True) -> str:
    opening = (
        '<a class="brand" href="/" aria-label="Fencepost report home">'
        if linked
        else '<span class="brand" aria-label="Fencepost">'
    )
    closing = "</a>" if linked else "</span>"
    return f"""
{opening}
  <svg class="brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M2 8h20M2 16h20"/>
    <path d="M6 3v18M12 3v18M18 3v18"/>
    <path class="brand-post-offset" d="M12 9v18"/>
  </svg>
  <span class="wordmark"><span>fence</span><span class="wordmark-post">post</span></span>
{closing}""".strip()


def _masthead(
    current: str | None,
    *,
    student_href: str = "/#student-view",
) -> str:
    links = (
        ("report", "/report", "Report"),
        ("student", student_href, "Student"),
        ("method", "/method", "Method"),
    )
    nav_parts = []
    for key, href, label in links:
        current_attr = ' aria-current="page"' if current == key else ""
        nav_parts.append(
            f'<a href="{_text(href)}"{current_attr}>{label}</a>'
        )
    nav = "".join(nav_parts)
    return (
        '<header class="masthead"><div class="shell masthead-inner">'
        f'{_logo()}<nav aria-label="Run navigation">{nav}</nav>'
        "</div></header>"
    )


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
        if "author_matches_committer" in line:
            pieces.append(
                "author and committer match"
                if line.get("author_matches_committer") is True
                else "author and committer differ"
            )
        if "co_authors" in line:
            coauthors = [
                _mapping(item).get("email")
                for item in _sequence(line.get("co_authors"))
                if _mapping(item).get("email")
            ]
            pieces.append(
                "co-author trailer: " + ", ".join(_text(item) for item in coauthors)
                if coauthors
                else "no co-author trailer"
            )
        if "moved_by_blame" in line or "copied_by_blame" in line:
            origin = []
            if line.get("moved_by_blame") is True:
                origin.append("-M move match")
            if line.get("copied_by_blame") is True:
                origin.append("-C copy match")
            pieces.append(
                ", ".join(origin) if origin else "no -M/-C match detected"
            )
            origin_path = line.get("origin_path")
            origin_line = line.get("origin_line")
            if origin and origin_path and origin_line is not None:
                pieces.append(
                    f"blame origin {_code(f'{origin_path}:{origin_line}')}"
                )
        if pieces:
            provenance.append(f"<li>{' · '.join(pieces)}</li>")
    return f"""
<section class="authored-source">
  <p class="step-label"><span>1</span> Source Git attributes to this commit</p>
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
        f'<span class="change-arrow" aria-label="changed to">{_icon("arrow")}</span>'
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
        '<span class="validation-pass">passed on original</span>'
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
  <div class="failure-body">
    <p class="step-label"><span>5</span> Result on changed code</p>
    {f'<p class="state-result">{_text(status)}</p>' if status is not None else ''}
    {f'<p class="failure-node">{_code(nodeid)}</p>' if nodeid else ''}
    {f'<pre class="failure-message"><code>{_text(message)}</code></pre>' if message is not None else ''}
    {f'<details class="trace">{_inline_disclosure("Full assertion trace")}<pre><code>{_text(detail)}</code></pre></details>' if detail else ''}
  </div>
</section>""".strip()


def _mutation_story(mutant: Mapping[str, Any], *, open_story: bool = False) -> str:
    mutation = _mapping(mutant.get("mutation"))
    evidence = _mapping(mutant.get("evidence"))
    change = _change_line(mutation)
    suite = _suite_state(mutant)
    adversarial = _adversarial_section(evidence)
    failure = _failure_section(evidence)
    artifact = evidence.get("triage_artifact_ref")
    unified_diff = mutation.get("unified_diff")
    return f"""
<details class="mutation-story"{' open' if open_story else ''}>
  <summary class="mutation-summary">
    <span class="mutation-summary-copy">
    <p class="step-label"><span>2</span> Change considered</p>
    {f'<div class="change-line">{change}</div>' if change else ''}
    </span>
    {_icon("chevron", "disclosure-icon")}
  </summary>
  <div class="mutation-evidence">
  {f'<details class="unified-diff">{_inline_disclosure("Full source diff")}<pre><code>{_text(unified_diff)}</code></pre></details>' if unified_diff else ''}
  <div class="state-sequence">
    <div>
      <p class="step-label"><span>3</span> Submitted tests</p>
      {suite}
    </div>
    {adversarial}
    {failure}
  </div>
  {f'<p class="evidence-ref">Execution artifact {_code(artifact)}</p>' if artifact else ''}
  </div>
</details>""".strip()


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
                + (f"<details>{_inline_disclosure('Full assertion trace')}<pre><code>{_text(detail)}</code></pre></details>" if detail else "")
                + "</li>"
            )
        parts.append("</ul>")
    parts.append("</section>")
    return "".join(parts)


def _site_card(place: Mapping[str, Any], *, open_site: bool = False) -> str:
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
    stories = "".join(
        _mutation_story(mutant, open_story=open_site and index == 0)
        for index, mutant in enumerate(mutants)
    )
    return f"""
<details class="site-card"{' open' if open_site else ''}>
  <summary>
    <span class="summary-copy">
      <span class="site-meta">{_code(location, 'location')} {f'<span>{" · ".join(metadata)}</span>' if metadata else ''}</span>
      {f'<span class="question">{_text(question)}</span>' if question else ''}
    </span>
    {count_text}
    <span class="disclosure-label" aria-hidden="true">view evidence</span>
    {_icon("chevron", "disclosure-icon")}
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
      {_inline_disclosure("Technical evidence for audit")}
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
      {_inline_disclosure("Technical evidence for audit")}
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
        parts.append(
            f"Their suite executes <strong>{covered} of {total}</strong> mutatable lines "
            "Git attributes to them."
        )
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


def _attribution_context(report: Mapping[str, Any]) -> str:
    summary = _mapping(report.get("attribution_summary"))
    limitation = summary.get("limitation")
    if not summary or not limitation:
        return ""
    facts = []
    excluded = summary.get("coauthored_excluded_line_count")
    if isinstance(excluded, int) and not isinstance(excluded, bool):
        suffix = "line" if excluded == 1 else "lines"
        facts.append(
            f'<li><span class="data-value">{excluded}</span> student-attributed {suffix} '
            "excluded because the commit carries a co-author trailer.</li>"
        )
    mismatches = summary.get("author_committer_mismatch_commit_count")
    if isinstance(mismatches, int) and not isinstance(mismatches, bool):
        suffix = "commit" if mismatches == 1 else "commits"
        facts.append(
            f'<li><span class="data-value">{mismatches}</span> analyzed {suffix} '
            "where author and committer differ.</li>"
        )
    moved = summary.get("moved_line_count")
    copied = summary.get("copied_line_count")
    if isinstance(moved, int) and isinstance(copied, int):
        facts.append(
            f'<li><span class="data-value">{moved}</span> -M move match'
            f'{"es" if moved != 1 else ""}; <span class="data-value">{copied}</span> '
            f'-C copy match{"es" if copied != 1 else ""}.</li>'
        )
    repository_signals = [
        _text(value.replace("_", " "))
        for value in _sequence(summary.get("repository_history_signals"))
        if isinstance(value, str)
    ]
    if repository_signals:
        facts.append(
            "<li>Repository history signals: "
            + ", ".join(repository_signals)
            + ".</li>"
        )
    commit_rows = []
    for item in (_mapping(value) for value in _sequence(summary.get("commits"))):
        commit = item.get("commit")
        if not commit:
            continue
        detail = []
        author = item.get("author_email") or item.get("author_name")
        committer = item.get("committer_email") or item.get("committer_name")
        if author:
            detail.append(f"author {_text(author)}")
        if committer:
            detail.append(f"committer {_text(committer)}")
        coauthors = [
            _mapping(value).get("email")
            for value in _sequence(item.get("co_authors"))
            if _mapping(value).get("email")
        ]
        if coauthors:
            detail.append(
                "co-author trailer " + ", ".join(_text(value) for value in coauthors)
            )
        signals = [
            value.replace("_", " ")
            for value in _sequence(item.get("history_rewrite_signals"))
            if isinstance(value, str)
        ]
        if signals:
            detail.append("signals " + ", ".join(_text(value) for value in signals))
        rendered = f'{_code(str(commit)[:7])}'
        if detail:
            rendered += ": " + "; ".join(detail)
        commit_rows.append(f"<li>{rendered}</li>")
    return f"""<section class="attribution-context" aria-labelledby="attribution-heading">
  <div class="section-intro"><p class="eyebrow">Attribution limits</p><h2 id="attribution-heading">What Git can and cannot tell us</h2></div>
  <p>{_text(limitation)}</p>
  {f'<ul>{"".join(facts)}</ul>' if facts else ''}
  {f'<details class="attribution-commits">{_inline_disclosure("Inspect analyzed commit signals")}<ul>{"".join(commit_rows)}</ul></details>' if commit_rows else ''}
</section>"""


def _number_word(value: int) -> str:
    words = (
        "zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    )
    return words[value] if 0 <= value < len(words) else str(value)


def _instructor_headline(report: Mapping[str, Any]) -> tuple[str, str, str]:
    coverage = _mapping(report.get("authored_line_coverage"))
    sufficient = coverage.get("sufficient_for_assessment")
    covered = coverage.get("covered_authored_mutatable_line_count")
    authored = coverage.get("authored_mutatable_line_count")
    tests = report.get("submitted_suite_tests_passed")
    if isinstance(tests, int) and not isinstance(tests, bool):
        test_phrase = (
            f"{_number_word(tests).capitalize()} "
            f"{'test passes' if tests == 1 else 'tests pass'}."
        )
    else:
        test_phrase = "The submitted suite passes."
    if sufficient is False:
        if isinstance(covered, int) and isinstance(authored, int):
            detail = (
                f"Their suite executes {covered} of {authored} mutatable lines Git "
                "attributes to this student. Fencepost cannot assess code their tests "
                "never run."
            )
        else:
            detail = "Fencepost cannot assess code the submitted tests never run."
        return test_phrase, "Coverage is too low to assess.", detail

    mutation = _mapping(report.get("mutation_summary"))
    total = mutation.get("total_mutants")
    killed = mutation.get("killed_by_submitted_tests")
    survived = mutation.get("survived_submitted_tests")
    fair = report.get("question_mutant_count")
    withheld = report.get("not_questioned_mutant_count")
    conversations = report.get("conversation_count")
    if isinstance(conversations, int) and not isinstance(conversations, bool):
        conversation_phrase = (
            f"{_number_word(conversations).capitalize()} "
            f"{'function says' if conversations == 1 else 'functions say'} nothing."
        )
    else:
        conversation_phrase = "The evidence identifies questions worth discussing."
    detail = []
    if isinstance(total, int) and isinstance(killed, int):
        detail.append(
            f"We made {total} small changes to code Git attributes to this student. "
            f"Their own tests caught {killed}."
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
    return test_phrase, conversation_phrase, " ".join(detail)


def _count(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _outcome_flow(
    *,
    total: object,
    segments: Sequence[tuple[str, str, object]],
    label: str,
    compact: bool = False,
) -> str:
    """Render an artifact-sized part-to-whole without inline styles or scripts."""
    whole = _count(total)
    if whole is None or whole == 0:
        return ""
    present = [
        (class_name, noun, count)
        for class_name, noun, raw_count in segments
        if (count := _count(raw_count)) is not None and count > 0
    ]
    if not present or sum(item[2] for item in present) > whole:
        return ""
    labels = "".join(
        f'<th class="flow-label flow-label-{class_name}" colspan="{count}" scope="col">'
        f'<span class="data-value">{count}</span> {_text(noun)}</th>'
        for class_name, noun, count in present
    )
    bars = "".join(
        f'<td class="flow-segment flow-{class_name}" colspan="{count}">'
        f'<span class="visually-hidden">{count} {_text(noun)}</span></td>'
        for class_name, noun, count in present
    )
    remainder = whole - sum(item[2] for item in present)
    if remainder:
        labels += f'<th class="flow-label flow-label-unclassified" colspan="{remainder}" scope="col"></th>'
        bars += f'<td class="flow-segment flow-unclassified" colspan="{remainder}" aria-hidden="true"></td>'
    compact_class = " outcome-flow-compact" if compact else ""
    return f"""<table class="outcome-flow{compact_class}" aria-label="{_text(label)}">
  <caption>{_text(label)}</caption>
  <thead><tr>{labels}</tr></thead>
  <tbody><tr>{bars}</tr></tbody>
</table>"""


def _headline_flow(report: Mapping[str, Any]) -> str:
    """Render Direction D's compact, directly-labelled run flow."""
    mutation = _mapping(report.get("mutation_summary"))
    total = _count(mutation.get("total_mutants"))
    if total is None or total == 0:
        return ""
    candidates = (
        ("caught", "caught by their tests", _count(mutation.get("killed_by_submitted_tests"))),
        ("discuss", "worth discussing", _count(report.get("question_mutant_count"))),
        ("withheld", "withheld", _count(report.get("not_questioned_mutant_count"))),
    )
    segments = [item for item in candidates if item[2] is not None and item[2] > 0]
    if not segments or sum(item[2] for item in segments) > total:
        return ""
    cells = "".join(
        f'<td class="flow-segment flow-{kind}" colspan="{count}">'
        f'<span class="visually-hidden">{count} {_text(noun)}</span></td>'
        for kind, noun, count in segments
    )
    remainder = total - sum(item[2] for item in segments)
    if remainder:
        cells += (
            f'<td class="flow-segment flow-unclassified" colspan="{remainder}" '
            'aria-hidden="true"></td>'
        )
    legend = []
    for kind, noun, count in segments:
        label = f'<span class="data-value">{count}</span> {_text(noun)}'
        if kind == "withheld":
            label = f'<a href="#withheld">{label} — see why</a>'
        legend.append(
            f'<span><i class="legend-swatch flow-{kind}" aria-hidden="true"></i>{label}</span>'
        )
    return f"""
<div class="headline-flow">
  <table class="flow-bar" aria-label="Outcome of {_text(total)} code changes"><tbody><tr>{cells}</tr></tbody></table>
  <div class="flow-legend">{"".join(legend)}</div>
</div>""".strip()


def _mutation_flow(report: Mapping[str, Any]) -> str:
    mutation = _mapping(report.get("mutation_summary"))
    total = mutation.get("total_mutants")
    caught = mutation.get("killed_by_submitted_tests")
    discuss = report.get("question_mutant_count")
    withheld = report.get("not_questioned_mutant_count")
    flow = _outcome_flow(
        total=total,
        segments=(
            ("caught", "caught", caught),
            ("discuss", "to discuss", discuss),
            ("withheld", "withheld", withheld),
        ),
        label=f"Outcome of {total} code changes" if _count(total) is not None else "Code-change outcomes",
    )
    if not flow:
        return ""
    return f"""<section class="mutation-flow" aria-labelledby="mutation-flow-heading">
  <div class="mutation-flow-heading"><p class="eyebrow">The run at a glance</p><h2 id="mutation-flow-heading">What happened when the code changed</h2></div>
  {flow}
</section>"""


def _function_flows(assessments: Sequence[Mapping[str, Any]]) -> str:
    ordered = sorted(
        assessments,
        key=lambda item: (
            item.get("status") != "CLEAN",
            -(
                (_count(item.get("killed_by_submitted_tests")) or 0)
                / (_count(item.get("total_mutants")) or 1)
            ),
            str(item.get("qualified_function_name") or ""),
        ),
    )
    rows = []
    for item in ordered:
        name = item.get("qualified_function_name")
        total = item.get("total_mutants")
        caught = item.get("killed_by_submitted_tests")
        discuss = item.get("question_mutants")
        withheld = item.get("not_questioned_mutants")
        flow = _outcome_flow(
            total=total,
            segments=(
                ("caught", "caught", caught),
                ("discuss", "to discuss", discuss),
                ("withheld", "withheld", withheld),
            ),
            label=f"{name or 'Unknown function'} change outcomes",
            compact=True,
        )
        if not flow:
            continue
        rows.append(
            '<li class="function-flow-row">'
            f'<div class="function-flow-name">{_code(name or "<unknown>")}'
            f'{f"<span><span class=\"data-value\">{caught}</span> of <span class=\"data-value\">{total}</span> caught</span>" if _count(caught) is not None and _count(total) is not None else ""}'
            f'</div>{flow}</li>'
        )
    if not rows:
        return ""
    return (
        '<div class="function-flow-list" aria-label="Change outcomes by function">'
        '<p class="eyebrow">Change outcomes by function</p>'
        f'<ul>{"".join(rows)}</ul></div>'
    )


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
  {_function_flows(assessments)}
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
        return "".join(
            _site_card(place, open_site=index == 0)
            for index, place in enumerate(places.values())
        )
    rendered = []
    first_site_opened = False
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
        cards = []
        for site_id in _sequence(group.get("site_ids")):
            if site_id not in places:
                continue
            cards.append(
                _site_card(places[site_id], open_site=not first_site_opened)
            )
            first_site_opened = True
        rendered.append(
            f"""<section class="conversation-group">
  <header class="conversation-header">
    <p class="eyebrow">{_text(path) if path else 'Source function'}</p>
    <h3>{_code(name or '<unknown>')}</h3>
    {f'<p class="group-meta">{" · ".join(metadata)}</p>' if metadata else ''}
    {f'<p class="priority-reason"><strong>Why this comes first.</strong> {_text(reason)}</p>' if reason else ''}
  </header>
  {''.join(cards)}
</section>"""
        )
    return "".join(rendered)


def _top_ranked_context(
    report: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    places = [_mapping(item) for item in _sequence(report.get("places"))]
    by_id = {item.get("site_id"): item for item in places if item.get("site_id")}
    for group in (_mapping(item) for item in _sequence(report.get("function_groups"))):
        ranked = [
            by_id[site_id]
            for site_id in _sequence(group.get("site_ids"))
            if site_id in by_id
        ]
        if not ranked:
            continue
        signals = {str(value) for value in _sequence(group.get("ranking_signals"))}
        reason = str(group.get("priority_reason") or "").casefold()
        if "commit_claim" in signals and reason:
            for place in ranked:
                authored = [
                    _mapping(item)
                    for item in _sequence(
                        _mapping(place.get("grounding")).get("authored_lines")
                    )
                ]
                matches_claim = any(
                    (
                        line.get("commit")
                        and str(line["commit"])[:7].casefold() in reason
                    )
                    or (
                        line.get("commit_summary")
                        and str(line["commit_summary"]).casefold() in reason
                    )
                    for line in authored
                )
                if matches_claim:
                    return place, group
        return ranked[0], group
    return (places[0], {}) if places else ({}, {})


def _direction_diff(
    grounding: Mapping[str, Any], mutation: Mapping[str, Any]
) -> str:
    authored = [_mapping(item) for item in _sequence(grounding.get("authored_lines"))]
    if not authored:
        return ""
    line = authored[0]
    before = line.get("text")
    original = mutation.get("original_segment")
    changed = mutation.get("mutated_segment")
    if not all(isinstance(value, str) for value in (before, original, changed)):
        return ""
    offset = before.find(original)
    after = (
        before[:offset] + changed + before[offset + len(original) :]
        if offset >= 0
        else changed
    )
    number = line.get("line")
    number_html = _text(number) if number is not None else ""
    return f"""
<div class="diff" aria-label="Source change">
  <div class="diff-row diff-del"><span class="diff-number">{number_html}</span><span class="diff-sign">−</span><code>{_text(before)}</code></div>
  <div class="diff-row diff-add"><span class="diff-number" aria-hidden="true"></span><span class="diff-sign">+</span><code>{_text(after)}</code></div>
</div>""".strip()


def _duration_label(execution: Mapping[str, Any]) -> str | None:
    duration = execution.get("duration_seconds")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        return f"{duration:.2f}s"
    return None


def _run_row(kind: str, who: object, status: object, metadata: Sequence[str]) -> str:
    meta = (
        f'<span class="run-meta">{_text(" · ".join(metadata))}</span>'
        if metadata
        else ""
    )
    return (
        f'<div class="run run-{kind}"><span class="run-who">{_text(who)}</span>'
        f'<strong class="run-verb">{_text(status)}</strong>{meta}</div>'
    )


def _hero_run_rows(mutant: Mapping[str, Any], evidence: Mapping[str, Any]) -> str:
    submitted = _mapping(_mapping(mutant.get("mutant")).get("execution"))
    changed = _mapping(evidence.get("mutant_execution"))
    test = _mapping(evidence.get("adversarial_test"))
    rows = []
    if submitted.get("status") is not None:
        submitted_meta = []
        tests = mutant.get("submitted_suite_tests_passed")
        if isinstance(tests, int) and not isinstance(tests, bool):
            submitted_meta.append(f"{tests} tests")
        duration = _duration_label(submitted)
        if duration:
            submitted_meta.append(duration)
        rows.append(_run_row("ok", "Their submitted suite", "passed", submitted_meta))
    if changed.get("status") is not None:
        contributor = test.get("model") or test.get("provider")
        who = f"Test written by {contributor}" if contributor else "Adversarial test"
        changed_meta = []
        sandbox = _mapping(evidence.get("sandbox"))
        if evidence.get("sandboxed") is True or sandbox.get("enabled") is True:
            changed_meta.append("sandboxed")
        network = evidence.get("network_access", sandbox.get("network_access"))
        if network in (False, "none", "disabled"):
            changed_meta.append("no network")
        duration = _duration_label(changed)
        if duration:
            changed_meta.append(duration)
        rows.append(_run_row("no", who, changed.get("status"), changed_meta))
    failure = _mapping(evidence.get("failing_assertion"))
    if failure.get("message") is not None:
        rows.append(
            '<blockquote class="execution-quote"><p class="quote-caption">What it printed</p>'
            f'<pre><code>{_text(failure.get("message"))}</code></pre></blockquote>'
        )
    return f'<div class="runs">{"".join(rows)}</div>' if rows else ""


def _hero_evidence(report: Mapping[str, Any]) -> str:
    """Render the top-ranked question and both executed states at equal rank."""
    place, group = _top_ranked_context(report)
    grounding = _mapping(place.get("grounding"))
    mutants = [_mapping(item) for item in _sequence(place.get("mutants"))]
    if not grounding or not mutants:
        return ""
    mutant = mutants[0]
    mutation = _mapping(mutant.get("mutation"))
    evidence = _mapping(mutant.get("evidence"))
    submitted = _mapping(_mapping(mutant.get("mutant")).get("execution"))
    if submitted.get("status") != "survived":
        return ""
    if _mapping(evidence.get("failing_assertion")).get("message") is None:
        return ""
    diff = _direction_diff(grounding, mutation)
    if not diff:
        return ""
    authored = [_mapping(item) for item in _sequence(grounding.get("authored_lines"))]
    first = authored[0] if authored else {}
    provenance = []
    line = grounding.get("start_line")
    if line is not None:
        provenance.append(f"line {_text(line)}")
    commit = first.get("commit")
    if commit:
        provenance.append(_code(str(commit)[:7]))
    date = first.get("author_date")
    if date:
        provenance.append(f'<time datetime="{_text(date)}">{_text(date)}</time>')
    signals = {str(value) for value in _sequence(group.get("ranking_signals"))}
    summary = first.get("commit_summary")
    priority = (
        f'<p class="priority-claim">Their commit says &quot;{_text(summary)}&quot; '
        "— and their tests never checked it.</p>"
        if summary and "commit_claim" in signals
        else ""
    )
    question = _mapping(place.get("question")).get("question_text")
    function_name = group.get("qualified_function_name") or mutant.get(
        "qualified_function_name"
    )
    total_sites = _count(report.get("unverified_place_count"))
    rank = f"1 of {total_sites} · ranked by evidence" if total_sites else "ranked by evidence"
    provenance_html = " · ".join(provenance)
    return f"""<article class="question-card" aria-label="Top-ranked execution evidence">
  <header class="question-card-header"><span class="card-kicker">Start here</span>{f'<code>{_text(function_name)}</code>' if function_name else ''}<span class="card-rank">{_text(rank)}</span></header>
  <div class="question-card-body">
    {f'<h2 class="hero-question">{_prose_with_code(question)}</h2>' if question else ''}
    {f'<p class="hero-provenance">{provenance_html}</p>' if provenance_html else ''}
    {priority}
  </div>
  {diff}
  {_hero_run_rows(mutant, evidence)}
</article>"""


def render_report_document(report: Mapping[str, Any]) -> str:
    """Render report schema 2.0 using the committed Direction D composition."""
    schema = report.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        return render_error_document(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the supplied data declares {schema!r}."
        )
    commit = report.get("repository_commit")
    student = report.get("student_name") or report.get("student_email")
    headline, headline_secondary, summary = _instructor_headline(report)
    run_meta = []
    if student:
        run_meta.append(f'<span class="student-name">{_text(student)}</span>')
    if commit:
        run_meta.append(f'<span>commit {_code(str(commit)[:7])}</span>')
    repository_path = report.get("repository_path")
    if isinstance(repository_path, str) and repository_path:
        run_meta.append(f'<span>{_code(Path(repository_path).name)}</span>')
    started_at = report.get("run_started_at")
    if started_at:
        run_meta.append(
            f'<span><time datetime="{_text(started_at)}">{_human_timestamp(started_at)}</time></span>'
        )
    shielded = [
        _mapping(item) for item in _sequence(report.get("deliberately_not_asked"))
    ]
    pedagogical = [
        _mapping(item) for item in _sequence(report.get("pedagogically_not_asked"))
    ]
    withheld_content = "".join(_shielded_item(item) for item in shielded) + "".join(
        _pedagogically_withheld_item(item) for item in pedagogical
    )
    coverage = _mapping(report.get("authored_line_coverage"))
    empty_conversations = (
        "Question generation is inconclusive because the submitted tests do not "
        "execute enough student-authored code."
        if coverage.get("sufficient_for_assessment") is False
        else "No fair question sites are present in this report."
    )
    title = report.get("title") or "Fencepost comprehension report"
    meta_html = " · ".join(run_meta)
    hero = _hero_evidence(report)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{_text(title)}</title>
  <link rel="stylesheet" href="/assets/direction-d.css">
</head>
<body class="report-page" id="top">
  {_icon_sprite()}
  <a class="skip-link" href="#main">Skip to report</a>
  {_masthead("report")}
  <main class="shell" id="main">
    <section class="report-head" aria-labelledby="run-title">
      <h1 id="run-title">{_data_text(headline)} <em>{_data_text(headline_secondary)}</em></h1>
      {f'<p class="report-summary">{_data_text(summary)}</p>' if summary else ''}
      {f'<p class="report-meta">{meta_html}</p>' if meta_html else ''}
      {_headline_flow(report)}
    </section>
    {hero}
    {f'<section class="withheld-stack" id="withheld" aria-labelledby="withheld-heading"><h2 id="withheld-heading">Deliberately not asked</h2>{withheld_content}</section>' if withheld_content else ''}
    {_function_outcomes(report)}
    {_coverage_section(report)}
    {_attribution_context(report)}
    <section class="places" aria-labelledby="places-heading">
      <div class="section-intro"><p class="eyebrow">Instructor conversation guide</p><h2 id="places-heading">Conversations worth having</h2><p>Related sites are grouped by function and ordered by the strength of their execution and commit evidence.</p></div>
      {_conversation_groups(report) or f'<p class="empty-state">{empty_conversations}</p>'}
    </section>
  </main>
  <footer class="shell"><span class="wordmark small"><span>fence</span><span class="wordmark-post">post</span></span><span>Execution-grounded. Formative, human-reviewed, never a verdict.</span></footer>
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
  <link rel="stylesheet" href="/assets/direction-d.css">
</head>
<body class="method-page" id="top">
  {_icon_sprite()}
  <a class="skip-link" href="#main">Skip to method</a>
  {_masthead("method")}
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


def _command_arg(value: object) -> str:
    rendered = str(value)
    if not rendered or any(character.isspace() for character in rendered):
        return f'"{rendered.replace(chr(34), chr(92) + chr(34))}"'
    return rendered


def render_landing_document(
    report: Mapping[str, Any],
    *,
    artifact_dir: Path,
    probe_url: str,
) -> str:
    """Render the artifact-backed doorway to the instructor and student views."""
    schema = report.get("schema_version")
    if schema != SUPPORTED_REPORT_SCHEMA:
        return render_error_document(
            f"This viewer requires report schema {SUPPORTED_REPORT_SCHEMA}; "
            f"the supplied data declares {schema!r}."
        )
    student = report.get("student_name") or report.get("student_email")
    repository_path = report.get("repository_path")
    repository_name = (
        Path(repository_path).name
        if isinstance(repository_path, str) and repository_path
        else None
    )
    commit = report.get("repository_commit")
    started_at = report.get("run_started_at")
    run_facts = []
    if repository_name:
        run_facts.append(
            f'<div><dt>Repository</dt><dd>{_code(repository_name)}</dd></div>'
        )
    if commit:
        run_facts.append(f'<div><dt>Commit</dt><dd>{_code(commit)}</dd></div>')
    if student:
        run_facts.append(f'<div><dt>Student</dt><dd>{_text(student)}</dd></div>')
    if started_at:
        run_facts.append(
            f'<div><dt>Run started</dt><dd><time datetime="{_text(started_at)}">{_human_timestamp(started_at)}</time></dd></div>'
        )

    artifact_arg = _command_arg(artifact_dir)
    commands = []
    if repository_path and report.get("student_email") and commit:
        commands.append(
            (
                "Produce this analysis",
                "fencepost "
                f"{_command_arg(repository_path)} --student-email "
                f"{_command_arg(report['student_email'])} --output {artifact_arg} "
                f"--commit {_command_arg(commit)}",
            )
        )
    commands.extend(
        (
            ("Open this home and instructor report", f"fencepost serve {artifact_arg}"),
            (
                "Open the evidence-withheld student probe",
                f"fencepost probe {artifact_arg} --out answers.json",
            ),
        )
    )
    command_rows = "".join(
        f'<li><span>{_text(label)}</span><pre><code>{_text(command)}</code></pre></li>'
        for label, command in commands
    )
    title = report.get("title") or "Fencepost comprehension report"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Fencepost run home</title>
  <link rel="stylesheet" href="/assets/direction-d.css">
</head>
<body class="landing-page" id="top">
  {_icon_sprite()}
  <a class="skip-link" href="#main">Skip to run views</a>
  {_masthead(None, student_href=probe_url)}
  <main class="shell landing-main" id="main">
    <section class="landing-hero">
      <p class="eyebrow">One run, two human views</p>
      <h1>Choose where you enter the conversation.</h1>
      <p class="headline-detail">Fencepost keeps the instructor's execution evidence separate until the student has committed each answer.</p>
    </section>
    {f'<dl class="run-facts">{"".join(run_facts)}</dl>' if run_facts else ''}
    <section class="view-choices" aria-labelledby="views-heading">
      <h2 class="visually-hidden" id="views-heading">Run views</h2>
      <article class="view-choice" id="student-view">
        <p class="eyebrow">Instructor view</p>
        <h2>Read the report.</h2>
        <p>Review what the submitted tests protect and decide whether to have a conversation.</p>
        <a class="view-link" href="/report">Open instructor report {_icon("arrow")}</a>
      </article>
      <article class="view-choice">
        <p class="eyebrow">Student view</p>
        <h2>Answer from your code.</h2>
        <p>Answer questions about your own code, then see what your tests never checked.</p>
        <a class="view-link" href="{_text(probe_url)}">Open student probe {_icon("arrow")}</a>
      </article>
    </section>
    <p class="probe-origin-note">The student probe runs on its own local address so unrevealed instructor evidence is not reachable from that view. Start it with the command below.</p>
    <section class="command-list" aria-labelledby="commands-heading">
      <div class="section-intro"><p class="eyebrow">From the terminal</p><h2 id="commands-heading">Produce and open the views.</h2></div>
      <ol>{command_rows}</ol>
    </section>
    <section class="method-door"><div><p class="eyebrow">For reviewers</p><h2>Audit how the evidence was filtered.</h2><p>Both equivalence rates, their raw counts, and the contract limitation remain in the method view.</p></div><a class="view-link" href="/method">Open method {_icon("arrow")}</a></section>
  </main>
  <footer class="shell"><span class="wordmark small"><span>fence</span><span class="wordmark-post">post</span></span><span>{_text(title)} · local and offline</span></footer>
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
  <link rel="stylesheet" href="/assets/direction-d.css">
</head>
<body id="top">
  {_icon_sprite()}
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
    "render_landing_document",
    "render_method_document",
    "render_report_document",
    "resolve_report_path",
]
