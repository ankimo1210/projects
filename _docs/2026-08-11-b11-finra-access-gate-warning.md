# B11 着手前の注意 — FINRA が access gate を通っていない

作成日: 2026-08-11
対象: `analytics/quant_research` / B11（Week 41–44）
実施者: Claude（リポジトリ内ファイルは未変更）
関連: `_docs/2026-08-10-quant-research-curriculum-alignment-feedback.md` 追記8 §4

## 要点

B11 の実装計画 `docs/plans/2026-08-11-stage-2e-b11.md` は、Week 42 の Core データ源に
**FINRA Treasury Daily Aggregate Statistics** を置いている。しかしこのデータ源は
Treasury / SEC に適用した5 gate を通っていない。**Notebook 6冊を書き始める前に
feasibility spike を1本入れることを勧める。**

## 現状

`FINRA` の文字列がリポジトリ内に存在するのは1ファイルだけである。

```bash
$ grep -rln "FINRA" docs/ src/ tools/ notebooks/ tests/
docs/plans/2026-08-11-stage-2e-b11.md
```

`docs/updates/`、`docs/contracts/`、`src/`、`tools/`、`tests/`、`notebooks/` には無い。
つまり access ノートも contract も snapshot も無い状態で、実装計画の
Week 42 と Final project の「observable liquidity fields」がこの source に依存している。

対して既存の2 source は、Core に入れる前に判定表を通している。

| Source | Access | Semantics | Sample | Baseline | Teaching fit | 記録先 |
|---|---|---|---|---|---|---|
| U.S. Treasury daily par yield | pass | pass | pass | pass | pass | `docs/updates/2026-08-10-stage-2-data-feasibility-follow-up.md` |
| SEC EDGAR (PIT panel) | pass | pass | pass | pass | pass | `docs/updates/2026-08-11-sec-baseline-gate.md` |
| **FINRA Treasury daily aggregates** | **未確認** | 未確認 | 未確認 | 未確認 | 未確認 | — |

## 確認すべき3点

### 1. 利用条件（最優先）

**このプロジェクトには前例がある。** FRED / ALFRED は「取得できるか」ではなく
**ToS の ML/AI 利用制限**を理由に不採用にした。FINRA も同様に、取得可否とは別に
以下を一次資料で読む必要がある。

- 再配布と派生物（snapshot を repository にコミットしてよいか）
- 教材・非商用利用の扱い
- 自動取得（スクリプトによる daily file 取得）の可否とレート

「取れたから使える」で進めると、後から Treasury/SEC と同じ
「snapshot + manifest + hash を repository に置く」再現契約が組めない可能性がある。

### 2. 実際に取得できるか

計画が挙げている一次資料（未検証・plan からの引用）:

- <https://www.finra.org/finra-data/browse-catalog/about-treasury/daily-data>
- <https://www.finra.org/finra-data/browse-catalog/about-treasury/daily-file>

確認項目:

- daily file の URL 形式と、認証・アカウント登録の要否
- 履歴の遡及範囲（計画は 2023-02-13 以降の公開開始と記載）
- 提供フィールドが計画の主張範囲と一致するか
  （trade count、par volume、ATS/interdealer 対 dealer-to-customer、
  on/off-the-run composition、一部 VWAP）
- Treasury bulk CSV が 403 だった前例（feasibility spike 参照）と同種の
  アクセス制限が無いか

### 3. 再現契約に載るか

Treasury は「年次 XML を固定 snapshot 化 + manifest + 年ごとの hash」で
ビット単位再現を実証した。FINRA も同じ形に落とせるか。落とせないなら、
Week 42 は offline fixture ベースの単位検証（quoted / effective / realized spread の
式検証）に限定し、実データ分析の主張を外す判断が要る。

## なぜ着手前なのか

B9 で同じ構造の再設計を一度やっている。原典の「中央銀行文書・market reaction」題材は
データが取得できず、SEC filing + fundamentals へ丸ごと置換した。あのときは
Notebook を書く前に feasibility gate を通したので置換で済んだ。

B11 で Notebook 6冊と `quant_specialization.py` の API を FINRA 前提で固めた後に
「使えない」と判明すると、章構成・演習・Final project contract まで巻き戻る。
gate は Notebook より前に置くほうが安い。

## 巻き戻りを最小化する代案（gate が通らなかった場合）

計画の Week 42 は「observable liquidity と execution boundary の区別」を教えることが
主眼で、FINRA はその実例に過ぎない。gate が通らない場合は次で目的を達成できる。

- spread / impact の**恒等式と単位検証**は合成 quote fixture で完結する
  （計画自身が「trade-level quote fixture で単位検証」と書いている）
- 「aggregate volume から spread や Kyle lambda を逆算しない」という
  **主張境界の教育**は、データが無いことそのものを教材にできる
  （B9 で「取得不能なデータを合成しない」を教材化したのと同じ手）
- 公式 Treasury curve だけで Week 41・43・44 は成立する

つまり最悪ケースでも B11 全体が崩れるわけではなく、Week 42 の
「実データ分析」部分だけが「fixture による式検証 + データ不在の明示」へ縮む。
この退避先を先に決めておけば、gate の結果がどちらでも進める。

## 状態

未着手。この spike は GPT の章執筆と衝突しない（読み取りと外部取得の検証だけで、
リポジトリ内ファイルを変更しない）ので、依頼があれば実施できる。
