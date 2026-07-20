# Reproduction scope

本プロジェクトは次の4区分を混同しない。

- `A_AUTHOR_CODE_EXACT`: 固定した公式コードの挙動を対象とする。
- `B_PAPER_EXACT`: 論文が明示した設定だけを厳密に固定する。
- `C_PAPER_CONSTRAINED`: 論文の制約内で、未開示事項を assumption として分離する。
- `D_MODERNIZED_AUDIT`: leakage、device、安全性などを監査する訂正版。

既定の成果はすべて合成データ上の structural reproduction である。論文の accuracy、
F1、stock-level empirical conclusion は検証対象外であり、実データを追加して同一
dataset variant、split、label、horizon、feature、metric を満たすまで数値比較しない。

DeepLOB の TensorFlow 2 profile は、公式 notebook の実行仕様と解析的 parameter
count を既定環境で検証し、TensorFlow を導入した環境でのみ native forward を行う。
DeepLOB 公式コードは指定コミットで明示的ライセンスがないため、再配布しない。

