# M22 §26.5 Forward Start Options

承認範囲：既存計画P2とユーザーの「1 and move to next」に従い、M21をmainへローカル統合し、次の§26.5を実装する。日付2026-10-01。原典：Hull 11e Global Edition p.618。準備資料：`docs/prep/sections/ch26.md` §26.5。

## 目的と要求

ATM欧州型コールの開始時点T1、開始時点で決まる行使価格S(T1)、満期T2を明示し、説明・実装・独立検証・図・実画面の5軸で受け入れる。原典に印刷数値例はない。価格と経路は仮定を示した合成例とする。

- FS01：満期給付max(S(T2)−S(T1),0)、行使価格決定と支払の時点、従業員オプションの将来ATM付与との関係を説明する。
- FS02：τ=T2−T1、同じ長さの今日のATMコール価格cを用い、開始時点の価値cS(T1)/S0と現在価値c exp(−qT1)を導く。定数r,q,σのGBMに限る。
- FS03：新しい専用モジュール`hullkit.forward_start.forward_start_call(S,r,sigma,T1,T2,q=0)`でscalarとbroadcast可能な配列を扱う。S>0、σ≥0、0≤T1≤T2、すべて有限。T1=0はvanilla、T1=T2は0、σ=0は決定的給付、q=0は同じτなら開始時点によらない。
- FS04：hullkitと正規CDF公式を使わない二時点GBMの密度求積と、固定seedの二時点Monte Carloを別に作り、価格・一次同次性・開始時点の割引・τの取り違えを検出する。MC標準誤差と求積誤差は区別する。
- FS05：vol10 §4.12.1–4.12.6に共有4図を追加する。経路上のstrike fixing、開始時点価値の一次同次性、τ固定の開始日掃引、T2固定の開始日掃引を示す。後二者の契約の違いを明記する。
- FS06：M21の旧169セルを保持し、Book/portal×1440/1000pxの16状態・16画像、数値改変拒否、既受入21節のD1再検査、両保管庫復元、台帳受入22・未評価284を検証する。

## 構成と制約

既存pricingコードと公開関数のシグネチャは維持する。新しいproduction依存は追加しない。`forward_start.py`はBSMの一次同次性を利用し、既存の複数の専用公開モジュールと同様に直接importする。`hullkit.__init__`への追加は不要。`_forward_start_lesson.py`は検証済み保存参照から図を作り、notebookとportalが共有する。汎用moneyness・put・cliquet・smile dynamicsはこの節へ追加しない。

scalar APIはfloat、配列APIはbroadcastしたshapeのndarrayを返す。非実数、非有限、負の時点、満期の逆転、負のσ、不整合shape、表現可能範囲を超える計算はValueErrorとする。ゼロ長契約は過大な割引率でも0を返し、不要な指数計算を行わない。

作業は既存の分離worktree `/home/kazumasa/worktrees/m18`、branch `codex/m22-forward-start-options`。基点はM21を統合したmain `e2706e43`。共有venvを使いGit/buildはWSLで実行する。mainのmarket-research変更は保持する。M22はローカルでコミットし、pushやmain統合は別の明示選択を待つ。

## 受入

参照・数値・notebook・browser・M22統合ゲート、台帳の通常/成果物照合、hullkit+report全pytest、ruff、release contractとコミット後のtracked-file検査がPASS。独立した最終レビューを1本行う。D1 driverは依存不変なら再利用、変更なら描画を選ぶ。旧基点固定notebookゲートは履歴用として保持し、現行保持はM22 notebookゲートとD1で検証する。
