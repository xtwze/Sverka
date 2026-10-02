from source.domain.models import Charge
from source.domain.reconciliation import reconcile_charges


def charge(identifier: str, amount: int, account: str = "acc-alice") -> Charge:
    return Charge(identifier, account, "2026-08", amount)


def test_matching_rows_and_exact_kopeck_total():
    rows = (charge("charge-1", 125050), charge("charge-2", 24950))
    report = reconcile_charges("2026-08", rows, rows, {"acc-alice": "10001"})
    assert report["status"] == "MATCH"
    assert report["source"] == {"count": 2, "total_kopecks": 150000}
    assert report["postgres"] == report["source"]


def test_missing_extra_and_changed_amount_are_reported():
    source = (charge("missing", 100), charge("changed", 200))
    target = (charge("changed", 201), charge("extra", 300))
    report = reconcile_charges("2026-08", source, target, {"acc-alice": "10001"})
    assert report["status"] == "MISMATCH"
    assert [row["type"] for row in report["differences"]] == [
        "amount_mismatch",
        "extra_in_postgres",
        "missing_in_postgres",
    ]


def test_other_month_is_excluded():
    source = (Charge("september", "acc-alice", "2026-09", 5000),)
    report = reconcile_charges("2026-08", source, (), {"acc-alice": "10001"})
    assert report["status"] == "MATCH"
    assert report["source"]["count"] == 0


def test_account_and_amount_changes_are_reported_independently():
    report = reconcile_charges(
        "2026-08", (charge("changed", 100),),
        (charge("changed", 101, "acc-bob"),),
        {"acc-alice": "10001", "acc-bob": "20002"},
    )
    assert [(row["type"], row["source_value"], row["postgres_value"])
            for row in report["differences"]] == [
        ("account_mismatch", "acc-alice", "acc-bob"),
        ("amount_mismatch", 100, 101),
    ]


def test_account_only_change_includes_both_account_ids():
    report = reconcile_charges(
        "2026-08", (charge("changed", 100),),
        (charge("changed", 100, "acc-bob"),), {},
    )
    assert len(report["differences"]) == 1
    assert report["differences"][0]["source_value"] == "acc-alice"
    assert report["differences"][0]["postgres_value"] == "acc-bob"
