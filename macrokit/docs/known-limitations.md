# 既知の制約と次フェーズへの引き継ぎ

Phase 1（基盤）完了時点、2026-08-17。設計書は
[`docs/superpowers/specs/2026-08-17-macrokit-design.md`](../../docs/superpowers/specs/2026-08-17-macrokit-design.md)。

Phase 1 のレビューで見つかったが、意図的に次フェーズへ送った項目。放置すると
Plan 2 で再発見する。**上ほど先に効いてくる。**

## 1. 秘匿情報：httpx が URL を INFO でログする

`httpx` は `_client.py::_send_single_request` で **API キーを含む完全な URL** を
`logger.info` に出す。今は root logger の既定が WARNING なので不活性。

**Plan 2 で cron エントリポイントを書くとき、`logging.basicConfig(level=INFO)` を
1 行書いた瞬間にキーが cron ログに出続ける。** 例外側の漏洩は
`sources/alfred.py` の `_redact()` で塞いであるが、こちらは別経路。

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
```

関連して `AlfredRequestError.__context__` には未 redact の `HTTPStatusError` が
残っている（`from None` は `__cause__` と既定のトレースバック出力しか抑止しない）。
標準の traceback と pytest は出さないが、`__context__` を無条件に辿るエラー
レポータ（Sentry 等）を入れると再漏洩する。`err.__context__ = None` で潰せる。

## 2. 営業日カレンダーが年末年始を落としている

祝日の出所は内閣府「国民の祝日」CSV のみ。**行政機関の休日（12/29〜1/3）と
銀行休業日（12/31〜1/3）を含まない。** そのため `release.nth_business_day` は
1 月と 12 月の営業日を最大 2 日多く数える。

日銀「消費活動指数」は**毎月第 5 営業日** 14:00 公表なので、この規則を実装した
時点で 1 月の公表日が 1 日ずれる。`tests/test_release.py` の該当アサーション横に
CAVEAT コメントを置いてあるが、値は未修正のまま。

`ReleaseRule.calendar` は `jp` / `us` を受け付けるが、現状 `jp` 以外は拒否する
だけで、カレンダーの選択には使われていない。本来は `{jp_gov, jp_bank, us}` の
ように**どの休日体系を使うか**を選ぶフィールドであるべきで、上記と一緒に設計し
直すのが安い。

## 3. 公表規則が「期末の翌月」固定

`release._month_after` が固定なので、以下が**原理的に表現できない**。

| 系列 | 実際の公表 |
|---|---|
| JP 実質 GDP 1 次速報 | 期末の約 1.5 か月後（翌々月） |
| 法人企業統計 | 約 2 か月後 |
| 日銀短観 | 期初月 |

`ReleaseRule` に月オフセット相当のフィールドが無い。加えて `release_lag_days` は
カタログの必須フィールドなのに**コード中に読み手が 1 つも無い**（公表タイミングの
表現が 2 つあり、片方が死んでいる）。

Plan 2 は JP 15 群を手書きする工程なので、**書き始める前に**スキーマを決めること。

## 4. `vintage_seq` の意味は取得窓に依存する

`vintage_seq = 1` が「速報」を意味するのは、`fetch_raw` が realtime 窓全体
（`1776-07-04`..`9999-12-31`）を要求している間だけ。

設計書 §5.3 の第 2 層（差分だけ取る）を素直に実装すると窓を絞りたくなり、その
瞬間 `seq=1` は「要求した窓の中での初回」に変わる。`sources/alfred.py` の
docstring に明記済みだが、ストア側に密度の検証は無い。

テスト用 fixture `tests/fixtures/alfred_pcepilfe.json` は本番より狭い窓
（`2024-04-01`..`2024-12-31`）で録ってあるため、そこに見える最初の vintage は
**実際の初回公表ではない**。

## 5. `validated` 状態に到達する経路が無い

`status.load_validated` は `data/validated.json` を読むが、**書くコードは存在
しない**。実際に到達可能な最高状態は `parsed`。

本物の検証ランは「同一指標を 2 ソースから取って突合」（設計書 §6 の最重要施策）で、
日本のソースが入る Plan 2/3 まで実装できない。設計書 §7 の Phase 1 目標は
`parsed` に改訂済み。

## 6. スケールに関するもの

- `status._has_snapshot` は**指標ごとに manifest 全体を読み直す**。1 指標では
  不可視、50 指標 × 日々伸びる manifest で効いてくる。`macrokit ingest` を書く
  ときに 1 回走査して指標名の集合を作る形に変えるのが自然。
- `sources/alfred.py` の tenacity は **4xx でも 3 回リトライ**し、429 の
  `Retry-After` を見ない。設計書 §5.4 のレート制限（FRED 30 req/min）も未実装。
  400 が 4 秒消費するため、テストスイートの実行時間の大半をこれが占めている。
  `retry_if_not_exception_type(AlfredRequestError)` で解消できる。
- `snapshot.last_sha` は `source` かつ `indicator` で照合するが、
  `status._has_snapshot` は `indicator` のみ。指標名が一意な現状では同値だが、
  相互検証で同一指標を 2 ソースから取ると意味が分かれる。

## 7. 配置・環境の前提

- **`macrokit` は editable install 前提。** `ingest.default_catalog_root()` は
  ソース配置からパスを解決するので、非 editable な wheel では成立しない
  （`macrokit/catalog/` は hatchling の `packages` に含まれない）。カタログは
  人が手で編集する約 50 個の YAML になるため、発見性を優先して現在地に置く決定を
  した。パスが存在しなければ明示的に落ちる。
- **CLI の `--data-root` 既定値は CWD 相対**（`macrokit/data`）。リポジトリルート
  以外から叩くとその場に `macrokit/data/` が生えて「全部 declared」と出る。
  Plan 2 で cron から CWD 不定で走らせると **snapshot 履歴が 2 箇所に分裂し、
  `last_sha` が過去を見失って全件を「変化あり」として再保存する。**
- ワークスペース root の pytest には `-m "not live"` の既定が無い。
  `FRED_API_KEY` を export した状態で `make test` を回すと実 API を叩く。
  ワークスペース全体の方針に関わるため未変更。

## 8. 小さいもの

- `periods.period_end_for` の未知 freq、`insert_observations` の全件衝突時の
  戻り値、`resolve_release` の引数欠落時の `ValueError` 群は未テスト。
- naive datetime のガードは `datetime` 以外（`date`、`numpy.datetime64`）に対して
  `ValueError` ではなく `AttributeError` を出す。拒否はするが、メッセージが不親切。
- `resolve_release` は `calendar="us"` かつ `kind="manual"` でも例外を投げる
  （以前は `None` を返した）。カタログを走査して公表カレンダーを組む処理では、
  スキップではなくクラッシュになる。
- `ingest.ADAPTERS` は現状どこからも使われていない（`macrokit ingest` 待ち）。
- `components` テーブルは作られるが読み書きもテストも無い（設計どおり、Phase 4）。
- 祝日 CSV のキャッシュに失効が無い。CSV は翌年分までしか含まないので、1 年以上
  前のキャッシュを使うと当年後半の営業日計算が静かに間違う。またこの取得だけが
  snapshot / manifest 層を通らない独自キャッシュになっている。
- `tests/test_status.py` の truncated manifest の fixture は壊れた行を中間に置く。
  追記専用ファイルでは末尾行しか壊れ得ないので、有効行 → 末尾に truncated 行 →
  別指標を照会、という順序の方が物理的に忠実（現行でも無防備な実装に対しては
  実際に落ちるので、テストとしては有効）。
