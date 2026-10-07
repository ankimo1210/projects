"""Private Hull GE Ch1 lessons: dated source observations and explicit cash units."""

import numpy as np
import plotly.graph_objects as go

from . import _intro_contracts as c

SECTIONS = [
    (
        "1.1",
        "取引所市場",
        [24, 25],
        """取引所は数量・品質・受渡条件を標準化した契約を定義します。清算機関（CCP）は売買成立後に双方の相手方となり、証拠金などで履行リスクを管理します。証拠金は購入代金やpremiumではなく担保です。

金100oz、6か月、1oz当たり1,750 USDの原典例は「AがCCPから買う」「CCPがBから買う」の2契約となり、数量・価格・期限を保存します。相手方リスクの管理先が変わり、CCP自身のリスクが消えるわけではありません。

原典の沿革はCBOT設立1848年、CME設立1919年、CBOEのcall開始1973年（16銘柄）とput開始1977年。open outcryから電子取引への移行で注文照合が自動化され、HFTが可能になりました。電子取引は**執行**、CCPは**成立後の清算**です。

**確認:** 注文照合と履行リスク管理を区別してください。""",
    ),
    (
        "1.2",
        "OTC市場",
        [25, 28],
        """OTCには相対清算とCCP清算の両方があります。相対契約では終了条件、終了時の支払額、担保を定めます。market makerのbidはディーラーが買う価格、askは売る価格なので、顧客の買いはask、売りはbidです。

原典は危機後の制度として対象となる標準化OTC商品のSEF等での執行、CCP清算、取引報告を区別しています。地域・商品・当事者の条件を無視して「すべてのOTCがCCP」とは扱いません。これはHull 11e時点の紹介で、現行法令適用の判定ではありません。systemic riskは取引網を介して破綻が連鎖するリスクです。

2019年末の原典統計はOTC想定元本558.5兆USD、取引所96.5兆USD、OTC gross market value11.6兆USD。両市場の集計定義は完全には同じでなく、想定元本100百万USDの契約でも価値は1百万USDの場合があります。元本を損失額と読み替えません。BISではCCP介在で2契約として数えますが、双方に+1/-1百万USDの価値がある1契約のgross market valueは1百万USDです。compressionは経済的な取引関係を整理し想定元本を減らし、元本減少だけからリスク減少を断定しません。

2008年のLehman事例は高レバレッジ31:1、危険な投資、短期資金の更新停止の組合せです。100万超の取引・約8,000相手先、担保再利用が終了時精算を複雑にしました。以上は歴史事例と記述統計であり、最新値や価格モデルの検証値ではありません。

**確認:** 想定元本・市場価値と執行・清算・報告を区別してください。""",
    ),
    (
        "1.3",
        "フォワード契約",
        [28, 30],
        """forwardは将来の指定日に指定価格Kで売買する**義務**です。longは買い、shortは売り。spotはほぼ即時の売買です。数量Q、満期価格Sₜの受払はlong = Q(Sₜ−K)、short = Q(K−Sₜ)。新規forward priceと既存契約の受渡価格K、満期受払と途中時点の契約価値を区別します。

Table 1.1は2020-05-21のUSD/GBP（1GBP当たりUSD）の例です。

| 期限 | bid | ask |
|---|---:|---:|
| spot | 1.2217 | 1.2220 |
| 1か月 | 1.2218 | 1.2222 |
| 3か月 | 1.2220 | 1.2225 |
| 6か月 | 1.2224 | 1.2230 |

6か月後の1百万GBP買いはask1.2230を使い、1,223,000 USDを支払います。満期1.3000なら77,000 USD、1.2000なら−23,000 USDの受払。1GBP当たり0.077／−0.023 USDで、双方の和はゼロです。

無配当株60 USD、1年5%の借入・運用なら公正forwardは60×1.05=63 USD。67なら60を借りて株を買いforwardで売り、63を返して4の利益。58なら保有株を60で売って63まで運用し、58で買い戻して保有継続より5有利です。初期保有または空売り可能性、同じ借入／運用率、費用なしを仮定します。これは1年単利／年複利で、連続複利60 exp(0.05)を混ぜません。

以下はGBP/USDが非負のシナリオで、ゼロは境界の説明用です。非負の原資産で固定Kならlongの最大損失はQK、shortは上値とともに損失が増えます。負値を許す一般の原資産の定義域とは区別します。

**確認:** GBPを買う顧客はどちらのquoteを使いますか。""",
    ),
    (
        "1.4",
        "先物契約",
        [30, 31],
        """futuresも将来の売買義務ですが、原典の基本例では取引所が条件を標準化し、清算機関が両側に入ります。原資産は金・銅などの商品、株価指数、通貨、国債など。

原典の9月1日時点の12月限金1,750 USD/ozは、12月受渡の価格の例で、需給により動きます。forwardとの共通点は売買義務、制度差は標準化・証拠金・日次決済です。満期差額だけでは途中の資金繰りを表せません。詳細は第2章と第5章へ進みます。

**確認:** 証拠金と取引価格は何が違いますか。""",
    ),
    (
        "1.5",
        "オプション",
        [31, 33],
        """callは買う権利、putは売る権利。保有者は行使しない選択ができ、売り手は行使された場合の義務を負います。Americanは満期まで、Europeanは満期だけ行使可能で、地理の名称ではありません。long call、short call、long put、short putの4ポジションがあります。

原典の米国株例は1契約100株。call payoff=max(Sₜ−K,0)、put=max(K−Sₜ,0)、売り手は逆符号。単位premiumは1株当たりです。利益は買い側で数量×(payoff−単位premium)、売り側で数量×(単位premium−payoff)です。利息と手数料を省略した終端比較です。

2020-05-21のApple株bid316.23／ask316.50 USD、Table 1.2–1.3を使います。12月18日満期K340 callをask20.30で1契約買うと代金2,030 USD。Sₜ400でpayoff6,000・利益3,970、Sₜ≤340で損失2,030。9月18日満期K290 putをbid12.70で1契約売ると受取1,270。Sₜ250で支払4,000・純損失2,730、Sₜ≥290で利益1,270です。

歴史的表では同じ満期でKが増すとcallは安くputは高く、同じKで6月19日→9月18日→12月18日と長い満期ほど高い傾向です。これは観測例で、一般のEuropean optionの満期単調性やBSMの正解表ではありません。Figure 1.3と以下の利益図はEuropeanと仮定し、途中の早期行使をモデル化しません。

**確認:** premium20.30と代金2,030の単位は何ですか。""",
    ),
    (
        "1.6",
        "取引者の目的",
        [33, 34],
        """ヘッジャーは既存リスクを減らし、投機家は新しい価格方向のリスクを取り、裁定者は複数取引で価格差を固定します。目的の異なる参加者が反対側の取引を引き受け、流動性を作ります。

hedge fundという名称は必ずリスクを減らす意味ではありません。Business Snapshot 1.3にはlong/short株（割安買い・割高売り）、convertible（転換社債と株short）、distressed（経営危機の証券）、emerging markets（新興国の債券・株）、global macro（景気見通し）、merger（合併成立の予想）があります。呼称だけで無リスクと判断しません。

戦略決定後にリスクを評価し、受容するリスクとヘッジするリスクを分け、ヘッジを設計します。原典の規制・報酬・規模の記述は当時のもので、現在の一般条件とは断定しません。

**確認:** 同じ商品がヘッジにも投機にもなる理由は何ですか。""",
    ),
    (
        "1.7",
        "ヘッジャー",
        [34, 36],
        """ImportCoは3か月後の10百万GBP支払をask1.2225のlong forwardで固定し、12,225,000 USDを支払います。無ヘッジなら満期1.2で12,000,000、1.3で13,000,000。ExportCoは30百万GBP受取をbid1.2220のshort forwardで固定し、36,660,000 USDを得ます。支払／受取とhedge受払を合算してリスクを相殺します。ヘッジで事後的な利益が必ず改善するわけではありません。

株1,000株（当初28 USD）、2か月のK27.50 putを10契約、premium1 USD/株で買う原典例は1契約100 USD・総費用1,000 USD。終端保有価値は1,000 max(Sₜ,27.5)、保険費用後はそこから1,000を引き、床27,500／26,500 USDです。元の株購入費用を引かないので購入時からの利益ではありません。

forwardは価格を固定し、putは費用を払って下値を守り上値を残します。Figure 1.4は保険費用後の価値と無ヘッジ価値を比較します。日中行使やpremium利息は省略します。

**確認:** 保険費用後の床26,500を株購入時からの利益と呼べますか。""",
    ),
    (
        "1.8",
        "投機家",
        [36, 39],
        """Table 1.4では250,000 GBP現物（1.2220 USD/GBP）の購入費305,500 USDに対し、62,500 GBP×4先物（1.2223）は初期証拠金5,000×4=20,000 USDで同じ数量を持ちます。証拠金は担保で、購入代金や損失上限ではなく、追加証拠金・日次決済の資金が必要になり得ます。

満期1.3000で現物／先物の利益19,500／19,425 USD、1.2000で−5,500／−5,575 USD。75 USD差は金利を省略した比較で、裁定利益とは判断しません。

Table 1.5の資金2,000 USDは株20 USD×100株、またはK22.5 callのpremium1 USD×2,000単位に使います。2,000 optionsは100株単位の20契約です。満期27で株利益700、call単位payoff4.5・合計payoff9,000・利益7,000 USD（このシナリオでは10倍）。満期15では株損失500、call損失2,000 USD。callの買い側の損失上限はpremiumですが、売り側には同じ上限を当てはめません。

図は数量と初期資金を明示した終端シナリオで、将来の予測や投資推奨ではありません。

**確認:** 2,000 optionsと2,000契約は何倍違いますか。""",
    ),
    (
        "1.9",
        "裁定者",
        [39, 39],
        """同一株をNYで120 USD、Londonで100 GBP、為替1.23 USD/GBPで同時売買できる原典例です。100株をNYで買い（−12,000 USD）、Londonで売り（+10,000 GBP）、GBPを+12,300 USDに換えて300 USDが残ります。

| 同時に組み合わせる取引 | USD収支 | GBP収支 |
|---|---:|---:|
| NYで100株を購入 | −12,000 | 0 |
| Londonで100株を売却 | 0 | +10,000 |
| GBPをUSDへ換算 | +12,300 | −10,000 |
| 合計 | +300 | 0 |

利益=数量×(海外売値×USD/GBP−国内買値)−USD費用−GBP費用×USD/GBP。USD総費用400なら−100 USDで、機会は消えます。同一銘柄・同時に実行可能なbuy/sell quote・資金と株の調達・換算方向を確認します。時間差があれば価格リスクが残ります。

割安市場の買いと割高市場の売りが価格差を縮め、この無裁定が後の価格理論の基礎です。

**確認:** 換算方向を逆にしても同じ利益になりますか。""",
    ),
    (
        "1.10",
        "危険と統制",
        [39, 40],
        """ヘッジや裁定の権限でも投機を隠している場合があります。原典のSocGen／Kerviel事例は架空の反対売買で見かけ上のhedgeを作り、大きな株価指数ポジションを持ったものです。2008年の解消損失4.9十億EURは歴史事例で、価格検証の正解値ではありません。Barings／Leeson、AIB／Rusnakも権限と実態の乖離の事例です。

明確なリスク限度・日次監視・取引の実在確認が必要です。一方、限度を守ってもモデルの想定不足で損失が生じます。2007–08年の住宅価格下落と地域をまたぐdefault相関は共通要因を過小評価した例です。権限逸脱とモデル・シナリオ不足を別々に検討します。

**確認:** 不利な状況で何が起き、そのときいくら失うかを問い直してください。""",
    ),
]


