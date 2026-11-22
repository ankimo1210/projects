# Lean でのブラック・ショールズ方程式の導出

更新日 2026-11-22

ブラウン運動を出発点として、株価の確率微分方程式、コール価格の偏微分方程式、デルタ・ヘッジの自己資金調達を Lean で検証する。

## 到達点

| 段階 | 状態 | 検証した内容 |
|---|---|---|
| ブラウン運動と伊藤の公式 | 完了 | 構成済みのブラウン運動を使い、二次変動と有限和の恒等式から、二乗に対する伊藤の公式を平均二乗収束として導いた。幾何ブラウン運動が株価の確率微分方程式を満たすことも検証した。 |
| 確率微分の係数比較 | 完了 | 一定係数の場合はブラウン運動の正規分布から両係数を特定した。時間・経路に依存する場合は、有界で各経路が連続な拡散係数と、時間について一様にリプシッツ連続な累積ドリフトを対象に、ゼロ過程の分解の一意性を証明した。 |
| ヨーロピアン・コール | 完了 | 現実測度のドリフトを任意の定数とし、価格付け測度の下でコールを割引期待値として定義した。有限個の取引時点での無裁定、満期前の偏微分と方程式、自己資金調達の等式、および満期ペイオフへの収束を検証した。 |
| 満期までのコール複製と無裁定価格 | 完了 | デルタ・ヘッジの確率積分を満期まで $L^2$ で延長し、ペイオフを複製した。複製費用と割引期待値が一致し、この価格が $L^2$ の株取引とコールの売買を許す市場で唯一の無裁定価格であることを証明した。 |
| 一般の連続時間モデルへの拡張 | 残り | 有界性の条件を局所化で緩め、一般の価格過程について、係数比較による方程式の導出を接続する。割引資産額が下から有界であるような、より広い取引戦略での無裁定を扱う。 |

[BlackScholesFromBrownian.lean](../BlackScholesFromBrownian.lean) の価格は、満期ペイオフを市場の価格付け測度で評価したもの。残存期間を $\tau=T-t$ とするので、方程式の時間項は $-\partial_\tau V$ になる。偏微分方程式は MathFin の熱核を使ったファインマン・カッツの定理から従う。株価の確率微分方程式と自己資金調達の等式は、MathFin の伊藤の公式と伊藤積分に依存する。 [MathFin の価格方程式の証明](https://github.com/formal-applied-math/formal-mathfin/blob/cbe842dda1e71fd7173f3325971796686dbf7feb/MathFin/Models/BlackScholes/PDEFromFeynmanKac.lean) [MathFin の自己資金調達の証明](https://github.com/formal-applied-math/formal-mathfin/blob/cbe842dda1e71fd7173f3325971796686dbf7feb/MathFin/Models/BlackScholes/BlackScholesSelfFinancing.lean)

[ItoCoefficients.lean](../ItoCoefficients.lean) では、$A_t+\int_0^t b_s\,dW_s=0$ が各時点でほとんど確実に成り立つと仮定する。二次変動の極限から $\int_0^T b_s^2\,ds=0$ が従い、拡散係数 $b$ は時間と確率についてほとんど至る所でゼロ、累積ドリフト $A$ は各時点でほとんど確実にゼロになる。 [MathFin の二次変動の証明](https://github.com/formal-applied-math/formal-mathfin/blob/cbe842dda1e71fd7173f3325971796686dbf7feb/MathFin/Probability/Brownian/AdaptedQuadraticVariation.lean)

価格付け測度では、割引株価 $\widetilde S_s=e^{-rs}S_s$ の二次モーメントは $\mathbb E_Q[\widetilde S_s^2]=S_0^2e^{\sigma^2 s}$ になる。コールのデルタは $0\le\Delta_s\le1$ なので、$\sigma\widetilde S_s\Delta_s$ は満期まで二乗可積分である。満期前の局所化した積分をこの $L^2$ 積分と同定し、確率積分の連続性とコール価格の極限から満期の複製を得た。 [BlackScholesCallReplication.lean](../BlackScholesCallReplication.lean)

コールを価格 $p$ で $q$ 枚取引して満期まで保有し、代金を無リスク口座で調達すると、割引損益は $q(e^{-rT}(S_T-K)^+-p)$ になる。これに株取引の $L^2$ 伊藤積分を足したものを、初期資金ゼロの戦略として扱う。価格が複製費用と一致すると損益の期待値はゼロになる。価格差があれば、コールの売買と逆向きのヘッジを組み、正の満期損益を得られる。時刻 $t<T$ での割引価格と割引ペイオフの条件付き期待値の一致も証明した。

## WSL での検証

MathFin はコミット `cbe842dda1e71fd7173f3325971796686dbf7feb` を使用する。この版の Lean 4.35.0 は検証用チェックアウト内に設置した。Lean とビルドキャッシュを含む検証環境の実測は約 12 GiB。入門用の `Proofs.lean` は通常の Lean 4.36.0 で実行できる。今回の追加定理は警告をエラーに設定して検証し、`#print axioms` で依存する公理が `propext`、`Classical.choice`、`Quot.sound` のみであることを確認した。

```bash
cd ~/projects/_data/lean-practice/mathfin-cbe842d
export ELAN_HOME="$PWD/.elan-local"
export XDG_CACHE_HOME="$PWD/.cache"
lake env lean -DwarningAsError=true ../../../lean-practice/ItoCoefficients.lean
lake env lean -DwarningAsError=true ../../../lean-practice/BlackScholesFromBrownian.lean
lake env lean -DwarningAsError=true ../../../lean-practice/BlackScholesCallReplication.lean
```

新しい環境で検証するときは、MathFin の上記コミットを取得し、チェックアウト内で `lake exe cache get` を実行してから対象モジュールをビルドする。

```bash
lake build +BrownianMotion.Gaussian.BrownianMotion \
  +MathFin.Probability.Brownian.BrownianExpMoment \
  +MathFin.Probability.Brownian.AdaptedQuadraticVariation \
  +MathFin.Probability.Brownian.Ito.ItoSquaringIdentity \
  +MathFin.Models.BlackScholes.PDEFromFeynmanKac \
  +MathFin.Models.BlackScholes.Market \
  +MathFin.Models.BlackScholes.BlackScholesSDE \
  +MathFin.Models.BlackScholes.BlackScholesSelfFinancing
```
