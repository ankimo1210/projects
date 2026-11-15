"""Property screen booklet, CPU raster/vector only. No model changes."""

import json

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .cost_report import ACCENT, LINE, MUTED, PAPER, para, table, tx
from .property import DATA, calculate, search_total

PAGES = []


def page(code, title):
    f = plt.figure(figsize=(420 / 25.4, 297 / 25.4), facecolor=PAPER)
    tx(f, 18, 279, code, 13, ACCENT)
    tx(f, 62, 279, title, 20)
    tx(
        f,
        18,
        265,
        "2026-11-15 / ⑦物件条件表 / 東京・男性専用40人・280㎡計画 / 金額：万円 / 3D・GPU作業は保留",
        8.5,
        MUTED,
    )
    f.add_artist(plt.Line2D([18 / 420, 402 / 420], [257 / 297, 257 / 297], color=LINE, lw=0.7))
    tx(
        f,
        18,
        12,
        "物件未取得・取引見積なし / 数値は計画・探索条件 / 構造・法適合・許可取得は未確定 / 外部送信なし",
        7,
        MUTED,
    )
    tx(f, 398, 12, f"{len(PAGES) + 1:02d}", 8, MUTED, ha="right")
    return f


def save(f, code, pdf):
    pdf.savefig(f, facecolor=PAPER)
    f.savefig(DATA / "previews" / f"{code}.png", dpi=110, facecolor=PAPER)
    PAGES.append({"code": code, "title": f.texts[1].get_text()})
    plt.close(f)


def man(x, dec=1):
    return f"{x / 10000:,.{dec}f}"


