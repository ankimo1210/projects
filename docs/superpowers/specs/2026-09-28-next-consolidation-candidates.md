# 次の統合候補の個別調査

更新日: 2026-09-28。対象: `rates_volatility_model`、`johnhull/hullkit`、境界確認として `deep_hedge_price`。調査は現在の実装・依存・対象テストに限定した。

## 判断

**現時点では3つとも独立継続する。** 名前が似たモデルをまとめても、フォルダを探す負担はほとんど減らず、`ratesvol` の教材用の実装と `hullkit` の独立照合を失う。ルート索引の関連表示を確定し、実際に共有したくなった関数単位で再評価する。`deep_hedge_price` は PyTorch を使う学習・評価の正本として保持する。

| 領域 | `ratesvol` | `hullkit` | 判断 |
|---|---|---|---|
| lognormal SABR | [smile.py](../../../rates_volatility_model/src/ratesvol/smile.py) の `sabr_black_vol`・較正・ATM逆算 | [sabr.py](../../../johnhull/hullkit/src/hullkit/sabr.py) の独立式・Greeks と [sabr_normal.py](../../../johnhull/hullkit/src/hullkit/sabr_normal.py) の normal / shifted 系 | 式の重なりはある。教材の別実装を保持し、共通化しない |
| 金利オプション・短期金利 | Black-76 / Bachelier、Vasicek / CIR / HW1F / G2++ の教材・シミュレーション | Hull-White の厳密遷移・債券オプション・Jamshidian swaption、より広い金利ライブラリ | 入出力・精度・教材の目的が異なる。関数を無条件に置換しない |
| 市場モデル・スマイル | 教材の HJM、spot 測度 LMM、SVI と delta-strike | 金利・ボラ・信用を横断する参照実装 | `ratesvol` に固有の学習経路を維持 |
| ニューラル価格・ヘッジ | 対象外 | torch-free の金融教師と検証 | [deep_hedge_price](../../../deep_hedge_price/README.md) の学習・checkpoint・walk-forward は引き続き独立 |

`rates_volatility_model/tests/test_smile.py` の4つの SABR golden 値は独立実装 `hullkit.sabr` と照合した値であり、実行時に `hullkit` を import してはいない。この比較を単一の関数に置き換えると、実装間の独立性がなくなる。一方、golden 値だけでは全パラメータ域の同等性は保証しない。将来の共通化は公開 API の単位・エラー条件・較正出力・ノートブック実行を比較し、独立した参照を残せる場合に限る。

## 見つけ方と再評価条件

- `rates_volatility_model` は [教材入口](../../../rates_volatility_model/README.md)と `ratesvol` のまま、`johnhull` は [モデル索引](../../../johnhull/MODEL_INDEX.md)と `hullkit` のまま使う。ルート索引には両者の関連と独立継続を記す。
- 同じ市場データ前処理や同じ検証 fixture を**実際に**二重保守し始めたら、その部品だけ共有を再検討する。先に利用側の入出力契約・単位・許容差・性能を並べる。
- `johnhull` の M15 は [D1-preflight](../../../johnhull/docs/prep/design/D1_PREFLIGHT_PLAN.md) の完了後。今回のフォルダ判断を M15 の受入や D1 完了と混同しない。
- `rough_volatility`・`optimal_execution` は [johnhull の境界](../../../johnhull/CLAUDE.md)で独立とされる研究ラボ。今回の3件の証拠だけで統合や退避を決めない。

## 確認した検証

2026-09-28、専用 worktree で `rates_volatility_model/tests` **63 passed**（ノートブック実行を含む）。`hullkit` の SABR / normal SABR / Hull-White / 金利 / RFR 関連7 suiteは **56 passed**。これらはコード移動をしていない状態の回帰確認であり、将来の統合後の互換性を証明するものではない。
