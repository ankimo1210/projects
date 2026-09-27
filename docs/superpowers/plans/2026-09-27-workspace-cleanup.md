# ワークスペース整理計画

更新日: 2026-09-28（先行整理と工程3cの再開を反映）

状態: 工程0–2は完了。工程3a・3bは main `7b7cbd1b` までに取込み済み。工程3cの作りかけを専用worktreeに保全してフォルダ整理を先行し、2026-09-28に同worktreeで工程3cを再開した（`codex/market-research-stage3c`、`bbda0077`、main未反映）。旧市場プロジェクトの退避、旧入口の切替、容量移管、履歴変更は未実施。別件の HSK3 は main `6dd2e69f` へ取込み済み。以下の初回調査の数値は `5852c526` 時点。

## 目的と決まった方針

第一目的は、使いたい成果物をすぐ見つけられ、各プロジェクトの役割と正本が分かること。市場データ・投資分析・可視化からコード統合を始め、既存のいずれかに寄せるのではなく、新しい統合プロジェクトを作る。最終的には少数の大きなプロジェクトにしたい。完成した小さな学習・実験作品は成果として見える場所に残す。アーカイブは「後継があり内容が重複」を主な基準とし、候補ごとに確認する。

継続利用の可能性が高い johnhull、不動産投資関連、portfolio-analyzer は更新日だけで退避しない。portfolio-analyzer は当面独立させ、新しい市場分析基盤との連携を設計する。独立リポジトリへ移管済みの re_invest_os は、このリポジトリからの案内リンクを整える。既存の起動入口は統合時に一斉切替できるが、退避前に機能と検証結果を照合する。

## 実施の前提と外部依存

各工程は、以下の前提を満たしてから始める。

**基準点と作業環境**

- 2026-09-27 に main を origin へ push し、作業ツリーをクリーンにした（`5852c526`）。以後の工程はこの状態から始める。
- `/home/kazumasa/projects` の作業ツリーと index は、複数のセッション（Claude Code・Codex）が共有している。同日だけで rates_volatility_model と johnhull にそれぞれ11コミットが並行して入った。整理作業は工程ごとに専用の worktree とブランチで行い、main へ統合する前に他セッションの作業状況を確かめる。README やルート設定のように全員が触るファイルは、小さなコミットに分けて変更する。

**公開リポジトリ**

- `ankimo1210/projects` は PUBLIC（2026-09-27 に `gh repo view` で確認）。README の索引、_archive の索引、大容量ファイルの manifest は公開される前提で書く。口座・健康・LINE などの個人データの中身や所在の詳細を書かない。
- 履歴を書き換えても、すでに取得されたクローンやキャッシュからは消えない。容量削減の手段にはなっても、公開済み内容を回収する手段にはならない。

**Git の外にあるパス依存**

ディレクトリの移動・改名・ルート設定の変更の前に、次の依存を照合する。いずれも Git の差分には現れない。

