# 短期・0DTE v1 — 基礎実装と検証

2026-10-09。ブランチ codex/rbf05-short-maturity。main の研究成果とは区別する。

## 現在地

| 部分 | 状態 | 証拠 |
|---|---|---|
| 合成欧州call教師・時計・compact IID統計 | 基礎実装済み | 36 scoped tests、別UTC/時計/元N共分散/expiry |
| 独立級数・density/境界Gamma・Merton・3幅FD | 実装済み | 47 tests、全84候補の参照精度 preflight |
| CPU price-only / Delta-DML learner | 基礎実装済み | 25 tests、physical Gamma・plain weights replay |
| 条件・seed台帳・review/source freeze | 候補規約実装済み | 23 tests。実pilot/全金融source不足ではmain生成を拒否 |
| C² quintic Hermite・raw/safe・費用/誤差集計 | 基礎実装済み | 11 tests。独立log-spot polynomial/FD、endpoint・bound・費用祖先/overflow回帰 |
| 教師→学習→保存重み | 接続smoke済み | FOUNDATION_SMOKE.json、pilot-only16条件/32updates |
| pilot/主runner/教材builder | 実装・事前レビュー完了 | 基礎最終1275 PASS。正式pilot承認/実freeze、640教師/6fits/336点/追加12条件、両復元/3図は完了。Python19件ruff/format PASS。最終関連3suite7998 PASS/6 skip・最終独立208checks・tracked release PASS。v1受入済み、mainは未反映 |

## 判断に影響する発見

- 独立second-moment積分で最大分散1.17279024246。SE(C)≤0.002には当初の最大N2^18が不足するため、正式pilot前に2^20を追加。精度基準と元の84×3条件は維持する。価格だけの予測で正式pilotのDelta/Gamma/rare-count判断は代替しない。
- Gammaまで同じ価格関数を微分するため、discounted intrinsic＋smooth residualの構成は避ける。W>0のATM kinkを持たないunconstrained total-price networkを使用する。
- CPU学習のaccelerator RNG seed変更、ambient meta deviceでのAdam状態生成、no_grad内予測の問題を回帰RED→GREENで修正。学習数式・公開API・依存は変更していない。
- 密度Deltaの正負score積分の誤差を別々に積み上げると相対QUADPACK誤差が最終予算を超える場合があった。合計に対する絶対誤差再計算を追加し、最終精度基準は維持した。

## 接続smokeの限界

16件、N16384、1 paired seed、32updates。主実験のseed11/29/47を使っていない。
event条件2件はrare_event_unresolvedを保持した。full precision selection、主実験、
性能比較、採否、金融source freezeではない。Torch/NumPy C/Delta/Gamma再生差は
最大約5e-16。paired batch順は同一。

最初のprice-only fitにはAdamの初回準備費用が入る。このsmokeの2fit wall差を
速度優位として扱わない。主実験では共通・初回・反復・cold費用を分離する。

## 次

全関連3suite7998 PASS/6 skip（443.32秒）・19Pythonruff/format PASS。独立総合208checks/重要0とtracked release PASS。mainへ反映する。
正式pilot承認・金融source固定・主6fits/336点・追加検証・両復元・実3図/全費用は完了。[結果](RESULTS.md)。
動的ヘッジ、多曲線risk/P&L、増分XVAは全体ロードマップの後続として保持する。

## rootのレビュー対応

Hermiteのexp(log(endpoint))が生んだ重複時刻で、390分の42条件にNaNが出ることを再現し、endpointをunion前に確定する回帰RED→GREENで修正。誤差RMSの二乗overflow、費用の祖先をまたぐ二重計上、既知call下限違反もRED→GREENで修正。raw出力と元の条件数は維持した。

Minor記録：custom Hermite gridのnode自体Inf拒否は未追加（canonical生成と保存checkerの配列検査で別確認）。±2sqrtWのbucket境界には算術roundoff幅がなく、厳密境界の分類が片側へずれる場合がある。全体元分母は不変。OOD/invalid/expiryはmain固定48bucketとは別の元件数でrunnerが報告する。これらの限界を主実験前レビューと最終採否に渡す。

## 合成gate

最終基礎129件と両packageのMODEL_INDEX/docstring guardsを合わせて1183 passed（4.74秒）。[実行receipt](FOUNDATION_TESTS.json)・[stdout](FOUNDATION_TESTS.txt)。全3suite/release/研究受入の完了を示す数字ではない。

## pilot実装checkpoint

pilot.pyの全84×3・4N候補・原始draw/compact保存とsaved-only checkerを実装。21 tests PASS。固定clock/pulse/CPU networkの実装が読み取らないmetadataの不一致と、84条件/3paired-seed rosterの変更を13回帰RED→GREENで拒否した。関連163件＋両package索引/docstringで1217 passed（6.10秒）。[receipt](PILOT_CODE_TESTS.json)。full sampling、source freeze、主6fitsはまだ行っていない。

## 主実験・教材実装checkpoint

main runnerとartifact-only notebook builderを実装。全short-maturity対象と両packageの索引/docstring guardは1270 passed（19.85秒）。[実行receipt](PREFLIGHT_TESTS.json)。全3suite・正式pilot・main・最終受入の完了ではない。

pilot費用の閉集合は29 testsと独立改変再検査で確認。[pilot事前レビュー](PILOT_CODE_REVIEW.md)。runner初回独立レビューの費用・pending・fit lifecycleの3 Importantを41 testsで修正したが、再レビューで「ゼロ更新time capなのに学習済み重みを保持できる」Importantを追加検出した。追加46回帰で修正し、独立再確認で残Critical/Important0。[初回review](RUNNER_CODE_REVIEW_INITIAL.md)／[修正記録](RUNNER_REVIEW_FIXES.md)／[最終事前review](RUNNER_CODE_REVIEW.md)。最終対象gateは1275 passed（20.73秒）、Python16ファイルruff/format PASS。[最終receipt](PREFLIGHT_TESTS_FINAL.json)。

教材builderはtoy保存物を実kernelで実行し、乱数・optimizer・学習・network禁止のまま3PNGを確認した（4 tests）。正式mainからの教材生成・3図の目視は未実施。[教材実装記録](NOTEBOOK_CODE_VALIDATION.md)。金融source10件、予約seed3870件、候補84条件をcandidate_protocol.jsonへ保存した。NPZはGitへ直接追加せず、実生成後に両保管庫へ保存・独立復元する。

正式pilotの実84×3、N選択・両341054854-byte復元の数値PASSは[README](README.md#正式pilot)とJSON receiptsを参照。tracked releaseは全新source/testをcommit後にPASSした（[receipt](PREFLIGHT_RELEASE.json)）。過去のuntracked study testによるFAILを現在のPASSと混同しない。
