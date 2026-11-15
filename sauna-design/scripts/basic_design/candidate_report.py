"""CPU-only A3 comparison booklet from the candidate register and cash model."""

import json
import unicodedata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager as fm
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

from .candidates import DATA, calculate

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
FILL = "#EFF2EB"


def tx(fig, x, y, text, size=9, color=INK, **kwargs):
    return fig.text(x / 420, y / 297, str(text), fontsize=size, color=color, va="center", **kwargs)


def wrap(text, capacity):
    lines, line, count = [], "", 0
    for char in str(text):
        weight = 1 if unicodedata.east_asian_width(char) in "WFA" else 0.55
        if char == "\n" or (count + weight > capacity and line):
            lines.append(line)
            line, count = "", 0
            if char == "\n":
                continue
        line += char
        count += weight
    return lines + [line]


def paragraph(fig, x, y, text, width=384, size=9, color=INK, gap=3, url=None):
    step = size / 2.83465 * 1.42
    for line in wrap(text, width / (size / 2.83465) * 0.95):
        if y < 24:
            raise ValueError("Candidate paragraph overflow")
        tx(fig, x, y, line, size, color, url=url)
        y -= step
    return y - gap


def table(fig, y, widths, headings, rows, size=8.5, min_height=12, x=18):
    for number, values in enumerate([headings] + rows):
        blocks = [
            wrap(value, width / (size / 2.83465) * 0.92) for value, width in zip(values, widths)
        ]
        height = max(min_height, max(map(len, blocks)) * size / 2.83465 * 1.3 + 4)
        if y - height < 24:
            raise ValueError("Candidate table overflow")
        left = x
        for width, lines in zip(widths, blocks):
            fig.add_artist(
                Rectangle(
                    (left / 420, (y - height) / 297),
                    width / 420,
                    height / 297,
                    transform=fig.transFigure,
                    facecolor=INK if number == 0 else (FILL if number % 2 else PAPER),
                    edgecolor=LINE,
                    lw=0.35,
                )
            )
            for index, line in enumerate(lines):
                tx(
                    fig,
                    left + 2,
                    y - 3 - size / 2.83465 * 0.5 - index * size / 2.83465 * 1.3,
                    line,
                    size,
                    PAPER if number == 0 else INK,
                )
            left += width
        y -= height
    return y


def page(number, title):
    fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4), facecolor=PAPER)
    tx(fig, 18, 279, f"P-{number:03d}", 13, ACCENT)
    tx(fig, 62, 279, title, 19)
    tx(
        fig,
        18,
        265,
        "2026-11-15 / 男性40人・計画280㎡・3サ室・2水風呂＋炭酸泉 / 金額：万円",
        8.6,
        MUTED,
    )
    fig.add_artist(plt.Line2D([18 / 420, 402 / 420], [257 / 297, 257 / 297], color=LINE, lw=0.7))
    tx(
        fig,
        18,
        12,
        "公開募集の比較。全件資料不足 / 空室・浴場用途・収まり・再利用未確認 / 追加費未算入 / GPU不使用",
        7.4,
        MUTED,
    )
    tx(fig, 401, 12, f"{number:02d} / 06", 8, MUTED, ha="right")
    return fig


def man(yen, decimals=1):
    return f"{yen / 10000:,.{decimals}f}"


def source_lines(fig, sources, y=43):
    for source in sources:
        tx(
            fig,
            18,
            y,
            f"出典：{source['publisher']} / 確認 {source['checked_at']}",
            7.5,
            ACCENT,
            url=source["url"],
        )
        y = paragraph(
            fig, 18, y - 5, source["url"], size=6.9, color=MUTED, gap=3, url=source["url"]
        )


def save(fig, code, pdf, pages):
    pdf.savefig(fig, facecolor=PAPER)
    fig.savefig(DATA / "previews" / f"{code}.png", dpi=110, facecolor=PAPER)
    pages.append({"code": code, "title": fig.texts[1].get_text()})
    plt.close(fig)


