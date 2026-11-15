"""A3 architectural study sheets. Physical axes preserve the stated print scale.

Run from scripts: python -B -m basic_design.report
"""

import csv
import json
import math
import unicodedata

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Polygon, Rectangle

from .analysis import calculate
from .audit import DATA, ML, ROOT, WL, dump, write_csv
from .compliance import classify
from .plans import (
    BLUE,
    GREEN,
    INK,
    LINE,
    MUTED,
    PAPER,
    RED,
    WOOD,
    alarm_points,
    dim,
    draw_plan,
    export_dxf,
    label,
    plan_axes,
    rect,
)

SHEETS = []


def new_page(code, title, subtitle="建築基本計画 / 物件未定の条件比較 / 2026-11-15"):
    fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4), facecolor=PAPER)
    fig._paper_mm = (420, 297)
    tx(fig, 18, 279, code, 14, color=GREEN)
    tx(fig, 56, 279, title, 21)
    tx(fig, 18, 264, subtitle, 8.5, color=MUTED)
    fig.add_artist(plt.Line2D([18 / 420, 402 / 420], [257 / 297, 257 / 297], color=LINE, lw=0.6))
    tx(
        fig,
        18,
        12,
        "検討図・施工指示に使用しない / 構造・法適合・メーカー承認は未確認 / 全図はFL=0を仮基準",
        7,
        color=MUTED,
    )
    tx(fig, 400, 12, f"{len(SHEETS) + 1:02d}", 8, ha="right", color=MUTED)
    return fig


def tx(fig, x, y, text, size=9, color=INK, ha="left", va="center", **kwargs):
    w, h = fig._paper_mm
    return fig.text(x / w, y / h, str(text), fontsize=size, color=color, ha=ha, va=va, **kwargs)


def wrap(s, units):
    rows = []
    row = ""
    n = 0
    for c in str(s):
        if c == "\n":
            rows.append(row)
            row = ""
            n = 0
            continue
        k = 1 if unicodedata.east_asian_width(c) in "WFA" else 0.55
        if n + k > units and row:
            rows.append(row)
            row = ""
            n = 0
        row += c
        n += k
    rows.append(row)
    return rows


def paragraph(fig, x, y, text, width=380, size=9.2, color=INK):
    lines = wrap(text, width / (size / 2.83465) * 0.96)
    for row in lines:
        tx(fig, x, y, row, size, color=color)
        y -= size / 2.83465 * 1.48
    return y - 3


def table(fig, x, y, widths, headers, rows, size=8.1, row_min=10):
    pw, ph = fig._paper_mm

    def one(values, top, header):
        blocks = [wrap(v, w / (size / 2.83465) * 0.92) for v, w in zip(values, widths)]
        height = max(row_min, max(map(len, blocks)) * size / 2.83465 * 1.25 + 4)
        if top - height < 24:
            raise ValueError(f"Table overflow on {headers[0]} at {top - height:.1f}mm")
        xx = x
        for i, (w, lines) in enumerate(zip(widths, blocks)):
            fig.add_artist(
                Rectangle(
                    (xx / pw, (top - height) / ph),
                    w / pw,
                    height / ph,
                    facecolor=INK if header else ("#ede8dd" if one.idx % 2 == 0 else PAPER),
                    edgecolor=LINE,
                    lw=0.25,
                    transform=fig.transFigure,
                )
            )
            for j, line in enumerate(lines):
                tx(
                    fig,
                    xx + 2,
                    top - 3 - size / 2.83465 * 0.5 - j * size / 2.83465 * 1.25,
                    line,
                    size,
                    color=PAPER if header else INK,
                )
            xx += w
        one.idx += 1
        return top - height

    one.idx = 0
    y = one(headers, y, True)
    for r in rows:
        y = one([str(v) for v in r], y, False)
    return y


def save(fig, code, pdf, scale=None):
    fig.savefig(DATA / "drawings" / f"{code}.png", dpi=180, facecolor=PAPER)
    fig.savefig(DATA / "drawings" / f"{code}.svg", facecolor=PAPER)
    pdf.savefig(fig, facecolor=PAPER)
    SHEETS.append(
        {"code": code, "size_mm": [420, 297], "title": fig.texts[1].get_text(), "scale": scale}
    )
    plt.close(fig)


def overview(pdf, b, r, p, plan):
    fig = new_page("B-001", "検討の結論と、まだ決めていないこと")
    tx(fig, 18, 241, "V8の体験を維持しながら、建物へ納めるための条件を整理した。", 16)
    rows = [
        ["床下型", "深い槽の下に仮1.31mの空間が必要。既存ピット・地上階等を検討する条件。"],
        ["床上げ型", "デッキ+1.31m、梁下3mの仮条件で頭上1.34m。現V8の平面と高さでは採用困難。"],
        ["併用型", "床下0.70m＋デッキ0.61m、頭上2.04m。階段と踊り場の専用区画も必要。"],
        [
            "設備帯",
            "浴室主ダクトの仮包絡0.35m。仮の梁下3mでは浴室天井2.65mで比較。交差部は未解決。",
        ],
        ["水風呂", "10℃/16℃はユーザー承認の計算仮条件。4時間冷却＋維持余裕で約19.7/6.3kWの冷熱。"],
        ["人の集中", "休憩24か所。40人全員が休む場面は16人不足。水風呂前の待機場所は未確保。"],
        ["更衣・下足", "更衣48区画。元モデル下足20区画→40区画案を提示。WC個室の扉も検討図へ追加。"],
        ["判定の範囲", "計算・図面の整合を確認した基本計画。物件・機器・構造・管轄条件は未確定。"],
    ]
    table(fig, 18, 225, [40, 344], ["対象", "今回分かったこと"], rows, size=9, row_min=18)
    paragraph(
        fig,
        18,
        54,
        "今回の実行範囲は①前提整理〜⑤要件照合。費用試算と物件候補の選定・最終内装3D統合は次段階。既存V8は凍結し、断面検討用の別3Dを付属する。",
        size=9,
    )
    save(fig, "B-001", pdf)
    fig = new_page("B-002", "基準表・仮定・未確定情報")
    table(
        fig,
        18,
        246,
        [43, 58, 95, 188],
        ["区分", "条件", "状態", "扱い"],
        [
            ["施設", "東京・男性専用・1系統", "ユーザー指定", "所在地・階・建物は未定"],
            ["計画人数", "館内40／イベント約20", "計画条件", "営業定員・避難人数の承認ではない"],
            ["面積", "20×14m＝280㎡", "区画外形", "柱・設備シャフト・実際の壁厚への適合は未確認"],
            [
                "サ室",
                "主66.21／セルフ25.76／ドライ21.83m³",
                "仕上内法から算出",
                "ベンチ体積を引かず、気積として比較",
            ],
            ["温度", "主90／セルフ85／ドライ100℃", "計画仮定", "温度分布や到達性能は未検証"],
            ["水温", "深10／座16／炭酸37℃", "10/16は承認済の仮条件", "炭酸37℃は作成側の仮定"],
            [
                "営業時間等",
                "16h/日・200人/日",
                "計画仮定",
                "日量は150/200/300人の条件比較。来客予測ではない",
            ],
            ["給湯", "原水15／混合40／貯湯60℃", "計画仮定", "原水5/15/25℃、同時3/6組を比較"],
            ["浴室環境", "28℃・60%RH", "計画仮定", "夏32℃70%RH、冬5℃50%RHは感度条件"],
            [
                "建物断面",
                "仮梁下3.00／スラブ上端-0.20m",
                "現地値なし",
                "既存3Dの高さを実物件の測定値として扱わない",
            ],
            [
                "資料",
                "入力CSV・数量JSON・根拠12件",
                "追跡可能",
                "管轄別・メーカー別に未取得情報を残す",
            ],
        ],
        size=8.7,
        row_min=15,
    )
    paragraph(
        fig,
        18,
        51,
        "物件待ち：所在地・現況用途・検査済証・構造図・梁/柱/床下・受電・給水/排水の接続高さ・排気/排熱経路・貸主工事条件。メーカー待ち：施工図、離隔、能力表、保守・交換条件。",
        size=9,
    )
    save(fig, "B-002", pdf)


