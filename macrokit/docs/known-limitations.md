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

## 3. 公表規則が「期末の翌月」固定 → 解消済み

`ReleaseRule.month_offset`（既定 1）を追加し、`release._month_after` を
`_publication_month(period_end, month_offset)` に置き換えた。期末の翌々月に
公表される法人企業統計のような系列も `month_offset: 2` で表現できる。

`release_lag_days` も `int | None = None` にして任意化した。`Indicator` には
model_validator を追加し、`release_rule` と `release_lag_days` の少なくとも
一方は必須（両方 None なら公表タイミングを何も表現できないため拒否）とした。
既存の US エントリ（`release_lag_days` のみを持つ）はそのまま検証を通る。

JP 実質 GDP の 148 個の実測公表日時は Plan 2 の後続タスクが e-Stat の XML から
取り込むため、`jp_real_gdp_qoq_saar` の `release_rule` は `kind: manual`（
`resolve_release` は常に `None` を返す）とし、`month_offset: 2` は目安として
だけ添えてある。

残っている開いた項目は §2 の `ReleaseRule.calendar` のみ：現状は `jp` を
受理し他を全拒否するだけで、`{jp_gov, jp_bank, us}` のように**どの休日体系を
使うか**を選ぶフィールドにはなっていない。

## 4. `vintage_seq` の意味は取得窓に依存する

`vintage_seq = 1` が「速報」を意味するのは、`fetch_raw` が realtime 窓全体
（`1776-07-04`..`9999-12-31`）を要求している間だけ。

設計書 §5.3 の第 2 層（差分だけ取る）を素直に実装すると窓を絞りたくなり、その
瞬間 `seq=1` は「要求した窓の中での初回」に変わる。`sources/alfred.py` の
docstring に明記済みだが、ストア側に密度の検証は無い。

テスト用 fixture `tests/fixtures/alfred_pcepilfe.json` は本番より狭い窓
（`2024-04-01`..`2024-12-31`）で録ってあるため、そこに見える最初の vintage は
**実際の初回公表ではない**。

**同じ制約は GDP 側にもある。** `store.recompute_vintage_seq` は
`observations` に入っている分だけを公表順に採番するので、`seq=1` は
「取り込んだ中で最も古いリリース」であって「真の初回公表」ではない。
GDP の取り込みは 2008 年 Q4 以降なので、1994〜2008 年の期間について
`seq=1` が指すのは 2009 年のリリースである。

なお既存 DB の `vintage_seq` を直すには `gdp vintages` の再実行が必要で、
これは 141 回の逐次取得で約 15 分かかる。安価な修復経路は用意していない。
`vintage_seq` を読むのは `pit.revisions` だけで、パネルの数値には一切
影響しないため、急いで直す必要はない。

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
- **`store.connect()` はセッションのタイムゾーンを `Asia/Tokyo` に固定する
  （`SET TimeZone='Asia/Tokyo'`）。** DuckDB は保存した `TIMESTAMPTZ`
  （`release_date`、`ingested_at`）をセッションタイムゾーンで描画するが、
  `panel.py`（`release_date.date()`）と `expectations.py`（前営業日の判定）は
  その値から「どの東京の暦日か」を決める。固定していなければホストのローカル
  タイムゾーンに依存し、`TZ=UTC` のホストでは 08:50 JST の公表が前日 23:50 UTC
  （日曜）と解釈されて取引セッションが見つからず、パネル行数が変わり、
  `expectations.as_of` の 過半数が 1 営業日早くずれる（§6.1 の「知り得ない未来」
  エラーの逆、「知り得たはずの改定を静かに握りつぶす」バグ）——何も例外を
  出さずに、である。開発ホストがたまたま JST なので、この固定を外しても
  ローカルでは再現しない。回帰確認は `tests/test_store.py` のタイムゾーン
  テストが別プロセス＋`TZ=UTC` で行っている。

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
- `2nd_prelim_revised` は `releases` テーブルには載るが `observations` には
  絶対に載らない。`gdp vintages` が `esri_gdp.menu_url` の窓（1st_prelim /
  2nd_prelim の `qe{YY}{Q}[_2]` パターン）しか知らず、`2nd_prelim_revised` は
  取得元 URL を導出できないため意図的に除外している（`cli.py` の
  `exclude_kinds`）。以前 `panel.event_panel` にあった `include_revised` フラグは
  この理由で常に無意味だった（本番データで `include_revised=True` としても行数・
  内容が変わらず、revised 種別の JOIN が 0 件だったことを確認して削除した）。
  改定履歴の取り込みを実装する場合は menu URL をハードコードするか手作業で
  解決する仕組みが要る（未実装、意図的にスコープ外）。
- `gdp vintages` は約 141 件を逐次取得するループで、再開マーカーが無い。途中で
  中断すると（公表日の新しい順に走るわけではないので）欠けるのは最新側の
  vintage で、その状態のまま `gdp expectations` を走らせると欠けた vintage
  抜きで期待値が計算・保存される（例：2026 Q1 の 1 次速報しか無い状態で計算した
  2026 Q2 の `random_walk` は 2.1 になるが、2026 Q1 の 2 次改定まで揃っていれば
  正しくは 1.8）。`insert_expectations` は `INSERT OR REPLACE` なので後続の
  完全な再実行は正しい値で上書きするが、**再実行するのを忘れると古い期待値が
  永久に残る**。`gdp vintages` が `skipped` を報告した、または途中で落ちた場合は、
  その後に必ず `gdp expectations` を再実行すること。