def _values():
    """Compute the 37 printed cash amounts/ratios, without historical-price fitting."""
    f = c.forward_cashflows(1_000_000, 1.223, [1.3, 1.2])
    u = c.forward_cashflows(1, 1.223, [1.3, 1.2])
    hi = c.simple_carry_comparison(60, 67, 0.05, 1)
    lo = c.simple_carry_comparison(60, 58, 0.05, 1)
    call = c.option_contract_cashflows(400, 340, 20.3)
    put = c.option_contract_cashflows(250, 290, 12.7, kind="put", side="short")
    imp = c.fx_forward_hedge(10_000_000, 1.2225, [1.2, 1.3])
    exp = c.fx_forward_hedge(30_000_000, 1.222, [1.2, 1.3], obligation="receive")
    protect = c.protected_holding(1000, [20, 27.5], 27.5, 1)
    fx = c.speculation_comparison(1.222, 1.2223, [1.3, 1.2], units=250000, initial_margin=20000)
    opt = c.stock_option_speculation(20, [27, 15], 22.5, 1, 2000)
    return {
        "1.3": dict(
            zip(
                [
                    "delivery",
                    "gain_high",
                    "loss_low",
                    "unit_high",
                    "unit_low",
                    "fair",
                    "carry_gain",
                    "interest",
                    "reverse_gain",
                ],
                [
                    -f["delivery_cash"],
                    *f["payoff"],
                    *u["payoff"],
                    hi["financed_spot"],
                    hi["relative_gain"],
                    hi["interest"],
                    lo["relative_gain"],
                ],
                strict=True,
            )
        ),
        "1.5": dict(
            call_cost=-call["premium_cash"],
            call_payoff=float(call["payoff"]),
            call_profit=float(call["profit"]),
            put_premium=put["premium_cash"],
            put_payment=-float(put["payoff"]),
            put_loss=-float(put["profit"]),
        ),
        "1.7": dict(
            import_fixed=-float(imp["net_cash"][0]),
            export_fixed=float(exp["net_cash"][0]),
            import_low=-float(imp["unhedged_cash"][0]),
            import_high=-float(imp["unhedged_cash"][1]),
            cost_contract=protect["premium_per_contract"],
            cost_total=protect["premium_cost"],
            floor=float(protect["terminal_value"][0]),
            floor_after_cost=float(protect["value_after_premium"][0]),
        ),
        "1.8": dict(
            spot_outlay=fx["spot_outlay"],
            margin=fx["initial_margin"],
            spot_high=float(fx["spot_profit"][0]),
            future_high=float(fx["futures_profit"][0]),
            spot_low=float(fx["spot_profit"][1]),
            future_low=float(fx["futures_profit"][1]),
            stock_high=float(opt["stock_profit"][0]),
            stock_low=float(opt["stock_profit"][1]),
            call_unit=float(opt["option_payoff"][0] / opt["option_units"]),
            call_payoff=float(opt["option_payoff"][0]),
            call_high=float(opt["option_profit"][0]),
            call_low=float(opt["option_profit"][1]),
            ratio=float(opt["option_profit"][0] / opt["stock_profit"][0]),
        ),
        "1.9": dict(arbitrage=float(c.cross_market_cashflows(100, 120, 100, 1.23)["net_cash"])),
    }


