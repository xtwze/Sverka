import pytest

from source.models import SourceContractError, parse_snapshot


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
