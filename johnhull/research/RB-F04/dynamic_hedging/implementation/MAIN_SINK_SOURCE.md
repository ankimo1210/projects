# 主実験結果の分割保存接続 — source確認

2026-10-10。**限定source承認済み。正式pilot・freeze・主実験・金融精度・研究受入は未完了。**

## 実装範囲

`run_reference.run_execution_main` に任意の `evaluation_sink` を追加した。事前のsource、別execution readiness、元12fit、4×14baselineの保存検算を通った後、各生成モデル・seed・level・取引集合の結果をsinkへ渡す。全18ケース×2集合の36結果が、元44cell×3seed×3levelの396件を収録する。

sinkを指定した場合は返却されたcaller所有の参照だけを結果リストへ保存し、元のrowと配列への参照を次の評価前に解放する。全件の元経路配列を同時にメモリへ保持する必要を減らす。sinkが返す参照に配列を入れた場合のcaller側の保持は制約しない。

sink未指定の戻り値と旧strict v1入口を保持する。保存例外はそのまま伝播し、欠損artifactをretryやfallbackで補わない。sourceやraw guardに失敗した場合はloaderもsinkも開かない。

これは保存接続の実装であり、結果参照のbyte由来・元配列の保存復元・金融算術の検算は正式main実行器とcheckerの責任である。全費用・Q・数値精度・頻度診断の受入もこの変更だけでは成立しない。

## 検証と限定レビュー

| 検査 | 結果・範囲 |
|---|---|
| 著者のscoped tests | 41 PASS、28.44秒。追加2件はREDからGREEN。元N32,768の配列、36回の順序、weakrefによる解放、事前gateの拒否をsource-unitで検査 |
| 独立検証 | runner41件＋当時のmain15件＝56 PASS、30.96秒。著者41件へ重複加算しない |
| 独立writer例外probe | PASS。最初のsink例外を伝播、retry・fallbackなし |
| 変更Python2ファイル | Ruff check / format PASS |
| 独立レビュー | 未解決0、宣言した保存接続sourceのみ承認 |

評価engineとsource registryは合成のsource-unit入力である。実A/raw guardは保持したが、正式Heston/local市場経路や396件の金融結果を計算した証拠ではない。返却qualificationもunknownのままである。

## sourceと原証拠

| 対象 | SHA-256（由来の照合用途） |
|---|---|
| `run_reference.py` | `7a8f4a3e3d0289a06ca2d1732fe8287a3a87a1ca10a2585a4e3fab400ae22110` |
| `test_dynamic_hedging_runner.py` | `88474feec57cb9b6fff64be2251b2a237b43be164885304338355766658726e7` |

[原証拠一覧](sink-source-evidence/files.json)。RED/GREEN、独立レビュー、probe source・stdoutを原byteで保持する。Python・logの原証拠は末尾に `.txt` を付ける。数値の比較にSHAは使わない。

次は正式pilotの保存算術・caps・sourceレビューを完了し、事前planと原入力を固定する。主実験実行器はこのsinkへimmutable artifactsを書き、全396件の元分母・失敗・費用・数値誤差をcheckerで再検算する。両CAS復元・3図・全関連suite・最終独立受入・main統合は後続で行う。