VALUE_LABELS = {
    "delivery": "GBP購入額（USD）",
    "gain_high": "GBP高の受払（USD）",
    "loss_low": "GBP安の受払（USD）",
    "unit_high": "GBP高の単位受払（USD/GBP）",
    "unit_low": "GBP安の単位受払（USD/GBP）",
    "fair": "公正forward（USD/株）",
    "carry_gain": "割高forwardの利益（USD）",
    "interest": "1年の利息（USD）",
    "reverse_gain": "割安forwardの改善額（USD）",
    "call_cost": "callの購入代金（USD）",
    "call_payoff": "callの満期受払（USD）",
    "call_profit": "callの利益（USD）",
    "put_premium": "put売りの代金受取（USD）",
    "put_payment": "put売りの満期支払（USD）",
    "put_loss": "put売りの損失額（USD）",
    "import_fixed": "輸入の固定支払（USD）",
    "export_fixed": "輸出の固定受取（USD）",
    "import_low": "GBP安の無ヘッジ支払（USD）",
    "import_high": "GBP高の無ヘッジ支払（USD）",
    "cost_contract": "putの1契約費用（USD）",
    "cost_total": "putの総保険費用（USD）",
    "floor": "保有価値の床（USD）",
    "floor_after_cost": "保険費用後の床（USD）",
    "spot_outlay": "GBP現物の購入費（USD）",
    "margin": "先物の初期証拠金（USD）",
    "spot_high": "GBP高の現物利益（USD）",
    "future_high": "GBP高の先物利益（USD）",
    "spot_low": "GBP安の現物損益（USD）",
    "future_low": "GBP安の先物損益（USD）",
    "stock_high": "株高の株利益（USD）",
    "stock_low": "株安の株損益（USD）",
    "call_unit": "callの単位受払（USD/株）",
    "call_high": "株高のcall利益（USD）",
    "call_low": "株安のcall損益（USD）",
    "ratio": "株高シナリオの利益比（倍）",
    "arbitrage": "同時売買の残余（USD）",
}

