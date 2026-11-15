"""Do not silently approve an unknown jurisdiction or missing evidence."""


def classify(rule_jurisdiction, site_jurisdiction, evidence):
    if not site_jurisdiction:
        return "管轄未確定"
    if rule_jurisdiction not in ("全国", "東京都", site_jurisdiction):
        return "他管轄参考"
    if evidence is None:
        return "資料不足"
    if not evidence:
        return "要修正"
    return "図面上確認・承認未取得"
