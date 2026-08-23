# Ch.08 Securitization and the Financial Crisis of 2007-8

> **Source**: Hull 11e, Chapter 8 (pp. 201-215). Paraphrased summary for personal use.

## 1. 要点

- 証券化（Securitization）とは、ローン等の資産をSPVに売却してトランシェに分割し、投資家に販売する仕組み。GNMA・FNMA・FHLMCが1960年代に住宅ローン担保証券（MBS）市場を創設した。
- ABS（資産担保証券）はウォーターフォール構造で現金フローを配分する。シニア→メザニン→エクイティの順に元本を受け取り、損失はエクイティ→メザニン→シニアの順に吸収する。
- ABS CDO（「CDO二乗」）は複数ABSのメザニントランシェを束ねて再度トランシェ化した構造。元の資産損失率が10%台半ばを超えると、AAA格付けのシニアトランシェでさえ大きな損失を被る。
- 2000〜2006年の米国住宅バブルはサブプライムローンの急拡大・審査緩和・ARMのティーザーレートによって膨らみ、2007年にバーストして大規模なデフォルト連鎖を引き起こした。
- 危機の本質的原因はデフォルト相関の過小評価、格付け機関とトランシェ発行者間のエージェンシーコスト、規制裁定、短期ボーナス重視の報酬体系にある。

## 2. キー用語

- **MBS (Mortgage-Backed Security)**: 住宅ローンを束ねて証券化したもの。GNMAなどが元本・利息を保証。
- **ABS (Asset-Backed Security)**: 保証なしでローン等の資産を束ねてトランシェ化した証券（Figure 8.1）。
- **SPV (Special Purpose Vehicle)**: 資産の法的分離のためにABSで使われるビークル（特別目的会社）。
- **トランシェ (Tranche)**: 優先度の異なる元本クラス。シニア（AAA）・メザニン（BBB）・エクイティ（無格付け）の三層が基本。
- **ウォーターフォール (Waterfall)**: 現金フローをトランシェに配分するルール。元本はシニア→メザニン→エクイティの順、損失は逆順。
- **ABS CDO (Mezzanine ABS CDO)**: 複数ABSのメザニントランシェを再度束ねてトランシェ化した構造（Figure 8.3）。「CDO二乗」とも呼ぶ。
- **CDO (Collateralized Debt Obligation)**: 債務をコラテラルとする担保付き債務証書の総称。
- **サブプライムローン**: 平均より信用リスクが高いとみなされる住宅ローン。2000年以降は第一抵当権にも拡大。
- **ARM (Adjustable-Rate Mortgage)**: 変動金利型住宅ローン。低いティーザーレート期間後に大幅な金利上昇。
- **FICO スコア**: Fair Isaac Corporation が開発した個人信用スコア（300〜850）。
- **LTV (Loan-to-Value Ratio)**: ローン残高 / 物件評価額の比率。担保価値の指標。
- **デフォルト相関 (Default Correlation)**: 複数借り手が同時にデフォルトする傾向の強さ。相関が高いほどシニアトランシェが脆弱。
- **規制裁定 (Regulatory Arbitrage)**: ローン直接保有よりトランシェ保有の方が自己資本規制上の資本賦課が低くなることを利用した行動。
- **エージェンシーコスト (Agency Costs)**: 取引関係の当事者間でインセンティブが不一致な状態から生じるコスト。
- **TED スプレッド**: 3ヶ月ユーロドル金利と3ヶ月米国債利回りの差。金融ストレスの指標。通常30〜50 bp、2008年10月には450 bp超。
- **LIBOR-OIS スプレッド**: 3ヶ月LIBORとOIS（翌日物金利スワップ）の差。銀行間信用リスクの指標。2008年10月に364 bp超。
- **Basel I/II/III/IV**: バーゼル委員会が策定した国際的な銀行自己資本規制の体系。危機後にBasel II.5→Basel IIIへ強化。
- **Dodd-Frank 法**: 危機後に米国で成立した包括的金融規制改革法。Volcker ルール等を含む。

## 3. 主要公式

### トランシェ損失の簡易計算（Figure 8.3 の例）