def plan_sheets(pdf, b, r, p, plan):
    fig = new_page(
        "A-101", "全体平面図  1/100", "A3を100%印刷 / 濡れた領域と着衣・裏方を区別 / V8基準の配置"
    )
    ax = plan_axes(fig, 18, 66, (-0.6, -0.6, 20.6, 14.6), 100)
    draw_plan(ax, plan)
    dim(ax, (0, 14), (20, 14), 0.35, "20,000 mm")
    dim(ax, (0, 0), (0, 14), -0.35, "14,000 mm", True)
    rows = [[q["name"], f"{q['zone_area_m2']:.2f}"] for q in b["rooms"]]
    table(fig, 242, 245, [124, 36], ["ゾーン外形面積", "㎡"], rows, size=8.3, row_min=9.6)
    paragraph(
        fig,
        18,
        46,
        "休憩24＝休憩室15＋離れ4＋予備3＋造り付け2。図は区画と外形包絡。扉金物、柱、シャフト、避難の屋外接続は未確定。",
        width=214,
        size=8.3,
    )
    save(fig, "A-101", pdf, "1/100")
    fig = new_page("A-111", "浴室と休憩の離れ  1/50")
    ax = plan_axes(fig, 18, 126, (5.7, 6.2, 17.3, 11.3), 50)
    draw_plan(ax, plan, names=False)
    for pid in ["deep", "seated"]:
        q = next(x for x in b["pools"] if x["id"] == pid)
        x, y, w, h = q["rect"]
        dim(ax, (x, y), (x + w, y), -0.23, f"{w * 1000:.0f}")
        dim(ax, (x + w, y), (x + w, y + h), 0.17, "1,900", True)
        label(ax, x + w / 2, y + 0.82, ("深10℃" if pid == "deep" else "座16℃") + "\n仮条件", 7)
    c = b["clearances"]
    table(
        fig,
        265,
        245,
        [85, 50],
        ["通路/部位", "実測/基準"],
        [
            ["水風呂北側", f"{c['walkway_north_of_pools']:.3f}m"],
            ["予備席の足先まで", "1.020m"],
            ["休憩扉前", "0.840m"],
            ["離れ内", "0.928m"],
            ["離れ入口", "0.790m"],
            ["深い槽階段", "手すり内0.700m"],
            ["座る槽階段", "0.600m"],
            ["階段下", "静止人数に算入しない"],
        ],
        size=8.0,
        row_min=12,
    )
    paragraph(
        fig,
        18,
        111,
        "青い数値は現モデルの内部踏面レベル。深い槽の蹴上げ0.252m、座る槽0.220mは、法適合・使いやすさを確認した寸法ではない。",
        width=232,
        size=8.5,
    )
    table(
        fig,
        18,
        88,
        [57, 72, 105, 150],
        ["槽", "水面㎡", "水量m³（階段控除前→後）", "読み方"],
        [
            ["深い槽", "3.382", "4.058 → 3.508", "既知の階段形状だけ控除"],
            ["座る槽", "3.040", "1.824 → 1.713", "人体・手すり・細部は未控除"],
            ["炭酸泉", "7.260", "4.356 → 未計算", "循環・熱計算は大きめの控除前を使用"],
        ],
        size=8.4,
        row_min=12,
    )
    save(fig, "A-111", pdf, "1/50")
    fig = new_page("A-112", "3サ室の拡大平面  1/50")
    ax = plan_axes(fig, 18, 121, (-0.2, 8.7, 12.8, 14.2), 50)
    draw_plan(ax, plan, names=False)
    for x0, x1 in [(0, 6), (6, 9.5), (9.5, 12.5)]:
        dim(ax, (x0, 14), (x1, 14), 0.12, f"{(x1 - x0) * 1000:.0f}")
    table(
        fig,
        290,
        245,
        [45, 66],
        ["室", "寸法/位置数"],
        [
            ["メイン", "内法5.776×4.776m / 20位置"],
            ["セルフ", "3.276×3.276m / 6位置"],
            ["ドライ", "2.776×3.276m / 4位置"],
            ["天井", "3室とも2.40m"],
            ["サ室扉", "開口1.00m・框内約0.90m"],
        ],
        size=8.1,
        row_min=18,
    )
    paragraph(
        fig,
        18,
        103,
        "ZL-300の外形は880×510×710mm。元の木柵との最短約171mmは幾何値で、メーカーが認めた離隔ではない。熱源周囲・上方・保守空間の条件が確定すると、柵と通路を修正する可能性がある。",
        size=9,
    )
    paragraph(
        fig,
        18,
        75,
        "メインの20位置＝脚を下ろす18＋角で足を上げる2。14位置は直接アクセス、6位置は他の利用者の協力が必要。中央ストーブで実演床が分かれ、現在の配置ではタオルを水平に大きく一周させる動きが制限される。",
        size=9,
    )
    save(fig, "A-112", pdf, "1/50")
    fig = new_page("A-113", "受付・更衣・WC  1/50  改善の検討案")
    ax = plan_axes(fig, 18, 142, (-0.2, -0.3, 17.3, 3.9), 50)
    draw_plan(ax, plan, front_proposal=True)
    dim(ax, (4, 0), (11.5, 0), -0.18, "更衣 7,500")
    dim(ax, (0, 3.6), (4, 3.6), 0.13, "受付 4,000")
    table(
        fig,
        18,
        125,
        [57, 83, 244],
        ["項目", "V8の元モデル", "今回の検討案/残る条件"],
        [
            [
                "下足",
                "西側5列×4段＝20区画",
                "北側5列×4段＝20区画を追加し計40。受付カウンターを2.20→1.70mへ短縮する仮案。",
            ],
            [
                "更衣",
                "北20列＋南4列、各2段＝48区画",
                "計画40人に対する区画数はある。扉を開いた時、入替時の利用、荷物、清掃域を実寸で確認する必要がある。",
            ],
            [
                "WC",
                "便器2・洗面2。個室の入口が未実装",
                "緑の破線と円弧が入口を追加する案。便器・扉の使用域、アクセシビリティは未確定で、この割付を承認済みとしない。",
            ],
            [
                "浴室導入",
                "更衣の北東開口から洗い場へ",
                "着衣待合から浴室が直接見えない条件と、スタッフ・利用者の交差を確認する。",
            ],
            [
                "扉寸法",
                "框幅50mm×両側、扉高2.05m",
                "框内幅＝図の開口長-0.10m。扉厚・取手・開放角を含む実際の有効幅とは別。",
            ],
        ],
        size=8.5,
        row_min=14,
    )
    save(fig, "A-113", pdf, "1/50")


