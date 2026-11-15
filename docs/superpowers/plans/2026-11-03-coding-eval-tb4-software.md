# coding-eval（TB4 ソフトウェア課題のサブスク計測） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Terminal-Bench 4.0 のソフトウェア 18 課題を、AA の mini-swe-agent 設定に合わせて Claude Code・Codex のサブスク経由で解かせ、条件ごとの正解率と API 換算費用を図と表にする。

**Architecture:** Harbor の外部エージェント `SubscriptionMiniAgent` がホスト側で動く。各 CLI（`claude -p` / `codex exec`）に mini-swe-agent の指示文と、bash ツールを 1 つだけ持つ MCP サーバを渡し、エージェントのループは CLI 自身に回させる。bash ツールの呼び出しは、ホスト側のブリッジ（Unix ソケット）を経由して課題コンテナの `environment.exec` で実行される。ブリッジは返事を止めることで一時停止を実現し、提出の合図を検出したら CLI を止める。呼び出しごとのトークンは JSONL の台帳に残し、集計・統計・図は台帳と Harbor のジョブ出力だけから再生成する。

**Tech Stack:** Python 3.12（uv workspace）、Harbor（TB4 公式実行器）、mini-swe-agent（指示文とテンプレートの出典、版固定）、`mcp`（stdio MCP サーバ）、Docker Engine（WSL）、numpy、matplotlib、pytest。

**Spec:** `/home/kazumasa/projects/docs/superpowers/specs/2026-11-03-coding-eval-tb4-software-design.md`（承認 2026-11-03）

## Global Constraints

- TB4: dataset `terminal-bench/terminal-bench`、タグ `v4.0.0`、commit `452bf305c6daa62fc59061d22133a7cbc7c1572e`。
- 対象 18 課題: `bun-sourcemap-leak`, `cumulative-layout-shift`, `data-anonymization`, `distributed-dedup`, `kv-live-surgery`, `live-database-cutover`, `mvcc-lsm-compaction`, `nextjs-performance`, `ontology-kg-querying`, `payments-pipeline-fix`, `photonic-waveguide-routing`, `react-lead-form`, `rs-archive-clone`, `session-window-debug`, `telecom-entity-resolution`, `vba-userform-port`, `vf2-speedup-networkx`, `wal-recovery-ordering`。
- 1 回目の条件: `opus-5.5-high`（claude、`claude-opus-5-5`、effort `high`）と `gpt-6.1-sol-high`（codex、GPT-6.1 Sol、effort `high`）。各課題 1 回。
- 上限は 500 ステップ（モデル呼び出し数）と実働 8 時間（28800 秒、一時停止中は数えない）だけ。1 課題あたりの費用上限は設けない。
- 時間帯は 00:00〜08:00 Asia/Tokyo。週の上限はプロバイダーごとに 25 ポイント（週の枠の 25%）。5 時間枠が尽きる前に一時停止する。
- モデルの呼び出しは公式 CLI だけ。API キー、`--fallback-model`、認証情報が経由する中継プロキシは使わない。`claude --bare` は使わない（OAuth を読まない）。
- 混入検査の合格基準は spec §8 の「C8」。不合格の CLI のモデルは 1 回目から外す。
- 生データは `/home/kazumasa/projects/_data/coding-eval/`（worktree の中に置かない）。リポジトリに入れるのは設定・料金表・集計 CSV/MD・PNG・プローブ報告だけ。容量が 30 GiB を超えそうなら止めてユーザーに相談。
- 認証情報は `/home/kazumasa/projects/_data/coding-eval/secrets/`（chmod 600）。ログ・報告・fixture に書き出す前に伏せる。
- usage が欠けた呼び出しは 0 円で埋めない。欠けた割合が 5% を超えた点は図で白抜き。
- 図: 縦 = 正解率 0〜100%、横 = 1 課題あたり API 換算 USD（対数）、OpenAI は黒・Anthropic は橙、観測パレート線は点線、縦横の 95% 区間、注記（課題数・反復数・AA 設定との差・取得日・TB4 版）。AA の点は載せない。
- 統計: 課題単位ブートストラップの 95% 区間。2 条件の差の 95% 区間が 0 を含めば「判定できない」。
- 失敗の分類は spec §10。枠切れ・時間帯切れは一時停止で、無効にしない。
- 費用は「実行時の価格」と「現行価格」の 2 列。一時停止後の最初の呼び出しで、直前の呼び出しのプロンプト長までのトークンはキャッシュ読みとして計上し、差額は `pause_overhead_usd` として別に出す。
- 本番の見込み期間が 4 週間を超えるなら、本番の前にユーザーに相談する。
- ドキュメントは日本語、コード・識別子・コミットメッセージは英語。`uv` はリポジトリのルートで実行し、同期は `uv sync --all-packages`。`uv.lock` と `.env` のパスを Bash の引数に書かない（`git diff --stat` で見る）。
- 実装は分離した worktree・ブランチで行う（superpowers:using-git-worktrees）。
- テストはリポジトリ（worktree）のルートで `uv run --no-sync pytest coding-eval/tests/<file> -q`。各タスクの「失敗の確認」「通過の確認」はこのコマンドで行う。

## Review Focus

1. **PC の再起動や WSL の停止で、実行中の CLI とコンテナが消える**: 該当の実行は無効になり、`coding-eval run` を再実行すると未完了の課題だけが最初からやり直される。台帳は壊れない。→ Task 5（台帳の途中切れ行）、Task 10（CLI の異常終了）、Task 11（再実行で完了済みを飛ばす）。
2. **usage の重複行や欠落**（stream-json が同じメッセージを複数行に出す、強制終了で最後のイベントが届かない）: message id で重複を除き、欠けた分は欠測として数える。→ Task 5。
3. **一時停止中や実行中に週の枠がリセットされる**（使用率が下がる）: その週の消費量は 0 から数え直し、増加分が負にならない。→ Task 7。
4. **モデルが 1 回の応答で bash を複数回呼ぶ**: 順番に実行し、ステップ数はツール呼び出し数ではなくモデル呼び出し数で数える。→ Task 8、Task 10。
5. **巨大な出力・バイナリ出力・UTF-8 でない出力**: mini-swe-agent と同じ切り詰めをかけ、置換文字でデコードし、落ちない。→ Task 8。