プール損失率を $L$（%）、ABS のトランシェ構成をシニア 80%・メザニン 15%・エクイティ 5%、ABS CDO のトランシェ構成をシニア 65%・メザニン 25%・エクイティ 10% とするとき：

**ABS メザニントランシェへの損失率**

$$
L_{\text{mezz}}^{\text{ABS}} = \frac{\max(L - 0.05,\; 0)}{0.15} \times 100\%
$$

- $L$: 原資産プールの損失率（0〜1）
- 分子: エクイティ 5% を超えた損失分
- 分母: メザニントランシェの幅 15%

**ABS CDO シニアトランシェへの損失率**（全 ABS が同一損失率と仮定）

$$
L_{\text{senior}}^{\text{ABS CDO}} = \frac{\max(L_{\text{mezz}}^{\text{ABS}} - 0.35,\; 0)}{0.65} \times 100\%
$$

- 分子: ABS CDO エクイティ(10%) + メザニン(25%) = 35% を超えた ABS メザニン損失分
- 分母: ABS CDO シニアトランシェの幅 65%

> Hull Table 8.1 より。$L=17\%$ のとき $L_{\text{mezz}}^{\text{ABS}}=80\%$、$L_{\text{senior}}^{\text{ABS CDO}}=69.2\%$。

## 4. アルゴリズム / 手順

### 手順 A：証券化（ABS 組成）プロセス

1. **資産プールの組成**: 銀行がローン群（住宅ローン等）を特別目的会社（SPV）に売却。
2. **トランシェ設計**: SPV がプールの現金フローをシニア・メザニン・エクイティの各トランシェに分割。ウォーターフォールルールを法的文書（数百ページ）に規定。
3. **格付け取得**: 格付け機関（S&P・Moody's・Fitch）がトランシェを査定。シニアに AAA、メザニンに BBB 等を付与。
4. **販売**: シニアトランシェは一般投資家へ、エクイティトランシェは組成銀行またはヘッジファンドが保有。
5. **現金フロー配分（ウォーターフォール）**: 毎期、プールから受け取った元本・利息を以下の優先順位で配分する（手順 B 参照）。

### 手順 B：ウォーターフォール ペイアウト（元本）

1. 入手した元本回収額を確認する。
2. **シニアトランシェ**の元本が完済されるまでシニアへ配分。
3. シニア完済後、**メザニントランシェ**の元本が完済されるまでメザニンへ配分。
4. メザニン完済後、残額を**エクイティトランシェ**に配分。

### 手順 C：ウォーターフォール ペイアウト（利息）

1. 入手した利息収入を確認する。
2. シニアが約定利率（例：LIBOR + 60 bp）分の利息を受け取るまでシニアへ配分。
3. 次にメザニンが約定利率（例：LIBOR + 250 bp）分を受け取るまでメザニンへ配分。
4. 残額をエクイティへ配分（エクイティの「利率」は残差）。

### 手順 D：ABS CDO 組成

1. 複数の ABS からメザニントランシェを集めてプールを形成（各 ABS のメザニンは BBB 格が多い）。
2. そのプールを SPV に移し、同様のウォーターフォールで再度トランシェ化。
3. 新しいシニアトランシェ（65%）・メザニン（25%）・エクイティ（10%）を設計。
4. シニアに AAA 格を取得。結果として元の資産プールの約 90% が AAA 格となる（ABS シニア 80% + ABS CDO シニア 65% × ABS メザニン 15% = 89.75%）。

## 5. Python reference