FIGURE_SECTIONS = {
    "intro_forward": "1.3",
    "intro_options": "1.5",
    "intro_protection": "1.7",
    "intro_speculation": "1.8",
}


def _series():
    """Compute shared terminal scenarios with explicit quantities and premium."""
    fx = np.array([0, 1.2, 1.223, 1.3, 2.0])
    stock = np.array([0, 250, 290, 340, 400, 500.0])
    protected = np.array([0, 20, 27.5, 28, 40.0])
    spec = np.array([0, 15, 20, 22.5, 27, 30.0])
    return {
        "intro_forward": [
            ("long", fx, c.forward_cashflows(1_000_000, 1.223, fx)["payoff"]),
            ("short", fx, c.forward_cashflows(1_000_000, 1.223, fx, side="short")["payoff"]),
        ],
        "intro_options": [
            ("long_call", stock, c.option_contract_cashflows(stock, 340, 20.3)["profit"]),
            (
                "short_put",
                stock,
                c.option_contract_cashflows(stock, 290, 12.7, kind="put", side="short")["profit"],
            ),
        ],
        "intro_protection": [
            ("unhedged", protected, 1000 * protected),
            (
                "insured_after_cost",
                protected,
                c.protected_holding(1000, protected, 27.5, 1)["value_after_premium"],
            ),
        ],
        "intro_speculation": [
            ("stock", spec, c.stock_option_speculation(20, spec, 22.5, 1, 2000)["stock_profit"]),
            ("call", spec, c.stock_option_speculation(20, spec, 22.5, 1, 2000)["option_profit"]),
        ],
    }