---

## File Structure

```
coding-eval/
  pyproject.toml            # workspace member "coding-eval", package coding_eval, script `coding-eval`
  README.md                 # 使い方・手順・認証の準備（日本語）
  docs/STATUS.md            # 進捗・枠の消費・未対応（日本語）
  docs/interfaces.md        # Task 2 で確認した外部仕様（版つき）
  config/conditions.toml  config/tasks.toml  config/run.toml  config/prices.toml
  src/coding_eval/
    config.py               # 設定の読み込み
    events.py               # 共通イベント型・Usage
    events_claude.py        # claude stream-json の解析
    events_codex.py         # codex exec --json の解析
    pricing.py              # 料金表と費用計算
    ledger.py               # JSONL 台帳
    mini_prompts.py         # mini-swe-agent のテンプレートを版固定パッケージから描画
    gate.py                 # 夜間の時間帯・週の上限・5 時間枠
    bridge.py               # ホスト側ブリッジとコンテナ実行
    mcp_bash.py             # stdio MCP サーバ（bash ツール 1 つ）
    cli_claude.py  cli_codex.py   # CLI の起動内容（argv・env・設定ファイル）
    episode.py              # 1 課題分のループ制御
    outcome.py              # 結果の分類
    harbor_agent.py         # Harbor の外部エージェント
    probe.py                # 混入検査
    stats.py  collect.py  report.py  chart.py
    cli.py                  # `coding-eval probe|run|collect|report|status`
  tests/  (fixtures/claude_stream, fixtures/codex_stream, fixtures/tasks/hello, fakes/fake_cli.py)
  results/<YYYY-MM-DD>/     # コミットする小さな成果物
/home/kazumasa/projects/_data/coding-eval/{jobs,ledger,state,secrets,cli-home}/
```

### 共通の型（Task 4・5 で定義し、以降はこれを使う）

```python
# events.py
@dataclass(frozen=True)
class Usage:
    input_uncached: int; cache_read: int; cache_write_5m: int; cache_write_1h: int
    output: int                # 課金される出力（思考・推論を含む）
    reasoning: int | None      # output の内数。報告がなければ None
    def prompt_tokens(self) -> int: ...  # input_uncached + cache_read + cache_write_5m + cache_write_1h

@dataclass(frozen=True)
class ModelCall:  call_id: str; request_id: str | None; model: str | None; usage: Usage | None; stop_reason: str | None
@dataclass(frozen=True)
class RateLimit:  window: Literal["five_hour", "seven_day"]; used_pct: float; resets_at: datetime | None
@dataclass(frozen=True)
class SessionInit: session_id: str; model: str | None; tools: tuple[str, ...] | None
@dataclass(frozen=True)
class TurnEnd:    is_error: bool; error_kind: str | None   # "rate_limited" | "context_overflow" | "cli_error" | None
Event = ModelCall | RateLimit | SessionInit | TurnEnd

class EventParser(Protocol):
    def feed(self, line: str) -> list[Event]: ...   # 状態を持ち、同じ call_id の重複を 1 件にまとめる
```

---

### Task 1: 前提環境とプロジェクトの骨組み

**Files:**
- Create: `coding-eval/pyproject.toml`, `coding-eval/README.md`, `coding-eval/docs/STATUS.md`, `coding-eval/src/coding_eval/__init__.py`, `coding-eval/tests/test_smoke.py`
- Modify: `pyproject.toml`（`[tool.uv.workspace].members` と `testpaths` に `coding-eval` を追加）

**Interfaces:**
- Produces: import 可能なパッケージ `coding_eval`（`__version__ = "0.1.0"`）、依存 `harbor`・`mini-swe-agent`・`mcp`・`numpy`・`matplotlib` を版固定（`==`）で宣言。

