def test_ward_rule_never_passes_for_unknown_jurisdiction():
    from basic_design.compliance import classify

    assert classify("港区", None, True) == "管轄未確定"
    assert classify("港区", "新宿区", True) == "他管轄参考"
    assert classify("港区", "港区", None) == "資料不足"
    assert classify("港区", "港区", False) == "要修正"
    assert classify("港区", "港区", True) == "図面上確認・承認未取得"
