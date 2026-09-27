# ワークスペース整理計画

更新日: 2026-09-27  
状態: 調査と計画。移動・統合・削除・履歴変更は未実施。

## 目的と決まった方針

第一目的は、使いたい成果物をすぐ見つけられ、各プロジェクトの役割と正本が分かること。市場データ・投資分析・可視化からコード統合を始め、既存のいずれかに寄せるのではなく、新しい統合プロジェクトを作る。最終的には少数の大きなプロジェクトにしたい。完成した小さな学習・実験作品は成果として見える場所に残す。アーカイブは「後継があり内容が重複」を主な基準とし、候補ごとに確認する。

継続利用の可能性が高い johnhull、不動産投資関連、portfolio-analyzer は更新日だけで退避しない。portfolio-analyzer は当面独立させ、新しい市場分析基盤との連携を設計する。独立リポジトリへ移管済みの re_invest_os は、このリポジトリからの案内リンクを整える。既存の起動入口は統合時に一斉切替できるが、退避前に機能と検証結果を照合する。

## 調査範囲と確かめたこと

調査は main の追跡ファイルのパス・サイズ・履歴、ルート設定、対象プロジェクトの README と一部のソースに限定した。_data、_logs、_scratch、生成物の中身、秘密情報、外部リポジトリは走査していない。サイズは Git の追跡ファイルを展開したときの合計であり、Git pack やローカルのディスク使用量ではない。再現時は git ls-tree -r -l HEAD、git log -- <path>、ルート pyproject.toml を使う。

| 観測 | 結果 | 意味 |
|---|---:|---|
| トップレベルのプロジェクト相当ディレクトリ | 48 | README の一覧は3件不足 |
| uv workspace メンバー | 32 | パス変更はルート設定に波及 |
| 追跡ファイル | 23,243件、約1,437 MiB | ディレクトリ移動だけでは履歴内の容量は減らない |
| johnhull | 13,337件、約539 MiB | references/processed 約287 MiB、docs/validation 約103 MiB |
| market_nn | 2,092件、約310 MiB | corpus/papers 約274 MiB |
| models | 1,779件、約151 MiB | 主体は翻訳済み本文・画像・HTML |
| quant-agent-benchmark | 1,831件、約81 MiB | 評価提出物・実験記録を含む |

全48件に2026年6月以降のコミットがある。この履歴だけでは「今後使わない」とは判定できない。直近の変更日が古いことを単独のアーカイブ基準にしない。

主な確認元: [ルート README](../../../README.md)、[ルート AGENTS.md](../../../AGENTS.md)、[uv/pytest 設定](../../../pyproject.toml)、[johnhull ROADMAP](../../../johnhull/ROADMAP.md)、[market_nn のコーパス規約](../../../market_nn/docs/paper_corpus.md)、[知識保存先の ADR](../../decisions/0003-keep-knowledge-in-repository.md)。

構成上は Python/uv が中心で、TypeScript/pnpm・npm、Rust、Swift、C#、C++/CUDA、Jupyter もある。入口はルート README と Makefile、各プロジェクトの README・CLI・アプリ・ノートブック。ルート pyproject.toml の workspace members と pytest testpaths、conftest.py、Makefile、プロジェクト文書にパスが埋まっているため、親ディレクトリへの一括移動は最初の手段にしない。

## 見つけ方を先に直す

ルート README をカテゴリ付きの案内表に改め、各行に「目的」「入口」「状態」「後継・関連」を短く載せる。ディレクトリ自体は、統合または退避が決まるまで原則その場に保つ。これで完成済みの小さな作品も一覧から見つけられる。

| 案内カテゴリ | 対象 |
|---|---|
| 市場・投資・意思決定 | stock、quantkit、market-viz、macrokit、autostock、portfolio-analyzer、JHRMBS、aisan_lbo_case、labor_ai_quadrant、timesfm_lab、market_nn、quant-agent-benchmark、small_ma_search、housing-buy-vs-rent |
| 定量・数学の教材と研究 | johnhull、rates_volatility_model、rough_volatility、deep_hedge_price、optimal_execution、rates-ui-lab、analytics |
| ゲーム・シミュレーター・体験アプリ | gto、akinator、pokemon、monster_gate、EitanQuest、NeonThread、WSET、My Tianjin、b737-ops-sim、eagle、komorebi-3d、tokyo_subway_3d、nbody-gpu |
| 個人データ・開発環境 | health、genequest、line_backup、agent-profiler、agentic-setup |
| 学習ラボ・単発の成果 | jp_llm_lab、cpp_algo_lab、shortest_path、csharp_calc、CsharpApp、ts-rosetta、kaggle、notebooks、interactive-email-demo |

