"""Auditable static policy for pedagogically relevant adversarial tests.

STRICT mode deliberately applies none of these restrictions. CONTRACT mode is
not a claim about all Python behavior; it is an explicit caller-domain policy
used to decide which execution-grounded gaps are suitable probe targets.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .models import ContractViolation, TriageMode, json_value


@dataclass(frozen=True)
class ContractRules:
    allowed_imports: tuple[str, ...]
    allowed_function_definitions: str
    forbidden_definition_nodes: tuple[str, ...]
    forbidden_comparison_operators: tuple[str, ...]
    forbidden_inspection_calls: tuple[str, ...]
    forbidden_inspection_attributes: tuple[str, ...]
    allowed_input_values: tuple[str, ...]
    target_arguments: str


CONTRACT_RULES = ContractRules(
    allowed_imports=("pytest", "<module-under-test>"),
    allowed_function_definitions="top-level synchronous test_* functions only",
    forbidden_definition_nodes=("ClassDef", "AsyncFunctionDef", "Lambda"),
    forbidden_comparison_operators=("Is", "IsNot"),
    forbidden_inspection_calls=("isinstance", "type", "id"),
    forbidden_inspection_attributes=("__class__",),
    allowed_input_values=(
        "int",
        "float",
        "str",
        "bool",
        "None",
        "list",
        "tuple",
        "dict",
        "set",
    ),
    target_arguments=(
        "plain literals, containers of plain literals, unary signed numeric "
        "literals, or local names bound directly to those values"
    ),
)

CONTRACT_LIMITATION = (
    "CONTRACT mode can hide a genuine behavioral gap when the only witness uses "
    "type, identity, a custom object, or another excluded input. This deliberate "
    "false-negative risk means its rate is execution-grounded only under the "
    "stated caller contract, not universal truth."
)


@dataclass(frozen=True)
class ContractValidation:
    mode: TriageMode
    accepted: bool
    violations: tuple[ContractViolation, ...]


def contract_rules_payload(module_path: str) -> dict[str, object]:
    payload = json_value(CONTRACT_RULES)
    payload["resolved_allowed_imports"] = ["pytest", module_path]
    payload["limitation"] = CONTRACT_LIMITATION
    return payload


def _dotted_name(node: ast.AST) -> str | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _plain_value(node: ast.AST, plain_names: set[str]) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is None or type(node.value) in (int, float, str, bool)
    if isinstance(node, ast.Name):
        return node.id in plain_names
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return (
            isinstance(node.operand, ast.Constant)
            and type(node.operand.value) in (int, float)
        )
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_plain_value(item, plain_names) for item in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            key is not None
            and _plain_value(key, plain_names)
            and _plain_value(value, plain_names)
            for key, value in zip(node.keys, node.values)
        )
    return False


def _assigned_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        result: set[str] = set()
        for item in target.elts:
            result.update(_assigned_names(item))
        return result
    return set()


def _plain_bindings(function: ast.FunctionDef) -> set[str]:
    """Conservatively identify locals bound directly to allowed literal values."""
    plain: set[str] = set()
    tainted: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            names = set().union(*(_assigned_names(target) for target in node.targets))
            if _plain_value(node.value, set()) and not names.intersection(tainted):
                plain.update(names)
            else:
                plain.difference_update(names)
                tainted.update(names)
        elif isinstance(node, ast.AnnAssign):
            names = _assigned_names(node.target)
            if (
                node.value is not None
                and _plain_value(node.value, set())
                and not names.intersection(tainted)
            ):
                plain.update(names)
            else:
                plain.difference_update(names)
                tainted.update(names)
        elif isinstance(node, ast.AugAssign):
            names = _assigned_names(node.target)
            plain.difference_update(names)
            tainted.update(names)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            names = _assigned_names(node.target)
            plain.difference_update(names)
            tainted.update(names)
        elif isinstance(node, ast.NamedExpr):
            names = _assigned_names(node.target)
            plain.difference_update(names)
            tainted.update(names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            receiver = _dotted_name(node.func.value)
            if receiver is not None:
                root = receiver.split(".", 1)[0]
                if root in plain:
                    plain.remove(root)
                    tainted.add(root)
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            root = _dotted_name(node.value)
            if root is not None:
                name = root.split(".", 1)[0]
                plain.discard(name)
                tainted.add(name)
    return plain


def _violation(rule: str, node: ast.AST | None, message: str) -> ContractViolation:
    return ContractViolation(
        rule=rule,
        line=getattr(node, "lineno", None) if node is not None else None,
        column=getattr(node, "col_offset", None) if node is not None else None,
        message=message,
    )


def validate_adversarial_test(
    source: str, *, module_path: str, mode: TriageMode
) -> ContractValidation:
    """Apply the static caller contract, or explicitly bypass it in STRICT mode."""
    if mode == "STRICT":
        return ContractValidation(mode=mode, accepted=True, violations=())

    try:
        tree = ast.parse(source, filename="<generated-adversarial-test>")
    except SyntaxError as exc:
        return ContractValidation(
            mode=mode,
            accepted=False,
            violations=(
                ContractViolation(
                    rule="syntax",
                    line=exc.lineno,
                    column=exc.offset,
                    message=f"generated test is not valid Python: {exc.msg}",
                ),
            ),
        )

    violations: list[ContractViolation] = []
    direct_targets: set[str] = set()
    module_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    continue
                if alias.name == module_path:
                    module_aliases.add(alias.asname or alias.name.split(".")[0])
                    continue
                violations.append(
                    _violation(
                        "imports",
                        node,
                        f"import {alias.name!r} is outside pytest and {module_path!r}",
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ""
            if node.level or imported not in {"pytest", module_path}:
                violations.append(
                    _violation(
                        "imports",
                        node,
                        f"import from {imported!r} is outside pytest and {module_path!r}",
                    )
                )
            elif imported == module_path:
                for alias in node.names:
                    if alias.name == "*":
                        violations.append(
                            _violation(
                                "imports",
                                node,
                                "wildcard imports from the module under test are not allowed",
                            )
                        )
                    else:
                        direct_targets.add(alias.asname or alias.name)

    parent: dict[ast.AST, ast.AST] = {}
    for owner in ast.walk(tree):
        for child in ast.iter_child_nodes(owner):
            parent[child] = owner

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            violations.append(
                _violation("definitions", node, "class definitions are not allowed")
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            violations.append(
                _violation(
                    "definitions", node, "async function definitions are not allowed"
                )
            )
        elif isinstance(node, ast.Lambda):
            violations.append(
                _violation("definitions", node, "lambda definitions are not allowed")
            )
        elif isinstance(node, ast.FunctionDef):
            if not isinstance(parent.get(node), ast.Module) or not node.name.startswith(
                "test_"
            ):
                violations.append(
                    _violation(
                        "definitions",
                        node,
                        "only top-level test_* functions may be defined",
                    )
                )
        elif isinstance(node, ast.Compare) and any(
            isinstance(operator, (ast.Is, ast.IsNot)) for operator in node.ops
        ):
            violations.append(
                _violation(
                    "identity",
                    node,
                    "identity comparisons ('is' and 'is not') are not allowed",
                )
            )
        elif isinstance(node, ast.Call):
            called = _dotted_name(node.func)
            final_name = called.rsplit(".", 1)[-1] if called else None
            if final_name in set(CONTRACT_RULES.forbidden_inspection_calls):
                violations.append(
                    _violation(
                        "inspection_calls",
                        node,
                        f"call to {final_name}() is not allowed",
                    )
                )
        elif isinstance(node, ast.Attribute) and node.attr in set(
            CONTRACT_RULES.forbidden_inspection_attributes
        ):
            violations.append(
                _violation(
                    "inspection_attributes",
                    node,
                    f"inspection through .{node.attr} is not allowed",
                )
            )

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    for function in functions:
        plain_names = _plain_bindings(function)
        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue
            called = _dotted_name(node.func)
            is_target = (
                isinstance(node.func, ast.Name) and node.func.id in direct_targets
            ) or (
                called is not None
                and any(
                    called == alias or called.startswith(alias + ".")
                    for alias in module_aliases
                )
            )
            if not is_target:
                continue
            for argument in node.args:
                if isinstance(argument, ast.Starred) or not _plain_value(
                    argument, plain_names
                ):
                    violations.append(
                        _violation(
                            "plain_inputs",
                            argument,
                            "code-under-test arguments must be plain literal values",
                        )
                    )
            for keyword in node.keywords:
                if keyword.arg is None or not _plain_value(keyword.value, plain_names):
                    violations.append(
                        _violation(
                            "plain_inputs",
                            keyword.value,
                            "code-under-test keyword arguments must be plain literal values",
                        )
                    )

    # Stable de-duplication keeps feedback and artifacts concise.
    unique: list[ContractViolation] = []
    seen: set[tuple[object, ...]] = set()
    for item in violations:
        key = (item.rule, item.line, item.column, item.message)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return ContractValidation(
        mode=mode,
        accepted=not unique,
        violations=tuple(unique),
    )
