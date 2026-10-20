# クロスアセット研究候補の引き継ぎ（Codex 向け、2026-10-20）

候補12を閉じたあと、次の候補に移るための引き継ぎです。Claude Code が 2026-10-20 に書きました。`_docs/` の一時メモなので、正本は各ラボの README と PREREG です。リポジトリの決まりは `/home/kazumasa/projects/AGENTS.md` に従ってください。

**最初にすること：** §4 の推奨を示して、次の候補をユーザーに確かめる。決まったら、§5 の型で設計（spec）から始める。ユーザーへの返答は日本語で書く。

## 1. 基準状態（2026-10-20）

- main は origin/main の c6f672ad に、この引き継ぎと候補12を閉じた記録の commit が1つ載っています（push はユーザーの承認待ち）。
- `make test`（main のチェックアウト、c6f672ad）は 12,156 passed、59 skipped、0 failed でした。スキップのうち37件は gto の拡張（`gto_py`・`gto_cuda`）が未ビルドなためです。
- worktree `/home/kazumasa/worktrees/sector-leadlag` があります。branch は `claude/close-candidate-12`（この commit）と `claude/sector-leadlag-corrected`（merge 済み）です。
  - 中の `.superpowers/sdd/` には作業フォルダが2つあり、2026-10-20 の分は 334MB、2026-10-19 の分は 2.1MB です。台帳とレビューの記録が入っています。
  - ユーザーは残すと選びました。worktree と branch を消すには承認が要ります。worktree を消すと、この2つのフォルダも消えます。
- main のチェックアウトには、別のセッションの未コミットの変更（`docs/superpowers/README.md` の virtual-tryon の行、未追跡の `docs/superpowers/specs/2026-10-19-virtual-tryon-notes.md`）があります。触らないでください。

## 2. 研究の流れと、ここまでの結果

2026-10-17 にユーザーが「クロスアセット・クオンツトレーディング研究候補」（15本）を渡しました。Claude が一次資料と照合し、追加の関連研究17本と合わせて32本の一覧にしています（claude.ai の非公開 Artifact「クロスアセット研究候補」。Codex からは読めないので、要る部分は §3 に写しました）。

方針は、無料のデータで反証を設計できる候補から順に検証することです。結果は次のとおりです。

| 候補 | 実体 | 結果 |
|---|---|---|
| 4 相関構造変化の予測（塚本、FIN-037） | 使い捨ての確認（2026-10-18、結果はリポジトリに無い） | 追わない。目的変数の63日窓どうしが58日重なり、学習なしの「抜け落ち」統計量だけで AUC 0.802 になる。重ならない目的変数では、どのモデルも 0.50 前後だった。 |
| 9 債券リスクプレミアムの ML（Bianchi ら RFS 2021） | `/home/kazumasa/projects/bond_timing_lab/` | 判定 `no_usable_signal`（2026-10-19）。毎月推定し直す追加の確認（PREREG §5）は `leak_partial`。 |
| 12 日米業種リードラグ（中川ら・廣橋ら FIN-036/037） | `/home/kazumasa/projects/sector_leadlag_lab/` | 記録の判定は `usable`（2026-10-19）。yfinance の誤りを規則で直した確認（PREREG §5）は `verdict_data_dependent`。2026-10-20 に、ユーザーの判断で次の段階（紙の上の売買）に進まずに閉じた。 |

候補12の要点：
- 弱点は3つです。片道 2bp の費用で現物の買いがほぼ0になること（記録 +0.09%、直したデータ −0.18%）。2024-11-05 の取引時間の延長のあと、バスケットの係数が負になったこと。yfinance の誤りで結果の符号が変わること。
- 詳しくは `/home/kazumasa/projects/sector_leadlag_lab/README.md`、`/home/kazumasa/projects/sector_leadlag_lab/results/corrected/summary.md`、`/home/kazumasa/projects/docs/knowledge/2026-10-19-yfinance-japan-data-errors.md` にあります。

## 3. 残りの候補

番号は資料の優先順位（1〜15）と、追加の関連研究（16〜32）です。成績は著者の報告値で、独立には再現していません。外部の事実は 2026-10-17〜18 の照合のままで、見直していません。