models、reports、papers はプロジェクト一覧から区別し、「成果物・資料」として案内する。_docs は一次資料の置き場にしない。_archive には索引を新設し、退避日・退避理由・後継・実行可能性・保管上の注意を記す。

### 文書の修正候補

| 優先 | 対象 | 確認したずれ | 計画 |
|---|---|---|---|
| 高 | ルート README | agentic-setup、quant-agent-benchmark、rates-ui-lab が一覧にない | カテゴリ付き索引に追加 |
| 高 | ルート README / AGENTS.md | README は make test を「全体」と記すが対象は testpaths に限定。AGENTS.md は johnhull/report/tests を未登録と記すが、pyproject.toml には登録済み | 実設定に合わせて説明と未対象一覧を更新 |
| 高 | agentic-setup/AGENTS.md | 旧 wiki を保存先と記す。ADR 0003 と今回の共通指示はリポジトリ内保存 | 稼働中のグローバル指示との差分を確認し、バックアップの同期手順に従って更新。単独編集で復元元と実体を食い違わせない |
| 中 | notebooks/README.md | re_invest_os/ を同じリポジトリ内の例として挙げるが、本文では独立リポジトリと説明 | 入口と移管先の表現を統一 |
| 中 | Makefile 冒頭の member 説明 | ルート pyproject.toml に対し列挙が部分的 | 正本は pyproject.toml と明記し、重複列挙を減らす |
| 中 | stock、line_backup、akinator、autostock、aisan_lbo_case、deep_hedge_price の README | 最終コミットより README が約53～74日古い | 起動手順・依存・現状の差を点検。日付差だけで誤記と断定しない |
| 中 | _archive | 入口となる README がない | 案内索引と退避時テンプレートを作る |

## 市場分析の統合設計

第一候補は仮称 market-research という新しいプロジェクト。設計確定前に利用頻度、画面方式、名称を決める。新プロジェクトの中で、データ取得・時点管理・研究計算・表示の正本を各1つにする。単純なファイル移動やコードの全コピーはしない。

| 領域 | 現状の重なり | 正本を決めるための比較 |
|---|---|---|
| 市場データ | stockkit と quantkit に J-Quants v2、yfinance、Stooq 等の取得器。market-viz に yfinance/ccxt 更新器 | 調整後価格、通貨、日付、欠損、取得元、キャッシュ、失敗時の挙動を fixture で比較 |
| マクロ時点管理 | quantkit.macro.store と macrokit.pit に as_of/latest/revisions。後者は DuckDB、時刻帯付き公開日時などを扱う | リリース日の境界、ヴィンテージ、未来情報漏れ防止、既存データ移行 |
| バックテスト | stockkit、quantkit、market_viz の各実装に BacktestResult と実行関数 | シグナル反映時点、取引コスト、調整後価格、指標定義、既存結果との照合 |
| 表示 | stock は Dash、market-viz は Streamlit/FastAPI と任意の Next.js、quantkit は Jupyter/HTML | 実際に使う画面を選び、重複を整理。画面方式は追加質問の回答で決める |
| 自動探索 | autostock の Mag7 戦略実験 | 後継の研究ワークフローに再現例として移せるか確認 |

統合順は (1) 共通データ契約と fixture、(2) 正本となる取得・時点管理、(3) 計算とバックテスト、(4) 必要な画面とノートブック、(5) 旧入口の切替と退避。最初の設計成果物は機能対応表と各ソースの採否表にする。いまのコードには相互参照がなく、同名関数でも契約が違うため、採用元を名前だけで決めない。

portfolio-analyzer は口座データをローカル専用のまま保持する。連携は市場価格・為替・指標を新プロジェクトから受け取る一方向の境界から検討し、個人の保有・取引データを共有 DB や Git 管理対象へ移さない。re_invest_os とは README 上の関係だけを整理し、外部リポジトリを今回の移動対象に含めない。

## アーカイブ判定

現時点で無条件に移す新規候補はない。小さい・完成済み・最近触っていない、だけでは退避しない。各候補について、後継機能、検証、参照元、秘密情報、再開可能性を個別に確認する。

| 候補 | 退避の条件 |
|---|---|
| stock、quantkit、market-viz、macrokit | 統合先に採用機能と文書が揃い、各ソースの契約・テスト・アプリ動作を照合してから、1件ずつ判断 |
| autostock | 戦略実験の再現例を新プロジェクトに収録するか、明確に非採用と決めてから判断 |
| rates-ui-lab | UI 実験の結論と採用デザインを記録し、次の実験予定がなくなった後に判断 |
| interactive-email-demo | メール表示方式の後継ができた場合だけ候補にする。現状は独立した完成作として残す |

johnhull、portfolio-analyzer、housing-buy-vs-rent、quant-agent-benchmark は進行中または次の実験が文書にあり、今回の退避候補から外す。既存の _archive/land_price_api_app と _archive/notebooks は、後継案内を索引に載せる。アーカイブ後はルートの設定・テスト対象・リンク・起動手順を照合し、退避物を現役の入口として案内しない。