def section_sheets(pdf, b, r, p):
    for index, s in enumerate(r["sections"], 1):
        code = f"A-20{index}"
        fig = new_page(
            code,
            f"{s['name']}  断面 1/20",
            "深い水風呂の階段を通る断面 / 水深1.20mは全案共通 / 躯体は仮の比較線",
        )
        ax = plan_axes(fig, 13, 15, (-0.30, -1.60, 5.20, 3.19), 20)
        z = s["deck_z_m"]
        water = s["water_z_m"]
        floor = s["bottom_z_m"]
        outer = s["assembly_bottom_z_m"]
        ceiling = p["soffit_z"] - p["service_depth"]
        rect(ax, -0.3, -1.6, 5.5, 1.4, "#e5e2dc", "none", 0)
        ax.plot([-0.3, 5.2], [p["slab_top_z"]] * 2, color=RED, lw=1.2, ls="--")
        rect(ax, 0, outer, 1.9, p["pool_assembly"], "#b8b4ab", INK, 0.7)
        rect(ax, -0.12, outer, 0.12, z - outer, "#b8b4ab", INK, 0.7)
        rect(ax, 1.9, outer, 0.12, z - outer, "#b8b4ab", INK, 0.7)
        rect(ax, 0, floor, 1.9, water - floor, "#b9d7e2", BLUE, 0.6)
        q = WL.pool("deep")
        for x0, y0, x1, y1, top in q["treads"]:
            y = y0 - 6.8
            rect(ax, y, floor, y1 - y0, z + top - floor, "#b8b4ab", INK, 0.5)
        ax.plot([-0.3, 0], [z, z], color=INK, lw=2)
        ax.plot([1.9, 2.2], [z, z], color=INK, lw=2)
        if s["n_risers"]:
            n = s["n_risers"]
            rise = s["riser_m"]
            run = s["stair_run_m"]
            for k in range(n - 1):
                rect(ax, 2.2 + k * 0.28, 0, 0.28, z - (k + 1) * rise, "#cbb79a", INK, 0.5)
            ax.plot([2.2 + run, 5.2], [0, 0], color=INK, lw=1)
            ax.plot([2.12, 2.2 + run], [z + 0.90, 0.90], color=GREEN, lw=1)
            ax.plot([3.588, 3.588], [0, 3.0], color=RED, lw=1, ls="--")
            label(ax, 3.66, 2.0, "既存の\nサ室側壁線", 6, color=RED)
        else:
            ax.plot([2.02, 5.2], [0, 0], color=INK, lw=1)
        ax.plot([-0.3, 5.2], [ceiling] * 2, color=GREEN, lw=1.1)
        ax.plot([-0.3, 5.2], [p["soffit_z"]] * 2, color=RED, lw=0.8, ls="--")
        rect(ax, -0.3, ceiling, 5.5, p["service_depth"], "#e3e8e0", edge="none", alpha=0.6)
        label(ax, 1.0, p["soffit_z"] - 0.1, "仮梁下 +3.000 / 設備帯0.350", 7)
        label(ax, 0.60, water - 0.25, "水面 - 底\n1,200mm", 8, color=BLUE)
        label(ax, 1.0, z + 0.16, f"デッキ FL{z:+.3f}", 7)
        label(ax, 0.68, outer - 0.05, f"支持下端 {outer:+.3f}", 7)
        dim(ax, (0, water), (0, floor), -0.20, "1,200", True)
        # Standing example at the deck. A static 1.85m box, not a movement/evacuation analysis.
        hx = 2.05
        ax.add_patch(Circle((hx, z + 1.73), 0.10, facecolor="#c98667", edgecolor=INK, lw=0.5))
        ax.plot([hx, hx], [z + 0.50, z + 1.62], color=INK, lw=2)
        ax.plot([hx - 0.13, hx + 0.13], [z, z + 0.50], color=INK, lw=2)
        label(ax, 4.4, 0.12, "既存仕上FL ±0", 6.5)
        label(ax, 4.45, p["slab_top_z"] - 0.10, "仮スラブ上 -0.200", 6, color=RED)
        table(
            fig,
            302,
            244,
            [53, 47],
            ["項目", "計算値"],
            [
                ["床下空間", f"{s['pit_depth_m']:.3f}m"],
                ["デッキ上昇", f"{z:.3f}m"],
                ["頭上", f"{s['clear_headroom_m']:.3f}m"],
                ["外階段", f"{s['n_risers']}蹴上げ"],
                ["外階段の出", f"{s['stair_run_m']:.3f}m"],
                ["階段＋踊り場", f"{s['stair_and_landing_area_m2']:.3f}㎡"],
                ["北通路への超過", f"{s['north_aisle_overrun_m']:.3f}m"],
                ["2.1m頭上に要る梁下", f"{s['required_soffit_z_for_2_1m_headroom']:.3f}m"],
            ],
            size=7.8,
            row_min=12,
        )
        yy = paragraph(fig, 302, 119, s["decision"], width=100, size=8.5)
        paragraph(
            fig,
            302,
            yy - 4,
            "底下の包絡0.25mは仮。水深だけの掘削量ではない。スラブ切断・基礎・地下水・防水・支持は未確認。外階段の0.18m/踏面0.28m/幅0.90m/踊り場0.90mは比較用仮定で、適法寸法の認定ではない。",
            width=100,
            size=7.7,
        )
        save(fig, code, pdf, "1/20")
    fig = new_page(
        "A-211",
        "座面高さと頭上の比較模式図  1/20",
        "異なる位置の席を並べた高さ比較 / 同じ切断面上の実配置ではない",
    )
    for rid, x, w in [("self", 18, 3.276), ("dry", 226, 2.776)]:
        ax = plan_axes(fig, x, 77, (-0.15, -0.15, w + 0.15, 2.85), 20)
        rect(ax, 0, 0, w, 2.4, "#eee6da", INK, 0.9)
        if rid == "self":
            ranges = [(0, 0.6, 0.45), (0.6, 1.94, 0.675), (1.94, w, 0.90)]
        else:
            ranges = [(0, 1.50, 0.45), (1.75, 2.35, 0.90)]
        for a, c, z in ranges:
            rect(ax, a, 0, c - a, z, WOOD)
            ax.add_patch(
                Circle(((a + c) / 2, z + 0.84), 0.09, facecolor="#bd896c", edgecolor=INK, lw=0.4)
            )
            ax.plot([(a + c) / 2] * 2, [z + 0.2, z + 0.74], color=INK, lw=2)
            label(ax, (a + c) / 2, 0.10, f"{z:.3f}", 6)
        dim(ax, (w, 0), (w, 2.4), 0.07, "2,400", True)
        label(
            ax,
            w / 2,
            2.65,
            "セルフの高さ3種類" if rid == "self" else "ドライ：寝座＋高い腰掛け",
            10,
        )
        label(ax, w / 2, 2.10, "最上段の頭上0.58m（高めの座高では0.52m）", 6.4)
    paragraph(
        fig,
        18,
        58,
        "0.45mの段上に身長1.85mの人が立つと頭上は0.10m。これは静止した寸法で、動作の余裕を保証しない。ベンチ前縁・手すり・熱い部位・退出時の動きは、機器施工図と利用者動作を合わせて再検討する。",
        size=9,
    )
    save(fig, "A-211", pdf, "1/20")


