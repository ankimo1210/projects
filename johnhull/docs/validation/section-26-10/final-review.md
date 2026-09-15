# M2b §26.10 最終独立レビュー

日付: 2026-09-15 JST。開始コミット: `ad3b9ab5e501654acdbe61b331b89104b41502c6`。

**判定: 承認。重大・中程度の未解決指摘なし。** D01–D06の教材・4図・検査・配布証跡の接続は整合している。コミット・main反映・pushはcontrollerの担当で、本レビューはそれらの完了を意味しない。

## 対象と方法

`changed-files.txt`、両task brief、最終承認済みtaskレビュー、`final-source.diff`を確認した。新ブラウザ検査349行、実際の受入ノート、M2b統合記録、両節のbrowser記録、§26.9 m2b-recheck、台帳D01–D06全件とB01ほかの参照、現行・履歴文書の差分を読んだ。生成notebookはJSONから必要なsourceと出力だけを抽出した。

実装を変更せず、ビルド・ブラウザ検査の再実行・コミット・追加agentは行っていない。唯一の成果物書込みはこのレビューファイルである。原典数理の詳細は既に独立承認済みのTask 1/2レビューを前提とし、本レビューは統合と証跡を中心に確認した。

## 指摘と解消

- **P3・解消済み — 生成元と同期保証の説明。** `johnhull/report/report_builder/figures.py:3–6` の「全builderがplotly_viz由来」「gallery can never drift」は新しい内部教材builderと検査の必要性を正確に表さず、`johnhull/report/README.md:8` の生成元一覧にも内部教材がなかった。controllerによる共有hullkit/internal lesson/versioned artifactsとsemantic/browser検査を説明する修正を実ファイルで再読し、解消を確認した。金融計算・描画動作の変更はない。
- **証跡表現の明確化。** `verify_core_notebooks.py:177–186` の比較は出力種別・MIMEキー・正規化した決定的テキストを対象とし、画像/Plotly payloadの全値比較ではない。「保存出力と別実行一致」はこの範囲として読む必要がある。これは既存checkerを広げる要求ではない。本レビューでは補完として、保存された新4図のPlotly JSON全dataとlayoutを現行 `_figures()` の生成値と比較し、全4図の完全一致も確認した。controllerへ受入記録の表現の明確化を依頼した。

## 統合上の確認

- ブラウザ検査は実際のメニューヘッダーとcall/putボタンをclickし、タイトル更新後の可視 `_fullData` を検査する。各選択でcash/assetの符号付きleg・再構成・vanillaを80/100/120の各点で個別照合する。
- payoff検査はactual payoff roleだけを使って4契約のtieを確認し、one-sided-limit markerを実際の決済と混同しない。誤った個別legを合計だけで見逃さないよう、putのcash+1/asset−1という一時改変を両配布面で拒否し、元データへ復元後に再照合する。これは固定元配列だけの検査ではなく、描画中の可視traceに対する検査である。
- Bookの価格検査は4契約名と6桁価格を同一table row内で照合する。spread/butterflyはh=1/5/15で別のvanilla-payoff計算、deltaは3満期の独立積分差分基準を使う。
- 両配布面で4図を特定し、viewport幅1440/1000でoverflow、図内の注記/タイトル/凡例の境界、凡例と注記、軸文字と凡例文字の交差を検査する。Bookは6小節、数式52箇所、math error 0、両幅の数式overflow検査を持つ。portalはHTTP(S)遮断下で外部要求0。Bookの既存MathJax CDNは明示的な依存として残る。
- notebookのbinary4図は別々のshowセルで、各保存出力にPlotly MIMEとHTML fallbackが存在する。4価格表の出力も保存されている。55セルという記録と一致する。
- §3以降のbuilder本文とnotebookのcell type/source列は開始コミットと一致する。旧変数を維持したため後続lessonの暗黙依存を壊していない。
- 台帳はaccepted2/unreviewed304。D01–D06に説明・実装・独立検証・図・描画の各根拠がつながる。D04の定性的要求は価格エンジン/数値oracleをnot_applicableとし、理由が明示される。D05を原典の追加小節であるかのように主張していない。
- §26.9は共有sourceの変更後に171テスト・新notebook出力・両配布面を再検査したm2b-recheckを参照する。historical double-checkのbytesは開始コミットから変わっていない。古い記録のハッシュだけを新規証拠として更新していない。
- 現在地のROADMAP/ledger/guide/handoff/acceptanceと、M2a等の日時付き履歴が区別される。portal86図/12テーマ/exotics6図のregistry・manifest・README・テストが整合する。