| # | 候補 | データ | コード | メモ |
|---|---|---|---|---|
| 1 | Attention Factors（Epstein ら 2025、米大型株の統計的裁定） | 有料（CRSP） | 未確認 | 費用後 Sharpe 2.3 の主張。 |
| 2 | DeePM（Wood ら 2026、連続先物50本） | 有料（連続先物） | MIT で公開 | 資料が主軸に推した候補。データを買えば最も早く試せる。手元の GPU は RTX 5080（16GB）。 |
| 3 | Deep Learning Statistical Arbitrage（Pelger ら） | 有料 | 未確認 | 1 の比較相手。 |
| 5 | Transformer＋GNN の相関予測（S&P 500） | 一部無料 | 一部 | 過去の構成銘柄を揃えないと生存バイアスが入る。 |
| 6 | MASTER（AAAI 2024、中国株） | 一部無料 | MIT で公開 | 日本株に移すなら J-Quants が要る。 |
| 7 | Momentum Transformer（連続先物50本） | 有料 | MIT で公開 | 2 のリポジトリに実装がある。 |
| 8 | X-Trend（少数ショットのトレンド追随） | 有料 | 未公開 | |
| 10 | EXFormer（Liu ら 2025、EUR/USD・USD/JPY・GBP/USD の日次） | 無料の見込み（FRED の為替と公開の外生変数28本） | 未公開 | 約1年の売買で費用後 7%・19%・9%、Sharpe 1.8超の主張。検証期間が短い。 |
| 11 | FX Fixing Reversal（Krohn ら JF 2024） | 有料（日中の為替） | 複製パッケージあり | |
| 13 | 織り込みの相関と実現した相関（Cboe COR3M） | 一部無料 | なし | 売買の検証にはオプション価格（有料）が要る。 |
| 14 | オプションのリターン予測（Bali ら RFS 2023） | 有料 | 未確認 | |
| 15 | DP-DPO（河村ら FIN-037、予測と売買の同時最適化） | 無料（月次の指数） | なし | 「よく当たる予測」と「儲かる予測」の違いを方法として扱う。 |

追加の17本は、多くが候補を判定する物差しです。無料で使えるのは次のものです。
- 16 Nagel：RFF の「複雑なほど良い」の反証。
- 17 Kilic：為替の RFF。OLS には勝つが、ランダムウォークには一部の通貨でしか勝てない。売買の Sharpe 0.40 は切片を入れると消える。
- 21：非同期の終値の相関の補正。
- 24：基盤モデルとランダムウォーク。
- 25 Kronos：MIT で、重みも公開されている。
- 26：Transformer の文脈内予測の理論上の限界。
- 27：東京と NY の日中・夜間リターンの波及。
- 30 JKP：ファクターの再現性。コードは公開。

## 4. 次の候補の推奨（ユーザーが決める）

**推奨：10（EXFormer）を、17 と 26 を物差しにして「日次の為替予測の反証」として設計する。**

- **選ぶ理由：**
  - 無料のデータで組める見込みで、9（債券）・12（株の業種）に続く3つ目の資産クラスになる。
  - 主張が強く（費用後 Sharpe 1.8超）、検証期間は約1年と短い。反証しやすく、学ぶことも多い。
  - 金利の外生変数には macrokit の利回りが使える。
- **反証の切り口：**
  - 長い期間と、2026年の公開後のデータで確かめる。
  - 比べる相手は、ランダムウォーク、キャリー、単純なモメンタム、切片付きのモデル（17 の教訓）、同じ入力の線形 AR（26 の教訓）。
  - 費用は先に事前登録する。
- **注意：** コードが無いので論文からの再実装になり、論文の数値とは比べにくい。データが本当に無料で揃うか（外生変数28本の中身と取得元）は、設計の最初に確かめる。

**ほかの道：**
- 15 DP-DPO：方法の研究で、データは軽い。
- 25 Kronos：timesfm_lab の続きで、公開後のデータと汚染の確認が要る。手間は小さい。
- 2 DeePM：ユーザーが先物データの購入を決めた場合だけ。