def operation_sheets(pdf, b, r, p, plan):
    fig = new_page("O-101", "通常・集中・満席・清掃の動線")
    panels = [
        ("通常：サ室→水風呂→休憩", r["operations"]["normal_cycle"], BLUE),
        ("イベント直後：水風呂への集中", [(6, 9.75), (8, 9.75), (12.2, 9.45)], RED),
        ("離れ満席→休憩室→予備", b["water_routes"][3]["path"], GREEN),
        (
            "清掃・保守：スタッフから機械室へ",
            [(15.5, 1.4), (17.5, 2.2), (18.5, 4), (18.5, 8.5), (18.5, 11.9), (17, 11.9)],
            MUTED,
        ),
    ]
    for (title, path, color), (x, y) in zip(panels, [(18, 147), (218, 147), (18, 42), (218, 42)]):
        tx(fig, x, y + 94, title, 10, color=color)
        ax = plan_axes(fig, x, y, (0, 0, 20, 14), 160)
        draw_plan(ax, plan, names=False)
        xx, yy = zip(*path)
        ax.plot(xx, yy, color=color, lw=2)
        ax.annotate(
            "",
            xy=path[-1],
            xytext=path[-2],
            arrowprops={"arrowstyle": "->", "color": color, "lw": 2},
        )
    save(fig, "O-101", pdf, "1/160（概念動線）")
    fig = new_page("O-102", "イベント後の集中を時間で確認する")
    table(
        fig,
        18,
        245,
        [65, 35, 55, 55, 174],
        ["到着条件", "占有秒", "待った人数", "最大待ち秒", "読み方"],
        [
            [
                q["case"],
                q["occupancy_s"],
                q["queued_people"],
                f"{q['max_wait_s']:.0f}",
                "水の中5位置の単純な待ち行列。出入り時間と温度選択は含めない。",
            ]
            for q in r["operations"]["pool_cases"]
        ],
        size=8.4,
        row_min=14,
    )
    paragraph(
        fig,
        18,
        92,
        "一斉20人・5位置・仮の占有60秒では15人が待ち、最後の入槽まで180秒になる。これは入浴時間の推奨ではない。通路や浴槽縁を待ち場所とする提案はしておらず、実際の処理能力は出入りと温度の好みを考えるとさらに変わる。",
        size=9.2,
    )
    paragraph(
        fig,
        18,
        63,
        "休憩は40人対24で16人不足。イベント20＋別の利用者17の37人場面では13人不足。休憩を増やす・イベント人数と入場を合わせる等の判断が必要で、今回は人数や希望を変更せず課題として残した。",
        size=9.2,
    )
    save(fig, "O-102", pdf)


def section_3d_sheet(pdf, r):
    fig = new_page(
        "A-204",
        "断面3案を実3Dで比較する",
        "同じ水深・同じ内部階段で比較 / 元の内装モデルを置き換える3Dではない",
    )
    for s, x in zip(r["sections"], [18, 148, 278]):
        path = DATA / "renders" / f"section_{s['id']}_3d.png"
        if not path.is_file():
            raise FileNotFoundError(path.name)
        tx(fig, x, 242, s["name"], 12)
        ax = fig.add_axes([x / 420, 137 / 297, 124 / 420, 90 / 297])
        ax.imshow(plt.imread(path))
        ax.axis("off")
    table(
        fig,
        18,
        116,
        [65, 57, 57, 70, 135],
        ["案", "床下空間m", "デッキm", "仮条件の頭上m", "結果"],
        [
            [
                s["name"],
                f"{s['pit_depth_m']:.2f}",
                f"{s['deck_z_m']:.2f}",
                f"{s['clear_headroom_m']:.2f}",
                s["decision"],
            ]
            for s in r["sections"]
        ],
        size=8.5,
        row_min=16,
    )
    paragraph(
        fig,
        18,
        43,
        "赤は仮の既存スラブ・梁下・サ室側壁の比較線、緑は天井レベル。人体は身長1.85mの静止例。浴槽外殻と支持は仮の包絡で、構造設計や耐水施工を表すモデルではない。",
        size=9,
    )
    save(fig, "A-204", pdf)


def service_plan(fig, plan, kind):
    ax = plan_axes(fig, 18, 67, (-0.4, -0.4, 20.8, 14.6), 100)
    draw_plan(ax, plan, names=False)
    if kind == "air":
        main = [(18.3, 6), (16.2, 6), (16.2, 9.8), (6.4, 9.8)]
        ax.plot(*zip(*main), color=BLUE, lw=2)
        for x, y in [(3, 11), (7.7, 12), (11, 12), (14.5, 12), (12, 5), (8, 8)]:
            ax.plot([x, 16.2], [y, y], color=BLUE, lw=0.8, ls="--")
        label(ax, 18.3, 13.4, "屋外へ\n経路未定", 7, color=RED)
        ax.annotate(
            "", (18.3, 14.6), (18.3, 6), arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.6}
        )
    elif kind == "water":
        for target in [(11.75, 7.6), (13.7, 7.6), (14.7, 12.1), (14, 4)]:
            ax.plot([18, 16.2, 16.2, target[0]], [4, 4, target[1], target[1]], color=BLUE, lw=1)
        for x in [11.3, 12.3, 13.3, 14.3, 15.3, 16.3]:
            ax.plot([x, x], [4, 3.7], color=RED, lw=1.2)
        label(ax, 18.4, 0.6, "引込/排水先\n高さ未定", 7, color=RED)
    else:
        ax.add_patch(Rectangle((14.5, 0.5), 0.6, 0.3, facecolor="#d9bd6b", edgecolor=INK))
        for target in [(3, 10.95), (8.78, 11.25), (11.9, 11.1), (18.5, 4)]:
            ax.plot(
                [14.8, 15.7, 15.7, target[0]],
                [0.8, 0.8, target[1], target[1]],
                color="#b28c35",
                lw=1.2,
            )
        points = alarm_points(plan)
        for rid in ["main", "self", "dry"]:
            x, y = points[rid]
            ax.add_patch(Circle((x, y), 0.12, facecolor=RED, edgecolor="none"))
            label(ax, x, y, "B", 4.5, color=PAPER)
        x, y = points["receiver"]
        rect(ax, x - 0.15, y - 0.15, 0.30, 0.30, RED, INK)
        label(ax, x, y, "R", 6, color=PAPER)
        for rid in ["main", "self", "dry"]:
            q = next(q for q in plan["rooms"] if q["id"] == rid)
            x, y, w, h = q["rect"]
            label(
                ax,
                x + 0.34,
                y + 0.38,
                "T",
                7,
                color=GREEN,
                bbox={"facecolor": PAPER, "edgecolor": GREEN, "pad": 0.5},
            )
    return ax


