from epb_power.discovery import discover, select_sources
from epb_power.quality import publication_blockers, validate_sources


def test_june_overlap_and_rounding_tolerance(tmp_path, detailed_factory, product_factory):
    detailed_factory(tmp_path / "detail.xlsx", "July-June 2025-26", {"85042100": 1.00}, 3.00)
    product_factory(tmp_path / "product.xlsx", {"85042100": 1.00, "90283000": 2.09}, 3.00)
    infos = discover(tmp_path)
    selected, messages = select_sources(infos)
    issues = validate_sources(infos, selected, messages)
    codes = {item["issue_code"] for item in issues}
    assert "june_overlap_match" in codes
    assert "june_total_rounding" in codes
    assert "june_overlap_mismatch" not in codes


def test_publication_gate_distinguishes_draft_and_incomplete():
    issues = [
        {"severity": "critical", "issue_code": "scope_not_approved"},
        {"severity": "critical", "issue_code": "missing_source"},
    ]
    assert publication_blockers(issues, allow_incomplete=False, allow_draft_scope=False) == {
        "scope_not_approved",
        "missing_source",
    }
    assert publication_blockers(issues, allow_incomplete=True, allow_draft_scope=True) == set()