def generate():
    d = calculate()
    (DATA / "previews").mkdir(parents=True, exist_ok=True)
    with PdfPages(DATA / "sauna_property_v1.pdf") as pdf:
        f = page("P-001", "2億円以内を目指す物件の探し方")
        tx(
            f,
            18,
            240,
            "家賃100〜110万円・保証金6か月以下。適合する既存ピットと設備を優先する。",
            17,
        )
        y = para(
            f,
            18,
            224,
            "現280㎡・3サ室・深い水風呂を含む3槽の希望を維持する賃貸案。最優先は地上階の元浴場/温浴施設。ただし居抜きも用途許可・支持・水質設備・費用の確認が必要。家賃が安い一般店舗を改造すると、構造/インフラ工事で総額が上がる。",
            size=10,
        )
        table(
            f,
            y,
            [63, 178, 143],
            ["項目", "探索目標・必須条件", "確認すべきこと"],
            [
                [
                    "月額固定費",
                    "家賃/共益費/固定外部利用料：税抜100〜110万円目標。120万円は条件付き",
                    "家賃120万だけで2億にはならない。工事減額と初期費も合わせる",
                ],
                [
                    "保証金・取得費",
                    "全額返還6か月以下を目標。礼金/仲介/保証料/償却/譲渡代を別取得",
                    "返還保証金と費用を分け、税込実支払額を確認",
                ],
                [
                    "面積と形",
                    "20×14mの280㎡計画を柱/PS/動線と照合。募集目安300〜330㎡程度",
                    "募集面積と使える区画は異なる。余剰面積の工事費は別",
                ],
                [
                    "階・床下",
                    "地上階＋適合する既存ピット優先。深槽は仮スラブ上端から支持下端まで1.31m",
                    "ピット位置/地中梁/基礎/支持/防水/掘削承諾。地上階でも自動成立しない",
                ],
                [
                    "高さ・設備",
                    "局所梁下3.0m以上を比較目標。三相電源・給排水・ガス・屋外機と排気経路",
                    "3.0mは法定最低でない。受電103kVAは包絡、110kWは料金仮定",
                ],
                [
                    "貸主・建物全体",
                    "湿式公衆浴場/サウナ/ロウリュ/イベント/営業時間と工事を承諾",
                    "用途/避難/消防/衛生基準・共用改修・搬入更新まで書面で照合",
                ],
            ],
            size=9,
            min_h=20,
        )
        para(
            f,
            18,
            55,
            "現実的な順序：募集条件と基本図面 → 用途・ピット・支持・外部経路の一次確認 → 物件図への収まり照合 → 工事範囲/追加費の見積 → 総資金の再判定。正式相談や契約は行っていない。",
            size=9.3,
        )
        save(f, "P-001", pdf)

        f = page("P-002", "家賃・保証金・工事削減の組合せ")
        tx(f, 18, 241, "工事直接費1200万円減を得られた場合の総資金（運転3か月込み）", 12)
        rents = [1000000, 1100000, 1200000, 1300000, 1400000, 1500000]
        deps = [4, 6, 8, 10]
        table(
            f,
            231,
            [100, 71, 71, 71, 71],
            ["税抜家賃/月"] + [f"保証金{n}か月" for n in deps],
            [[man(r, 0)] + [man(search_total(r, n, 12000000)) for n in deps] for r in rents],
            size=9,
            min_h=12,
        )
        tx(f, 18, 134, "同じ条件で2億円以内に必要な直接工事減額（税抜、万円単位へ切上げ）", 11)
        import math

        table(
            f,
            124,
            [100, 71, 71, 71, 71],
            ["税抜家賃/月"] + [f"保証金{n}か月" for n in deps],
            [
                [man(r, 0)]
                + [
                    f"{math.ceil(max(0, (search_total(r, n, 0) - 2e8) / 1.3915) / 10000):,}"
                    for n in deps
                ]
                for r in rents
            ],
            size=9,
            min_h=11.5,
        )
        para(
            f,
            18,
            33,
            "工事5か月・礼金1・仲介1・保証会社0.7・全額返還保証金の固定式。元請10%/予備15%/消費税と運転3か月を維持。物件候補は実額で再計算する。",
            size=8.7,
        )
        save(f, "P-002", pdf)

        groups = list(dict.fromkeys(r["group"] for r in d["conditions"]))
        for i, g in enumerate(groups):
            code = f"P-{3 + i:03d}"
            f = page(code, g + "の具体条件")
            rows = []
            for r in d["conditions"]:
                if r["group"] == g:
                    rows.append(
                        [
                            r["id"],
                            r["topic"],
                            r["priority"],
                            r["target"],
                            r["hold_or_reject"],
                            r["documents"] + "\n根拠：" + r["source_ids"],
                        ]
                    )
            table(
                f,
                246,
                [14, 36, 28, 120, 100, 86],
                [
                    "ID",
                    "対象",
                    "区分",
                    "具体条件・数値の意味",
                    "保留・見送り・誤認防止",
                    "必要資料・根拠",
                ],
                rows,
                size=8.1,
                min_h=22,
            )
            if g == "予算・契約":
                para(
                    f,
                    18,
                    45,
                    "物件由来の再利用700万円減しか確認できない場合、保証金6か月で家賃上限約90.6万円/月。調達500万円減は物件の良さから自動的に得られるものではない。",
                    size=9,
                )
            elif g == "面積・建物":
                para(
                    f,
                    18,
                    44,
                    "280㎡は15ゾーンの外形合計。募集300〜330㎡は使えない部分を仮に見込む探索幅。躯体支持・間取り・アクセスを成立させる最低面積の保証ではない。",
                    size=8.8,
                )
            elif g == "設備・屋外":
                para(
                    f,
                    18,
                    44,
                    "機器外形・口径・電力/風量等は仮包絡。設備の適用/効率/揚程/配管・ダクト経路と貸主割当を合わせて照合する。実機メーカーの施工/保守条件は未取得。",
                    size=8.8,
                )
            elif g == "用途・安全":
                para(
                    f,
                    18,
                    69,
                    "所在地未定のため管轄別判定は未実施。港区の2026年基準例を他区へ自動適用しない。旧許可・居抜き・用途地域だけで新計画の営業可否を確定しない。",
                    size=9,
                )
            else:
                para(
                    f,
                    18,
                    115,
                    "契約前に費用/権限/範囲を一体で確認。工事許可がない設備や確保できない避難経路は、予備費で成立扱いにしない。建物所有者の工事とテナント工事の同一部分を二重加算しない。",
                    size=10,
                )
            save(f, code, pdf)

        f = page("P-008", "候補物件をどう判定するか")
        table(
            f,
            246,
            [88, 296],
            ["予備判定", "条件"],
            [
                [
                    "資料不足",
                    "物件名/所在地、費用値/根拠又は9主要条件の証拠/有効日付が不足。空白や未確認の文字では成立見込みにしない",
                ],
                [
                    "成立困難",
                    "用途禁止や支持/経路確保不能等を証拠付きで確認。根拠のない否定は資料不足のまま",
                ],
                [
                    "予算超過・変更案未確認",
                    "2億円を超え、解消する具体策が未記録。値引きや改修で対応できると決めない",
                ],
                [
                    "変更で対応",
                    "根拠付きの変更案を持つ。予算超過時は解消案を別欄へ記録。金額/承諾の再照合が必要",
                ],
                [
                    "成立見込み（予備判定）",
                    "費用欄が揃い2億以下、9条件すべて根拠資料と日付を確認。構造安全/法適合/許可の確定ではない",
                ],
            ],
            size=9.2,
            min_h=15.5,
        )
        tx(f, 18, 148, "仲介・貸主から先に取得する資料（未送信の照会項目）", 13)
        y = 135
        for line in [
            "1. 寸法入り区画図・断面・柱梁/PS・面積内訳・最低梁下・階と直下用途",
            "2. 元用途/確認・検査/増改築履歴・旧浴場許可/変更/承継に関する資料",
            "3. ピット実測/構造図/床伏/基礎・防水/漏水履歴と掘削/支持の承諾",
            "4. 当該区画の電力割当・給水口径/動水圧・排水径/管底高/許容流量・ガス供給",
            "5. 屋外機/排気の使用権と経路・騒音/運転制限・搬入/交換経路",
            "6. 用途/イベント/営業時間承諾、避難/消防/アクセス図、工事区分/指定業者見積",
            "7. 家賃等の全固定費・保証金返還/償却・礼金/保証会社・譲渡代・免賃/期間/原状回復",
        ]:
            y = para(f, 18, y, line, size=9.6)
        para(
            f,
            18,
            36,
            "Excelの候補欄は全て未入力で納品。費用比較例は仮想条件で、実物件の推薦や適合判定ではない。入力値や確認状態は後から更新できる。",
            size=8.8,
        )
        save(f, "P-008", pdf)

        for j, start in enumerate(range(0, len(d["sources"]), 6)):
            code = f"P-{9 + j:03d}"
            f = page(code, "根拠と適用範囲 " + str(j + 1))
            y = 244
            for source in d["sources"][start : start + 6]:
                tx(
                    f,
                    18,
                    y,
                    source["id"] + " " + source["title"],
                    10.5,
                    ACCENT,
                    url=source["url"] or None,
                )
                y -= 7
                y = para(f, 18, y, source["scope"], size=9.3)
                if source["url"]:
                    y = para(f, 18, y, source["url"], size=7.8, color=MUTED)
                y -= 5
            para(
                f,
                18,
                38,
                "①〜⑤・⑥は凍結。⑦の物件条件/候補フォームのみ作成。物件の実測・外部照会・申請・発注・3D統合は未実施。GPU/Blenderは起動していない。",
                size=8.8,
            )
            save(f, code, pdf)
    (DATA / "verification").mkdir(exist_ok=True)
    (DATA / "verification/pages.json").write_text(
        json.dumps(PAGES, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"pages": len(PAGES), "conditions": len(d["conditions"])}, ensure_ascii=False))


if __name__ == "__main__":
    generate()