def service_sheets(pdf, b, r, p, plan):
    fig = new_page("M-101", "換気・除湿と天井内の仮経路")
    service_plan(fig, plan, "air")
    rows = [[q["room"], f"{q['flow_m3_h']:.0f}", q["ach"]] for q in r["ventilation"]]
    table(fig, 244, 245, [73, 48, 35], ["ゾーン", "m³/h", "回/h"], rows, size=8, row_min=10)
    paragraph(
        fig,
        18,
        48,
        "線は経路の予約。浴室主ダクトは内法600×250mmの比較で約3.9m/s。保温・吊り余裕込み設備帯0.35mを計上した。交差・防火ダンパー・耐熱・消音・点検域はまだ納まり未確定。",
        width=220,
        size=8.6,
    )
    save(fig, "M-101", pdf, "1/100（経路予約）")
    fig = new_page("M-102", "換気だけでは除湿できない外気条件")
    table(
        fig,
        18,
        245,
        [34, 55, 55, 60, 60, 120],
        ["季節", "外気℃/RH", "内部kg/h", "換気の持込kg/h", "要除湿kg/h", "潜熱のみkW"],
        [
            [
                q["season"],
                f"{q['outside_C']:.0f} / {q['outside_RH'] * 100:.0f}%",
                q["internal_kg_h"],
                f"{q['ventilation_added_kg_h']:.1f}",
                f"{q['dehumidification_kg_h']:.1f}",
                f"{q['latent_kw']:.1f}",
            ]
            for q in r["humidity_sensitivity"]
        ],
        size=9,
        row_min=16,
    )
    paragraph(
        fig,
        18,
        119,
        "浴室28℃60%RH、夏の仮外気32℃70%RHでは外気の絶対湿度が高く、浴室の排気を増やすだけでは除湿できない。内部の発湿4kg/hに対して約21kg/hの除湿となる一次計算。内部発湿は2/4/6kg/hの仮定で、浴槽蒸発の実測値や選定済み除湿能力ではない。",
        size=10,
    )
    paragraph(
        fig,
        18,
        83,
        "この表は絶対湿度の収支。室内空気の混合・局所結露・人体の顕熱・日射・外皮・ドア開閉・冷水面での結露等は精算していない。機械室も初期6回/h約340m³/hだけでは、仮3kWを温度差8℃で処理する約1,120m³/hに不足する。",
        size=9.2,
    )
    paragraph(
        fig,
        18,
        50,
        "サ室6回/hはHarviaの他社参考値。給排気位置・センサーとの関係は、管轄の衛生基準と採用するMETOS等の施工図で整合させる。数字だけを移植して確定しない。[S04・S02]",
        size=9.2,
    )
    save(fig, "M-102", pdf)
    fig = new_page("P-101", "給水・給湯・排水の初期容量")
    service_plan(fig, plan, "water")
    table(
        fig,
        244,
        245,
        [57, 48, 51],
        ["条件", "値", "単位"],
        [
            ["3組同時", "24", "L/min混合"],
            ["6組同時", "48", "L/min混合"],
            ["原水15→40℃・3組", "41.9", "kW熱"],
            ["同・6組", "83.7", "kW熱"],
            ["炭酸泉15→37℃・4h", f"{r['carbon_fill_4h_kw']:.1f}", "kW熱"],
            ["3組＋炭酸初期昇温", "69.7", "kW熱"],
            ["3槽同時30分排水", "20.48", "m³/h 仮"],
            ["同時排水量", "5.69", "L/s 仮"],
        ],
        size=8.0,
        row_min=14,
    )
    paragraph(
        fig,
        18,
        48,
        "給湯のピークと開店前の浴槽昇温を同時とするかで必要熱源が変わる。排水管の径・勾配・床下横引き・ポンプ要否は、排水先の高さが未定のため選定していない。給水の逆流対策も方式確認が必要。",
        width=220,
        size=8.5,
    )
    save(fig, "P-101", pdf, "1/100（経路予約）")
    fig = new_page("P-201", "3槽の循環・冷却・炭酸  検討系統図")
    for (row, pool), y in zip(enumerate(b["pools"]), [220, 152, 84]):
        rid = pool["id"]
        name = {"deep": "深い槽10℃", "seated": "座る槽16℃", "carbonPool": "炭酸泉37℃（仮）"}[rid]
        flow = next(
            q["flow_base_2_turnovers_m3_h"] for q in r["circulation"] if q["pool_id"] == rid
        )
        tx(
            fig,
            18,
            y + 19,
            f"{name} / 控除前水量{pool['gross_water_m3']:.3f}m³ / 仮2回転={flow:.2f}m³/h",
            11,
        )
        boxes = ["浴槽", "集毛", "ポンプ", "ろ過", "熱交換", "水質制御", "戻り"]
        for i, title in enumerate(boxes):
            x = 18 + i * 55
            fig.add_artist(
                Rectangle(
                    (x / 420, (y - 14) / 297),
                    45 / 420,
                    22 / 297,
                    facecolor="#e5e9e3",
                    edgecolor=INK,
                    lw=0.6,
                    transform=fig.transFigure,
                )
            )
            tx(fig, x + 22.5, y - 3, title, 9, ha="center")
            if i < 6:
                tx(fig, x + 50, y - 3, "→", 12, ha="center", color=BLUE)
        caption = (
            "冷却熱源は屋外側。配管損失・揚程・逆洗条件は未計算。"
            if rid != "carbonPool"
            else "炭酸の添加区間/消毒の接触区間は機器メーカーと確定。容器・検知・局所換気を別途計画。"
        )
        paragraph(fig, 18, y - 28, caption, size=8.8)
    paragraph(
        fig,
        18,
        36,
        "各槽を独立した水系として仮計画。水質制御の注入位置・接触時間・配管順序は確定施工図ではない。溢水は循環戻りへ直結せず排水の仮計画。ろ過の根拠と地方基準は[S02・S03]を照合。",
        size=8.5,
    )
    save(fig, "P-201", pdf)
    fig = new_page("P-202", "冷却・循環と給水日量の感度")
    table(
        fig,
        18,
        245,
        [51, 45, 45, 50, 50, 143],
        ["槽", "冷却時間h", "初期冷却kW", "維持余裕kW", "冷熱計kW", "条件"],
        [
            [
                q["pool_id"],
                q["cooldown_h"],
                f"{q['pull_down_kw']:.1f}",
                q["maintenance_allowance_kw"],
                f"{q['cooling_kw']:.1f}",
                "25℃充填から。水量は階段控除前、維持負荷は仮定。",
            ]
            for q in r["pool_cooling"]
        ],
        size=8.3,
        row_min=12,
    )
    y = table(
        fig,
        18,
        137,
        [51, 65, 65, 65, 138],
        ["来客人/日", "シャワーm³", "槽充填m³", "補給/逆洗m³", "日量計m³（トイレ等除く）"],
        [
            [
                q["visitors"],
                f"{q['shower_m3']:.1f}",
                f"{q['assumed_full_pool_fill_m3']:.2f}",
                f"{q['makeup_allowance_m3'] + q['backwash_allowance_m3']:.1f}",
                f"{q['daily_total_m3']:.2f}",
            ]
            for q in r["daily_water"]
        ],
        size=8.5,
        row_min=12,
    )
    paragraph(
        fig,
        18,
        y - 12,
        "循環の比較流量：深8.12、座3.65、炭酸8.71m³/h。2回/hは計画仮定で、実ポンプは揚程と能力曲線から選定する。日量は全槽1日1回充填・補給20L/人・逆洗1m³/日を仮定し、衛生運用の確定値ではない。",
        size=8.8,
    )
    save(fig, "P-202", pdf)
    fig = new_page("E-101", "熱源・受電容量と非常呼出の予約")
    service_plan(fig, plan, "electric")
    power = {q["case"]: q for q in r["electrical_cases"] if q["heater_basis"] == "thermal_envelope"}
    table(
        fig,
        244,
        245,
        [57, 48, 51],
        ["部位", "計算値", "条件/型式"],
        [
            [q["room"], f"{q['base']['suggested_evaluation_kw']:.1f} kW", "2h昇温＋定常"]
            for q in r["sauna_heat"]
        ]
        + [
            ["主室候補", "24.8 kW", "ZL-300・未適合確認"],
            ["ガス給湯側受電", f"{power['gas']['planning_kva_with_reserve']:.0f} kVA", "仮余裕込"],
            [
                "HP通常受電",
                f"{power['HP-normal']['planning_kva_with_reserve']:.0f} kVA",
                "仮余裕込",
            ],
            [
                "HP冬期6組＋昇温",
                f"{power['HP-winter6']['planning_kva_with_reserve']:.0f} kVA",
                "厳しい仮条件",
            ],
        ],
        size=8,
        row_min=16,
    )
    paragraph(
        fig,
        18,
        48,
        "赤丸Bは各サ室内の呼出点候補、赤四角Rは受付受信点、緑Tは室温表示用温度計の候補。感温部位置と耐熱/防水・停電時・受信/駆けつけは要確認。受電は計画負荷の比較で契約容量ではない。詳細E-103。",
        width=220,
        size=8.5,
    )
    save(fig, "E-101", pdf, "1/100（経路予約）")
    fig = new_page("E-102", "サ室の熱収支と昇温時間")
    rows = []
    for s in r["sauna_heat"]:
        for q in s["sensitivity"]:
            rows.append(
                [
                    s["room"],
                    q["ach"],
                    q["warmup_h"],
                    f"{q['steady_kw']:.1f}",
                    f"{q['warmup_storage_kw']:.1f}",
                    f"{q['suggested_evaluation_kw']:.1f}",
                ]
            )
    table(
        fig,
        18,
        245,
        [59, 45, 45, 75, 75, 85],
        ["室", "換気回/h", "昇温h", "定常kW", "熱容量分kW", "合計の比較kW"],
        rows,
        size=8.1,
        row_min=8.5,
    )
    paragraph(
        fig,
        18,
        62,
        "定常＝換気＋外皮＋扉余裕＋ロウリュ蒸発。昇温は仮の木部質量・石量と平均温度変化から算出。0.335の換気係数は標準空気の近似で、高温密度・排気温度等は精算していない。熱橋、蓄熱、ガラス、実際の水量と扉開閉は大きな不確かさ。",
        size=8.6,
    )
    paragraph(
        fig,
        18,
        36,
        "主室66.21m³にZL-300一台で足りるという判定は行わない。計算の仮定とメーカーの施工・能力条件を合わせ、昇温時間と利用負荷を決めて型式・台数を選定する。[S05]",
        size=8.6,
    )
    save(fig, "E-102", pdf)


