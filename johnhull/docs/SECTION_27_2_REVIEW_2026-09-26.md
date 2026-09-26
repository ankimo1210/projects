# §27.2 Stochastic Volatility Models：原典照合と要求

日付：2026-09-26。原典：Hull 11e Global Edition §27.2（PDF物理・印刷 pp.646–649、§27.3開始前まで）。
式27.1–27.3、Hull–Whiteの混合公式、相関とHeston、SABRの近似式、rough volatilityの記述を確認した。
金額は通貨（SABRはフォワード1単位あたりの割引前価値）、時間は年、金利・ボラは年率小数。

## 要求契約

| 要求 | 原典上の要点 | 独立検証・教材 |
|---|---|---|
| SV01 時間依存ボラ | 式27.1。BSMに平均分散率を入れれば正しい。20%→30%の例で0.065、25.5%。 | $\sigma(t)$を直接使う独立Crank–Nicolson PDE（3行使価格）。単純平均25%との差。vol06 §8.1、`stochvol_term` |
| SV02 Hull–White混合公式 | 式27.2–27.3。無相関なら$c=\int c(\bar V)g(\bar V)d\bar V$。$V$の過程によらない。 | 厳密なCIR遷移で$\bar V$を抽出する条件付きMCと、独立のHeston特性関数Gil-Pelaez積分（ρ=0、26行使価格）。§8.2 |
| SV03 過大・過小評価 | 無相関ならBSMはATM付近を過大、深いITM/OTMを過小評価。通貨のスマイルに近い。 | 同じ$E[\bar V]$のBSMとの差の符号、連続した過大評価帯、ρ=0で$\ln(K/F_0)$について対称。§8.3、`stochvol_mixing` |
| SV04 相関とHeston | 相関があるとMC、α=0.5ならHestonの解析解。負の相関で株式型スキュー。p.649のHeston表記。 | 公開COS価格と独立Gil-Pelaez（3相関×26行使価格）。ATMのIV傾きの符号。§8.4、`stochvol_correlation` |
| SV05 SABR | $dF=\sigma F^\beta dz$、$d\sigma/\sigma=\nu dw$。p.648の$x,y,A,B,\phi,\chi$とATM式。$\sigma_0$は水準、ρは傾き、νは強さ。金利ではβ=0.5。 | 原典式の独立転記と`hullkit.sabr.sabr_implied_vol`（216値）。Euler MC（40万経路）の逆算IV（7行使価格）。ρ・νの形状。§8.5、`stochvol_sabr` |
| SV06 位置付け・限界・配布 | GARCH(1,1)（Duan）、rough volatility（H=0.06–0.20、rough/lifted Heston）。 | §8.6の説明とξ→0・決定的分散の極限。vol06 §8.1–8.6、共有4図、Book/portal両面2幅、既受入10節の再検証 |

## 独立参照

[`build_stochastic_volatility_reference.py`](../scripts/build_stochastic_volatility_reference.py)はNumPy/SciPyだけで、`hullkit`をimportしない。
[`reference.json`](validation/section-27-2/reference.json)を`--check`でbyte再現し、
[`verify_stochastic_volatility_numerics.py`](../scripts/verify_stochastic_volatility_numerics.py)が公開APIと照合して
[`numerical-check.json`](validation/section-27-2/numerical-check.json)に実測値を残す。

| 項目 | 実測 | 基準 |
|---|---:|---:|
| 平均分散率・BSMボラ | 0.065・0.254951 | 原典0.065・25.5% |
| 平均分散BSMと独立PDE（K=80/100/120） | 最大1.58e-4通貨 | 5e-4 |
| 単純平均25%のBSMとの差（ATM） | 0.187通貨 | — |
| 混合公式MC（20万経路・250ステップ）と独立Fourier（26価格） | 最大0.31 SE | 3 SE |
| BSM($\sqrt{E[\bar V]}$)の過大評価帯とATMの差 | K=88–128、−0.718通貨 | ATM負・両裾正・連続帯 |
| COSと独立Gil-Pelaez（78価格） | 最大1.6e-13通貨 | 1e-8 |
| ρ=0のIV対称性（$\ln K/F_0=\pm0.1$〜$\pm0.4$） | 最大1.8e-15 | 1e-10 |
| ATMのIV傾き（ρ=−0.7／+0.7） | −0.00301／+0.00275 /通貨 | 符号 |
| SABR式の独立転記（216値）とATM極限 | 最大3.1e-16、ATM差5.1e-8 | 1e-12、1e-6 |
| SABR式とMC逆算IV（7行使価格） | 最大6.5e-4、1.49 SE | 2e-3、3 SE |
| νによるスマイルの曲がり（ν=0.2/0.4/0.8） | 0.034／0.084／0.218 | 単調増加 |
| ξ=1e-3のHestonとBSM | 2.8e-6通貨 | 1e-5 |

公開COSは当初、コールを直接COSで計算するとρ=+0.7の右裾の打切りで行使価格によらない2.3e-3の誤差が出た。
プットをCOSで計算しコールはプット・コール・パリティで求め、打切り幅を30標準偏差にして解消した。
ξが1e-3未満では特性関数の丸め誤差が大きいため、公開関数は入力を拒否しBSM極限の使用を案内する。

## 実装・配布

- 公開APIは`hullkit.stochastic_volatility`の6関数：`average_variance_rate`、`time_dependent_bsm_price`、
  `expected_average_variance`、`simulate_average_variance`、`mixing_price`、`heston_price`。SABRは既存の
  `hullkit.sabr.sabr_implied_vol`（原典の式と一致）を使う。
- vol06に§8.1–8.6を追加し、Longstaff-Schwartzを§9、練習問題を§10へ繰り下げた。4図は
  `hullkit._stochastic_volatility_lesson`でBook/portalへ共通生成する。
- [`verify_stochastic_volatility_notebook.py`](../scripts/verify_stochastic_volatility_notebook.py)は、§8以外の46セルが
  基点`c3dd6ae5`と本文・出力署名で一致すること（見出し番号の変更2件だけを許す）、§27.1と§27.2の保存図が共有図と
  一致すること、新規実行と保存出力の一致を確かめる。4種類の改変（§7.1本文、SABR保存値、未登録の見出し番号変更、
  §27.1 CEV保存値）を拒否することも記録する。
- ChromiumでBook/portal×1440/1000px、4図とSABRの2メニュー状態（20状態・20画像）を保存参照と照合し、IVの改変を両面で拒否した。

## 既受入節への影響

共有のportalレジストリ・stylesheet・vol06 notebookを変えたため、§26.9–§26.17と§27.1の個別テストと両画面を
`recheck_accepted_m11.py`／`.cjs`で再実行し、`m11-recheck.json`／`browser-m11-recheck.json`として保存した。
M10の`verify_alternative_models_notebook.py`は基点`7cfd0864`の見出し「## 8. Longstaff-Schwartz」を
§7の終端に使うため、番号変更後のnotebookでは基点比較が成り立たない。§7の保存は上記のM11 notebook検査が代わりに確かめる。

## 限界

一定パラメータ、欧州バニラ、合成市場の例。Hull–Whiteの混合公式は無相関のときだけ成り立ち、MCは$\bar V$の台形則と
標本誤差を含む。SABRは近似式で、MCとの差は選んだ7行使価格・1満期での実測であり誤差上界ではない。Euler法の
MCはフォワードの離散化誤差を持つ（ゼロ吸収の経路は0）。rough volatilityとGARCHは説明と参照先の提示のみで、
数値検証していない。市場較正、ヘッジ成績、ジャンプは受入範囲外。
