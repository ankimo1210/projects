# ワークスペース整理計画

更新日: 2026-09-27（同日レビュー反映）  
状態: 調査と計画。移動・統合・削除・履歴変更は未実施。基準点は origin へ push 済みの main `5852c526`。

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
| CI（`.github/workflows/` の eagle.yml・gto-ts.yml・health.yml） | paths フィルタと working-directory | 移動後に CI が発火しない、または失敗する |
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

第一候補は仮称 market-research という新しいプロジェクト。設計確定前に利用頻度、画面方式、名称を決める。新プロジェクトの中で、データ取得・時点管理・研究計算・表示の正本を各1つにする。単純なファイル移動やコードの全コピーはしない。

| 領域 | 現状の重なり | 正本を決めるための比較 |
|---|---|---|
| 市場データ | stockkit と quantkit に J-Quants v2（両方とも v2 の実装。ライブの疎通は今回確認していない）、yfinance、Stooq の取得器。market-viz に yfinance/ccxt 更新器。portfolio-analyzer も日次レポートとファクター推定で yfinance を直接取得し、桁のずれた終値の除去（`clean_closes`）と、取引中の足を終値扱いしない判定（`bar_is_final`）を持つ | 調整後価格、通貨、日付、欠損、取得元、キャッシュ、失敗時の挙動を fixture で比較。portfolio-analyzer の2つの規則は実データで見つかった品質問題なので、共通データ契約の要件に入れる |
| マクロ時点管理 | quantkit.macro.store と macrokit.pit に as_of/latest/revisions。前者は DataFrame、後者は DuckDB で時刻帯付き公開日時などを扱う | リリース日の境界、ヴィンテージ、未来情報漏れ防止、既存データ移行 |
| バックテスト | stockkit、quantkit、market_viz の各実装に BacktestResult と実行関数 | シグナル反映時点、取引コスト、調整後価格、指標定義、既存結果との照合 |
| 表示 | stock は Dash、market-viz は Streamlit/FastAPI と任意の Next.js、quantkit は Jupyter/HTML | 実際に使う画面を選び、重複を整理。画面方式は追加質問の回答で決める |
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
| Codex の hsk3-course worktree（codex/hsk3-first-lesson） | 未マージの3コミット（My Tianjin の HSK 講座）を origin/codex/hsk3-first-lesson へ push したうえで、worktree とローカルブランチを削除。main へのマージは未判断（この環境には Xcode がなくビルド検証できない） |
| Codex の atlas-project worktree | 未コミットの WSET Atlas UX 作業を一時 index で木にして main と比べたところ、2026-09-18 の `c03ef39c` で main に全部取り込み済みだった。差分の8ファイルは、その後の main 側の修正（1.0.1 build 2 など）による新しい内容。push するものがないため、ブランチは作らずに worktree を削除 |
| stash@{0}（housing-buy-vs-rent/docs/STATUS.md） | 削除 |