def overview(data, pdf, pages):
    fig = page(1, "実在物件の比較：2億円へ近づく条件")
    tx(fig, 18, 241, "家賃が合う掲載はある。浴場として成立する物件は、まだ確定していない。", 16)
    y = paragraph(
        fig,
        18,
        226,
        "同じ280㎡案の⑥費用に、各掲載の賃料・保証金等を反映した参考値。"
        "敷地/区画固有の追加工事・超過面積の内装・未公表費用は含まない。"
        "700/1,200万円の直接工事純減は比較仮定で、既存設備の再利用や値引きは全件未確認。",
        size=9.5,
    )
    rows = []
    for candidate in data["candidates"]:
        cases = candidate["cases"]
        rows.append(
            [
                candidate["id"] + " " + candidate["name"],
                f"{candidate['area_m2']:.2f}㎡\n{man(cases[0]['monthly_rent_gross_yen'])} / 月",
                *[man(case["reference_total_yen"]) for case in cases],
                man(candidate["required_net_direct_saving_yen"]),
            ]
        )
    y = table(
        fig,
        y,
        [105, 61, 56, 56, 56, 50],
        [
            "区画 / 全件資料不足",
            "面積 / 月額税込\n家賃＋共益費",
            "純減なし\n参考総額",
            "純減700万\n参考総額",
            "純減1,200万\n参考総額",
            "2億円に届く\n必要純減※",
        ],
        rows,
        size=8.5,
        min_height=19,
    )
    y = paragraph(
        fig,
        18,
        y - 8,
        "※追加費を含めない計算上の必要純減。減額が実現できることを示さない。"
        "川口町は共益費未記載につき未算入。共益費なしの確認が取れた扱いにはしない。",
        size=9,
    )
    frozen = data["frozen_basis"]
    y = paragraph(
        fig,
        18,
        y,
        f"共通条件：直接工事 {man(frozen['direct_yen'])}万円、元請経費10%、予備費15%、"
        f"消費税10%。設計/調査/開業準備 {man(frozen['soft_yen'])}万円、"
        "開業前の支払賃料5か月、売上相殺なしの運転資金3か月。"
        "家賃以外の月次支出は⑥を継承し、立地別の集客・運用差は未反映。",
        size=9,
    )
    table(
        fig,
        y - 2,
        [80, 304],
        ["確認の順序", "費用以外の判断条件"],
        [
            [
                "最初に用途・工事承諾",
                "全件サウナ用途未確認。飲食可・業態相談・検済ありを浴場許可済みと解釈しない。",
            ],
            [
                "次に断面と支持",
                "深い槽は仮の床下1.31mが必要。梁・基礎・既存地下階・排水高さが分かるまで掘削可能としない。",
            ],
            [
                "最後に費用を置換",
                "既存機器の能力/劣化/適合と撤去・修理を確認し、工種単位の純減にする。未算入追加費と相殺して再判定。",
            ],
        ],
        size=8.5,
        min_height=15,
    )
    save(fig, "P-001", pdf, pages)


def candidate_page(data, candidate, index, pdf, pages):
    fig = page(index, candidate["id"] + "  " + candidate["name"])
    tx(fig, 18, 242, f"{candidate['area_m2']:.2f}㎡ / {candidate['floor']}", 13, ACCENT)
    tx(fig, 402, 242, "判定：資料不足", 11, MUTED, ha="right")
    facts = [
        ["所在地・交通", candidate["address"] + "\n" + candidate["access"]],
        ["構造・築年", candidate["structure_age"]],
        ["掲載家賃", candidate["rent_published"]],
        ["掲載共益費", candidate["common_published"]],
        ["保証金・償却", f"{candidate['deposit_months']}か月 / " + candidate["deposit_writeoff"]],
        ["礼金", candidate["key_published"]],
        ["契約・引渡", candidate["lease"] + "\n" + candidate["condition"]],
        [
            "掲載日付",
            f"公開：{candidate['listing_date'] or '記載なし'} / 次回予定：{candidate['next_update'] or '記載なし'}",
        ],
    ]
    left_end = table(
        fig, 229, [38, 150], ["掲載条件", "公表事項と未確認点"], facts, size=8.2, min_height=10.6
    )
    y = 226
    for heading, text in [
        ("掲載状態", candidate["availability"]),
        ("用途・営業時間の制限", candidate["restrictions"]),
        ("再利用の記載", candidate["reuse_listed"]),
        ("再利用・成立に必要な資料", candidate["reuse_conditions"]),
        ("最初に確認すること", candidate["first_check"]),
    ]:
        tx(fig, 217, y, heading, 9.3, ACCENT)
        y = paragraph(fig, 217, y - 6, text, width=185, size=8.4, gap=4)
    table_top = min(left_end - 6, y - 2)
    if table_top < 96:
        raise ValueError(candidate["id"] + " notes leave too little room")
    rows = [
        [
            f"直接工事の純減 {man(case['saving_direct_yen'], 0)}万円",
            man(case["reference_total_yen"]),
            man(case["headroom_yen"]),
            f"{man(case['monthly_opex_reference_yen'])} / 月",
        ]
        for case in candidate["cases"]
    ]
    end = table(
        fig,
        table_top,
        [116, 90, 90, 88],
        ["比較仮定 / 未取得", "参考総額・税込", "2億円との差額※", "月次支出・参考"],
        rows,
        size=8.5,
        min_height=12,
    )
    paragraph(
        fig,
        18,
        end - 5,
        "※正数は計算上の余白、負数は不足。追加費未算入なので予算内判定ではない。"
        f"純減なしの保証金支払参考 {man(candidate['cases'][0]['deposit_paid_yen'])}万円。"
        "保証金の月数基準・返還・償却時課税は未確認。",
        size=8.0,
    )
    source_lines(fig, candidate["sources"], y=40 if len(candidate["sources"]) == 1 else 49)
    save(fig, f"P-{index:03d}", pdf, pages)