def plant_sheet(pdf, b, r, p, plan):
    fig = new_page("M-201", "機械室の仮配置と屋外排熱スペース")
    ax = plan_axes(fig, 25, 55, (16.7, -0.3, 20.3, 7.3), 40)
    rect(ax, 17, 0, 3, 7, "#ece7dd", INK, 1)
    for rid, y, diam in [
        ("F-deep", 3.25, 0.70),
        ("F-seated", 4.30, 0.60),
        ("F-carbon", 5.35, 0.70),
    ]:
        ax.add_patch(Circle((17.55, y), diam / 2, facecolor="#b9d7e2", edgecolor=INK, lw=0.7))
        label(ax, 17.55, y, rid, 6.5)
    for y in [3.25, 4.30, 5.35]:
        rect(ax, 19.15, y - 0.25, 0.60, 0.50, "#c4d1c2", INK)
        label(ax, 19.45, y, "P/HX", 6)
    rect(ax, 17.12, 0.25, 0.8, 0.9, "#d8c9b8", RED)
    label(ax, 17.52, 0.7, "薬注\n別区画案", 6.5)
    rect(ax, 19.15, 0.25, 0.7, 0.9, "#d8c9b8", RED)
    label(ax, 19.5, 0.7, "CO2\n別区画案", 6.5)
    rect(ax, 19.15, 1.5, 0.65, 1.2, "#d1b89b", INK)
    label(ax, 19.47, 2.1, "熱源\n比較枠", 6.5)
    ax.add_patch(Circle((18.7, 6.35), 0.5, facecolor="#d1b89b", edgecolor=INK, lw=0.7))
    label(ax, 18.7, 6.35, "蓄熱", 7)
    rect(ax, 17, 1.8, 0.18, 0.9, PAPER, "none")
    ax.annotate(
        "", (18.55, 2.25), (16.8, 2.25), arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.5}
    )
    rect(ax, 18.0, 2.8, 1.0, 2.95, "none", GREEN, 1, ls="--")
    label(ax, 18.5, 4.2, "点検・通路\n仮1.00m", 7, color=GREEN)
    dim(ax, (17, 7), (20, 7), 0.1, "3,000")
    dim(ax, (17, 0), (17, 7), -0.15, "7,000", True)
    rows = [
        ["F-deep", "0.70×0.70×1.40", "計画包絡"],
        ["F-seated", "0.60×0.60×1.30", "計画包絡"],
        ["F-carbon", "0.70×0.70×1.40", "計画包絡"],
        ["循環P/HX", "3組の予約", "実寸と揚程未定"],
        ["蓄熱槽", "径1.0×高さ2.1", "扉框内0.80に対し0.20m不足"],
        ["CO2/薬注", "互いに分離する枠", "保管・検知・換気未確定"],
        ["冷却機", "屋外1.6×0.8＋1.2×0.7", "機種/保守/吸排気が別途必要"],
    ]
    table(fig, 145, 245, [60, 103, 94], ["部位", "仮寸法m", "扱い"], rows, size=8.8, row_min=15)
    reject = sum(q["heat_rejection_kw"] for q in r["pool_cooling"] if q["cooldown_h"] == 4)
    paragraph(
        fig,
        145,
        112,
        f"冷却系の4hケースは冷熱約26kW、COP3の仮条件で屋外へ約{reject:.1f}kWを放熱する。冷却機本体を室内の機械室へ置けるという意味ではない。外部への経路と保守用空間が別途必要。",
        width=257,
        size=9.3,
    )
    paragraph(
        fig,
        145,
        77,
        "仮の蓄熱槽径1.00mは、機械室扉開口0.90m・框内0.80mを一体で通れず0.20m不足。分割搬入可能な機種・開口変更・別の交換経路のいずれかが必要。枠はメーカー図ではなく、点検・配管・排水・騒音・換気も未確定。",
        width=257,
        size=9,
    )
    save(fig, "M-201", pdf, "1/40（仮包絡）")