## 5. 進め方（9 と 12 で使った型）

- **流れ：**
  1. brainstorming で目的と判定を決める。
  2. 設計書 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` を書き、ユーザーが承認する。
  3. 実装計画 `docs/superpowers/plans/…` を書き、ユーザーが実行方法を選ぶ。
  4. 実行する。
  5. ブランチ全体を最終レビューする。
  6. merge と push は、それぞれユーザーの承認を得てから行う。
- **ラボの形：** お手本は `/home/kazumasa/projects/bond_timing_lab/` と `/home/kazumasa/projects/sector_leadlag_lab/` です。
  - ワークスペースのメンバー `<name>_lab` を作り、root `pyproject.toml` の members・testpaths・ruff の除外と、root `README.md` の一覧に足す。
  - 生データは `/home/kazumasa/projects/_data/<lab>/raw/`（Git の外）に1回だけ snapshot を取り、入力のハッシュを `results/inputs.json` に残す。
  - 段の順番は CLI で強制する。G0（データの検査と原論文の再現）→ G1（シグナルの無い世界と、効果を埋め込んだ世界で道具を確かめる）→ 本番 A → 本番 B（1回だけ。`results/main_b.lock`）→ 判定のあとの診断。
  - 各段の前に `PREREG.md` を commit する。判定の読み方は計算の前に決める。
- **言語：** README と PREREG は日本語で、表は `results/summary.md` から写す。コード・計画・commit は英語。

## 6. 守ること

- リポジトリは PUBLIC です。秘密情報、ユーザーのメールアドレス（外部 API の User-Agent などにも入れない）、勤務先・顧客の機密は書かない。
- **共有 .venv の同期は、リポジトリのルートで `uv sync --all-packages`（`make sync`）だけ。** 素の `uv sync` はメンバーの依存（pandas など）を全部外す（2026-10-20 に一度起き、すぐ戻した）。どちらでも、ロックの外にある maturin 製の `gto_py`・`gto_cuda` は消える。
- worktree の中では `uv sync`・`uv run` を使わず、共有 .venv の Python に `PYTHONPATH` を付けて動かす。`make test` は単一スレッドの BLAS で動く（Makefile が設定している）。
- 終わった研究の段は回し直さない。
  - 本番 B の lock を外さない。
  - `snapshot` を取り直さない（yfinance は過去の値も変わる）。
  - sector_leadlag_lab の `corrections` は回し直さない。`meta.ran_at` でハッシュが変わり、PREREG §5.3 と結果の `corrections_sha256` が合わなくなる。
- 大きな計算は先に容量を見積もる。1つの出力先が 30GiB を超えそうなら、ユーザーの承認が要る（AGENTS.md）。
- merge・push・branch や worktree の削除・外部への送信は、ユーザーの承認を得てから行う。worktree を消す前には `git -C <wt> status --ignored --short` と `du -sh <wt>` を確かめる。
- yfinance の日本の ETF・株には誤りが多い（配当の日付のずれ、分割の未記録、営業日の欠け）。Adj Close を信じない。詳しくは §2 の知識ノート。

## 7. 残件

- **sector_leadlag_lab の軽微な指摘63件：** どれも結果は変えない。2026-10-20 の Claude Code セッションの最終報告にあり、台帳は §1 の作業フォルダの `progress.md`。ラボを使い続けるなら、先に直す価値があるのは次の3件。
  - `corrections` を回し直すとハッシュの対応が切れる（`sector_leadlag_lab/src/sector_leadlag/cli.py:262-275`）。
  - `correct` を実データで確かめるテストがない。
  - README と summary の「既知の誤り（設計書 §2）」は、「PREREG §5.2」が正しい。
- **片付け：** §1 の worktree と branch（ユーザーの承認待ち）。
- **知識の置き場の提案：** 研究候補の一覧が、非公開の Artifact とこの一時メモにしかない。研究を続けるなら、一覧と各候補の結果を正本の文書（`docs/knowledge/` など）に移すことを、ユーザーに提案する。