def decisions(data, pdf, pages):
    fig = page(6, "再利用の条件、保留・除外、次の確認")
    y = paragraph(
        fig,
        18,
        244,
        "既存サウナ・浴槽・ろ過冷却設備の再利用減額は4候補とも未確認。"
        "工事純減700/1,200万円を確保するには、再利用/調達の見積減から撤去・改修・修理費を引き、"
        "建物側の追加工事を加え直す。予備費15%と運転資金3か月は保持して比較した。",
        size=9,
    )
    tx(fig, 18, y, "保留：主比較に含めない", 11, ACCENT)
    y = table(
        fig,
        y - 7,
        [68, 168, 148],
        ["物件", "保留理由・掲載条件", "出典URL"],
        [[c["name"], c["area_floor"] + "\n" + c["why"], c["url"]] for c in data["holds"]],
        size=7.7,
        min_height=13,
    )
    tx(fig, 18, y - 7, "除外：成約済・規模不一致を現在の候補に数えない", 11, ACCENT)
    y = table(
        fig,
        y - 14,
        [68, 168, 148],
        ["物件", "除外理由", "出典URL"],
        [[c["name"], c["why"], c["url"]] for c in data["excluded"]],
        size=7.6,
        min_height=11,
    )
    y -= 8
    tx(fig, 18, y, "次のステップ（照会・申込・契約は未実施）", 11, ACCENT)
    y = paragraph(
        fig,
        18,
        y - 7,
        "1. 空室・募集条件と浴場用途/営業時間/工事承諾を確認。2. 平面/断面・構造・設備割当・屋外機経路を入手。"
        "3. 280㎡案を当て込み、既存再利用と追加工事を工種ごとに置換。4. 契約期間/原状回復を含め総資金を再計算する。",
        size=8.5,
    )
    save(fig, "P-006", pdf, pages)


def generate():
    # Re-read the parent-owned source so the booklet cannot silently use a stale cash snapshot.
    data = calculate()
    if len(data["candidates"]) != 4:
        raise ValueError("This booklet expects four primary candidates")
    for candidate in data["candidates"]:
        if (
            candidate["bath_use_permission"] != "未確認"
            or candidate["verified_reuse_saving_yen"] is not None
        ):
            raise ValueError("Revisit the booklet before presenting changed verification status")
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "previews").mkdir(exist_ok=True)
    (DATA / "verification").mkdir(exist_ok=True)
    pages = []
    with PdfPages(DATA / "sauna_candidates_20261115.pdf") as pdf:
        overview(data, pdf, pages)
        for index, candidate in enumerate(data["candidates"], 2):
            candidate_page(data, candidate, index, pdf, pages)
        decisions(data, pdf, pages)
    (DATA / "verification" / "report_pages.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=2)
    )
    print(
        json.dumps(
            {
                "pages": len(pages),
                "candidate_count": len(data["candidates"]),
                "all_permissions_unverified": True,
                "gpu_used": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    generate()
