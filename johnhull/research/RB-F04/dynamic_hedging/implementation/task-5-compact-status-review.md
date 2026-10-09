# Task5 compact status 独立レビュー

2026-10-09。source/spec/quality は **proceed 可**。Critical / Important / Minor / unresolved はすべて 0。正式pilot・主実験は未承認。

## 確認した範囲

- private optional `compact_status=False` の変更diffと、対象30件PASS・ruff2ファイルPASSのrun receiptを読み、現在の2 source SHAと一致することを確認した。全suiteは再実行していない。
- 変更前の保存sourceを別名で読み、Heston/local・正常/非有限driverの4ケースで旧35キーすべてを比較した。default と compact の金融値は `rtol=1e-12, atol=1e-14, equal_nan=True` で一致。category・mask・理由・原始Nは保持。
- 独立の混合local fieldで interior / wing_left / wing_right / wing_both / early_time / novel_status / unsupported_time / nonfinite_coefficient を確認。全32経路×8step、失敗27経路を落とさず、辞書復号が旧Unicode cubeと一致した。失敗後・未実行stepの空categoryは code0 のまま。
- settled の32×0stepでは空cubeと legend [""] を保持。未来index0・範囲外・重複・逆順・非整数を default/compact の両方で拒否することを確認した。
- NumPy full / zeros / empty / ones に独立allocation recorderを付けた。compact の32×8step allocation は uint8 の1個のみでUnicode cubeはなかった。sourceでもUnicode cube作成は false branch に限定される。
- 256個の非空category（空categoryを含め257個）を供給すると明示ValueErrorになり、uint8 overflow/上書きは起きない。現行LocalVarianceGridのcategory数はこの上限内。

## メモリと限界

最大候補65536×768で status cube は legacy 12,884,901,888 bytes → compact 50,331,648 bytes。Unicodeは辞書の小配列とstep単位vectorに限られ、元の全経路/stepのcoordinateは残る。この最大サイズ自体はレビューでallocateしていない。

辞書はlegacy category幅64を継承する。これは保存形式の変更の承認であり、金融モデル・Q整合性・教師/Greeks・P&L・正式pilotの精度認証ではない。source/testsの変更はレビュー側では行っていない。

## Source provenance

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py`: `9007e30a45375fbb7c8b4afe5fa4e4f694b5bc68e924b138bd993d8bdbf2b025`
- `johnhull/hullkit/tests/test_dynamic_hedging_conditional.py`: `cfed5aaa3aa87abcb8ef90b45d8d0b733a3e83506f343e3eb67aec878240ef83`
