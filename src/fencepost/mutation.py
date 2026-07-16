"""AST-only mutation and source-coordinate preservation.

``ast.unparse`` necessarily rewrites a complete Python file.  This module keeps
the original AST coordinate as the attribution/coverage anchor and reparses the
generated source to obtain a separate generated coordinate for execution UI.
"""

from __future__ import annotations

import ast
import copy
import hashlib
from dataclasses import dataclass
from typing import Iterator

from .models import MutationCandidate, PathStep, SourceSpan


class MutationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedMutation:
    source: str
    generated_anchor: SourceSpan


def _walk_paths(
    node: ast.AST, path: tuple[PathStep, ...] = ()
) -> Iterator[tuple[ast.AST, tuple[PathStep, ...]]]:
    yield node, path
    for field, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            yield from _walk_paths(value, path + (PathStep(field),))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, ast.AST):
                    yield from _walk_paths(item, path + (PathStep(field, index),))


def _resolve(root: ast.AST, path: tuple[PathStep, ...]) -> ast.AST:
    current: ast.AST = root
    for step in path:
        value = getattr(current, step.field)
        current = value if step.index is None else value[step.index]
        if not isinstance(current, ast.AST):
            raise MutationError(f"AST path reaches a non-node at {step}")
    return current


def _replace(root: ast.AST, path: tuple[PathStep, ...], replacement: ast.AST) -> None:
    if not path:
        raise MutationError("replacing the module root is not supported")
    parent = _resolve(root, path[:-1])
    final = path[-1]
    if final.index is None:
        setattr(parent, final.field, replacement)
    else:
        getattr(parent, final.field)[final.index] = replacement


def _span(node: ast.AST) -> SourceSpan:
    try:
        return SourceSpan(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
    except AttributeError as exc:
        raise MutationError(f"node has no source location: {type(node).__name__}") from exc


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    result: set[int] = set()
    owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, owners) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                result.add(id(first.value))
    return result


def _candidate_id(
    path: str,
    ast_path: tuple[PathStep, ...],
    kind: str,
    parameters: tuple[tuple[str, str], ...],
) -> str:
    structural_path = "/".join(
        f"{step.field}[{step.index}]" if step.index is not None else step.field
        for step in ast_path
    )
    payload = repr((path, structural_path, kind, parameters)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _make_candidate(
    *,
    source: str,
    path: str,
    node: ast.AST,
    ast_path: tuple[PathStep, ...],
    kind: str,
    before: str,
    after: str,
    parameters: dict[str, str] | None = None,
) -> MutationCandidate:
    packed_parameters = tuple(sorted((parameters or {}).items()))
    segment = ast.get_source_segment(source, node) or ast.unparse(node)
    return MutationCandidate(
        id=_candidate_id(path, ast_path, kind, packed_parameters),
        path=path,
        anchor=_span(node),
        ast_path=ast_path,
        kind=kind,
        before=before,
        after=after,
        source_segment=segment,
        parameters=packed_parameters,
    )


_COMPARE_REPLACEMENTS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}


_ARITHMETIC_REPLACEMENTS: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
    ast.Div: ast.FloorDiv,
}


