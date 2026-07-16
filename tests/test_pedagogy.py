from __future__ import annotations

from fencepost.pedagogy import validate_pedagogical_witness


NUMERIC_FUNCTION = "def clamp_percent(p):\n    return p\n"


def _codes(source: str, function: str = NUMERIC_FUNCTION) -> set[str]:
    return {
        code
        for code, _ in validate_pedagogical_witness(
            source,
            qualified_function_name="clamp_percent",
            original_function=function,
        )
    }


def test_plain_public_result_witness_is_pedagogically_eligible() -> None:
    source = (
        "from gradebook.analytics import clamp_percent\n\n"
        "def test_boundary():\n"
        "    assert str(clamp_percent(-0.0)) == '-0.0'\n"
    )
    assert _codes(source) == set()


def test_implicit_boolean_as_number_is_withheld() -> None:
    source = (
        "from gradebook.analytics import clamp_percent\n\n"
        "def test_boolean_quirk():\n"
        "    boundary = False\n"
        "    assert clamp_percent(boundary) == 0\n"
    )
    assert _codes(source) == {"implicit_bool_as_number"}


def test_boolean_input_is_allowed_when_function_declares_it() -> None:
    source = (
        "from gradebook.analytics import clamp_percent\n\n"
        "def test_flag():\n"
        "    assert clamp_percent(False) is False\n"
    )
    function = "def clamp_percent(p: bool):\n    return p\n"
    assert _codes(source, function) == set()


def test_implementation_introspection_is_withheld() -> None:
    source = (
        "from gradebook.analytics import clamp_percent\n\n"
        "def test_bytecode():\n"
        "    assert clamp_percent.__code__.co_argcount == 1\n"
    )
    assert _codes(source) == {"implementation_introspection"}
