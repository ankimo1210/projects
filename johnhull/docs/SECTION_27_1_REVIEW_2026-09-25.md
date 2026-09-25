# §27.1 Alternatives to Black–Scholes–Merton：原典照合と要求

対象は Hull 11e Global Edition §27.1（PDF物理 pp.641–646）。§27.2開始前まで。
2026-09-25に本文、Table 27.1、Figure 27.1を確認した。以降の節のHeston・SABRを
この節の受入には算入しない。金額は通貨、時刻は年、金利・ボラは年率。

| 要求 | 原典上の要点 | 独立検証・教材 |
|---|---|---|
| AM01 CEV | $dS=(r-q)Sdt+\sigma S^\beta dW$。$\beta=1$はBSM、$\beta<1$では下値の局所ボラが高く、$\beta>1$では逆。非心カイ二乗の欧州価格。 | $S_0$の局所ボラを20%に揃えた3曲線。$\beta=0.8$の3価格を独立Crank–Nicolson PDEで検査。 |
| AM02 Merton | $N_T\sim\mathrm{Poisson}(\lambda T)$、対数ジャンプ$N(\gamma,\delta^2)$、$k=e^{\gamma+\delta^2/2}-1$のドリフト補償。BSM級数。 | Hullの再重み付け級数と元のPoisson回数での条件付き対数正規期待値を26行使価格で比較。 |
| AM03 Table 27.1 | $\lambda=0.5$/年、$T=2$年の$m=0,\ldots,8$回の確率と累積。 | 印刷4桁の確率列を固定。$m\le2$は0.9197。経路では複数ジャンプの対数和を抽出。 |
| AM04 VG | $G_T\sim\Gamma(T/\nu,\nu)$、$\log S_T=\log S_0+(r-q+\omega)T+\theta G_T+\sigma W_{G_T}$。指数モーメント条件と$\omega$。 | 独立ガンマ密度積分で26価格。Figure 27.1条件の40万標本の満期株価密度とGBM対数正規密度を比較。 |
| AM05 極限・使い分け | BSMにない局所スキュー、ジャンプ、時計の変動を区別。 | $\beta=1,\lambda=0,\nu=0$でBSM、put-call parity、パラメータと境界の適用域を説明。 |
| AM06 配布 | 式・数値・図を学習者が読める形にする。 | vol06 §7.1–7.6と保存4図をBook/portalで共用。独立値、保存出力、両面実画面と既受入節の回帰を検査。 |

独立参照は `scripts/build_alternative_models_reference.py` と
`docs/validation/section-27-1/reference.json`。hullkitの価格関数をimportせずに生成する。
CEVはPDE格子誤差、VGの価格は求積誤差、分布図には有限標本誤差がある。
$\beta>1$のCEVは無限遠境界とマルチンゲール性の扱いに注意を要し、PDE照合を
$\beta=0.8$に限定した。市場較正、取引費用、動的ヘッジ成績は検証していない。
