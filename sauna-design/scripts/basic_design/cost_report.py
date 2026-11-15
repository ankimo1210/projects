"""CPU-only A3 concept budget booklet; no Blender or GPU runtime."""

import json
import unicodedata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager as fm
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

from .costs import CASES, DATA, calculate

FONT = next(
    Path(p)
    for p in [
        "/mnt/c/Windows/Fonts/YuGothM.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    if Path(p).exists()
)
fm.fontManager.addfont(str(FONT))
plt.rcParams.update(
    {
        "font.family": fm.FontProperties(fname=str(FONT)).get_name(),
        "pdf.fonttype": 42,
        "axes.unicode_minus": False,
    }
)
INK = "#263830"
MUTED = "#65726A"
PAPER = "#FAF9F5"
LINE = "#CDD4CD"
ACCENT = "#42775E"
PAGES = []


def tx(f, x, y, t, size=9, color=INK, **kw):
    return f.text(x / 420, y / 297, str(t), fontsize=size, color=color, va="center", **kw)


def wrap(s, n):
    out = []
    line = ""
    count = 0
    for c in str(s):
        k = 1 if unicodedata.east_asian_width(c) in "WFA" else 0.55
        if c == "\n" or (count + k > n and line):
            out.append(line)
            line = ""
            count = 0
            if c == "\n":
                continue
        line += c
        count += k
    return out + [line]


def para(f, x, y, t, width=384, size=9.5, color=INK):
    for line in wrap(t, width / (size / 2.83465) * 0.96):
        tx(f, x, y, line, size, color)
        y -= size / 2.83465 * 1.45
    return y - 4


def page(code, title):
    f = plt.figure(figsize=(420 / 25.4, 297 / 25.4), facecolor=PAPER)
    tx(f, 18, 279, code, 13, ACCENT)
    tx(f, 61, 279, title, 20)
    tx(
        f,
        18,
        265,
        "2026-11-15 / 280㎡・3サ室・2水風呂＋炭酸泉 / 単位：万円（明記のない単価・工種額は税抜）",
        8.5,
        MUTED,
    )
    f.add_artist(plt.Line2D([18 / 420, 402 / 420], [257 / 297, 257 / 297], color=LINE, lw=0.7))
    tx(
        f,
        18,
        12,
        "計画予算。物件・成約見積なし / 大規模な構造・建物全体改修や購入費は未算入 / GPU不使用",
        7,
        MUTED,
    )
    tx(f, 398, 12, f"{len(PAGES) + 1:02d}", 8, MUTED, ha="right")
    return f


def table(f, y, widths, headers, rows, size=8.5, min_h=12):
    for n, values in enumerate([headers] + rows):
        blocks = [wrap(v, w / (size / 2.83465) * 0.92) for v, w in zip(values, widths)]
        height = max(min_h, max(map(len, blocks)) * size / 2.83465 * 1.3 + 4)
        if y - height < 24:
            raise ValueError("Budget table overflow " + str(y - height))
        x = 18
        for w, lines in zip(widths, blocks):
            f.add_artist(
                Rectangle(
                    (x / 420, (y - height) / 297),
                    w / 420,
                    height / 297,
                    facecolor=INK if n == 0 else ("#EFF2EB" if n % 2 else PAPER),
                    edgecolor=LINE,
                    lw=0.3,
                    transform=f.transFigure,
                )
            )
            for j, line in enumerate(lines):
                tx(
                    f,
                    x + 2,
                    y - 3 - size / 2.83465 * 0.5 - j * size / 2.83465 * 1.3,
                    line,
                    size,
                    PAPER if n == 0 else INK,
                )
            x += w
        y -= height
    return y


def save(f, code, pdf):
    pdf.savefig(f, facecolor=PAPER)
    f.savefig(DATA / "previews" / f"{code}.png", dpi=110, facecolor=PAPER)
    PAGES.append({"code": code, "title": f.texts[1].get_text()})
    plt.close(f)


def man(v, dec=1):
    return f"{v / 10000:,.{dec}f}"


def generate():
    d = calculate()
    s = d["cases"]["base"]["summary"]
    (DATA / "previews").mkdir(exist_ok=True)
    with PdfPages(DATA / "sauna_cost_v1.pdf") as pdf:
        f = page("C-001", "総額2億円でできるか")
        tx(
            f,
            18,
            239,
            "基準：約2.26億円。2億円は条件改善で狙う目標。1億円は今の計画では厳しい。",
            17,
        )
        y = para(
            f,
            18,
            224,
            "賃貸で開業し、返還保証金・工事中賃料・設計/調査・開業準備・売上相殺なしの運転資金3か月を含む。土地建物購入は価格未定で含まない。低位/上振れは工事条件と調達条件の幅で、統計的な確率や見積上限ではない。",
        )
        keys = [
            ("construction_cash", "工事・機器・家具（税込、元請/予備費含む）"),
            ("soft_cash", "設計/調査/申請・開業準備・研修"),
            ("property_nonref", "物件費（工事中賃料・礼金等）"),
            ("refundable_deposit", "返還保証金（仮）"),
            ("opening_cash", "開業までの現金支出"),
            ("reserve_3m", "運転資金3か月分"),
            ("funding_3m", "総必要資金：3か月込み"),
            ("funding_6m", "総必要資金：6か月込み"),
        ]
        table(
            f,
            y,
            [189, 65, 65, 65],
            ["資金区分", "条件良好・低位", "基準", "上振れ"],
            [[label] + [man(d["cases"][c]["summary"][key]) for c in CASES] for key, label in keys],
            size=9.3,
            min_h=14,
        )
        para(
            f,
            18,
            60,
            "低位約1.29億／基準約2.26億／上振れ約3.86億（3か月込み）。物件未定のため幅が広い。低位は条件の良い建物と低い調達価格が揃う場合。建物全体の大改修はこの上振れにも含んでいない。",
            size=9.4,
        )
        save(f, "C-001", pdf)

        f = page("C-002", "工事費の中身：何にお金がかかるか")
        cats = [
            cat
            for cat in d["cases"]["base"]["categories"]
            if cat not in ["設計・調査・申請", "開業準備"]
        ]
        rows = [[cat] + [man(d["cases"][c]["categories"][cat]) for c in CASES] for cat in cats]
        for key, label in [
            ("direct", "直接工事/機器/家具計"),
            ("contractor_overhead", "元請経費（低8/基10/高12%）"),
            ("contingency", "予備費（経費込に低10/基15/高20%）"),
            ("construction_ex_tax", "工事計・税抜"),
            ("construction_cash", "工事計・税込"),
        ]:
            rows.append([label] + [man(d["cases"][c]["summary"][key]) for c in CASES])
        table(
            f,
            246,
            [189, 65, 65, 65],
            ["工種・加算", "低位", "基準", "上振れ"],
            rows,
            size=8.8,
            min_h=11.6,
        )
        para(
            f,
            18,
            46,
            "ろ過/冷却/炭酸約2,105万円は、ろ過3組720万＋冷却2系460万＋HX90万＋配管360万＋薬注105万＋炭酸150万＋CO2安全60万＋据付160万。これらを機器本体の定価と再加算していない。",
            size=8.5,
        )
        save(f, "C-002", pdf)

        f = page("C-003", "予算枠と、2億円へ寄せる条件")
        table(
            f,
            246,
            [70, 92, 92, 130],
            ["予算枠", "基準総額3か月込み", "不足額", "読み方"],
            [
                [f"{v / 1e8:g}億円", man(s["funding_3m"]), man(s["funding_3m"] - v), label]
                for v, label in [
                    (1e8, "今の規模・体験の新設計画では厳しい"),
                    (1.5e8, "相当良い居抜き/インフラ条件等が必要"),
                    (2e8, "基準から約2625万円の改善が必要"),
                ]
            ],
            size=9,
            min_h=17,
        )
        target = d["target_to_200m"]
        adj = target["summary"]
        delta = s["funding_3m"] - adj["funding_3m"]
        tx(
            f,
            18,
            164,
            f"仕様を維持する目標例：約{adj['funding_3m'] / 1e8:.2f}億円（未交渉・物件未取得）",
            15,
        )
        table(
            f,
            152,
            [104, 115, 165],
            ["変更条件", "基準→目標", "範囲と限界"],
            [
                [
                    "直接工事の削減",
                    "約1億1150万→約9950万円",
                    "既存ピット200万＋既存MEP再利用500万＋別工種の調達/仕様整理500万。計1200万円減の仮定",
                ],
                [
                    "月額家賃・共益費",
                    "150万→120万円（税抜）",
                    "工事中賃料/礼金/手数料/開業後賃料を連動して減額",
                ],
                [
                    "返還保証金",
                    "10か月→6か月",
                    "契約交渉が必要。返還性資金の減少で工事価格が安くなる訳ではない",
                ],
                [
                    "維持する条件",
                    "280㎡・3サ室・3槽・休憩",
                    "予備費15%と運転3か月を残す。撤去・調達範囲の重複控除はしない",
                ],
            ],
            size=8.8,
            min_h=18,
        )
        para(
            f,
            18,
            51,
            f"上記の条件が全て揃うと約{man(adj['funding_3m'])}万円で、基準から{man(delta)}万円減。2億円に対する余裕は約{man(2e8 - adj['funding_3m'])}万円に留まり、未算入の建物工事が出ると超える。現段階で予算内と確定はしない。",
            size=9,
        )
        save(f, "C-003", pdf)

        f = page("C-004", "月次費用：運転資金を別に確保する")
        rows = []
        for i, r in enumerate(d["cases"]["base"]["operation"]["rows"]):
            qty = f"{r['quantity']:,.1f} {r['unit']}"
            rows.append(
                [r["item"], qty]
                + [man(d["cases"][c]["operation"]["rows"][i]["cash"]) for c in CASES]
            )
        rows.append(
            ["月次現金支出", "売上を相殺しない"]
            + [man(d["cases"][c]["operation"]["monthly"]) for c in CASES]
        )
        table(
            f,
            246,
            [102, 111, 57, 57, 57],
            ["費目", "基準の数量条件", "低位/月", "基準/月", "上振れ/月"],
            rows,
            size=8.8,
            min_h=13,
        )
        para(
            f,
            18,
            72,
            "基準は200人/日×30日、営業時間16h、清掃等込み18h、現場3人相当＋管理枠、イベント月8回。来客予測ではない。電気は23MWh/月・110kWの仮契約、ガス1800m³/月は損失等込みの感度仮定。実際の契約・稼働・季節で再計算する。",
            size=9,
        )
        para(
            f,
            18,
            44,
            "水量は既計算20.0384m³/日＋便所/清掃等3m³/日＝691.152m³/月。ろ過循環量は水道使用量に足さない。月額に返済/事業利益への税/売上連動決済費は含まず、運転資金は売上を差し引かないバッファ。",
            size=8.7,
        )
        save(f, "C-004", pdf)

        for start in range(0, len(d["items"]), 14):
            items = d["items"][start : start + 14]
            code = f"C-{5 + start // 14:03d}"
            f = page(
                code,
                f"詳細明細 {start + 1}〜{min(start + 14, len(d['items']))} / 全{len(d['items'])}項目",
            )
            rows = []
            for r in items:
                scope = (
                    f"{r['scope_and_limit']}\n数量：{r['quantity_basis']} / 根拠：{r['source_ids']}"
                )
                rows.append(
                    [
                        r["id"],
                        r["item"],
                        f"{r['quantity']:,.2f}",
                        r["unit"],
                        man(r["low"], 2),
                        man(r["base"], 2),
                        man(r["high"], 2),
                        man(r["base_amount"]),
                        scope,
                    ]
                )
            table(
                f,
                246,
                [14, 60, 19, 11, 23, 23, 23, 25, 186],
                [
                    "ID",
                    "項目",
                    "数量",
                    "単位",
                    "低単価",
                    "基準単価",
                    "高単価",
                    "基準金額",
                    "含む範囲・数量根拠・未確認事項",
                ],
                rows,
                size=7.8,
                min_h=12,
            )
            para(
                f,
                18,
                35,
                "単価・金額は万円/税抜（O04人件費は消費税なし）。一式行は見積済ではなく明示した予算枠。詳細な部材/経路/メーカー条件が確定したら数量と単価を置き換える。",
                size=8.1,
            )
            save(f, code, pdf)

        f = page("C-011", "物件次第の追加工事と、断面による差額")
        y = table(
            f,
            246,
            [83, 127, 174],
            ["条件", "今回の予算の扱い", "次に必要な確認"],
            [
                [
                    "A 床下型",
                    "ピット12㎡×20万＋局所支持200万＋床下排水60万＝基準500万",
                    "深槽は床下1.31m。3槽の掘削面積/深さは未確定。地下水/基礎大補強は別",
                ],
                [
                    "B 床上げ型",
                    "代替価格未算定。安い成立案として使わない",
                    "梁下3m仮定で頭上1.34m。外階段が現在の平面に干渉",
                ],
                [
                    "C 併用型",
                    "再設計前なので差額は未算定",
                    "床下0.70m、頭上2.04m。外階段の平面干渉を解消してから拾い直す",
                ],
                [
                    "ガス→HP給湯",
                    "G01/G03を置き換えた純増の仮枠150〜450万円（直接工事）",
                    "HP性能・冬季能力・受電・室外機置場・契約。月次差額はCOPと料金条件で変わる",
                ],
                [
                    "建物側A/B/C工事",
                    "E03等には局所接続枠のみ。所有区分で二度足さない",
                    "貸主指定工事の見積が出たら同じ接続範囲の予算枠と置換",
                ],
                [
                    "予備費",
                    "基準は経費込み工事の15%＝約1840万円（税抜）",
                    "許可されないピットや避難不能を予備費で成立扱いにしない",
                ],
            ],
            size=8.9,
            min_h=22,
        )
        y -= 10
        for line in d["config"]["unpriced_exclusions"]:
            y = para(f, 18, y, "未算入：" + line, size=8.8)
        save(f, "C-011", pdf)

        for j, start in enumerate(range(0, len(d["sources"]), 5)):
            f = page(f"C-{12 + j:03d}", "価格と数量の根拠 / " + str(j + 1))
            y = 244
            for r in d["sources"][start : start + 5]:
                tx(f, 18, y, r["id"] + "  " + r["title"], 10.5, ACCENT, url=r["url"] or None)
                y -= 7
                y = para(f, 18, y, r["basis"] + " ［" + r["confidence"] + "］", size=8.7)
                if r["url"]:
                    y = para(f, 18, y, r["url"], size=7.5, color=MUTED)
                y -= 3
            para(
                f,
                18,
                37,
                "全工事の成約見積は未取得。公開価格は材料/機器の参考値で工事一式価格ではない。検索索引のみの価格、メーカー定価、販売者公開価格と作成者仮定を区別した。",
                size=8.7,
            )
            save(f, f"C-{12 + j:03d}", pdf)
    (DATA / "verification").mkdir(exist_ok=True)
    (DATA / "verification/pages.json").write_text(json.dumps(PAGES, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {
                "pages": len(PAGES),
                "target_3m_man": d["target_to_200m"]["summary"]["funding_3m"] / 10000,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    generate()
