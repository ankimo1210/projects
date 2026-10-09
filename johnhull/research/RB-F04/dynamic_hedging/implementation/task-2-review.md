# Task 2 independent source review

2026-10-09。対象: Task 2 conditional Asian / auxiliary GBM teacher。読み取り専用の独立レビュー。ソース、テスト、Git は変更していない。レビュー用 Markdown / JSON のみ保存。

## Verdict

- Spec compliance: **修正が必要**。主価格・主 Greek の invalid status は正しいが、raw 微分診断に失敗 path の隠れた zero replacement が残る。
- Code quality: **修正が必要**。同じ原因で derivative component summaries / covariance の保存値が未知性を反映しない。
- **Task 3 へのソース統合承認: 保留（false）**。下記 Important 1 件の修正・狭い回帰検証後に再確認する。
- Critical: 0 / Important: 1 / Minor: 0。
- この判定は source approval のみ。pilot、freeze、main、phase acceptance の判定ではない。

## Important I1: invalid raw path を x derivative 0 に置換する

位置: `johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py:420`（診断保存への伝播: 427–434, 520–528）。

`raw_sum` が NaN の失敗 path に対し `-(raw_sum > x).astype(float)` は 0 を作る。価格の raw/CE/CV は NaN を保持し、主 `f/f_x` は `unknown_invalid_primitives` になる一方で、raw derivative の component mean / SE / block covariance は有限値となる。元 N は維持されるが、失敗 path を暗黙にゼロ標本へ修復した診断値であり、no hidden zero および「invalid original path があれば全 metric unknown」に適合しない。

影響: 現行の主 CV / Task 3 primary price curve を有効にしてしまう問題ではない。しかし保存した raw derivative mean/SE/covariance は金融的な比較・再検算に使えず、原始証拠の failure-aware contract に違反する。

独立 tiny probe（テスト suite は再実行していない）: Heston parameters `(100,.03,.01,.04,2,.04,.3,-.6)`、N=32、2 steps、calendar `[0,.5,1]`、fixings `[1,2]`、memory_count=10、seed 17、`normals[0,0,0]=NaN`、threshold `[2]`。

保存結果:

- invalid paths: `[0]`、status: `unknown_invalid_primitives`、主 f / f_x: NaN。
- `derivative_component_means`: `[[-0.5625, NaN, NaN]]`。
- `derivative_component_se`: `[[0.08909830562090465, NaN, NaN]]`。
- first raw derivative block: `[0.0]`。
- raw derivative mean-estimator covariance: `0.012239583333333333`。

推奨する最小修正: raw derivative の invalid 個票を NaN に保ち、個票から component means、SE、block moments へ未知性を自然に伝播させる。同一原始 N / path mask は保つ。正常な raw indicator の数学定義は維持する。invalid 1 path の fixture で raw derivative の保存 summary / covariance が未知になることを確認する。

## 独立数式確認

### 正規化・単位

`R_j=S_j/S`、`x=(12K-A)/S` とすると通貨 payoff は `S/12 * (sum R_j-x)+`。従って `f` は normalized undiscounted、通貨価格は `D S f/12`。Heston は R の法則が S に依存せず `V_S=D(f-x f_x)/12`。local は `z=log S` として `V_S=D(f+f_z-x f_x)/12`、`w=log ell` として `V_ell=DS f_w/(12 ell)`。

ソース 282–300 の local coefficient は左 absolute stock と calendar midpoint で評価されるため、normalized f の absolute S dependence を保持する。Heston は S の scaling が b/c の正規化で相殺する。Task 2 自身は cache f_z/f_w を構築しない。Task 3 が上記 chain と同じ価格 surface を使うことは別の必須接続条件。

### 条件付き tail

`k=x-b>0` なら `d2=(log c+mu-log k)/sigma`、`d1=d2+sigma`。

`f=c exp(mu+sigma^2/2) Phi(d1)-k Phi(d2)`、`f_x=-Phi(d2)`、`f_xx=phi(d2)/(k sigma)`。ソース 55–64 と一致。k<=0 は lognormal mean の線形式。sigma=0/c=0 は deterministic、atom で普通の微分が存在しないことを 73–76 が明示する。

### 幾何 GBM control