def requirements_sheets(pdf):
    rules = list(csv.DictReader((ROOT / "plan/basic_design/rules.csv").open(encoding="utf-8-sig")))
    for row in rules:
        row["result"] = (
            "計画上の課題・未解決"
            if row["jurisdiction"] == "計画"
            else "メーカー/管轄資料待ち"
            if row["jurisdiction"] in ("メーカー", "管轄/メーカー", "計画/管轄", "全国/メーカー")
            else classify(row["jurisdiction"], None, None)
        )
    write_csv(DATA / "tables/requirements_register.csv", rules)
    for n in range(0, len(rules), 10):
        fig = new_page(
            f"R-30{n // 10 + 1}",
            "要件照合と未確定事項",
            "所在地未定のため適法・許可・メーカー承認を意味する「合格」は付けない",
        )
        table(
            fig,
            18,
            245,
            [15, 52, 29, 51, 127, 110],
            ["ID", "論点", "根拠", "管轄", "照合結果", "必要資料/次の確認"],
            [
                [
                    q["id"],
                    q["topic"],
                    q["source_id"],
                    q["jurisdiction"],
                    q["existing_evidence"] + " / " + q["assessment"],
                    q["needed"],
                ]
                for q in rules[n : n + 10]
            ],
            size=8.0,
            row_min=17,
        )
        paragraph(
            fig,
            18,
            48,
            "法令・条例、行政の指導資料、メーカー条件、計画上の仮定を区別。内部確認・呼出・扉等に関する港区の2026年10月改正を、他区に自動適用しない。全ての項目はCSVから追跡できる。",
            size=9,
        )
        save(fig, f"R-30{n // 10 + 1}", pdf)
    fig = new_page("R-401", "一次資料と確認日")
    sources = json.loads((ROOT / "plan/basic_design/sources.json").read_text())
    table(
        fig,
        18,
        245,
        [18, 85, 58, 223],
        ["ID", "資料", "管轄/時期", "URL"],
        [
            [q["id"], q["title"], q["jurisdiction"] + " / " + q["effective"], q["url"]]
            for q in sources
        ],
        size=7.4,
        row_min=14,
    )
    paragraph(
        fig,
        18,
        43,
        "全件の確認日：2026-11-15。公式ページの記載は資料として確認したもので、当施設の設計承認ではない。旧消防審査PDFは404だったため根拠に使わず、現行例規と公開届出様式へ切り替えた。V8は保存済みのモデル・検証記録を内部資料として参照。",
        size=8.4,
    )
    save(fig, "R-401", pdf)
    return rules


def access_and_performance_sheets(pdf, b, r, p, plan):
    fig = new_page("A-115", "床上げ案：外階段と踊り場の平面占有  1/50")
    for s, x in zip([q for q in r["sections"] if q["n_risers"]], [22, 220]):
        tx(fig, x, 243, s["name"], 13)
        ax = plan_axes(fig, x, 110, (9.3, 6.2, 15.4, 12.0), 50)
        draw_plan(ax, plan, names=False, step_level_labels=False)
        q = s["external_access_plan"]
        a, y, c, d = q["stair_xyxy"]
        rect(ax, a, y, c - a, d - y, "#e7c4ba", RED, 1, alpha=0.8)
        for k in range(max(0, s["n_risers"] - 1)):
            ax.plot([a, c], [y + k * 0.28] * 2, color=RED, lw=0.7)
        a, y, c, d = q["landing_xyxy"]
        rect(ax, a, y, c - a, d - y, "#bfd4c2", GREEN, 1, alpha=0.9)
        label(ax, (a + c) / 2, (y + d) / 2, "下踊り場\n0.90×0.90m", 5.7)
        ax.plot([9.3, 15.4], [10.388] * 2, color=RED, ls="--", lw=0.8)
        label(ax, 14.1, 10.66, "北側仕上壁の線", 6, color=RED)
        dim(ax, (c, 9), (c, d), 0.22, f"全長{(d - 9):.3f}m", True)
        tx(fig, x, 98, f"北壁線を{s['north_aisle_overrun_m']:.3f}m超える", 11, color=RED)
    paragraph(
        fig,
        18,
        77,
        "赤：外階段、緑：下踊り場。北通路1.388mに置くと、どちらも既存のサ室側壁の線へ入る。階段自体が東西の浴室内動線を遮るため、壁の超過だけ解消しても、そのまま採用することはできない。",
        size=9.3,
    )
    paragraph(
        fig,
        18,
        49,
        "比較の向きは深い槽の北側。東側への移設や浴室全体の床上げは別の間取り変更を要する。席を無断で減らす案には進めず、専用階段区画・階高・床下空間の条件として残した。",
        size=9.3,
    )
    save(fig, "A-115", pdf, "1/50")
    fig = new_page("A-116", "メイン：着席中の足と演者の動作範囲  1/40")
    ax = plan_axes(fig, 18, 76, (-0.1, 8.2, 6.2, 14.1), 40)
    draw_plan(ax, plan, names=False)
    for seat in ML.seats():
        for part, x0, y0, x1, y1, z0, z1 in ML.body_boxes(seat):
            if part in ("feet", "legs"):
                rect(ax, x0, y0, x1 - x0, y1 - y0, "#bb8165", RED, 0.5, alpha=0.7)
    octagon = [
        (3 + 0.75 * math.cos(k * math.pi / 4), 10.95 + 0.75 * math.sin(k * math.pi / 4))
        for k in range(8)
    ]
    ax.add_patch(Polygon(octagon, facecolor="none", edgecolor=RED, lw=0.9))
    c = (1.65, 9.75)
    ax.add_patch(Circle(c, 1.30, facecolor="none", edgecolor=RED, lw=1.2, ls="--"))
    ax.add_patch(Circle(c, 0.60, facecolor="none", edgecolor=GREEN, lw=1.1))
    rect(ax, c[0] - 0.30, c[1] - 0.30, 0.60, 0.60, "#c5d5c7", GREEN, 0.7)
    label(ax, 3, 13.65, "着席20の足・脚の包絡", 6.5)
    label(ax, 3.9, 9.55, "中央ストーブ\n機器離隔は未確認", 6.5, color=RED)
    table(
        fig,
        201,
        245,
        [56, 145],
        ["比較", "結果"],
        [
            ["演者の体", "仮0.60×0.60m。移動する体の確認ではない。"],
            ["大きな円R1.30", "腕0.65＋タオル0.65mという既存の仮定。例示位置では南壁を越える。"],
            ["小さな円R0.60", "動作を限定する比較用。実際に演技できるという確認ではない。"],
            ["座っている人", "脚を下ろす18＋角で足を上げる2。足先を通路に含めない。"],
            [
                "ストーブと木柵",
                "八角の柵は現形状。矩形ZL-300の角から木まで最短約0.171mは安全離隔値ではない。",
            ],
            [
                "判断が必要",
                "中央配置・約20人・大きなタオル動作の全てを、現平面で満たしたとは言えない。",
            ],
        ],
        size=8.6,
        row_min=19,
    )
    paragraph(
        fig,
        201,
        92,
        "今回の対応は制限を見える形にすること。機器・ガードの正式条件と演者の確認を得た後、演技内容・イベント人数・配置のどれを調整するか判断する。希望した中央配置はこの検討で変更していない。",
        width=201,
        size=9,
    )
    save(fig, "A-116", pdf, "1/40")


