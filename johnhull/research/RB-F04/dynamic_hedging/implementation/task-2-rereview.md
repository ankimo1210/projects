# Task 2 independent scoped rereview

2026-10-09。元レビュー Important I1 と修正差分・追加回帰だけを再確認。ソース・テスト・Git の変更なし。suite の再実行なし。

## Verdict

- Spec compliance: **承認**（Task 2 source scope）。
- Code quality: **承認**（Task 2 source scope）。
- **Task 3 へのソース統合承認: true**。
- I1: **解消**。新規 Critical / Important / Minor: 0 / 0 / 0。
- 元レビューで確認した数式・正規化・control・16 block の結論を維持する。この再レビューは source approval であり、pilot / freeze / main / phase acceptance ではない。

## I1 修正確認

`johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py:407–410` は非有限 raw_sum の raw x derivative を NaN とし、raw / conditioned / CV 全微分個票に original path_mask を適用する。元 path を drop せず、N と 16 block の定義を保つ。正常 path の indicator・CE・CV 数式に変更はない。

`raw_x_samples` / `conditioned_x_samples` の追加保存により、既存 f_x_samples とともに原始診断から unknown 伝播を検算できる。invalid path のみを補修せず、通常の NaN 演算を通じ derivative mean / SE / block covariance / joint covariance が unknown になる。

追加回帰 `test_invalid_original_path_keeps_derivative_diagnostics_and_covariance_unknown` は N32 と original denominator、invalid row の全微分 channel、valid row の finite 維持、component means / SE、block / joint moments の NaN を検査する。今回の失敗原因に直接対応する。

## 独立確認と証拠

元レビューと同じ tiny probe（N32、2 steps、Heston seed17、normals[0,0,0]=NaN、threshold2）を再実行した。結果:

- N=32 / original_path_count=32 / status=unknown_invalid_primitives。
- raw_x_samples / conditioned_x_samples / f_x_samples の invalid row は全 NaN、valid rows は有限。
- derivative_component_means / derivative_component_se / derivative_block_covariance / joint_block_covariance は全 NaN。
- first derivative block / first joint block は全 NaN。

修正 manifest の二つの current SHA256 は一致。修正前保存ソースは元レビュー source hash と一致しており、修正の基準を保持している。

- source: `37ebedfe935526fbf25d93f41b4e572b60f895efd88606aa26d93e07a519fbe5`
- tests: `a1b5844de2077eef344e49af7627d4f280a67fdac70b490d5d85de91ee1fa9fb`

Implementer と root から RED 24-pass/1-fail → GREEN 25-pass、ruff check / format PASS の証拠を受領。今回独立に suite を再実行していない。

## 範囲外・残る接続条件

元 `task-2-review.md` の Declined-to-judge を維持する。Task 3 の same-block node aggregation / same-price smooth f derivatives / local f_z chain、caller の monthly12 mapping と独立 CRN stream、moment / precision pilot、source freeze、main・経済性能、fresh / saved-only checker、全suite / phase acceptance は今回未認定。これらは将来の integration / phase gate であり、解消済み Task 2 source defect ではない。
