"""Auditable Stage 6 filter for technically valid but poor CS2 questions."""

from __future__ import annotations

import ast
from collections.abc import Mapping


PEDAGOGICAL_WITNESS_RULES: Mapping[str, str] = {
    "implementation_introspection": (
        "A student-facing witness must use the function's public result, not Python "
        "bytecode, dunder metadata, or reflective inspection of its implementation."
    ),
    "implicit_bool_as_number": (
        "A boolean may be used as a numeric argument only when the function signature "
        "explicitly declares or defaults that parameter as boolean. Treating False as "
        "integer zero is otherwise a Python quirk, not evidence of the assignment's "
        "intended numeric contract."
    ),
}


_REFLECTIVE_CALLS = frozenset({"dir", "getattr", "hasattr", "vars"})
_IMPLEMENTATION_ATTRIBUTES = frozenset(
    {
        "__annotations__",
        "__class__",
        "__closure__",
        "__code__",
        "__defaults__",
        "__dict__",
        "__kwdefaults__",
    }
)


def _function_node(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(source)
    node = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if node is None:
        raise ValueError("probe context has no function definition")
    return node


def _explicit_boolean_parameters(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    positional = [*function.args.posonlyargs, *function.args.args]
    defaults: dict[str, ast.expr] = {}
    if function.args.defaults:
        for argument, default in zip(
            positional[-len(function.args.defaults) :],
            function.args.defaults,
        ):
            defaults[argument.arg] = default
    defaults.update(
        {
            argument.arg: default
            for argument, default in zip(
                function.args.kwonlyargs, function.args.kw_defaults
            )
            if default is not None
        }
    )
    explicit = set()
    for argument in [*positional, *function.args.kwonlyargs]:
        annotation = (
            ast.unparse(argument.annotation) if argument.annotation is not None else ""
        )
        default = defaults.get(argument.arg)
        if annotation in {"bool", "builtins.bool"} or (
            isinstance(default, ast.Constant) and isinstance(default.value, bool)
        ):
            explicit.add(argument.arg)
    return explicit


def _target_aliases(tree: ast.AST, target_name: str) -> set[str]:
    aliases = {target_name}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for imported in node.names:
            if imported.name == target_name:
                aliases.add(imported.asname or imported.name)
    return aliases


def _is_target_call(node: ast.Call, target_name: str, aliases: set[str]) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id in aliases
    return isinstance(node.func, ast.Attribute) and node.func.attr == target_name


def _contains_boolean_input(node: ast.AST, boolean_bindings: set[str]) -> bool:
    return any(
        (
            isinstance(item, ast.Constant)
            and isinstance(item.value, bool)
        )
        or (
            isinstance(item, ast.Name)
            and item.id in boolean_bindings
        )
        for item in ast.walk(node)
    )


def _boolean_bindings(tree: ast.AST) -> set[str]:
    """Track the direct literal bindings already allowed by CONTRACT mode."""
    bindings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = (node.target,)
            value = node.value
        else:
            continue
        if not any(
            isinstance(item, ast.Constant) and isinstance(item.value, bool)
            for item in ast.walk(value)
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings.add(target.id)
    return bindings


def validate_pedagogical_witness(
    test_source: str,
    *,
    qualified_function_name: str,
    original_function: str,
) -> tuple[tuple[str, str], ...]:
    """Return rule violations that make a CONTRACT witness a poor CS2 probe."""
    tree = ast.parse(test_source)
    violations: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (
            node.attr in _IMPLEMENTATION_ATTRIBUTES
            or (node.attr.startswith("__") and node.attr.endswith("__"))
        ):
            violations["implementation_introspection"] = (
                f"accesses implementation attribute {node.attr!r}"
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _REFLECTIVE_CALLS
        ):
            violations["implementation_introspection"] = (
                f"calls reflective builtin {node.func.id}()"
            )

    function = _function_node(original_function)
    target_name = qualified_function_name.rsplit(".", 1)[-1]
    aliases = _target_aliases(tree, target_name)
    positional = [*function.args.posonlyargs, *function.args.args]
    explicitly_boolean = _explicit_boolean_parameters(function)
    boolean_bindings = _boolean_bindings(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_target_call(
            node, target_name, aliases
        ):
            continue
        for index, argument in enumerate(node.args):
            if not _contains_boolean_input(argument, boolean_bindings):
                continue
            parameter = positional[index].arg if index < len(positional) else None
            if parameter not in explicitly_boolean:
                violations["implicit_bool_as_number"] = (
                    "passes a boolean literal to a parameter that is not explicitly "
                    "boolean"
                )
        for keyword in node.keywords:
            if (
                keyword.arg not in explicitly_boolean
                and _contains_boolean_input(keyword.value, boolean_bindings)
            ):
                violations["implicit_bool_as_number"] = (
                    "passes a boolean literal to a parameter that is not explicitly "
                    "boolean"
                )

    return tuple(
        (code, f"{PEDAGOGICAL_WITNESS_RULES[code]} Witness: {detail}.")
        for code, detail in violations.items()
    )


__all__ = ["PEDAGOGICAL_WITNESS_RULES", "validate_pedagogical_witness"]
