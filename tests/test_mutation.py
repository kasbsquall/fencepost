from __future__ import annotations

from fencepost.mutation import enumerate_candidates, generate_mutation


def test_original_anchor_is_independent_of_unparse_line_numbers() -> None:
    source = '''# A comment ast.unparse will remove.
# Another comment.

def grade(score):
    # A source-only comment.
    if score >= 90:
        return "A"
    return "B"
'''
    candidate = next(
        item
        for item in enumerate_candidates(source, "gradebook/analytics.py")
        if item.kind == "compare" and item.source_segment.strip() == "score >= 90"
    )

    generated = generate_mutation(source, candidate)

    assert candidate.anchor.line == 6
    assert generated.generated_anchor.line == 2
    assert "if score > 90:" in generated.source


def test_slice_boundary_is_an_ast_generated_expression() -> None:
    source = '''def top_n(values, n):
    ordered = sorted(values, reverse=True)
    return ordered[:n]
'''
    candidate = next(
        item
        for item in enumerate_candidates(source, "gradebook/analytics.py")
        if item.kind == "slice_boundary" and item.after == "n + 1"
    )

    generated = generate_mutation(source, candidate)

    assert candidate.source_segment == "n"
    assert "return ordered[:n + 1]" in generated.source
