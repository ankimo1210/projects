# M28 §28.3 Martingales

日付2026-10-04。目標はP3 Ch28–34の37節全体の完了。本節はその第3受入単位。原典GE pp.675–676、p676画像と本文を照合。M27 main0aa51b13から承認済み工程を継続する。

## 意図・完全性

脚注3の履歴に条件付けた定義、式28.14のItô比のdrift相殺、式28.15の価格恒等式を教材/API/独立参照/図/両配布画面で検証する。時点0の標本平均一致だけでmartingaleを証明したとはしない。
本文のzero-driftという説明と、数学的な追加条件（正値取引numeraire、無収入、可積分性、有限時間GBMで全モーメント有限）を明確に分ける。一般の零drift局所martingaleを自動的に真のmartingaleとしない。時間・状態依存係数の原典定理を説明し、数値実演は定数係数GBMと表示する。確率金利の実演は§28.4、複数因子は§28.5へ継続しP3完了条件から除外しない。

## 計算契約

private hullkit._martingales: ratio_drift(mu_f,mu_g,s_f,s_g)はa=mu_f−mu_g+s_g(s_g−s_f)、ratio_conditional_mean(value,mu_f,mu_g,s_f,s_g,horizon)はvalue*exp(a*horizon)、numeraire_drifts(r,s_f,s_g)は(r+s_g*s_f,r+s_g²)。same Wiener source、signed loading、率year^-1/係数year^-1/2/horizon year、value=f_t/g_t>0。
有限実数/broadcast/real object/empty batch有効、complex（object内も）・NaN/Inf・不整合・計算overflow/正値平均underflow拒否。horizon>=0/ratio>0はbroadcast前に検査しempty batchで不正設定が隠れない。scalar float/batch ndarray。公開API/root exports/production依存は変更しない。

## 独立参照・教材

mathのみの参照：符号付き6市場、各市場のlambda=s_g/誤lambda、Itô drift項とlog drift、9条件付きfixture(t=0,.3,.7,T=1.5;state=.5,1.25,2)、複数horizon条件付き曲線、finite第二モーメント。時点0の比.5/2は別初期市場で、固定S0=100/G0=80の時点0は1.25のみ。call市場はこの条件付きfixtureとは別の例。r=.04,s_f=.3,s_g=.15/−.2、S0=100,G0=80等の追加例は全てsynthetic、印刷数値なし。
同一call給付K=100,T=1.5をcash/QとG測度で直接Gaussian求積、閉形式、固定seedの直接標本/SEで照合。条件付きMCは262144標本×9状態時刻、future incrementを独立生成し解析値との差/SE<=5、raw値を自己正規化しない。価格求積誤差1e−9、解析API差1e−12、保存4改変/実API4変異を拒否。
新親##6B. マルチンゲール（§28.3）、6B.1–6B.6の11セルを##7前へ追加し旧235セル本文/出力/Plotlyを保持（計246）。4共有図martingale_ito/conditional/conditional_mc/pricing。lessonはhashと結果配列のshape/有限性/独立参照一致を検査してから描画。

## 受入条件

27旧節D1、C:/F:復元、4--check/ruff/全hullkit+report/台帳--check-artifacts/tracked release、Book/portal×1440/1000の16状態/16画像/全trace/MathJax/幅700px/数値改変拒否。190図/12テーマ/exotics78、public72/private29。MT01–MT06の5軸、accepted28/unreviewed278/P3 3/37。新fresh reviewer一度、Important修正はRED→GREEN+全suite。既に承認されたmain統合/pushを検証後に実行し、P3の残34節を継続する。
