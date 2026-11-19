from epb_power.scope import validate_scope


def test_draft_included_scope_blocks_strict():
    rows = [{"hs8": "85042100", "product_group": "Transformers", "include": "Y", "review_status": "draft"}]
    assert "scope_not_approved" in {issue["issue_code"] for issue in validate_scope(rows)}


def test_duplicate_and_invalid_scope_detected():
    rows = [
        {"hs8": "85042100", "product_group": "A", "include": "Y", "review_status": "approved"},
        {"hs8": "85042100", "product_group": "B", "include": "Y", "review_status": "approved"},
    ]
    assert "scope_duplicate_code" in {issue["issue_code"] for issue in validate_scope(rows)}


def test_excluded_drafts_do_not_block_approved_included_scope():
    rows = [
        {"hs8": "85042100", "product_group": "Transformers", "include": "Y", "review_status": "approved"},
        {"hs8": "85044090", "product_group": "Converters", "include": "N", "review_status": "draft"},
    ]
    assert "scope_not_approved" not in {issue["issue_code"] for issue in validate_scope(rows)}

