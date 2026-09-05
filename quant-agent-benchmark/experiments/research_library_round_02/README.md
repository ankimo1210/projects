# 論文 × QuantLib 比較実験キット

現行計画は**全7モデルに論文＋QuantLibを与え、各1セッションだけ実行する**形。
実験用の規約・データ・資料・環境・7個の候補フォルダを準備するキット。
**各モデルの起動、非公開評価の実行、Git pushはしない。**
旧提出物・旧評価器・旧スコアは変更しない。

## まず見るもの

- [現行の全7モデル併用計画](COMBINED_PROTOCOL.md)
- [各モデルへの配布リンク](DISTRIBUTION.md)
- [全モデル共通プロンプト](public/combined_prompt.md)
- [新しい支払規約](public/CONVENTIONS.md)
- [モデルとキャンペーンの設定](config.json)
- [現行7実行分の検証結果](validation_combined.json)

対象はAstra/Sol/Terra/Luna/Sonnet/Opus/Fable。全員が併用条件、各60分。
同じ1セッション内で変更前・規約修正のみ・最終版を保存し、改善量を比較する。
論文とライブラリの個別効果・追加時間の効果は切り分けない。
旧100点スコアではなく、新しい隠しシナリオの年限別精度・フォワード・未見商品・
費用で比較する。1回の実行で統計的な優劣を断言しない。

旧4条件pilotは保存のみで今回使用しない。
[旧計画](PROTOCOL.md)、[旧プロンプト](public/common_prompt.md)、
[旧検証結果](validation.json)、[旧準備監査ノートブック](preparation_audit.ipynb)は履歴として残す。

## このMacで準備した場所

```text
/Users/ankimo1210/Documents/quant-agent-benchmark-private/
├── runtime-round-02-base/         # 旧pilot A/B用。今回不使用
├── runtime-round-02-quantlib/     # 今回は全7モデルで使用
└── research_library_round_02/
    ├── suite/                    # 主催者専用：訓練真値 + 非公開12シナリオ
    ├── materials/                # 元論文PDF・公式資料・SHA-256
    ├── baseline_training/        # 主催者QuantLib基準器の公開訓練データ出力
    ├── pilot/                    # 旧12実行分を変更せず保存。今回不使用
    └── combined_all_models/
        ├── run_plan.json         # 全7run prepared_not_started
        ├── astra_r1/PROMPT.md    # このファイルだけを対応タスクへ渡す
        └── ...                   # 各runにinput/baseline/materials/work/audit
```

各runのPROMPT.mdはMODEL_KEY/ARM/REPEAT/パス/Pythonを展開済み。
親combined_all_modelsフォルダ、旧pilot、suiteを候補へ公開してはいけない。
秘密データ・PDF・仮想環境はGit外。公開するのは本キットのソースと手順だけ。
PDFの再配布権は別途確認する。

## 準備状態を再検証する

```bash
cd /Users/ankimo1210/Documents/projects/quant-agent-benchmark
PYTHONDONTWRITEBYTECODE=1 /Users/ankimo1210/Documents/quant-agent-benchmark-private/runtime-round-02-quantlib/bin/python experiments/research_library_round_02/owner/validate_preparation.py --campaign combined_all_models --private-root /Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02 --output /Users/ankimo1210/Documents/projects/quant-agent-benchmark/experiments/research_library_round_02/validation_combined.json
```

候補作業開始後はwork_copyが当然変わるため、この**起動前**検査を再実行して
「データ破壊」と判断しない。初回検証結果を保存し、提出時にはimmutable部分と
最終提出物の別manifestを記録する。

## 別の場所で再準備する場合

ownerスクリプトは --help で引数を確認できる。順序は:

1. requirements-quantlib.txtからPython 3.12環境を用意。全7モデルで共用する。
   旧pilotも検証する場合のみrequirements-base.txtの別環境も用意する。
   推移依存も固定。既存の本番環境を変更しない。
2. owner/fetch_materials.py --destination にGit外の**新規**資料フォルダを指定。
3. owner/datasets.py --private-dir にGit外の**新規**suiteを指定。
   128bit seedを生成し、真値・パラメータ・seedをそこでのみ保存する。
4. owner/prepare_combined.py にroot/suite/materials/quantlib-pythonを指定。
   または owner/prepare_run.py --campaign combined_all_models --arm D でモデルを1つずつ準備。
5. owner/validate_preparation.py --campaign combined_all_models で確認。
   ローカル検証器は旧base環境との版比較も行う。既存run/suiteの上書きは拒否される。

新suiteを作り直した場合は全モデルで同じsuiteを使い、旧suiteと混ぜない。
1モデルだけ再試行して都合のよいrunを選ばない。

## QuantLib基準器

owner/quantlib_baseline.py --market-data CSV --output-dir NEW_DIRECTORY

QuantLibのlog-linear discount curveとSciPyのrobust least squaresを使用。
価格付けは実数年限の明示cash flowで接続し、暦日への丸めを避ける。
これは規約と接続の基準器であり、完全な候補CLI/研究成果物でも、最良推定法でもない。
単位補正等はヒューリスティックで、未知の市場での正しさを保証しない。
候補へこの基準器や出力を渡すと実験条件が変わるため、主催者専用とする。

## 提出後の評価

ホスト側で**別の隔離実行環境**を用い、固定した候補に各ケースの市場CSVだけを渡す。
出力を `predictions/<case_id>/curve.csv` に保存してから、主催者が次を使う:

```text
owner/evaluate_curves.py --suite PRIVATE_SUITE --predictions PREDICTIONS --output NEW_JSON
```

このスクリプトは候補コードを実行せず、保存されたカーブを採点する。
欠落・失敗を除いた平均は作らない。コストは実ログ取得後にPROTOCOLに従って集計する。

## 起動前に残ること

ホスト側のファイル/ネットワーク隔離と実アクセス拒否テスト、モデル設定と
セッションIDの記録。これらは本キットで自動設定していない。
`preparation_valid=true` と `launch_ready=false` は両立する。
chmodやプロンプトはセキュリティ境界ではない。現状のフルアクセスのタスクへ
PROMPTだけ渡して「ブラインド実験」と呼ばない。

検証スキルに従い、比較規約とデータ混入検査を推定法より先に固定し、主指標を
ゼロRMSE、診断を年限別/フォワード/価格、ガードレールを失敗率と形状に分離した。
