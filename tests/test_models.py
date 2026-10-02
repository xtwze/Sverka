import pytest

from source.domain.source_validation import DEFAULT_SOURCE_RULES
from source.dto.source_dto import SourceContractError, parse_snapshot


def test_broken_relation_is_rejected():
    with pytest.raises(SourceContractError, match="unknown account"):
        parse_snapshot(
            {
                "accounts": [],
                "charges": [
                    {
                        "id": "charge-1",
                        "account_id": "missing",
                        "period": "2026-08",
                        "amount_kopecks": 100,
                    }
                ],
                "payments": [],
            }
        )


def test_float_money_is_rejected():
    with pytest.raises(SourceContractError, match="integer"):
        parse_snapshot(
            {
                "accounts": [{"id": "account", "account_number": "1"}],
                "charges": [
                    {
                        "id": "charge",
                        "account_id": "account",
                        "period": "2026-08",
                        "amount_kopecks": 1.5,
                    }
                ],
                "payments": [],
            }
        )


@pytest.mark.parametrize("row", [None, [], "bad", 42, True])
def test_non_object_records_are_contract_errors(row):
    with pytest.raises(SourceContractError, match="items must be objects"):
        parse_snapshot({"accounts": [row], "charges": [], "payments": []})


def test_new_rule_rejects_duplicate_account_number():
    with pytest.raises(SourceContractError, match="Duplicate account_number"):
        parse_snapshot({
            "accounts": [{"id": "a", "account_number": "1"},
                         {"id": "b", "account_number": "1"}],
            "charges": [], "payments": [],
        })


def test_rules_can_be_extended_without_rewriting_parser():
    visited = []

    def additional_rule(snapshot):
        visited.append(snapshot)
        raise SourceContractError("Custom validation result")

    with pytest.raises(SourceContractError, match="Custom validation result"):
        parse_snapshot(
            {"accounts": [], "charges": [], "payments": []},
            rules=(*DEFAULT_SOURCE_RULES, additional_rule),
        )
    assert len(visited) == 1