```python
import numpy as np

def abs_tranche_losses(
    pool_loss: float,
    equity_pct: float = 0.05,
    mezz_pct: float = 0.15,
) -> dict:
    """Compute ABS tranche loss fractions given pool loss rate.

    Parameters
    ----------
    pool_loss : float
        Loss rate on underlying asset pool (0.0 - 1.0).
    equity_pct : float
        Equity tranche width as fraction of pool principal.
    mezz_pct : float
        Mezzanine tranche width as fraction of pool principal.

    Returns
    -------
    dict with keys 'equity', 'mezzanine', 'senior' (each 0.0 - 1.0).
    """
    senior_pct = 1.0 - equity_pct - mezz_pct

    equity_loss = min(pool_loss, equity_pct) / equity_pct
    mezz_loss = max(min(pool_loss - equity_pct, mezz_pct), 0.0) / mezz_pct
    senior_loss = max(pool_loss - equity_pct - mezz_pct, 0.0) / senior_pct

    return {"equity": equity_loss, "mezzanine": mezz_loss, "senior": senior_loss}


def abs_cdo_senior_loss(
    abs_mezz_loss: float,
    cdo_equity_pct: float = 0.10,
    cdo_mezz_pct: float = 0.25,
) -> float:
    """Compute ABS CDO senior tranche loss given ABS mezzanine loss rate."""
    cdo_senior_pct = 1.0 - cdo_equity_pct - cdo_mezz_pct
    return max(abs_mezz_loss - cdo_equity_pct - cdo_mezz_pct, 0.0) / cdo_senior_pct


# Reproduce Hull Table 8.1
print(f"{'Pool Loss':>10} {'ABS Mezz':>10} {'CDO Equity':>12} {'CDO Mezz':>10} {'CDO Senior':>12}")
for pool_loss in [0.10, 0.13, 0.17, 0.20]:
    t = abs_tranche_losses(pool_loss)
    cdo_sr = abs_cdo_senior_loss(t["mezzanine"])
    cdo_eq = min(t["mezzanine"], 0.10) / 0.10   # simplified equity exhaustion
    cdo_mz = max(min(t["mezzanine"] - 0.10, 0.25), 0.0) / 0.25
    print(f"{pool_loss:>10.0%} {t['mezzanine']:>10.1%} {cdo_eq:>12.1%} {cdo_mz:>10.1%} {cdo_sr:>12.1%}")
```

実行例（Hull Table 8.1 に対応）:
```
 Pool Loss   ABS Mezz   CDO Equity   CDO Mezz  CDO Senior
       10%      33.3%       100.0%      93.3%        0.0%
       13%      53.3%       100.0%     100.0%       28.2%
       17%      80.0%       100.0%     100.0%       69.2%
       20%     100.0%       100.0%     100.0%      100.0%
```

## 6. 注意点 / 典型的なミス

- **ABS と ABS CDO の AAA トランシェの安全性は大きく異なる**: ABS の AAA は損失が 20% を超えなければ保護されるが、ABS CDO の AAA は 10.25% 超の損失で急激に毀損し始める（Table 8.1）。同じ格付けでもリスクプロファイルは別物。
- **デフォルト相関は平時に低く、ストレス期に急上昇する**: モデルが平時の相関で校正されていると、同時デフォルトの可能性を大幅に過小評価する。
- **「薄いトランシェ」問題**: 実際の ABS には 1〜2% 幅のトランシェが 15〜20 枚存在した。このような薄いトランシェは「全か無か」の二値的な損失分布を持ち、BBB 格でも完全損失が容易に起こる。
- **格付け機関の評価基準の違い**: S&P・Fitch は損失確率（PD）でトランシェを評価し、Moody's は期待損失（EL）で評価した。PD と EL が等しい保証はなく、異なる格付け体系間の比較は注意が必要。
- **ウォーターフォールの法的文書は複雑**: 実務では数百ページの契約書で規定され、簡略版のルール理解だけでは不十分なケースがある。
- **非遡及ローン（nonrecourse mortgage）の「無料プット」効果**: 米国の多くの州でローンは非遡及型のため、債務者はデフォルトによって住宅を「売却」できる内在プットオプションを持ち、これが自発的デフォルトを促進した。

## 7. 関連トピック

- See: Ch.09 XVAs（カウンターパーティリスクと信用調整価値）
- See: Ch.24 Credit Risk（デフォルト確率・回収率・信用リスクモデル）
- See: Ch.25 Credit Derivatives（CDS・CDO のプライシング）
- 証券化と規制: Basel I → III の自己資本規制（Business Snapshot 8.1）
- 関連指数: ABX（ABS トランシェの価値追跡）、TABX（ABS CDO トランシェ）