| 依存元 | 参照しているもの | 壊れ方 |
|---|---|---|
| Windows タスク PortfolioPLTokyo・PortfolioDailyPL（`C:\Users\Kazumasa\Documents\pl-daily\run_daily_pl.cmd`） | `cd /home/kazumasa/projects && uv run --no-sync python portfolio-analyzer/scripts/daily_pl_report.py` | ルートや portfolio-analyzer を動かす、または共有 `.venv` を変えると日次レポートとメールが止まる。`--no-sync` なので依存の追加・削除は自動で同期されない。失敗は `run.log` にしか残らない |
| Windows タスク reio-daily | `/home/kazumasa/re_invest_os/scripts/daily.sh` | このリポジトリの外。README のリンク整理だけなら影響しない |
| GitHub Pages（gh-pages ブランチの crunote/・my-tianjin/） | App Store の必須 URL（アプリに埋め込み済み） | main のディレクトリ移動では壊れない。リポジトリの private 化や gh-pages の整理で壊れる |
| CI（`.github/workflows/` の eagle.yml・gto-ts.yml・health.yml・my-tianjin.yml） | paths フィルタと working-directory | 移動後に CI が発火しない、または失敗する |
| ルート conftest.py | gto、health、jp_llm_lab、labor_ai_quadrant、macrokit、optimal_execution、quantkit、rough_volatility、timesfm_lab の import | 退避・改名で全体 pytest の収集が壊れる |
| Makefile | パスを含む行が59行（johnhull、analytics、rough_volatility、optimal_execution、health、market_nn など） | ターゲットが存在しないパスを指す |
| `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、Claude の memory | リポジトリのルート、docs/knowledge、各プロジェクトのパス | エージェントが古いパスを案内する。移動後に更新する |
| agentic-setup | `~/.claude`・`~/.codex` の設定のバックアップ | 実体と食い違う（下の「文書の修正候補」を参照） |

## 調査範囲と確かめたこと

調査は main の追跡ファイルのパス・サイズ・履歴、ルート設定、対象プロジェクトの README と一部のソース、上記の Git の外のパス依存に限定した。_data、_logs、生成物の中身、秘密情報、外部リポジトリは走査していない。表のサイズは追跡ファイルを展開したときの合計で、ローカルの pack は別に測った。再現時は `git ls-tree -r -l HEAD`、`git log -- <path>`、`git count-objects -vH`、ルート pyproject.toml を使う。数値は `5852c526` 時点。

| 観測 | 結果 | 意味 |
|---|---:|---|
| トップレベルのプロジェクト相当ディレクトリ | 48 | README の一覧は3件不足 |
| uv workspace メンバー | 32 | パス変更はルート設定に波及 |
| pytest testpaths | 35 | make test の対象。deep_hedge_price/tests は未登録 |
| 追跡ファイル | 23,248件、約1,437 MiB | ディレクトリ移動だけでは履歴内の容量は減らない |
| ローカルの Git pack | 約914 MiB（13 pack） | 履歴を含む実際の保存量。展開合計より小さいのは圧縮のため |
| johnhull | 13,337件、約539 MiB | references/processed 約287 MiB、docs/validation 約103 MiB |
| market_nn | 2,092件、約310 MiB | corpus/papers 約274 MiB |
| models | 1,779件、約151 MiB | 主体は翻訳済み本文・画像・HTML |
| quant-agent-benchmark | 1,831件、約81 MiB | 評価提出物・実験記録を含む |
| 追跡されている作業用ディレクトリ | _scratch 11件・約7.9 MiB、_docs、_archive 4群 | _scratch も案内と整理の対象になる |

トップレベルには追跡外の __pycache__、_data、_logs、dist、node_modules、tmp もある（ローカルのみ）。

全48件に2026年6月以降のコミットがある（最も古い csharp_calc が 2026-06-04）。この履歴だけでは「今後使わない」とは判定できない。直近の変更日が古いことを単独のアーカイブ基準にしない。

主な確認元: [ルート README](../../../README.md)、[ルート AGENTS.md](../../../AGENTS.md)、[uv/pytest 設定](../../../pyproject.toml)、[johnhull ROADMAP](../../../johnhull/ROADMAP.md)、[market_nn のコーパス規約](../../../market_nn/docs/paper_corpus.md)、[知識保存先の ADR](../../decisions/0003-keep-knowledge-in-repository.md)、[文書の層の ADR](../../decisions/0001-workspace-docs-and-knowledge-layers.md)。

構成上は Python/uv が中心で、TypeScript/pnpm・npm、Rust、Swift、C#、C++/CUDA、Jupyter もある。入口はルート README と Makefile、各プロジェクトの README・CLI・アプリ・ノートブック。ルート pyproject.toml の workspace members と pytest testpaths、conftest.py、Makefile、CI、プロジェクト文書、Git の外のタスクにパスが埋まっているため、親ディレクトリへの一括移動は最初の手段にしない。

## 見つけ方を先に直す

ルート README をカテゴリ付きの案内表に改め、各行に「目的」「入口」「状態」「後継・関連」を短く載せる。ディレクトリ自体は、統合または退避が決まるまで原則その場に保つ。これで完成済みの小さな作品も一覧から見つけられる。analytics は1行にまとめ、配下の教材（workspace メンバー10冊と report）は analytics/report のポータルを入口として案内する。

| 案内カテゴリ | 対象 |
|---|---|
| 市場・投資・意思決定 | stock、quantkit、market-viz、macrokit、autostock、portfolio-analyzer、JHRMBS、aisan_lbo_case、labor_ai_quadrant、timesfm_lab、small_ma_search、housing-buy-vs-rent |
| 定量・数学の教材と研究 | johnhull、rates_volatility_model、rough_volatility、deep_hedge_price、optimal_execution、market_nn、analytics |
| ゲーム・シミュレーター・体験アプリ | gto、akinator、pokemon、monster_gate、EitanQuest、NeonThread、WSET、My Tianjin、b737-ops-sim、eagle、komorebi-3d、tokyo_subway_3d、nbody-gpu |
| 個人データ・開発環境・AI 評価 | health、genequest、line_backup、agent-profiler、agentic-setup、quant-agent-benchmark |
| 学習ラボ・単発の成果 | jp_llm_lab、cpp_algo_lab、shortest_path、csharp_calc、CsharpApp、ts-rosetta、kaggle、notebooks、interactive-email-demo、rates-ui-lab |

初版から3件の分類を変えた。market_nn は合成データによる LOB 論文の再現なので研究へ、quant-agent-benchmark はコーディングエージェントの評価なので AI 評価へ、rates-ui-lab は仮データによる UI 比較なので学習ラボへ移した。

models、reports、papers はプロジェクト一覧から区別し、「成果物・資料」として案内する。_docs は AGENTS.md と ADR 0001 のとおり一時的な作業メモの置き場で、一次資料の置き場にしない。ただし 2026-08 の quant_research データ調査のような恒久的な知見を含むメモがあるため、該当プロジェクトの docs か docs/knowledge へ昇格させるかを1件ずつ判断する。_scratch は追跡されているので、索引に「実験の置き場」と明記するか、不要な実験ノートを整理する。_archive には索引を新設し、退避日・退避理由・後継・実行可能性・保管上の注意を記す。

### 文書の修正候補

以下は調査時のずれと計画。工程1での対応結果は後段の「工程1の実施記録」を参照。

| 優先 | 対象 | 確認したずれ | 計画 |
|---|---|---|---|
| 高 | ルート README | agentic-setup、quant-agent-benchmark、rates-ui-lab が一覧にない | カテゴリ付き索引に追加 |
| 高 | ルート README / AGENTS.md | README は make test を「全体」と記すが、対象は testpaths の35件に限る。AGENTS.md は「まだ未登録の2件」として deep_hedge_price/tests と johnhull/report/tests を挙げつつ、後者に「2026-09-14 から登録済み」と注記しており自己矛盾している | README の説明を testpaths 限定に直す。AGENTS.md の未登録一覧から johnhull/report/tests を外し、deep_hedge_price/tests だけ残す |
| 高 | agentic-setup/AGENTS.md | 旧 `~/wiki` を保存先と記す。ADR 0003 と現行のグローバル指示はリポジトリ内保存 | 稼働中のグローバル指示との差分を確認し、バックアップの同期手順に従って更新。単独編集で復元元と実体を食い違わせない |
| 中 | notebooks/README.md | 5行目で re_invest_os/ を同じリポジトリ内の昇格例に挙げるが、12行目では独立リポジトリと説明 | 5行目の例から外すか、独立リポジトリと明記 |
| 中 | Makefile 冒頭のコメント | 正本は pyproject.toml とすでに明記しているが、併記した member の列挙が古い（quantkit、macrokit、rates_volatility_model などが抜けている） | 列挙を削り、pyproject.toml への参照だけ残す |
| 中 | stock、line_backup、akinator、autostock、aisan_lbo_case、deep_hedge_price の README | README の最終更新がプロジェクトの最終コミットより52～73日古い | 起動手順・依存・現状の差を点検。日付差だけで誤記と断定しない |
| 中 | _archive | 入口となる README がない。追跡されている群は capability_index（4件）、land_price_api_app（97件）、notebooks（16件）、restructure_prompts（1件）。ほかに追跡外の tmp がある | 4群すべてを索引に載せ、退避時のテンプレートを作る。tmp は中身を確認して扱いを決める |
| 低 | docs/knowledge/network-monitor.ps1 | 2026-09-27 にスクリプトだけ追加された。docs/knowledge/README.md からの案内も使い方の説明もない | 用途と実行方法の短いノートを添えて README に載せるか、置き場所を見直す |

## 市場分析の統合設計

新プロジェクト名は **market-research**、最初の入口は **Streamlit + Plotly** に決定。名称・入口・機能範囲の判断は本人から委任された。[統合仕様](../specs/2026-09-27-market-research-design.md) に機能の行き先 F01–F19、7画面、正本、データ契約、受入条件 Q01–Q13 を定義した。新プロジェクトの中で、データ取得・時点管理・研究計算・表示の正本を各1つにする。単純なファイル移動やコードの全コピーはしない。

| 領域 | 現状の重なり | 正本を決めるための比較 |
|---|---|---|
| 市場データ | stockkit と quantkit に J-Quants v2（両方とも v2 の実装。ライブの疎通は今回確認していない）、yfinance、Stooq の取得器。market-viz に yfinance/ccxt 更新器。portfolio-analyzer も日次レポートとファクター推定で yfinance を直接取得し、桁のずれた終値の除去（`clean_closes`）と、取引中の足を終値扱いしない判定（`bar_is_final`）を持つ | 調整後価格、通貨、日付、欠損、取得元、キャッシュ、失敗時の挙動を fixture で比較。両規則の問題意識を共通契約に入れる。ただし clean_closes は後続5観測を調べるため、当時の判定と後日訂正を分け、未来情報をバックテストに混ぜない |
| マクロ時点管理 | quantkit.macro.store と macrokit.pit に as_of/latest/revisions。前者は DataFrame、後者は DuckDB で時刻帯付き公開日時などを扱う | リリース日の境界、ヴィンテージ、未来情報漏れ防止、既存データ移行 |
| バックテスト | stockkit、quantkit、market_viz の各実装に BacktestResult と実行関数 | シグナル反映時点、取引コスト、調整後価格、指標定義、既存結果との照合 |
| 表示 | stock は Dash、market-viz は Streamlit/FastAPI と任意の Next.js、quantkit は Jupyter/HTML | 7画面へ集約。Streamlit を入口に、CLI・Jupyter と同じサービス層を使用。AIチャット・Next.js/FastAPI は初版に移さない |
| 自動探索 | autostock の Mag7 戦略実験 | 後継の研究ワークフローに再現例として移せるか確認 |

統合順は (1) 共通データ契約と fixture、(2) 正本となる取得・時点管理、(3) 計算とバックテスト、(4) 必要な画面とノートブック、(5) 旧入口の切替と退避。最初の設計成果物は機能対応表と各ソースの採否表にする。いまのコードには相互参照がなく（stock、quantkit、market-viz、macrokit、autostock、portfolio-analyzer の間に import なし）、同名関数でも契約が違うため、採用元を名前だけで決めない。

portfolio-analyzer は口座データをローカル専用のまま保持する。連携は市場価格・為替・指標を新プロジェクトから受け取る一方向の境界から検討し、個人の保有・取引データを共有 DB や Git 管理対象へ移さない。portfolio-analyzer はルートの共有 `.venv` を使って定時実行されているため、新しい workspace メンバーの追加や依存の変更で `uv sync` したあとは、日次レポートをメールなしで1回実行して動作を確かめる。re_invest_os とは README 上の関係だけを整理し、外部リポジトリを今回の移動対象に含めない。

## アーカイブ判定

現時点で無条件に移す新規候補はない。小さい・完成済み・最近触っていない、だけでは退避しない。各候補について、後継機能、検証、参照元（Git の外の依存を含む）、秘密情報、再開可能性を個別に確認する。

| 候補 | 退避の条件 |
|---|---|
| stock、quantkit、market-viz、macrokit | 統合先に採用機能と文書が揃い、各ソースの契約・テスト・アプリ動作を照合してから、1件ずつ判断 |
| autostock | 戦略実験の再現例を新プロジェクトに収録するか、明確に非採用と決めてから判断 |
| rates-ui-lab | UI 実験の結論と採用デザインを記録し、次の実験予定がなくなった後に判断 |
| interactive-email-demo | メール表示方式の後継ができた場合だけ候補にする。現状は独立した完成作として残す |

johnhull、portfolio-analyzer、housing-buy-vs-rent、quant-agent-benchmark は進行中または次の実験が文書にあり、今回の退避候補から外す。既存の _archive の4群は、後継案内を索引に載せる。アーカイブ後はルートの設定・テスト対象・CI・リンク・起動手順・Git の外の依存を照合し、退避物を現役の入口として案内しない。

### 作業ツリー・ブランチ・stash の整理（2026-09-27 完了）

本人の承認を得て、同日に次のとおり片付けた。残る worktree は main だけ、stash は0件。

| 対象 | 処置 |
|---|---|
| housing-inputs-20260918、johnhull-alternative-models、rates-vol-completion-20260927 の worktree | main にマージ済み・未変更を確認して削除し、ローカルブランチも削除 |
| Codex の hsk3-course worktree（codex/hsk3-first-lesson） | 未マージの3コミット（My Tianjin の HSK 講座）を origin/codex/hsk3-first-lesson へ push したうえで、worktree とローカルブランチを削除。当時は main 未マージ。その後、本人の承認と macOS CI の成功を経て `6dd2e69f` へ取込み済み（工程2の実施記録） |
| Codex の atlas-project worktree | 未コミットの WSET Atlas UX 作業を一時 index で木にして main と比べたところ、2026-09-18 の `c03ef39c` で main に全部取り込み済みだった。差分の8ファイルは、その後の main 側の修正（1.0.1 build 2 など）による新しい内容。push するものがないため、ブランチは作らずに worktree を削除 |
| stash@{0}（housing-buy-vs-rent/docs/STATUS.md） | 削除 |

Codex の作業ディレクトリ（`C:\Users\Kazumasa\Documents\Codex\2026-09-14\` 配下）にある worktree 以外のファイル（スクリーンショット・検証スクリプト）は残してある。

## 大容量ファイルの移管案

追跡ファイルの種類を「原本・手動監査」「再生成できる派生物」「過去の再検査証跡」に分ける。[ADR 0004](../../decisions/0004-artifact-storage-and-evidence.md) で内蔵 SSD のローカル正本と別 SSD の第2コピーを選定した（未作成・未移管）。ファイルごとの出典、SHA-256、生成条件、復元手順、ライセンス、参照元を manifest に残す。リポジトリが公開なので、移管先の公開範囲はライセンス（papers の再配布条件など）と合わせて決める。先に移管先から復元してテストできることを確認し、その後に個別のファイル群を Git の現行ツリーから外す。過去の Git 履歴は別判断にする。

| 群 | サイズの目安 | 暫定案と先に確認すること |
|---|---:|---|
| johnhull/docs/validation | 約103 MiB | 節の受入証跡と、再検査で撮り直した画像を分離。ROADMAP の D1 が再検査画像の増加を課題にしている。受入の最小証跡・ハッシュ・要約は Git に残す。新しい再検査画像は ADR 0004 の不変保管庫へ。先に D1-preflight と復元を検証 |
| johnhull/references/processed | 約287 MiB | 検索・引用と release gate が使う。原本 PDF・手動 gold・索引との依存を調べ、同一出力の再生成と復元後検証が通るまで現状維持 |
| market_nn/corpus/papers | 約274 MiB | Docling 生成物だが、手動転記・意味レビューは manifests と連動する。原本・手動判断を Git に残し、派生画像と本文を分離できるか、既存 QA で試す |
| models | 約151 MiB | 翻訳済み本文は再実行コストが高く、単なるキャッシュとして扱わない。版管理・閲覧・バックアップが保てる移管先だけ検討 |
| quant-agent-benchmark | 約81 MiB | 保存済みモデル提出物と評価結果は同じ結果を再生成できない。監査記録として保持し、移すなら不変の成果物と照合可能な manifest が必要 |

johnhull/ROADMAP.md の D1 によると、1マイルストーンで増える約13 MB の大半は受入済みの全節を撮り直した再検査画像で、この方式のまま306節まで続けると証跡は約45 GB になる。受入済みは306節中14節（4.6%）で、次の既定作業は M15（§27.6）。[D1 方針](../../../johnhull/docs/EVIDENCE_POLICY.md) は決定済み。影響のある節を再描画し、画像実体を不変保管庫で保持する。M15 の前に D1-preflight（依存指紋・参照互換・復元・負のテスト）を行う。数値・意味・受入検査は維持し、既存ファイルの移管は小さな群で実証する。

Git LFS 等へ移しても、過去コミットの blob は履歴を書き換えない限り残る。現環境の WSL では `git lfs version` が実行できず、LFS は現時点で利用可能と確認できていない。GitHub の LFS 容量・転送量の上限は、実施時に公式文書で確認する。履歴変更はこの計画の実行範囲外とし、必要なら影響・バックアップ・クローン先を調べた別工程にする。

## フォルダ整理の先行（2026-09-27）

本人の指示で、作りかけの工程3cよりフォルダ整理を優先する。市場分析の旧プロジェクトは
後継機能と受入検証が未完了なので、現時点では移さない。工程3cの作業中のファイルは
専用worktreeに保全し、この整理ブランチからは変更しない。

候補ごとの確認を経て、`_scratch/notebooks/2026-04/` の単発比較ノート8件を
`_archive/scratch/2026-04/` へ移す。現役コードからの参照はなく、
ノート本体と保存済み出力を保持する。機能の後継は未確定で、再実行も未検証。
退避理由・元の配置・再開方法は [_archive/scratch の索引](../../../_archive/scratch/README.md) に残す。
また `_docs` にあった quant_research の調査・レビュー5件は、内容の正本となる
[プロジェクト内の調査記録](../../../analytics/quant_research/docs/reviews/README.md) へ移す。
記録時点の主張と現行実装を混同しない索引を付け、ノート内の旧 `_docs` パス参照だけを更新する。
残る一時メモには [_docs の索引](../../../_docs/README.md) を設け、現在の仕様の正本ではないことを明示する。

この整理時点では `stock`・`quantkit`・`market-viz`・`macrokit`・`autostock` は
いずれも root uv workspace と pytest `testpaths` の対象である。うち `quantkit`・`macrokit` は
root `conftest.py` にも明示importがある。後継 `market-research` の工程3c/3dと受入が未完了なので、
5ディレクトリの退避は保留する。`rates-ui-lab` には次のUI比較実験が明記され、
`interactive-email-demo` には後継がないため、これらも退避しない。

2026-09-28時点で、先行できる整理はローカルの `codex/workspace-cleanup`（`eb42d389`）に記録済み。
古い作業ログ3件と旧スキル計画2件は、候補ごとの確認を受けて
[過去文書の退避記録](../../../_archive/docs/README.md)へ移した。本文は変更せず、現行の入口と実行上の注意を索引に残した。
工程3c側ではMag7の因果的な固定例を `f8d14c87` に実装した。基礎の独立レビューと指摘修正は済んだがmain未取込みであり、
旧 autostock の一括取得価格から過去のPIT成績は再現できない。独立レビューで指摘されたlockbox境界の検証依存は `bbda0077` で修正し、memberテスト226件が成功。旧プロジェクト退避の判断は維持する。
旧 autostock の設計・実装計画と quantkit の設定コメントに残る先読み防止の過大表現は、
当時の記録を残したまま注記・文言修正した。

## 実施順と完了条件

0. **基準点と作業ツリー**（2026-09-27 完了）: push 済みの基準点から始め、上の「作業ツリー・ブランチ・stash の整理」を本人の判断に沿って片付けた。以後の工程は工程ごとの worktree で行う。完了条件は、main がクリーンで origin と一致し、残る worktree・ブランチ・stash のすべてに残す理由があること。
1. **入口と文書**（2026-09-27 完了、ブランチ `codex/workspace-index`、実装コミット `06849a7a`・`25606280`。main `dd18befe` へ取込み済み）: ルート README をカテゴリ化し、欠けた3件、外部 re_invest_os、_archive 索引を加える。確認済みの矛盾を修正し、古い README は実装との照合結果に応じて更新する。完了条件は、48件すべてと成果物・資料・作業用ディレクトリが索引から到達でき、リンクと説明が実在すること。
2. **統合仕様**（2026-09-27 完了、main `1df81924` に反映済み）: 新市場分析プロジェクトの対象機能、正本、データ契約（portfolio-analyzer のデータ品質規則を含む）、UI、旧プロジェクトごとの採否、個人口座との境界を設計文書に固定する。[統合仕様](../specs/2026-09-27-market-research-design.md) に新契約と既存依存の候補を明示。旧入口の一斉切替は承認済み。実装で新規 production 依存が必要なら具体的な差分で確認する。完了条件は、旧機能の行き先と検証方法が対応表で追えること。
3. **統合実装**: 新しい workspace メンバーを追加し、fixture による価格・マクロ・バックテストの比較から段階的に移す。採用するアプリの主要操作を確認する。依存を変えたら portfolio-analyzer の日次レポートを確認する。完了条件は、採用機能のテストと代表画面が新入口で動き、未移行機能が明示され、定時タスクが動き続けること。
4. **個別退避**: 候補ごとに差分・依存・ローカルデータ・復元方法を確認し、承認を受けて _archive へ移す。pyproject.toml、testpaths、conftest.py、Makefile、CI、README、プロジェクト内リンク、Git の外の依存（「実施の前提と外部依存」の表）を更新する。完了条件は、現役の入口に壊れた参照がなく、退避理由と後継を索引から確認できること。
5. **容量整理**: 決定済みの johnhull D1 と保管先を基に、再生成できる群から小さな移管実験を行い、manifest、復元、品質ゲートを確認して群単位で移す。原本・人手レビュー・評価提出物は別判断とする。完了条件は、復元可能性と監査可能性を失わず、新規生成分の増加方針が定まること。
6. **次の統合候補**: 市場分析が安定した後、ratesvol（rates_volatility_model、2026-09-27 にテスト付きパッケージ化）と hullkit の重なりなどを個別に調査する。ratesvol の SABR テストは hullkit.sabr を独立実装として照合に使っているため、統合するとこの独立照合を失う点も比較に入れる。johnhull と deep_hedge_price の既存の役割分担は尊重し、題材が近いという理由だけで統合しない。

各工程の検証は変更範囲に合わせる。文書はリンクとコマンドの存在確認、Python の移動は対象 suite と uv workspace、画面は起動と主要操作、退避はルート設定・CI・参照元・定時タスク、容量移管は復元・ハッシュ・既存 QA を確認する。make test の成功だけを「全プロジェクト検証済み」とみなさない。

## 工程1の実施記録（2026-09-27）

**完了・main 取込み済み（`dd18befe`）**。実装時のブランチは `codex/workspace-index`。
`06849a7a` は索引と共有文書、`25606280` は6件の README の実装照合による修正。
本人側のレビューと fast-forward・push が完了し、同ブランチと worktree は削除済み。後続の工程2は次節に記す。

### 変更と根拠

- [ルート README](../../../README.md): 計画どおりの5分類・48件にし、目的・入口・状態・関連を記載。
  成果物3群、作業用3群、共有文書、外部 re_invest_os を案内。health 等の説明も現行 README に照合。
- [AGENTS.md](../../../AGENTS.md): `testpaths` 35件と登録済みの johnhull/report を明記。
  deep_hedge_price の過去のテスト成功を現在の全件検証と混同しない説明に修正。
- [notebooks/README.md](../../../notebooks/README.md): 外部リポジトリの区別と、旧ノート・旧アプリの別々の退避先を修正。
- [Makefile](../../../Makefile): 冒頭の古いメンバー列挙のみを削除。ターゲット・レシピは変更なし。
- [_archive/README.md](../../../_archive/README.md): 4群の退避日・理由・根拠コミット・後継・実行可能性と記録テンプレートを新設。
- [ネットワーク監視ノート](../../knowledge/2026-09-27-network-monitor.md) と [共有知識索引](../../knowledge/README.md):
  Windows PowerShell の実行方法、既定値、通信量、結果の読み方を追加。スクリプト本体は変更なし。

| README | 明確なずれに対する修正 | 照合先 |
|---|---|---|
| stock | uv をルートから使う起動例、依存バージョンを固定値でなく下限として記載 | [起動コード](../../../stock/app/app.py)、[依存宣言](../../../stock/pyproject.toml) |
| line_backup | 共有環境での CLI・テスト例、`--sample-rows 0` の説明 | [CLI](../../../line_backup/src/line_backup_exporter/cli.py)、[SQLite 検査](../../../line_backup/src/line_backup_exporter/sqlite_inspector.py) |
| akinator | 同梱35件は手作り seed、ライブ Wikidata 取得と区別 | [seed 生成](../../../akinator/scripts/seed_data.py) と同梱データの ID・件数 |
| autostock | ルート実行例と取得開始日、lockbox は指標非表示であって未来データへのアクセス制限ではないと訂正 | [戦略](../../../autostock/strategy.py)、[評価器](../../../autostock/prepare.py) |
| aisan_lbo_case | 存在しない PPTX 追記コマンドを除去し、取得処理の yfinance 依存を補足 | [report モジュール群](../../../aisan_lbo_case/src/report/)、[peer 取得](../../../aisan_lbo_case/src/fetch/fetch_peer_multiples.py) |
| deep_hedge_price | Python 3.12、共有環境の有効化、dev extra を明示 | [依存宣言](../../../deep_hedge_price/pyproject.toml)、[Makefile](../../../deep_hedge_price/Makefile) |

### 検証と対象範囲

- スクリプトで README・AGENTS・アーカイブ索引・本計画と変更した Markdown の相対リンク先の実在を確認。
- `git ls-tree -d HEAD` のトップレベルから管理用ディレクトリと成果物を除いた48件が、重複なく索引から到達可能。
  計画の分類と順序も一致（12 / 7 / 13 / 6 / 10）。
- TOML を読み、testpaths 35件、johnhull/report の登録、deep_hedge_price の未登録を確認。
  記載した Make ターゲット・モジュール・スクリプト・オプション・Python 要件を実装に照合。
- 合成 SQLite のみで `sample_rows=0` がサンプルを省略し行数計測は続けることを確認。
  ネットワーク監視の PowerShell 例は構文解析で確認し、通信は実行していない。
- pre-commit の対象フックと `git diff --check` を実施。Python / TOML / YAML の変更がないため
  ruff / ruff-format / check-toml / check-yaml は対象なしで skip。アプリ全体のテスト、実データ取得、UI 起動は未実施。
- 別レビュアーによる読み取り専用レビューで重大・要修正の指摘なし。
  退避日の明記もコミット日と照合して追加した。

判断: 文書だけの工程なので環境の全体 sync と `make test` は行わず、文書の実在・実装との整合を検証した。
アプリの実行可能性を再認定したものではない。アプリの worktree 作成機能は UNC の Git 所有権判定で失敗したため、
既存設定を変更せず WSL の Git で専用 worktree を作った。共有 main には変更を加えていない。

### 直さずに残したずれ・未検証事項

- `agentic-setup/AGENTS.md` と稼働中の共通グローバル指示を比較した。バックアップには旧 wiki 保存方針と
  「修正3回で停止」が残り、稼働版にはリポジトリ内の知識保存、既承認作業の自律継続、
  新しい証拠が得られない時点での再評価、進捗・検証を含む自己完結した報告がある。
  引き継ぎ指示どおり両方とも未編集。[同期手順](../../../agentic-setup/README.md#同期) に従う別作業が必要。
- Makefile の `help` 出力にもメンバーの手書き一覧が残り、macrokit / timesfm_lab / portfolio-analyzer が抜けている。
  今回の指定対象は冒頭コメントであり、help レシピは変更していない。正本は root pyproject.toml。
- stock の AGENTS / CLAUDE に Streamlit チャットの説明が残るが、現行 `app/pages/chat.py` は Dash。
  akinator の AGENTS / CLAUDE も冒頭の「no hand-built dataset」と下段の seed 説明が矛盾する。
  今回は指定された README を修正し、これらのプロジェクト指示ファイルは未編集。
- aisan_lbo_case の企業情報・モデル前提の最新性、外部 re_invest_os の移植機能の網羅性は未検証。
  歴史的な調査前提を現在の事実と断定して書き換えてはいない。
- アーカイブ内の旧 README は当時の起動手順を含む。新索引で注意点を明記し、本体の再実行や修復は行っていない。
  追跡外 tmp、個人データ、保存済み評価結果、大容量成果物も今回の整理対象外。

## 工程2の実施記録（2026-09-27）

本人から名称・入口・機能範囲・大容量保管先の判断を委任され、D1 の決定と HSK3 の
検証後のマージも承認された。設計作業は `codex/workspace-design` の専用 worktree で行った。
**工程2完了・main `1df81924` へ fast-forward 済み**。`fc95f1b9` は索引と起動案内の補足、`a0e75edd` は統合設計・
保管方針・D1 と ROADMAP、`866441dc` は HSK3 の検証記録。この計画書のコミットはその後に続く。

### 決定・変更

- [市場分析仕様](../specs/2026-09-27-market-research-design.md): `market-research` に名称を確定。
  Streamlit の7画面、CLI / Jupyter / HTML を同じ計算基盤へ接続する。機能19群の初版・後続・非採用と、
  価格・公開時点・バックテスト・口座側 export の契約、13群の受入条件を定義。
- [ADR 0004](../../decisions/0004-artifact-storage-and-evidence.md): 当初は別 SSD を正本とした。
  工程3開始時に、日常の参照が着脱式ドライブに依存するため、内蔵 SSD を正本・別 SSD を検証済み第2コピーへ更新。
  Git には manifest と最小証跡を残す。保管庫の作成・移管は未実施。
- [johnhull D1](../../../johnhull/docs/EVIDENCE_POLICY.md) と [ROADMAP](../../../johnhull/ROADMAP.md):
  影響のある節を再描画し、同一画像は実体を保持して参照。M15 前に D1-preflight を行う。
  数値・意味・受入検査と14節の受入状態は維持。D3 の軽量化は未決。
- [ルート README](../../../README.md) の48件にスタック列を復元し、
  [stock README](../../../stock/README.md) に既存 start.sh の案内を戻した。
  agentic-setup の同期、Makefile help、stock/akinator の指示ファイルは前節の残件のまま。

設計時に、portfolio-analyzer の `clean_closes` が後続5観測を使うことを確認した。
品質問題への対処は継承するが、当時利用可能なデータと後日訂正を分離する。
また旧バックテストは close/open の収益期間が異なるため、旧3実装同士の一致ではなく
新しい明示契約の手計算 fixture を受入の正本とする。

### HSK3 の取込み（別ブランチの残件）

- `origin/codex/hsk3-first-lesson` の3コミットを main 基準の `codex/hsk3-xcode-check` に統合し、
  [macOS CI](../../../.github/workflows/my-tianjin.yml) を追加。
- main へ取り込む正確な commit `6dd2e69f` を macOS 26 / Xcode 26.6 / iOS Simulator で検証。
  ビルドと XCTest **57件**、Node の新単元テスト **8件**、既存教材検証・self-test が成功。
  [GitHub Actions の記録](https://github.com/ankimo1210/projects/actions/runs/36301052893)。
- main がクリーンで origin と同じ `dd18befe` であることを再確認し、`6dd2e69f` へ
  fast-forward して push。直後に main / origin の一致とクリーンを確認した。
- [HSK3 文書](../../../My%20Tianjin/Docs/HSK3FirstLesson.md) に検証結果を追記。
  画面の手動操作、実機の音声・アクセシビリティ、教材の人手監修は未実施で、公開・配布は行っていない。

### 検証と境界

変更した文書と AGENTS・アーカイブ索引の相対リンク182件はすべて実在。
`git ls-tree -d HEAD` と照合して48件・重複なし・分類件数 12 / 7 / 13 / 6 / 10 を確認した。
48件のスタック、Make ターゲット、testpaths 35件、start.sh の構文と実装も照合。
pre-commit と `git diff --check` は成功。Markdown の変更なので ruff 等は対象なしで skip。
市場分析の全suiteや画面は未実施。文書の検証を市場分析の実行検証と混同しない。
独立した読み取り専用レビューで重大・要修正の指摘なし。価格の単位表現を明確にする軽微な指摘を反映した。
工程2の時点では市場分析コード、新しい依存、データ移管、個別退避、履歴書換えは未実施だった。
D1 の方針決定と保管先の選定を、ツール対応やバックアップ完了とは扱わない。

## 工程3の開始記録（2026-09-27）

[工程3初期計画](2026-09-27-market-research-core.md)に沿い、専用worktreeの
`codex/market-research-stage3` に新しいuvメンバーを追加。
[進捗](../../../market-research/docs/STATUS.md)を正本とし、価格の市場ID・時点・調整方式、
改定前後のマクロ読取、lag1バックテスト、合成デモのCLIとStreamlit 7画面まで実装した。
オフラインテスト38件、AppTest、CLI、ruff、pre-commitを確認。
旧アプリの移行・実API取得・旧DB移管・個人口座への接続・定時タスクの変更はまだ行っていない。
元の48件は新プロジェクト追加後49件となり、ルート索引とtestpathsは更新した。

保管先は本人が合理的な選択を委ね、レビューでは着脱式F:の運用負担が指摘された。
[ADR 0004](../../decisions/0004-artifact-storage-and-evidence.md)をC:正本/F:第2コピーへ更新。
物理ディスクと空き容量の確認はレビュー結果に基づく。フォルダーはまだ作成していない。

## 残る決定・次の作業

工程3aのレビュー後、未確定足の混在で読み込み全体が落ちる不具合を修正した。
[取得・保存計画](2026-09-27-market-data-ingestion.md)に従い、価格取得4系統、
入力ハッシュ・不変snapshot、価格/マクロのDuckDB保存、明示取得/オフライン読取CLIを追加。
86件のテストとBinance/yfinanceの小範囲ライブ取得・再読込を確認。
Stooqはブラウザ検証HTMLが返り、J-Quantsライブは未検証。
`exchange-calendars` の依存は承認後に追加し、日米株の自動時間表と共に
工程3bを main `7b7cbd1b` へ取込み済み。共有環境の同期と口座レポートの
メールなし実行も確認した。工程3cの入力層は別ブランチで着手。
詳細と外部マクロ/財務の残件は [STATUS](../../../market-research/docs/STATUS.md) に集約する。

- 工程3: 合成デモの次に実provider・保存・研究機能を接続し、Q01–Q13 を満たしてから旧入口を切り替える。新しい production 依存が具体的に必要になった場合だけ確認する。
- johnhull: D1-preflight を実装・検証してから M15。D3（定性節の軽量化・受入単位）は別途判断。
- 容量整理: 選定した保管庫を構築し、小群で2コピーと復元を実証。過去履歴の書換えは対象外。
- アーカイブは候補ごとに、後継の検証結果を添えて最終確認する。
- HSK3: 自動ビルド・テストは確認済み。主要画面の操作と教材監修を経て後続の製品判断をする。

## _docs の残存記録を退避（2026-09-28）

本人の「判断を求めず完了まで進める」という指示に沿い、残存する4件を個別に内容・参照先と
現行の入口を確認し、_archive/docs/ に移した。2026-04-30の再編記録とAIセッション索引、
2026-08-09のWindows/WSL環境ハンドオフ、旧不動産サービスの収益化・配置案である。
環境ハンドオフの未完了事項を現在も未完了と断定せず、旧調査案の価格・仕様は再検証を要する
と索引に明記した。AIセッション索引の相対リンクだけ移動後に直し、元記録の実施内容は変更していない。
_docs/ は新しい一時メモの入口だけを残す。現役プロジェクトの移動や旧市場入口の切替とは別作業。

## レビュー記録

2026-09-27 に初版を検証した。追跡ファイル数とサイズ、48件、32メンバー、README の欠落3件、johnhull ROADMAP の D1 の数値、市場分析のコード重複（取得器・BacktestResult・as_of/latest/revisions）、LFS が使えないことは再現した。反映した変更は次のとおり。

- 追加: 実施の前提（push 済みの基準点、共有作業ツリー、公開リポジトリ、Git の外のパス依存）、作業ツリー・ブランチ・stash の整理、工程0、ローカル pack の容量、testpaths 数、追跡されている _scratch。
- 訂正: AGENTS.md は「未登録と記している」のではなく自己矛盾。Makefile は正本の明記が既にあり、直すのは古い列挙。README の古さは52～73日。_archive は2群でなく4群。
- 追記: portfolio-analyzer の独自取得とデータ品質規則、定時タスクと共有 `.venv` の関係、ratesvol と hullkit の独立照合、D1 を M15 の前に決める理由、公開リポジトリでの移管先の制約。
- 変更: market_nn、quant-agent-benchmark、rates-ui-lab の案内カテゴリ。

初版の作業は計画書の作成とレビュー反映まで。その後の工程1・工程2の変更と検証は上の実施記録に記す。市場分析コードの統合・移動・削除・外部保存・履歴変更は行っていない。
