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


def test_monkeypatch_program_replacement_is_rejected_only_in_contract() -> None:
    source = '''import gradebook.analytics as analytics


def test_percentile_without_its_clamp(monkeypatch):
    monkeypatch.setattr(analytics, "clamp_percent", float)
    assert analytics.percentile([10, 20, 30, 40], -12.5) == 10
'''

    strict = validate_adversarial_test(source, module_path=MODULE, mode="STRICT")
    contract = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert strict.accepted
    assert not contract.accepted
    assert {item.rule for item in contract.violations} >= {
        "fixtures",
        "mocking",
        "program_replacement",
    }


def test_mock_patch_is_rejected_in_contract() -> None:
    source = '''from unittest.mock import patch
import gradebook.analytics as analytics


def test_percentile_with_patch():
    with patch.object(analytics, "clamp_percent", float):
        assert analytics.percentile([10, 20, 30], -12.5) == 10
'''

    validation = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not validation.accepted
    assert any(item.rule == "mocking" for item in validation.violations)


def test_direct_module_attribute_rebinding_is_rejected_in_contract() -> None:
    source = '''import gradebook.analytics as analytics


def test_percentile_rebinding_clamp():
    analytics.clamp_percent = float
    assert analytics.percentile([10, 20, 30], -12.5) == 10
'''

    validation = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not validation.accepted
    assert any(item.rule == "program_replacement" for item in validation.violations)


@pytest.mark.parametrize(
    "replacement",
    (
        'setattr(analytics, "clamp_percent", float)',
        'delattr(analytics, "clamp_percent")',
        'setitem(analytics.__dict__, "clamp_percent", float)',
    ),
)
def test_mutation_helpers_cannot_target_module_under_test(replacement: str) -> None:
    source = (
        "import gradebook.analytics as analytics\n\n"
        "def test_program_replacement_helper():\n"
        f"    {replacement}\n"
    )

    validation = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not validation.accepted
    assert any(item.rule == "program_replacement" for item in validation.violations)


def test_module_alias_cannot_bypass_program_replacement_rule() -> None:
    source = '''import gradebook.analytics as analytics


def test_alias_replacement():
    subject = analytics
    setattr(subject, "clamp_percent", float)
'''

    validation = validate_adversarial_test(
        source, module_path=MODULE, mode="CONTRACT"
    )

    assert not validation.accepted
    assert any(item.rule == "program_replacement" for item in validation.violations)


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