## 大容量ファイルの移管案

追跡ファイルの種類を「原本・手動監査」「再生成できる派生物」「過去の再検査証跡」に分ける。移管先は回答待ちだが、どの方法でもファイルごとの出典、SHA-256、生成条件、復元手順、ライセンス、参照元を manifest に残す。先に移管先から復元してテストできることを確認し、その後に個別のファイル群を Git の現行ツリーから外す。過去の Git 履歴は別判断にする。

| 群 | サイズの目安 | 暫定案と先に確認すること |
|---|---:|---|
| johnhull/docs/validation | 約103 MiB | 節の受入証跡と、再検査で撮り直した画像を分離。ROADMAP の D1 が再検査画像の増加を課題にしている。受入の最小証跡・ハッシュ・要約は Git に残し、再検査画像の保管先を決める |
| johnhull/references/processed | 約287 MiB | 検索・引用と release gate が使う。原本 PDF・手動 gold・索引との依存を調べ、同一出力の再生成と復元後検証が通るまで現状維持 |
| market_nn/corpus/papers | 約274 MiB | Docling 生成物だが、手動転記・意味レビューは manifests と連動する。原本・手動判断を Git に残し、派生画像と本文を分離できるか、既存 QA で試す |
| models | 約151 MiB | 翻訳済み本文は再実行コストが高く、単なるキャッシュとして扱わない。版管理・閲覧・バックアップが保てる移管先だけ検討 |
| quant-agent-benchmark | 約81 MiB | 保存済みモデル提出物と評価結果は同じ結果を再生成できない。監査記録として保持し、移すなら不変の成果物と照合可能な manifest が必要 |

johnhull/ROADMAP.md の D1 は現行の再検査方式を306節まで続けると証跡が約45 GiBになると推定している。まず将来の生成量を抑える方針を決め、既存ファイルの移管は小さな群で実証する。Git LFS 等へ移しても、過去コミットの blob は履歴を書き換えない限り残る。現環境の WSL では git lfs version が実行できず、LFS は現時点で利用可能と確認できていない。履歴変更はこの計画の実行範囲外とし、必要なら影響・バックアップ・共同利用者を調べた別工程にする。

## 実施順と完了条件

1. **入口と文書**: ルート README をカテゴリ化し、欠けた3件、外部 re_invest_os、_archive 索引を加える。確認済みの矛盾を修正し、古い README は実装との照合結果に応じて更新する。完了条件は、48件すべてが索引から到達でき、リンクと説明が実在すること。
2. **統合仕様**: 新市場分析プロジェクトの対象機能、正本、データ契約、UI、旧プロジェクトごとの採否、個人口座との境界を設計文書に固定する。公開 API・依存関係の変更はこの段階で承認を得る。完了条件は、旧機能の行き先と検証方法が対応表で追えること。
3. **統合実装**: 新しい workspace メンバーを追加し、fixture による価格・マクロ・バックテストの比較から段階的に移す。採用するアプリの主要操作を確認する。完了条件は、採用機能のテストと代表画面が新入口で動き、未移行機能が明示されること。
4. **個別退避**: 候補ごとに差分・依存・ローカルデータ・復元方法を確認し、承認を受けて _archive へ移す。pyproject.toml、testpaths、conftest.py、Makefile、README、プロジェクト内リンクを更新する。完了条件は、現役の入口に壊れた参照がなく、退避理由と後継を索引から確認できること。
5. **容量整理**: 再生成できる群から小さな移管実験を行い、manifest、復元、品質ゲートを確認して群単位で移す。原本・人手レビュー・評価提出物は別判断とする。完了条件は、復元可能性と監査可能性を失わず、新規生成分の増加方針が定まること。
6. **次の統合候補**: 市場分析が安定した後、ratesvol と hullkit の重なりなどを個別に調査する。johnhull と deep_hedge_price の既存の役割分担は尊重し、題材が近いという理由だけで統合しない。

各工程の検証は変更範囲に合わせる。文書はリンクとコマンドの存在確認、Python の移動は対象 suite と uv workspace、画面は起動と主要操作、退避はルート設定と参照元、容量移管は復元・ハッシュ・既存 QA を確認する。make test の成功だけを「全プロジェクト検証済み」とみなさない。

## 残る決定

- 新しい統合プロジェクトの名称、最初に使う入口、残す画面の範囲。
- 大容量ファイルの保管先と、過去履歴の容量も対象にするか。
- アーカイブは候補ごとに、後継の検証結果を添えて最終確認する。

今回の作業は計画書の作成まで。上記の実装・移動・削除・外部保存・履歴変更は行っていない。