Codex の作業ディレクトリ（`C:\Users\Kazumasa\Documents\Codex\2026-09-14\` 配下）にある worktree 以外のファイル（スクリーンショット・検証スクリプト）は残してある。

## 大容量ファイルの移管案

追跡ファイルの種類を「原本・手動監査」「再生成できる派生物」「過去の再検査証跡」に分ける。移管先は回答待ちだが、どの方法でもファイルごとの出典、SHA-256、生成条件、復元手順、ライセンス、参照元を manifest に残す。リポジトリが公開なので、移管先の公開範囲はライセンス（papers の再配布条件など）と合わせて決める。先に移管先から復元してテストできることを確認し、その後に個別のファイル群を Git の現行ツリーから外す。過去の Git 履歴は別判断にする。

| 群 | サイズの目安 | 暫定案と先に確認すること |
|---|---:|---|
| johnhull/docs/validation | 約103 MiB | 節の受入証跡と、再検査で撮り直した画像を分離。ROADMAP の D1 が再検査画像の増加を課題にしている。受入の最小証跡・ハッシュ・要約は Git に残し、再検査画像の保管先を決める |
| johnhull/references/processed | 約287 MiB | 検索・引用と release gate が使う。原本 PDF・手動 gold・索引との依存を調べ、同一出力の再生成と復元後検証が通るまで現状維持 |
| market_nn/corpus/papers | 約274 MiB | Docling 生成物だが、手動転記・意味レビューは manifests と連動する。原本・手動判断を Git に残し、派生画像と本文を分離できるか、既存 QA で試す |
| models | 約151 MiB | 翻訳済み本文は再実行コストが高く、単なるキャッシュとして扱わない。版管理・閲覧・バックアップが保てる移管先だけ検討 |
| quant-agent-benchmark | 約81 MiB | 保存済みモデル提出物と評価結果は同じ結果を再生成できない。監査記録として保持し、移すなら不変の成果物と照合可能な manifest が必要 |

johnhull/ROADMAP.md の D1 によると、1マイルストーンで増える約13 MB の大半は受入済みの全節を撮り直した再検査画像で、この方式のまま306節まで続けると証跡は約45 GB になる。受入済みは306節中14節（4.6%）で、次の既定作業は M15（§27.6）。増加を止めるには既存ファイルの移管より先に、M15 に着手する前に再検査方針（影響のある節に絞る、画像はハッシュだけ残す等）を決めるのが効果的。既存ファイルの移管は小さな群で実証する。

Git LFS 等へ移しても、過去コミットの blob は履歴を書き換えない限り残る。現環境の WSL では `git lfs version` が実行できず、LFS は現時点で利用可能と確認できていない。GitHub の LFS 容量・転送量の上限は、実施時に公式文書で確認する。履歴変更はこの計画の実行範囲外とし、必要なら影響・バックアップ・クローン先を調べた別工程にする。

## 実施順と完了条件

0. **基準点と作業ツリー**（2026-09-27 完了）: push 済みの基準点から始め、上の「作業ツリー・ブランチ・stash の整理」を本人の判断に沿って片付けた。以後の工程は工程ごとの worktree で行う。完了条件は、main がクリーンで origin と一致し、残る worktree・ブランチ・stash のすべてに残す理由があること。
1. **入口と文書**: ルート README をカテゴリ化し、欠けた3件、外部 re_invest_os、_archive 索引を加える。確認済みの矛盾を修正し、古い README は実装との照合結果に応じて更新する。完了条件は、48件すべてと成果物・資料・作業用ディレクトリが索引から到達でき、リンクと説明が実在すること。
2. **統合仕様**: 新市場分析プロジェクトの対象機能、正本、データ契約（portfolio-analyzer のデータ品質規則を含む）、UI、旧プロジェクトごとの採否、個人口座との境界を設計文書に固定する。公開 API・依存関係の変更はこの段階で承認を得る。完了条件は、旧機能の行き先と検証方法が対応表で追えること。
3. **統合実装**: 新しい workspace メンバーを追加し、fixture による価格・マクロ・バックテストの比較から段階的に移す。採用するアプリの主要操作を確認する。依存を変えたら portfolio-analyzer の日次レポートを確認する。完了条件は、採用機能のテストと代表画面が新入口で動き、未移行機能が明示され、定時タスクが動き続けること。
4. **個別退避**: 候補ごとに差分・依存・ローカルデータ・復元方法を確認し、承認を受けて _archive へ移す。pyproject.toml、testpaths、conftest.py、Makefile、CI、README、プロジェクト内リンク、Git の外の依存（「実施の前提と外部依存」の表）を更新する。完了条件は、現役の入口に壊れた参照がなく、退避理由と後継を索引から確認できること。
5. **容量整理**: johnhull の再検査方針（D1）を先に決め、再生成できる群から小さな移管実験を行い、manifest、復元、品質ゲートを確認して群単位で移す。原本・人手レビュー・評価提出物は別判断とする。完了条件は、復元可能性と監査可能性を失わず、新規生成分の増加方針が定まること。
6. **次の統合候補**: 市場分析が安定した後、ratesvol（rates_volatility_model、2026-09-27 にテスト付きパッケージ化）と hullkit の重なりなどを個別に調査する。ratesvol の SABR テストは hullkit.sabr を独立実装として照合に使っているため、統合するとこの独立照合を失う点も比較に入れる。johnhull と deep_hedge_price の既存の役割分担は尊重し、題材が近いという理由だけで統合しない。

各工程の検証は変更範囲に合わせる。文書はリンクとコマンドの存在確認、Python の移動は対象 suite と uv workspace、画面は起動と主要操作、退避はルート設定・CI・参照元・定時タスク、容量移管は復元・ハッシュ・既存 QA を確認する。make test の成功だけを「全プロジェクト検証済み」とみなさない。

## 残る決定

- 新しい統合プロジェクトの名称、最初に使う入口、残す画面の範囲。
- 大容量ファイルの保管先と、過去履歴の容量も対象にするか。
- johnhull の再検査方針（D1）を M15 の前に決めるか。
- origin/codex/hsk3-first-lesson を main へマージするか（Xcode のある環境でのビルドとテストが前提）。
- 案内カテゴリの変更（market_nn、quant-agent-benchmark、rates-ui-lab）でよいか。
- アーカイブは候補ごとに、後継の検証結果を添えて最終確認する。

## レビュー記録

2026-09-27 に初版を検証した。追跡ファイル数とサイズ、48件、32メンバー、README の欠落3件、johnhull ROADMAP の D1 の数値、市場分析のコード重複（取得器・BacktestResult・as_of/latest/revisions）、LFS が使えないことは再現した。反映した変更は次のとおり。

- 追加: 実施の前提（push 済みの基準点、共有作業ツリー、公開リポジトリ、Git の外のパス依存）、作業ツリー・ブランチ・stash の整理、工程0、ローカル pack の容量、testpaths 数、追跡されている _scratch。
- 訂正: AGENTS.md は「未登録と記している」のではなく自己矛盾。Makefile は正本の明記が既にあり、直すのは古い列挙。README の古さは52～73日。_archive は2群でなく4群。
- 追記: portfolio-analyzer の独自取得とデータ品質規則、定時タスクと共有 `.venv` の関係、ratesvol と hullkit の独立照合、D1 を M15 の前に決める理由、公開リポジトリでの移管先の制約。
- 変更: market_nn、quant-agent-benchmark、rates-ui-lab の案内カテゴリ。

今回の作業は計画書の作成とレビュー反映まで。上記の実装・移動・削除・外部保存・履歴変更は行っていない。