def mass_sheet(pdf, r):
    fig = new_page("A-205", "浴槽の質量と支持条件の概算")
    table(
        fig,
        18,
        245,
        [45, 58, 58, 63, 55, 50, 55],
        ["槽", "水・控除前t", "水・階段控除後t", "仮RC外殻t", "仮仕上t", "仮人数分t", "合計目安t"],
        [
            [
                q["pool_id"],
                f"{q['water_gross_kg'] / 1000:.2f}",
                "-"
                if q["water_less_known_steps_kg"] is None
                else f"{q['water_less_known_steps_kg'] / 1000:.2f}",
                f"{q['hypothetical_RC_shell_kg'] / 1000:.2f}",
                f"{q['finish_allowance_kg'] / 1000:.2f}",
                f"{q['people_allowance_kg'] / 1000:.2f}",
                f"{q['gross_mass_inventory_kg'] / 1000:.2f}",
            ]
            for q in r["mass_inventory"]
        ],
        size=8.8,
        row_min=18,
    )
    paragraph(
        fig,
        18,
        149,
        "水は1,000kg/m³の近似。合計は大きめの水量（階段控除前）＋仮RC外殻（底150mm・壁120mmの量の目安）＋仕上20mm＋人90kg/人の単純な質量棚卸し。浴槽の形式・部材寸法を決めたものではなく、階段・支持脚・基礎の質量も未計上。",
        size=10,
    )
    paragraph(
        fig,
        18,
        108,
        "水深1.20mに対する底部の水圧は約11.77kPa、0.60mでは約5.88kPa。水圧と、浴槽の脚・梁・スラブへ集中して伝わる荷重は別である。水面の面積で合計質量を割って「床荷重として安全」とする評価は行わない。",
        size=10,
    )
    paragraph(
        fig,
        18,
        67,
        "必要な資料：既存構造図・床と基礎の状態、支持方式、浴槽製品/施工図、掘削・スラブ変更・防水の条件。構造耐力やスラブの切断可否は未判定のまま残す。",
        size=10,
    )
    save(fig, "A-205", pdf)


def power_sheet(pdf, r):
    fig = new_page("E-103", "受電の比較条件と負荷の計上先")
    table(
        fig,
        18,
        245,
        [48, 52, 49, 48],
        ["熱源・運用条件", "ヒーター基準", "接続電力kW", "余裕込kVA"],
        [
            [
                q["case"],
                "接続候補" if q["heater_basis"] == "candidate" else "熱収支を包絡",
                f"{q['connected_electric_kw']:.1f}",
                f"{q['planning_kva_with_reserve']:.1f}",
            ]
            for q in r["electrical_cases"]
        ],
        size=8.2,
        row_min=12,
    )
    table(
        fig,
        230,
        245,
        [110, 62],
        ["補機の計上先", "接続枠kW"],
        [
            [k, f"{v:.2f}"]
            for k, v in r["electrical_connected_items_kw"].items()
            if not k.startswith("H-")
        ],
        size=8.1,
        row_min=11,
    )
    table(
        fig,
        18,
        119,
        [48, 65, 65, 19],
        ["サ室", "接続候補kW", "2h熱収支kW", "扱い"],
        [
            [k, r["electrical_connected_items_kw"][k], f"{v:.2f}", "仮"]
            for k, v in r["heater_evaluation_kw"].items()
        ],
        size=8.1,
        row_min=12,
    )
    paragraph(
        fig,
        230,
        95,
        "gas：給湯の熱はガス、補機1kW。HP-normal：原水15℃・シャワー3組＋炭酸保温。HP-startup：これに炭酸初期昇温を重ねる。HP-winter6：原水5℃・6組＋炭酸初期昇温＋保温を同時とする厳しい条件。",
        width=172,
        size=8.8,
    )
    paragraph(
        fig,
        18,
        55,
        "薬注0.5・CO2 0.3・TV等0.2kWを個別に計上。熱収支包絡側は主室・ドライの仮不足分も上乗せする。空調8kW、ポンプ等は未選定の枠で、実外皮・全館顕熱・始動・除霜・補助ヒーター等の精算は未了。力率0.9・余裕20%・COP3も仮条件のため、最大ケースも受電容量の承認値ではない。",
        size=8.8,
    )
    save(fig, "E-103", pdf)


def main():
    basis, result = calculate()
    config = json.loads((ROOT / "plan/basic_design/inputs.json").read_text())
    p = {q["id"]: q["value"] for q in config["parameters"]}
    plan = json.loads((ROOT / "plan/plan_a.json").read_text())
    with PdfPages(DATA / "drawings/sauna_architecture_v1.pdf") as pdf:
        pdf.infodict().update(
            {
                "Title": "Sauna architectural basic planning - scope 1 to 5",
                "Author": "Codex",
                "Subject": "Conditional study, not construction documents",
            }
        )
        overview(pdf, basis, result, p, plan)
        plan_sheets(pdf, basis, result, p, plan)
        access_and_performance_sheets(pdf, basis, result, p, plan)
        section_sheets(pdf, basis, result, p)
        section_3d_sheet(pdf, result)
        mass_sheet(pdf, result)
        operation_sheets(pdf, basis, result, p, plan)
        service_sheets(pdf, basis, result, p, plan)
        power_sheet(pdf, result)
        plant_sheet(pdf, basis, result, p, plan)
        rules = requirements_sheets(pdf)
    export_dxf(DATA / "drawings/A-101-control-mm.dxf", plan)
    dump(DATA / "verification/sheets.json", SHEETS)
    dump(
        DATA / "verification/calculation_checks.json",
        {
            "tests": "18 independent checks passed after review fixes; full artifact verification follows",
            "rule_count": len(rules),
            "frozen_source": basis["model_sha256"],
            "drawing_basis": "Shared coordinates and input records. Main benches and rest furniture drawn as envelopes.",
            "unit_notes": [
                "DXF uses INSUNITS=4 millimetres",
                "PDF is A3 landscape; use 100% print, no fit-to-page.",
                "Engineering 3D is a separate simplified section study, not a revised interior design.",
            ],
        },
    )
    print(
        json.dumps(
            {
                "pdf_pages": len(SHEETS),
                "requirement_items": len(rules),
                "scales": [q["code"] for q in SHEETS if q["scale"]],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
