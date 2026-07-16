import pytest

from fencepost.contract import CONTRACT_RULES, validate_adversarial_test


MODULE = "gradebook.analytics"


def test_decimal_witness_is_rejected_by_contract_but_allowed_by_strict() -> None:
    source = '''from decimal import Decimal
from gradebook.analytics import clamp_percent


def test_decimal_identity():
    boundary = Decimal("100")
    result = clamp_percent(boundary)
    assert result is boundary
'''

    strict = validate_adversarial_test(source, module_path=MODULE, mode="STRICT")
    contract = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert strict.accepted
    assert not contract.accepted
    assert {item.rule for item in contract.violations} >= {
        "imports",
        "identity",
        "plain_inputs",
    }


def test_class_definition_is_rejected_by_contract() -> None:
    source = '''from gradebook.analytics import clamp_percent


class AsymmetricNumber:
    def __lt__(self, other):
        return False


def test_custom_number():
    clamp_percent(AsymmetricNumber())
'''

    contract = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not contract.accepted
    assert "ClassDef" in CONTRACT_RULES.forbidden_definition_nodes
    assert any(item.rule == "definitions" for item in contract.violations)


def test_plain_builtin_values_are_accepted_in_both_modes() -> None:
    source = '''import pytest
from gradebook.analytics import percentile


def test_percentile_endpoint():
    scores = [10, 20, 30]
    assert percentile(scores, 100) == 30
    with pytest.raises(ValueError):
        percentile([], 50.0)
'''

    for mode in ("STRICT", "CONTRACT"):
        validation = validate_adversarial_test(
            source, module_path=MODULE, mode=mode
        )
        assert validation.accepted, validation.violations


@pytest.mark.parametrize(
    "assertion",
    (
        "assert isinstance(result, int)",
        "assert type(result) == int",
        "assert id(result) == id(result)",
        "assert result.__class__ == int",
    ),
)
def test_type_and_identity_inspection_is_rejected(assertion: str) -> None:
    source = (
        "from gradebook.analytics import clamp_percent\n\n"
        "def test_inspection():\n"
        "    result = clamp_percent(100)\n"
        f"    {assertion}\n"
    )

    validation = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not validation.accepted
    assert any(item.rule.startswith("inspection_") for item in validation.violations)