- [ ] **Step 1: ユーザーに Docker Engine の導入を依頼する。** WSL の自分の端末で実行してもらう（sudo のパスワード入力があるため）。Ubuntu 24.04、systemd なし。

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER" && sudo service docker start
```

- [ ] **Step 2: 確認。** 新しいシェルで `docker run --rm hello-world` が "Hello from Docker!" を出し、`docker compose version` が版を出す。WSL を再起動したら `sudo service docker start` が要ることを README に書く。
- [ ] **Step 3: 失敗するテストを書く。** `tests/test_smoke.py::test_package_imports` — `import coding_eval; assert coding_eval.__version__ == "0.1.0"`、`import harbor, minisweagent, mcp`。
- [ ] **Step 4: 実行して失敗を確認。** `uv run --no-sync pytest coding-eval/tests/test_smoke.py -q` → ModuleNotFoundError。
- [ ] **Step 5: 骨組みを作り、`uv sync --all-packages` をルートで実行。** `git diff --stat` で lock の変更を見る。**既存メンバーが使うパッケージの版が変わった、または解決に失敗した場合は止める**。その場合は `coding-eval` を単独の uv プロジェクト（独自 `.venv`、`make test-extra` に追加）に切り替え、spec との差としてユーザーに報告する。
- [ ] **Step 6: テストが通ることを確認。** 同じコマンドで PASS。`uv run --no-sync harbor --version` が版を出す。
- [ ] **Step 7: Commit** — worktree の中で `git add coding-eval pyproject.toml && git add -u`、`git status --short` で自分の変更（lock を含む）だけが入っていることを確かめてから `git commit -m "Add coding-eval project skeleton"`。

### Task 2: 外部仕様の確認と fixture の採取（spike）

**Files:**
- Create: `coding-eval/docs/interfaces.md`, `coding-eval/tests/fixtures/claude_stream/*.jsonl`, `coding-eval/tests/fixtures/codex_stream/*.jsonl`, `coding-eval/tests/test_fixtures_sanitized.py`

**Interfaces:**
- Produces: 以降のタスクが参照する事実（各項目に版と確認方法を書く）と、伏せ字済みの実イベント。

- [ ] **Step 1: ユーザーに認証の準備を依頼する。**
  - Claude: `claude setup-token` を実行してもらい、出たトークンを `/home/kazumasa/projects/_data/coding-eval/secrets/claude_oauth_token` に保存（chmod 600）。
  - Codex: `CODEX_HOME=/home/kazumasa/projects/_data/coding-eval/cli-home/codex codex login --device-auth`。普段の `~/.codex/auth.json` はコピーしない（更新トークンの取り合いで普段のログインが切れうるため）。
- [ ] **Step 2: 次の事実を確認し、`docs/interfaces.md` に「項目・値・確認方法・版」で記録する。** 推測で埋めない。確認できない項目は「未確認」と書いてユーザーに報告する。
  - Harbor: 版の固定方法（`-d terminal-bench/terminal-bench@4.0.0` 相当）、課題の絞り込み、`--env docker`、同時実行数、`-a module:Class`、`--ak`、エージェントの制限時間を延ばす方法（一時停止を含めて数日続く試行のため）、ジョブ出力の場所と報酬の読み方、保存される成果物と採点だけをやり直す方法、中断したジョブの再開、試行が同じプロセスか別プロセスか。
  - mini-swe-agent（固定する版）: bash ツールの名前・説明・引数スキーマ、system・instance・observation・format_error・timeout のテンプレートとその変数の出所、コマンドの実行方法（シェル、stderr の扱い、cwd、env）、コマンドの制限時間、提出の判定（`COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` が出力の 1 行目か）、ツールを呼ばない応答の扱い、Harbor の mini-swe-agent 連携が渡す設定（`-c mini`、`--cost-limit` の既定値）。
  - Claude Code 2.1.316: `--system-prompt` の扱い（自己紹介の 1 行が残るか）、`--tools ""` と `--strict-mcp-config --mcp-config` と `--allowedTools` で MCP の bash だけを許す方法、文脈の自動要約の無効化、MCP ツールの待ち時間の上限を延ばす方法、最大出力トークンの指定、`CLAUDE_CONFIG_DIR`、`CLAUDE_CODE_OAUTH_TOKEN`、`--max-turns` の既定、`--resume` と `-p` の併用、stream-json の各イベントの形（init の tools、assistant の usage と message id、`rate_limit_event`、拒否の停止理由、エラー）、送ったリクエストを手元に記録する公式の手段（デバッグ出力）。
  - Codex 0.164.0: `model_instructions_file`、`--disable shell_tool`、`apply_patch` など他の組み込みツールを外す方法、MCP サーバの設定キー（command・args・env・tool_timeout_sec）、`model_reasoning_effort`、GPT-6.1 Sol のモデル ID、`codex exec --json` のイベントの形（usage の区分、推論トークン）、枠の情報が出るか、`codex exec resume`、送ったリクエストを手元に記録する公式の手段。
  - 公式の料金（Opus 5.5、GPT-6.1 Sol）と Opus 5.5 の最大出力トークン。出典 URL と取得日。
- [ ] **Step 3: fixture を採る。** 最小の固定入力で、本番と同じ組み立て（隔離した設定・MCP の bash）で、各 CLI を 1 回ずつ動かす。Claude は `claude-haiku-5-5`、Codex は最安のモデルで構わない。正常終了、ツール呼び出しあり、ツールを呼ばずに終わる応答の 3 種を `tests/fixtures/{claude,codex}_stream/` に保存する。トークン・メールアドレス・ホームのパスは伏せる。
- [ ] **Step 4: 伏せ字のテストを書いて通す。** `test_fixtures_sanitized.py::test_no_secrets_in_fixtures` — 全 fixture に `sk-`・`oauth`・`@gmail.com`・`/home/kazumasa` が含まれない。
- [ ] **Step 5: Commit** — `git commit -m "Record CLI and harness interface facts with sanitized fixtures"`

### Task 3: 参照解答での採点確認と容量の測定

**Files:**
- Create: `coding-eval/results/oracle/<YYYY-MM-DD>.md`
- Modify: `coding-eval/docs/STATUS.md`

- [ ] **Step 1: 18 課題の oracle を 5 回ずつ流す**（Task 2 で確認したコマンド。例 `uv run --no-sync harbor run -d terminal-bench/terminal-bench@4.0.0 -a oracle -k 5 --env docker -t <18課題> --n-concurrent 2`、ジョブ出力は `_data/coding-eval/jobs/oracle-<date>`）。
- [ ] **Step 2: 確認。** 課題ごとの合格回数（x/5）を報告ファイルに表で残す。5/5 でない課題は除外候補としてユーザーに報告する（本番の前に決めてもらう）。
- [ ] **Step 3: 容量を測る。** `docker system df` と `du -sh /home/kazumasa/projects/_data/coding-eval`。合計が 30 GiB を超えるなら止めてユーザーに相談する。
- [ ] **Step 4: Commit** — `git commit -m "Record TB4 software oracle check and disk usage"`

### Task 4: 設定と料金

**Files:**
- Create: `src/coding_eval/config.py`, `src/coding_eval/events.py`（`Usage` だけ先に）, `src/coding_eval/pricing.py`, `config/*.toml`, `tests/test_config.py`, `tests/test_pricing.py`

**Interfaces:**
- Produces:
  - `Condition(id, provider: Literal["anthropic","openai"], cli: Literal["claude","codex"], model, effort, label)`
  - `RunSettings(step_limit=500, active_time_limit_sec=28800, night_start=time(0), night_end=time(8), tz="Asia/Tokyo", weekly_cap_points=25.0, concurrency=2, hollow_missing_usage_frac=0.05, bootstrap_resamples=10000, seed=20261103, invalid_retry_limit=2, data_root=Path("/home/kazumasa/projects/_data/coding-eval"), codex_weekly_run_cap: int | None = None)`
  - `TaskSet(dataset, version, commit, tasks: tuple[str, ...])`
  - `load_conditions(path) -> dict[str, Condition]`、`load_run_settings(path) -> RunSettings`、`load_task_set(path) -> TaskSet`
  - `Price(model, effective: date, source_url, retrieved: date, input, cache_read, cache_write_5m, cache_write_1h, output)`（USD / 100 万トークン）
  - `load_prices(path) -> list[Price]`、`price_on(prices, model, day) -> Price`、`cost_usd(usage, price) -> float`
  - `pause_counterfactual(prev_prompt_tokens: int, usage: Usage) -> tuple[Usage, Usage]` — (補正後, 移したトークン)。移したトークンは元の区分のまま返す。
  - `overhead_usd(moved: Usage, price: Price) -> float` — 移したトークンを元の区分で払った額と、キャッシュ読みで払った額の差。

- [ ] **Step 1: 失敗するテストを書く。**

```python
def test_task_set_has_18_software_tasks():
    ts = load_task_set(CONFIG / "tasks.toml")
    assert ts.version == "4.0.0" and ts.commit.startswith("452bf305")
    assert len(ts.tasks) == 18 and "wal-recovery-ordering" in ts.tasks

def test_run_settings_defaults_match_spec():
    s = load_run_settings(CONFIG / "run.toml")
    assert (s.step_limit, s.active_time_limit_sec, s.weekly_cap_points) == (500, 28800, 25.0)
    assert (s.night_start, s.night_end, s.tz) == (time(0), time(8), "Asia/Tokyo")

def test_price_on_picks_latest_effective_not_after_day(): ...   # 2 版のうち day 以前で最新
def test_price_on_unknown_model_raises_keyerror(): ...
def test_cost_usd_opus_example():
    u = Usage(96, 5_089_246, 0, 230_193, 128_976, None)
    p = Price("claude-opus-5-5", date(2026,10,17), "x", date(2026,10,17), 4.0, 0.20, 5.0, 8.0, 20.0)
    assert cost_usd(u, p) == pytest.approx(5.43930, abs=1e-4)   # docs/knowledge 2026-10-17 の区間と同じ内訳
def test_pause_counterfactual_moves_rewrite_into_cache_read():
    adj, moved = pause_counterfactual(100_000, Usage(10, 0, 0, 100_500, 50, None))
    assert adj.cache_read == 100_000 and adj.cache_write_1h == 500 and moved.cache_write_1h == 100_000
    assert overhead_usd(moved, OPUS) == pytest.approx(0.78)          # 100k × ($8 − $0.20) / 1M
def test_pause_counterfactual_openai_moves_uncached_input():
    adj, moved = pause_counterfactual(50_000, Usage(60_000, 0, 0, 0, 10, 5))
    assert adj.cache_read == 50_000 and adj.input_uncached == 10_000 and moved.input_uncached == 50_000
```

- [ ] **Step 2: 実行して失敗を確認。** `uv run --no-sync pytest coding-eval/tests/test_config.py coding-eval/tests/test_pricing.py -q`
- [ ] **Step 3: 実装する。** TOML は `tomllib`。`config/prices.toml` には Task 2 で確認した公式価格を出典 URL・取得日つきで入れる。`pause_counterfactual` は、キャッシュ書き込み（1h → 5m の順）と、OpenAI ではキャッシュなし入力から、`prev_prompt_tokens` までをキャッシュ読みへ移す。
- [ ] **Step 4: テストが通ることを確認。**
- [ ] **Step 5: Commit** — `git commit -m "Add config loading and versioned price table"`

### Task 5: イベント解析と台帳

**Files:**
- Create: `src/coding_eval/events.py`（残りの型）, `events_claude.py`, `events_codex.py`, `ledger.py`, `tests/test_events_claude.py`, `tests/test_events_codex.py`, `tests/test_ledger.py`

**Interfaces:**
- Consumes: Task 2 の fixture と `docs/interfaces.md`、Task 4 の `Usage`。
- Produces: `ClaudeStreamParser()`・`CodexJsonParser()`（どちらも `EventParser`）。
  - `CallRow(run_id, condition_id, task, seq: int, ts: datetime, session_id, call_id, request_id, model, stop_reason, usage: Usage | None, after_pause: bool)`
  - `RunRow(run_id, condition_id, task, attempt: int, outcome, reason, steps, active_sec, paused_sec, refusals, submitted, started, ended, cli_version, harbor_job)`
  - `Ledger(root: Path)`: `append_call(row)`、`append_run(row)`、`calls(run_id=None) -> list[CallRow]`、`runs() -> list[RunRow]`。

- [ ] **Step 1: 失敗するテストを書く。**

```python
def test_claude_parser_dedups_repeated_message_lines():      # fixture の同一 message id の複数行 → ModelCall 1 件
def test_claude_parser_reads_usage_categories():             # cache_creation の 5m/1h を分けて Usage に入る
def test_claude_parser_emits_rate_limits():                  # rate_limit_event → RateLimit("five_hour"/"seven_day", used_pct, resets_at)
def test_claude_parser_init_reports_tools_and_session():     # SessionInit.tools に MCP の bash だけ
def test_claude_parser_marks_refusal():                      # stop_reason == "refusal" の ModelCall
def test_codex_parser_usage_counts_reasoning_inside_output():# output は推論込み、reasoning は内数
def test_parsers_ignore_unknown_and_blank_lines():
def test_ledger_survives_truncated_last_line(tmp_path):      # 最後の行が途中で切れたファイルを読んでも例外にならず、その行だけ捨てる
def test_ledger_calls_dedup_by_run_and_call_id(tmp_path):
def test_ledger_missing_usage_stays_none(tmp_path):          # None が 0 に化けない
```

- [ ] **Step 2: 実行して失敗を確認。**
- [ ] **Step 3: 実装する。** 台帳は `ledger/calls.jsonl` と `ledger/runs.jsonl` への追記（1 行ごとに flush・fsync）。拒否の停止理由や usage のキー名は `docs/interfaces.md` の記録に従う。
- [ ] **Step 4: テストが通ることを確認。**
- [ ] **Step 5: Commit** — `git commit -m "Parse CLI usage events into an append-only ledger"`

### Task 6: mini-swe-agent のテンプレート描画

**Files:**
- Create: `src/coding_eval/mini_prompts.py`, `tests/test_mini_prompts.py`

**Interfaces:**
- Produces:
  - `MiniPrompts(version, system, tool_name, tool_description, tool_parameters: dict, env: dict[str, str], command_timeout_sec: int, submit_sentinel)`
  - `load_mini_prompts(template_vars: dict[str, str]) -> MiniPrompts`、`render_instance(task, template_vars) -> str`、`render_observation(returncode, output, exception_info=None) -> str`、`render_timeout(command, output) -> str`、`render_format_error(hit_output_limit: bool) -> str`、`is_submission(output) -> bool`

- [ ] **Step 1: 失敗するテストを書く。** 期待値は、固定した版の mini-swe-agent 自身のテンプレートと描画関数で作る（Task 2 で特定したもの）。手書きの期待文字列は使わない。

```python
def test_system_and_instance_match_mini_rendering(): ...       # mini 自身の描画結果とバイト単位で一致
def test_observation_truncates_like_mini():                    # 12_000 文字の出力 → mini と同じ先頭・末尾 5_000 文字と警告
def test_tool_schema_matches_mini_bash_tool(): ...             # 名前 "bash"、説明・引数スキーマが mini と一致
def test_is_submission_first_line_only():
    assert is_submission("COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\nrest")
    assert not is_submission("x\nCOMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")   # Task 2 の確認結果と食い違えば、確認結果に合わせる
def test_load_records_mini_version():                          # MiniPrompts.version == 固定した版
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。** テンプレートは `importlib.resources` で固定版パッケージの設定ファイルから読み、mini と同じ Jinja2 の設定で描画する。
- [ ] **Step 5: Commit** — `git commit -m "Render mini-swe-agent prompts from the pinned package"`

### Task 7: 一時停止の判定（時間帯・週の上限・5 時間枠）

**Files:**
- Create: `src/coding_eval/gate.py`, `tests/test_gate.py`

**Interfaces:**
- Consumes: `RateLimit`、`RunSettings`。
- Produces:
  - `GateDecision(allowed: bool, reason: str | None, resume_at: datetime | None)`
  - `NightWindow(start: time, end: time, tz: str)`: `contains(now) -> bool`、`next_open(now) -> datetime`
  - `QuotaBudget(state_path: Path, provider: str, weekly_cap_points: float, run_cap: int | None)`: `observe(rl: RateLimit, now, after_gap: bool, max_step_increment_pct: float) -> None`、`points_used_this_week() -> float`、`note_run_started(now) -> None`、`check(now) -> GateDecision`
    - 状態ファイルは fcntl でロックし、別プロセスの試行と共有する。増加分は「プロバイダー全体で最後に見た使用率」からの差で数えるので、同時に走る試行が同じ増加を二重に数えない。
    - `after_gap=True`（一時停止明けの最初の観測）では、増加分のうち `max_step_increment_pct` までだけを計測の消費とみなす（昼にユーザーが使った分を数えないため）。
  - `Gate(window: NightWindow, budget: QuotaBudget)`: `decide(now, last_five_hour: RateLimit | None, max_step_increment_pct: float) -> GateDecision`

- [ ] **Step 1: 失敗するテストを書く。**

```python
def test_night_window_jst():
    w = NightWindow(time(0), time(8), "Asia/Tokyo")
    assert w.contains(dt("2026-11-04T07:59+09:00")) and not w.contains(dt("2026-11-04T08:00+09:00"))
    assert w.next_open(dt("2026-11-04T08:00+09:00")) == dt("2026-11-05T00:00+09:00")
def test_night_window_uses_tz_not_system_clock():               # UTC で渡しても JST で判定
def test_budget_counts_only_increases_between_observations():   # 10→12→15 で 5 ポイント
def test_budget_rebaselines_after_daytime_gap():                 # 10 →（昼）→ 30、after_gap=True、max_step 2 → +2 だけ
def test_budget_no_double_count_across_trials():                 # 試行 A が 10→12、試行 B が 12 を観測 → 合計 +2
def test_budget_resets_when_weekly_window_resets():              # resets_at が変わる/使用率が下がる → 0 から数え直し、負にならない
def test_budget_blocks_at_25_points_until_reset():               # 25 に達したら allowed=False、resume_at=週のリセット時刻
def test_budget_run_cap_fallback_when_no_rate_limits():          # Codex で枠情報がなく run_cap=3 → 4 件目で止まる
def test_gate_pauses_before_five_hour_exhaustion():              # used 96 + max_step 5 ≥ 100 → 停止、resume_at = resets_at
def test_budget_state_shared_across_instances(tmp_path):         # 2 つの QuotaBudget が同じファイルで合計を共有
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。**
- [ ] **Step 5: Commit** — `git commit -m "Add night window, weekly budget and five-hour gate"`

### Task 8: ブリッジと MCP の bash サーバ

**Files:**
- Create: `src/coding_eval/bridge.py`, `src/coding_eval/mcp_bash.py`, `tests/test_bridge.py`, `tests/test_mcp_bash.py`

**Interfaces:**
- Consumes: `MiniPrompts`、`render_observation`、`render_timeout`、`is_submission`。
- Produces:
  - `ExecOutcome(returncode: int, output: str, timed_out: bool)`、`Executor = Callable[[str], Awaitable[ExecOutcome]]`
  - `harbor_executor(environment, env: dict[str, str], timeout_sec: int) -> Executor` — Task 2 で確認した mini の実行方法（シェル・stderr の合流・cwd・env）を `environment.exec` で再現する。
  - `BridgeServer(socket_path, executor, prompts, before_reply: Callable[[], Awaitable[None]], on_submit: Callable[[], None])`: `start()`・`stop()`、属性 `tool_calls: int`・`submitted: bool`。プロトコルは 1 行 JSON（要求 `{"command": str}`、応答 `{"text": str}`）。提出を検出したら返事をせず `on_submit()` を呼ぶ。
  - `mcp_bash.main()` — 環境変数 `CODING_EVAL_BRIDGE_SOCKET` と `CODING_EVAL_TOOL_SPEC`（ツールの名前・説明・スキーマの JSON ファイル）を読み、その仕様どおりの bash ツールを 1 つだけ公開する stdio MCP サーバ。

- [ ] **Step 1: 失敗するテストを書く**（偽の Executor を使う）。

```python
async def test_reply_is_mini_observation(tmp_path): ...            # 応答 text == render_observation(rc, out)
async def test_before_reply_blocks_until_released(tmp_path): ...    # before_reply が待つ間は応答が届かない
async def test_submission_calls_on_submit_and_never_replies(tmp_path): ...
async def test_parallel_calls_execute_sequentially(tmp_path): ...   # 2 接続から同時に来ても実行は 1 つずつ、tool_calls == 2
async def test_huge_binary_output_is_truncated_and_decoded(tmp_path):  # 2 MB の非 UTF-8 → 置換文字でデコード、mini の切り詰め、例外なし
async def test_timeout_uses_mini_timeout_text(tmp_path): ...
def test_mcp_server_lists_exactly_one_bash_tool(tmp_path): ...      # mcp のクライアントで stdio 起動 → ツール一覧が仕様どおりの 1 件
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。** `harbor_executor` は Docker が要るので Task 11 の結合テストで確かめる。
- [ ] **Step 5: Commit** — `git commit -m "Add host bridge and single-tool MCP bash server"`

### Task 9: CLI の起動内容

**Files:**
- Create: `src/coding_eval/cli_claude.py`, `src/coding_eval/cli_codex.py`, `tests/test_cli_claude.py`, `tests/test_cli_codex.py`

**Interfaces:**
- Consumes: `Condition`、`RunSettings`、`MiniPrompts`、`docs/interfaces.md`。
- Produces:
  - `CliLaunch(argv: list[str], env: dict[str, str], cwd: Path, stdin_text: str)`
  - `write_mcp_tool_spec(path, prompts) -> None`、`write_claude_mcp_config(path, python: str, socket: Path, tool_spec: Path) -> None`
  - `claude_launch(cond, prompts, message, resume_session: str | None, workdir, config_dir, oauth_token, mcp_config, settings) -> CliLaunch`
  - `write_codex_home(home, cond, instructions_file, python: str, socket: Path, tool_spec: Path) -> None`（`auth.json` は Task 2 の login で作られたものを使い、上書きしない）
  - `codex_launch(cond, message, resume_session: str | None, workdir, home) -> CliLaunch`

- [ ] **Step 1: 失敗するテストを書く。**

```python
def test_claude_launch_isolates_and_restricts():
    l = claude_launch(...)
    assert "--bare" not in l.argv and "--fallback-model" not in l.argv
    assert l.argv[l.argv.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in l.argv and l.argv[l.argv.index("--effort") + 1] == "high"
    assert l.env["CLAUDE_CONFIG_DIR"].startswith("/home/kazumasa/projects/_data/coding-eval/cli-home/")
    assert "HOME" not in l.env or l.env["HOME"] != os.environ["HOME"]   # Task 2 の結論に合わせる
    assert l.cwd.is_dir() and not any(l.cwd.iterdir())                  # 空の作業ディレクトリ
    assert l.stdin_text == message                                      # 長い指示文は argv ではなく stdin
def test_claude_resume_adds_resume_flag(): ...
def test_claude_launch_disables_autocompact_and_raises_tool_timeout(): ...   # Task 2 で確認したキー名と値
def test_codex_home_config_has_only_bridge_tool():
    cfg = tomllib.loads((home / "config.toml").read_text())
    assert cfg["model_reasoning_effort"] == "high" and "model_instructions_file" in cfg
    assert cfg["features"]["shell_tool"] is False and set(cfg["mcp_servers"]) == {"bash"}
def test_codex_home_preserves_existing_auth(tmp_path): ...
def test_codex_launch_uses_json_and_resume(): ...
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。**
- [ ] **Step 5: Commit** — `git commit -m "Build isolated Claude Code and Codex launches"`

### Task 10: 1 課題分のループ制御

**Files:**
- Create: `src/coding_eval/episode.py`, `tests/fakes/fake_cli.py`, `tests/test_episode.py`

**Interfaces:**
- Consumes: Task 5〜9 のすべて。
- Produces:
  - `EpisodeResult(end: str, steps: int, active_sec: float, paused_sec: float, refusals: int, session_id: str | None, model_ids: frozenset[str])`。`end` は `"submitted" | "step_limit" | "time_limit" | "refusal" | "gave_up" | "context_overflow" | "model_mismatch" | "cli_error" | "resume_failed"`。
  - `async run_episode(cond, instruction, executor, prompts, settings, gate, ledger, run_id, task, launcher, parser_factory, clock) -> EpisodeResult`
- 決めごと（spec と Task 2 の確認による）:
  - 最初の入力は `render_instance(...)`。CLI がツールを呼ばずに応答を終えたら、`render_format_error(...)` を次の入力にして同じセッションを再開する（mini と同じ扱い）。ただし停止理由が拒否なら `end="refusal"` で終える。
  - ステップ数はモデル呼び出し（重複除去後の `ModelCall`）の数。500 に達した時点で CLI を止める。
  - 実働時間 = 経過時間 − 一時停止時間。28800 秒に達したら止める。
  - 一時停止は、ブリッジの `before_reply` の中で `gate.decide(...)` が許可を出すまで待つことで行う。待ち始めと終わりを台帳に書き、次の `ModelCall` に `after_pause=True` を付ける。
  - 応答のモデル ID が条件の `model` と違えば、その場で止めて `end="model_mismatch"`（無効として扱う）。
  - CLI の異常終了は `cli_error`、再開の失敗は `resume_failed`。

- [ ] **Step 1: 失敗するテストを書く**（`fake_cli.py` はシナリオ JSON に従って fixture 形式のイベントを出し、ブリッジのソケットへ bash 要求を送る）。

```python
async def test_submission_stops_cli_and_records_steps(): ...      # end="submitted"、CLI プロセスが終了済み
async def test_step_limit_counts_model_calls_not_tool_calls(): ... # 1 応答で bash を 3 回 → steps は 1
async def test_step_limit_stops_at_500(): ...
async def test_time_limit_excludes_paused_time(): ...              # 偽の時計で 9h 経過・2h 停止 → まだ続く
async def test_no_tool_call_resumes_with_format_error(): ...       # 2 回目の起動が resume かつ入力が format_error
async def test_refusal_ends_episode_and_counts(): ...
async def test_model_mismatch_stops_episode(): ...
async def test_cli_crash_is_cli_error_and_ledger_intact(): ...     # Review Focus 1
async def test_pause_marks_next_call_after_pause(): ...
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。**
- [ ] **Step 5: Commit** — `git commit -m "Run one subscription-backed mini episode with pause and limits"`

### Task 11: 結果の分類、Harbor エージェント、実行コマンド

**Files:**
- Create: `src/coding_eval/outcome.py`, `src/coding_eval/harbor_agent.py`, `src/coding_eval/cli.py`（`run` と `status`）, `tests/test_outcome.py`, `tests/test_harbor_agent_docker.py`, `tests/fixtures/tasks/hello/`（Harbor の課題形式）

**Interfaces:**
- Produces:
  - `classify(end: str | None, reward: float | None, infra_error: str | None) -> tuple[str, str]` — 戻り値は `("pass"|"fail"|"invalid", 理由)`。
  - `SubscriptionMiniAgent(BaseAgent)`: `name() -> "coding-eval-subscription-mini"`、`__init__(self, logs_dir: Path, model_name: str | None = None, condition: str = "", **kwargs)`、`version()`、`async setup(environment)`（テンプレート変数をコンテナから集める）、`async run(instruction, environment, context)`（`run_episode` を呼び、`context.n_input_tokens`・`n_cache_tokens`・`n_output_tokens`・`cost_usd`（API 換算）・`metadata`（end、steps、paused_sec、refusals、model_ids）を埋め、台帳に `RunRow(outcome="pending", reason=end, ...)` を追記する）。採点はエージェントの後に Harbor が行うので、合否の確定は `classify` を使う側（`run` の開始前と Task 13 の `collect`）で行う。
  - `coding-eval run --condition ID [--tasks a,b] [--pilot]` — 開始前に、Harbor のジョブ出力の報酬と台帳を `classify` で突き合わせ、pass/fail が確定した（課題, 条件）は飛ばし、invalid は `invalid_retry_limit` 回までやり直す。そのうえで Harbor を `-a coding_eval.harbor_agent:SubscriptionMiniAgent --ak condition=ID`、固定した dataset と版、`--env docker`、`--n-concurrent {settings.concurrency}`、延ばした制限時間で呼ぶ。
  - `coding-eval status` — プロバイダーごとの今週の消費ポイント、一時停止の理由と再開時刻、残りの課題数を表示する。

- [ ] **Step 1: 失敗するテストを書く。**

```python
@pytest.mark.parametrize("end,reward,infra,expected", [
    ("submitted", 1.0, None, ("pass", "submitted")),
    ("step_limit", 1.0, None, ("pass", "step_limit")),      # 合否は採点だけで決める
    ("step_limit", 0.0, None, ("fail", "step_limit")),
    ("refusal", 0.0, None, ("fail", "refusal")),
    ("cli_error", None, None, ("invalid", "cli_error")),
    ("model_mismatch", 0.0, None, ("invalid", "model_mismatch")),
    ("submitted", None, None, ("invalid", "verifier_error")),
    (None, None, "docker_error", ("invalid", "docker_error")),
    ("unknown_end", 0.0, None, ("fail", "unknown")),        # 判別できないものは失敗
])
def test_classify(end, reward, infra, expected): assert classify(end, reward, infra) == expected

def test_run_skips_finished_and_retries_invalid(tmp_path): ...   # Review Focus 1: 台帳の内容から再実行対象を決める

@pytest.mark.skipif(not os.environ.get("CODING_EVAL_DOCKER"), reason="needs Docker")
def test_agent_solves_hello_task_with_fake_cli(tmp_path): ...    # 偽の CLI が bridge 経由で /app/hello.txt を作り提出 → reward 1、台帳に RunRow
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。** Docker のテストは `CODING_EVAL_DOCKER=1 uv run --no-sync pytest coding-eval/tests/test_harbor_agent_docker.py -q` で確かめる。
- [ ] **Step 5: Commit** — `git commit -m "Wire the subscription agent into Harbor with resumable runs"`

### Task 12: 混入検査

**Files:**
- Create: `src/coding_eval/probe.py`, `cli.py` に `probe` を追加, `tests/test_probe.py`

**Interfaces:**
- Produces:
  - `ProbeReport(condition_id, cli_version, tools: tuple[str, ...] | None, first_prompt_tokens: int | None, expected_prompt_tokens_upper: int, boilerplate: list[str], request_excerpt: str | None, model_self_report: str, model_ids: tuple[str, ...])`
  - `check_probe(report, allowed_tools: set[str], allowed_boilerplate: list[str]) -> list[str]` — 違反の一覧（空なら合格）。
  - `async run_probe(cond, settings) -> ProbeReport`、`coding-eval probe --condition ID`（報告を `results/probes/<cond>-<date>.json` に伏せ字で保存）。
- 決めごと: `expected_prompt_tokens_upper = ceil(len(system + instance + tool_spec_json) / 2) + 1000`。個人設定（CLAUDE.md・メモリなど数千トークン以上）が混ざれば超える。許す固定の文は spec C8 の 3 種だけで、全文を報告に残す。

- [ ] **Step 1: 失敗するテストを書く**（Task 2 の fixture から作った報告を使う）。

```python
def test_clean_report_passes(): assert check_probe(clean, {"mcp__bash__bash"}, ALLOWED) == []
def test_extra_tool_fails(): assert "extra tool: apply_patch" in check_probe(with_apply_patch, ...)
def test_prompt_too_large_fails(): ...       # first_prompt_tokens > upper → "prompt larger than expected"
def test_unknown_boilerplate_fails(): ...
def test_missing_tool_list_requires_request_excerpt(): ...   # tools が None で request_excerpt もなければ不合格
def test_saved_report_is_sanitized(tmp_path): ...
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。**
- [ ] **Step 5: Commit** — `git commit -m "Add contamination probe with spec acceptance rules"`

### Task 13: 集計・統計・表・図

**Files:**
- Create: `src/coding_eval/stats.py`, `collect.py`, `report.py`, `chart.py`, `cli.py` に `collect`・`report` を追加, `tests/test_stats.py`, `tests/test_collect.py`, `tests/test_report_chart.py`

**Interfaces:**
- Consumes: `Ledger`、`load_prices`、`price_on`、`cost_usd`、`pause_counterfactual`、Harbor のジョブ出力（報酬の読み方は `docs/interfaces.md`）。
- Produces:
  - `bootstrap_rate_ci(passes, n, seed, level=0.95) -> tuple[float, float, float]`、`bootstrap_mean_ci(values, n, seed, level=0.95)`、`paired_diff(a: Mapping[str, bool], b: Mapping[str, bool], n, seed, level=0.95) -> tuple[float, float, float, str]`（判定は `"a_better" | "b_better" | "undetermined"`）、`clopper_pearson(k, n, level=0.95) -> tuple[float, float]`
  - `RunResult(run_id, condition_id, task, outcome, reason, cost_runtime_usd: float | None, cost_current_usd: float | None, pause_overhead_usd: float, missing_usage_frac: float, steps, active_sec, refusals)`、`collect(ledger, prices, today: date, jobs_root: Path) -> list[RunResult]`
  - `ConditionSummary(condition_id, label, provider, n_tasks, n_excluded, pass_rate, pass_lo, pass_hi, cost_mean, cost_lo, cost_hi, cost_median, time_mean_sec, refusals, limit_hit_frac, missing_usage_frac, hollow: bool)`、`summarize(results, conditions, settings) -> list[ConditionSummary]`
  - `write_summary(summaries, csv_path, md_path)`、`write_task_matrix(results, csv_path)`、`write_comparisons(results, conditions, settings, md_path)`、`pareto_front(points: list[tuple[float, float]]) -> list[int]`、`plot_frontier(summaries, out_png, notes: list[str])`
  - `build_notes(task_set, settings, deviations_path: Path, data_date: date) -> list[str]` — 課題数・反復数・「10 ポイント未満の差は判定できない」・TB4 の版・取得日と、`config/deviations.toml`（AA 設定との違い。Task 14 で書く）の各行。
  - `coding-eval collect` と `coding-eval report --out coding-eval/results/<YYYY-MM-DD>`

- [ ] **Step 1: 失敗するテストを書く。**

```python
def test_paired_diff_all_vs_none():
    d, lo, hi, v = paired_diff({t: True for t in T18}, {t: False for t in T18}, 2000, 1)
    assert (d, lo, hi, v) == (1.0, 1.0, 1.0, "a_better")
def test_paired_diff_identical_is_undetermined(): ...   # d == 0、判定 "undetermined"
def test_bootstrap_is_seeded_and_reproducible(): ...
def test_clopper_pearson_known_value(): assert clopper_pearson(9, 18) == pytest.approx((0.260, 0.740), abs=1e-3)
def test_invalid_task_excluded_from_all_conditions(): ...    # 片方の条件で invalid が上限回数 → 両条件から除外、n_excluded == 1
def test_missing_usage_makes_point_hollow(): ...              # 欠測 6% → hollow=True、費用は None を 0 にしない
def test_pause_overhead_excluded_from_cost(): ...
def test_runtime_and_current_price_columns_differ_after_price_change(): ...
def test_pareto_front(): assert pareto_front([(1, .5), (2, .4), (3, .7)]) == [0, 2]
def test_plot_writes_png_with_notes(tmp_path): ...            # PNG が書かれ、注記が渡った文字列を含む（matplotlib の Agg）
def test_build_notes_includes_deviations_and_power_note(tmp_path): ...   # deviations.toml の行と「10 ポイント未満」の注記が入る
```

- [ ] **Step 2〜4: 失敗の確認 → 実装 → 通過の確認。** 図の見た目は、生成した PNG を開いて目で確認する（ラベルの重なり、白抜き、対数軸）。
- [ ] **Step 5: Commit** — `git commit -m "Summarize runs with bootstrap intervals and plot the frontier"`

### Task 14: 本物での混入検査と配線確認（枠を使う）

**Files:**
- Create: `coding-eval/results/probes/*.json`, `coding-eval/results/pilot/<YYYY-MM-DD>.md`
- Modify: `coding-eval/docs/STATUS.md`, `coding-eval/config/run.toml`（必要なら `codex_weekly_run_cap`）, `coding-eval/config/deviations.toml`

- [ ] **Step 1: 混入検査。** `uv run --no-sync coding-eval probe --condition opus-5.5-high` と `--condition gpt-6.1-sol-high`。不合格の条件は 1 回目から外し、理由を STATUS に書いてユーザーに報告する。合格した条件について、残った固定の文と、AA 設定との違い（温度、最大出力トークン、fallback、反復 1 回、ツール名の接頭辞など、`docs/interfaces.md` で確認したもの）を `config/deviations.toml` に 1 行ずつ書く。
- [ ] **Step 2: 配線確認**（ユーザーに開始の了承を得て、夜間に実行）。合格した条件ごとに、短い課題 1〜2 個（例 `photonic-waveguide-routing`、`bun-sourcemap-leak`）を `coding-eval run --condition ID --tasks ... --pilot` で流す。
- [ ] **Step 3: 確認。** `coding-eval collect && coding-eval report --out coding-eval/results/pilot-<date>` が通る。台帳の 1 課題あたりの費用が、Claude Code 自身の `total_cost_usd`（取れる場合）と 2% 以内で一致する。一時停止と再開を 1 回は通す（時間帯の終わりをまたぐか、設定で人工的に止める）。
- [ ] **Step 4: 期間の見積もり。** 1 課題あたりの実費と週 25% の枠から、18 課題 × 条件の期間を計算し、`results/pilot/<date>.md` と STATUS に書く。**4 週間を超えるならユーザーに相談して止める。** Codex で枠の情報が読めなかった場合は、ここで `codex_weekly_run_cap` を決めて設定に書く。
- [ ] **Step 5: Commit** — `git commit -m "Record contamination probes and pilot run"`

### Task 15: 本番の手順書と開始

**Files:**
- Modify: `coding-eval/README.md`（手順）, `coding-eval/docs/STATUS.md`

- [ ] **Step 1: README に本番の手順を書く。** 開始コマンド、`coding-eval status` での見方、PC を再起動したときの再開（`sudo service docker start` → 同じ `coding-eval run` を再実行）、止め方、終わったあとの `collect`・`report`。
- [ ] **Step 2: ユーザーの開始指示を待つ。** 指示が出たら、条件ごとに `coding-eval run --condition ID` を夜間の時間帯の前に起動する（時間帯の外では待機する）。
- [ ] **Step 3: 完了の確認**（spec §14）。`coding-eval report --out coding-eval/results/<date>` の PNG・CSV・MD がそろい、STATUS に結果・枠の実消費・AA 設定との違い・未対応が書かれている。
- [ ] **Step 4: Commit** — `git commit -m "Add run book and first TB4 software results"`