def _figures():
    """Build four interactive figures, shared by notebook and companion portal."""
    labels = {
        "long": "買いforward",
        "short": "売りforward",
        "long_call": "call買い・1契約",
        "short_put": "put売り・1契約",
        "unhedged": "株だけ",
        "insured_after_cost": "株＋put・保険費用後",
        "stock": "100株",
        "call": "2,000 options・20契約",
    }
    titles = {
        "intro_forward": "1百万GBPの満期受払",
        "intro_options": "Appleのpremium込み利益",
        "intro_protection": "1,000株の保険費用後の保有価値",
        "intro_speculation": "初期資金2,000 USDの利益比較",
    }
    result = {}
    for key, series in _series().items():
        fig = go.Figure()
        for role, x, y in series:
            fig.add_trace(
                go.Scatter(
                    x=x.tolist(),
                    y=np.asarray(y).tolist(),
                    name=labels[role],
                    mode="lines+markers",
                    meta=dict(role=role),
                )
            )
        fig.update_layout(
            title=titles[key],
            height=450,
            margin=dict(l=85, r=30, t=65, b=100),
            legend=dict(orientation="h", y=-0.2),
            xaxis_title="満期 USD/GBP" if key == "intro_forward" else "満期株価（USD/株）",
            yaxis_title="保有価値（USD）" if key == "intro_protection" else "受払／利益（USD）",
            meta=dict(
                section=FIGURE_SECTIONS[key],
                figure=key,
                source="Hull GE Ch1 inputs; terminal scenarios",
                synthetic=True,
            ),
        )
        result[key] = fig
    return result


def _format(value):
    """Format a cash amount or ratio, preserving sign and up to four decimals."""
    return f"{value:,.4f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"


def _cells():
    """Return individually addressable explanations, printed-value tables and plots."""
    cells = []
    values = _values()
    for sid, title, pages, body in SECTIONS:
        text = f"### §{sid} {title}\n\n出典: Hull 11e Global Edition pp.{pages[0]}–{pages[1]}。制度・quoteは原典時点です。\n\n{body}"
        if sid in values:
            text += "\n\n原典計算例との照合（単位は各行に記載）:\n\n| 計算値 | 結果 |\n|---|---:|\n"
            text += "\n".join(
                f"| {VALUE_LABELS[name]} | {_format(value)} |"
                for name, value in values[sid].items()
            )
        cells.append(dict(cell_type="markdown", metadata={}, source=text.splitlines(True)))
        key = next((k for k, s in FIGURE_SECTIONS.items() if s == sid), None)
        if key:
            code = (
                "from IPython.display import HTML, display\n"
                "from hullkit._chapter01_lesson import _html\n"
                f'display(HTML(_html("{key}", include_plotlyjs={key == "intro_forward"})))'
            )
            cells.append(
                dict(
                    cell_type="code",
                    metadata={},
                    source=code.splitlines(True),
                    outputs=[],
                    execution_count=None,
                )
            )
    return cells


def _html(key, *, include_plotlyjs=False):
    """Render a shared plot that follows its container's actual width."""
    import plotly.io as pio

    return pio.to_html(
        _figures()[key],
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        div_id=key,
        config=dict(responsive=True, displaylogo=False),
        post_script="""
        const chart=document.getElementById('{plot_id}');
        let previous=0;
        new ResizeObserver(()=>{
            const width=chart.clientWidth;
            if (width>0 && Math.abs(width-previous)>1) {
                previous=width;
                Plotly.Plots.resize(chart);
            }
        }).observe(chart);
        """,
    )