## 本レビュアーの独立検証

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=johnhull/hullkit/src:johnhull/report /home/kazumasa/projects/.venv/bin/python -m pytest -q -p no:cacheprovider johnhull/hullkit/tests/test_binary_lesson.py johnhull/hullkit/tests/test_binary_reference.py` → **92 passed in 0.81s**。
2. 保存notebookの新4図についてPlotly JSONの**全dataと全layout**を現行共有builderから生成した値と比較 → **4/4一致**。
3. browser記録の4価格と3満期deltaを、production pricer/CDFを使わず標準正規log-return密度積分とRichardson対称差分で再計算 → **全件一致**。価格差は1e-10未満、delta差は1e-8未満（実測最大約3.2e-11）。レビュー用積分の初回はasset payoffの中間expでoverflowしたため、指数を結合して再実行した。製品コード・テストの失敗ではない。
4. builder/notebookの§3+をbaseと比較、historical double-checkをbaseとbyte比較 → **一致**。
5. 更新前の証跡4JSON（binary m2b/browser、barrier m2b-recheck/browser）の全**89 source/artifactハッシュエントリ**を実ファイルと照合 → **一致**。P3文書修正後のcontrollerによる証跡再生成は別途最終追記で確認する。
6. `git diff --cached --check` → **PASS**。

controllerのログと実記録で、full pytest **1549 passed / 既存警告2件 / 76.84秒**、binary92、barrier171、registry/build契約、Book31ページのbuild成功、portal86/12、両ブラウザ記録のPASSを確認した。full suiteとブラウザの再実行は本レビュアーが行ったものではない。Bookビルダーは36警告を報告し、捕捉された分類行はPlotly MIME30件・見出し5件である。分類行合計を36件と誤記せず、新4図のHTML fallback確認と警告の限界を記録している。

## 残る実施範囲と限界

最終レビュー欄・関連ハッシュの更新、コミット後のtracked release契約、main反映・pushはcontrollerが実施する。新たな公開pricing APIや本番依存の追加はない。今回の承認は合成条件の当該教材と記録されたChromium/2幅の配布確認に限定される。Bookの完全offline、モバイル、他browser、全巻目視、全入力域、T=0/sigma=0、点質量、市場性能を承認していない。

## 最終証跡更新後の再確認 — 承認維持

再確認時刻: 2026-09-15T04:55:07.509990+00:00

- 最新のbinary `m2b-check.json` / `browser-check.json`、barrier `m2b-recheck.json` / `browser-check.json`の全**90 source/artifactハッシュエントリ**を実ファイルと照合し、すべて一致した（41+17+18+14）。4記録はすべてPASS。両binary配布面のcall/put選択、個別legのnegative control拒否、page error 0も再生成後の記録で確認した。
- 台帳の§26.9/§26.10の全**38 evidenceエントリ**について実ファイルのSHA-256一致を独立確認した。
- 最新の受入ノート:53、VALIDATION:20、vol10 PROGRESS:8、両m2b記録の `notebook.comparison_scope` を再読した。core notebook比較が出力型/MIME/正規化テキスト（計時セルは型のみ）であり、画像/Plotly payloadの全値比較ではない点が明示された。図の別検査と本レビューで実施した全data/layout比較を混同する表現は解消している。
- 台帳CLIの通常モードと `--check-artifacts` を本レビュアーが再実行し、両方 **PASS / inventory306 / accepted2**。`git diff --cached --check` も **PASS**。
- registry docstringとreport READMEのP3修正を含め、**未解決のレビュー指摘はない。最終判定は承認を維持する。**

検査時の `review.final_integration_review` はまだpendingである。これはcontrollerが本承認を記録し、その記録変更のledgerハッシュを更新するための残タスクであり、実装・教材・検証の不合格ではない。コミット後のtracked契約とmain反映/pushは引き続きcontrollerの実施範囲である。