`log(G/S)=(r-q-vc/2)*mean(d)+sqrt(vc)/m * sum W(d_j)`。従って分散は `vc/m^2 * sum min(d_i,d_j)`。実 fixing delay を使う 97–102 の known law と一致。

最後の stock normal の G loading は `sqrt(vc*dt_last)/m`。294–297 の normalized prefix と loading は、最後の increment が最後の fixing にだけ入ることから正しい。以前の increment は aux log-stock の累積と fixing ごとの log-sum により必要な重みが付く。model/aux は同じ last factor 0 を condition する。

`CV=CE_last(H_model)-CE_last(H_aux)+E(H_aux)` は beta=1 の unbiased identity。Heston/local 自身の geometric price を解析既知にしていない。224–237 は restart state/spot ごとに control variance を計算し直し、399–406 は同じ法則の known mean / x derivative を計算する。

### covariance / SE convention

個票成分 Y_i の SE は sample SD / sqrt(N)。B=16 の独立同サイズ block mean M_b の mean-estimator covariance は `sum (M_b-Mbar)(M_b-Mbar)' / [B(B-1)]`。356–362 と一致する。個票 SE と block covariance の対角平方根は有限標本で一致する必要はなく、別の一致推定量である。

427–429 は価格と derivative を同じ block partition で連結する。node 数を N に掛ける処理はない。Task 3 では各 node の同じ block ID を保って smooth operator を block に適用し、node 間 covariance を復元する必要がある。

## 確認した仕様適合部分

- 四つの private signatures / torch-free / 既存 SciPy と NumPy の利用。public API、init、production dependency の変更なし。
- Caller-owned `(N,steps,2)` normals、実暦 fixing indices、restart S0 の除外、元分母 12 / N の保持。
- 最後の old-v stock increment を condition し、claim に不要な最後の variance update は実行しない。
- x<=0 の exact Q linear branch は f/f_x、primary CV 個票、保存 block curve に同じ値を使う。unreplaced CV 個票は別保存する。
- negative CV 個票の価格 clip なし。sigma0 atom は unknown。stochastic all-zero/SE0、one-step tail underflow は unknown_underresolved。
- Invalid model path は primary price/Greek の全 label を unknown とする。I1 は追加の raw derivative diagnostics への伝播漏れ。
- 保存 raw/CE/CV と same16 blocks の構成・joint price/derivative covariance は、正常な path では整合する。
- 数値テストは independent quad、Black、独立 CIR root/reconstruction、非constant local one-step spot/state bump を含む。root から提示された 24-pass / ruff 結果を受領し、suite 再実行なし。

## Declined to judge / Task 3–7 integration requirements

以下は Task 2 source の範囲外または今回の証拠だけで認定しない。

1. Global 768-step IID driver の date/node reuse、market/train/test/oracle からの独立性、同じ model の全 restart の共通 block IDs。caller / runner で保証する。
2. Main K100/T1 の実 monthly12 calendar、memory_count+future fixings=12 の全 date invariant。Task 2 は calendar を受け取る core で、caller による claim mapping を認定しない。
3. Task 3 の固定 C1 tensor operator、same-price local f_z/f_w chain、support外 status 伝播、node root 一意性/J threshold、cross-node error propagation。
4. 本物 local field / Heston の金融精度、第四 moment gate の全 main/pilot candidate 適合、finite-N price/hedge precision、独立 reference 比較、768→1536 数値 refinement。
5. Pilot N/node選択、source/protocol freeze、main全attempt、P&L経済性能、学習・policy・raw failure denominators、fresh replay、notebook/checker acceptance。
6. 全 suite / release gate / build。今回再実行していない。`task-2-green.log` は以前の 16-pass/1-fail の記録であり、最終24-passのログとして扱っていない。

## Source identity

`task-2-review-source.json` の二つの SHA256 は current source と一致。review-package の追加 payload は各 current file と一致した。詳細 hash は同名 JSON review に保存する。

- conditional source: `636c6e060920c74be8f38ff0b95831effde1b72693280b2abc23c92966036b79`
- conditional tests: `ac88f7c901bfbf55bc52367fd139be7547f4a848b817277d59d94b2fcc8fb21d`
- review package: `3d08d40464a747a26813907d42b3068779a22aba6c2e8dd275487a6daa557c53`