def enumerate_candidates(source: str, path: str) -> tuple[MutationCandidate, ...]:
    """Enumerate single-node mutations without considering blame or coverage."""
    tree = ast.parse(source, filename=path)
    docstrings = _docstring_constant_ids(tree)
    candidates: list[MutationCandidate] = []

    for node, node_path in _walk_paths(tree):
        if isinstance(node, ast.Compare):
            for index, operator in enumerate(node.ops):
                replacement = _COMPARE_REPLACEMENTS.get(type(operator))
                if replacement is not None:
                    candidates.append(
                        _make_candidate(
                            source=source,
                            path=path,
                            node=node,
                            ast_path=node_path,
                            kind="compare",
                            before=type(operator).__name__,
                            after=replacement.__name__,
                            parameters={"op_index": str(index)},
                        )
                    )

        if isinstance(node, (ast.BinOp, ast.AugAssign)):
            replacement = _ARITHMETIC_REPLACEMENTS.get(type(node.op))
            if replacement is not None:
                candidates.append(
                    _make_candidate(
                        source=source,
                        path=path,
                        node=node,
                        ast_path=node_path,
                        kind="arithmetic",
                        before=type(node.op).__name__,
                        after=replacement.__name__,
                    )
                )

        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            replacement = ast.Or if isinstance(node.op, ast.And) else ast.And
            candidates.append(
                _make_candidate(
                    source=source,
                    path=path,
                    node=node,
                    ast_path=node_path,
                    kind="boolean",
                    before=type(node.op).__name__,
                    after=replacement.__name__,
                )
            )

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            candidates.append(
                _make_candidate(
                    source=source,
                    path=path,
                    node=node,
                    ast_path=node_path,
                    kind="drop_not",
                    before="Not",
                    after=type(node.operand).__name__,
                )
            )

        if isinstance(node, ast.Return) and node.value is not None:
            candidates.append(
                _make_candidate(
                    source=source,
                    path=path,
                    node=node,
                    ast_path=node_path,
                    kind="return_none",
                    before=ast.unparse(node.value),
                    after="None",
                )
            )

        if isinstance(node, ast.Constant) and id(node) not in docstrings:
            if isinstance(node.value, bool):
                candidates.append(
                    _make_candidate(
                        source=source,
                        path=path,
                        node=node,
                        ast_path=node_path,
                        kind="boolean_constant",
                        before=repr(node.value),
                        after=repr(not node.value),
                    )
                )
            elif type(node.value) in (int, float):
                for direction in (-1, 1):
                    candidates.append(
                        _make_candidate(
                            source=source,
                            path=path,
                            node=node,
                            ast_path=node_path,
                            kind="numeric_boundary",
                            before=repr(node.value),
                            after=repr(node.value + direction),
                            parameters={"direction": str(direction)},
                        )
                    )
            elif isinstance(node.value, str):
                replacement = "<fencepost-mutant>" if node.value == "" else ""
                candidates.append(
                    _make_candidate(
                        source=source,
                        path=path,
                        node=node,
                        ast_path=node_path,
                        kind="string_constant",
                        before=repr(node.value),
                        after=repr(replacement),
                    )
                )

        if isinstance(node, ast.Slice):
            for field in ("lower", "upper", "step"):
                bound = getattr(node, field)
                if not isinstance(bound, ast.AST):
                    continue
                bound_path = node_path + (PathStep(field),)
                for direction in (-1, 1):
                    sign = "-" if direction < 0 else "+"
                    candidates.append(
                        _make_candidate(
                            source=source,
                            path=path,
                            node=bound,
                            ast_path=bound_path,
                            kind="slice_boundary",
                            before=ast.unparse(bound),
                            after=f"{ast.unparse(bound)} {sign} 1",
                            parameters={"direction": str(direction), "slice_field": field},
                        )
                    )

    return tuple(candidates)


def generate_mutation(source: str, candidate: MutationCandidate) -> GeneratedMutation:
    """Apply exactly one candidate and derive its generated-source location."""
    tree = ast.parse(source, filename=candidate.path)
    target = _resolve(tree, candidate.ast_path)
    parameters = candidate.parameter_map

    if candidate.kind == "compare":
        if not isinstance(target, ast.Compare):
            raise MutationError("compare candidate no longer identifies a Compare node")
        index = int(parameters["op_index"])
        target.ops[index] = getattr(ast, candidate.after)()
    elif candidate.kind == "arithmetic":
        if not isinstance(target, (ast.BinOp, ast.AugAssign)):
            raise MutationError("arithmetic candidate no longer identifies an arithmetic node")
        target.op = getattr(ast, candidate.after)()
    elif candidate.kind == "boolean":
        if not isinstance(target, ast.BoolOp):
            raise MutationError("boolean candidate no longer identifies a BoolOp node")
        target.op = getattr(ast, candidate.after)()
    elif candidate.kind == "drop_not":
        if not isinstance(target, ast.UnaryOp) or not isinstance(target.op, ast.Not):
            raise MutationError("drop_not candidate no longer identifies a not expression")
        _replace(tree, candidate.ast_path, copy.deepcopy(target.operand))
    elif candidate.kind == "return_none":
        if not isinstance(target, ast.Return):
            raise MutationError("return candidate no longer identifies a Return node")
        target.value = ast.Constant(value=None)
    elif candidate.kind == "boolean_constant":
        if not isinstance(target, ast.Constant) or not isinstance(target.value, bool):
            raise MutationError("boolean constant candidate no longer identifies a boolean")
        target.value = not target.value
    elif candidate.kind == "numeric_boundary":
        if not isinstance(target, ast.Constant) or type(target.value) not in (int, float):
            raise MutationError("numeric boundary candidate no longer identifies a number")
        target.value = target.value + int(parameters["direction"])
    elif candidate.kind == "string_constant":
        if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
            raise MutationError("string constant candidate no longer identifies a string")
        target.value = "<fencepost-mutant>" if target.value == "" else ""
    elif candidate.kind == "slice_boundary":
        direction = int(parameters["direction"])
        _replace(
            tree,
            candidate.ast_path,
            ast.BinOp(
                left=copy.deepcopy(target),
                op=ast.Add() if direction > 0 else ast.Sub(),
                right=ast.Constant(value=1),
            ),
        )
    else:
        raise MutationError(f"unknown mutation kind: {candidate.kind}")

    ast.fix_missing_locations(tree)
    rendered = ast.unparse(tree) + "\n"
    reparsed = ast.parse(rendered, filename=candidate.path)
    generated_target = _resolve(reparsed, candidate.ast_path)
    return GeneratedMutation(source=rendered, generated_anchor=_span(generated_target))
