# Task 3 修正再レビュー — 2026-10-09

仕様適合: 承認。品質: 承認。Task5へのソース統合を進めてよい。
Critical 0 / Important 0 / Minor 0。原I1/I2は解決。phase/pilot/freeze/main/性能の承認ではない。

対象は原I1/I2とfix-review-package.diff、fix-source.json、更新report、直接関連する小確認だけ。保存されたfix-before参照/テストのhashは原レビューと一致し、現行3ファイルはfix manifestと一致した。surfaces本体のhashは原版から不変。19 scoped tests・ruff/format PASSは受領証拠として扱い、green suiteは再実行しない。ソース・テスト・Gitは変更せず、この再レビュー2ファイルだけを書いた。

I1 解決: reference_methods.py:255–258の独立xi=0 branchがtheta+(v-theta)*exp(-kappa*dt)を使う。stockは保存した旧varianceで更新する。原N32/seed17、v=.08/theta=.04、t=[11/12,23/24,1]の同一driver確認に、独立のspot/state半幅central bumpを加えたところ、価格・spot微分・state微分の個票差は各0。元N32は保持される。追加テスト321–356も非定常varianceの価格fixtureを持つ。

I2 解決: reference_methods.py:619–665でquad full_outputのP1/P2 raw値・absolute error・message/status・neval・使用subinterval・limit/tolerance/cutoffを保持し、通貨価格へ誤差を換算する。未収束の普通の返却価格はNaN、finite raw価格はreceiptに残す。selected helper:89–107,136–185は全base/bump receiptを保存し、積分によるprice/derivative errorをrefinement/finite-width差から分離する。未収束はNaNを通じunknownへ伝播する。

原limit1の小確認では、directはunknown、ordinary priceはNaN、raw priceはfinite、両積分はnonconverged。通貨換算errorは独立手計算と差0。selectedはunknown、39件のbase/bump receiptとnumeric derivative errorを保持する。成功側の通常candidate小確認はconverged、価格7.847973573300706、積分価格誤差推定8.65430464637659e-11。これはreceipt実装の確認であり、正式pilotの精度達成を認証しない。追加テスト359–381が未収束の保存・伝播を固定する。

Task5へ引き継ぐ要件は原レビューから変わらない。callerはcall/Asian state支持域の交差を明示設定・検査し、solver/interpolationのokだけで精度適格化しない。NaN/unmeasured errorを拒否し、独立参照の収束・有限error・固定gateとF07への誤差伝播を実装する。QUADPACK誤差推定はcutoff/grid/bump誤差と別で、厳密なtruncation boundではない。

18-state正式pilot、実grid/grid doubling、N/SDE refinement、Q/P&L gate、Task5 caller/checker/serialization/replay、runtime/memory/性能、source/protocol/pilot freezeとmain/phase受入は未判定。現行source・fix package・preserved originalsのSHA256は同名JSONに保存した。
