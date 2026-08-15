# SEC B9 offline panel builder — 実データでの試走レポート

作成日: 2026-08-11
対象: `analytics/quant_research/tools/build_b9_panel.py` /
`src/quant_textbook/sec_panel.py`（未コミット、`a7e16336` 以降の作業中コード）
実施者: Claude（リポジトリ内ファイルは未変更）

## 結論

network-free panel builder を、8/10–8/11 に取得済みの60社キャッシュに対して
実際に走らせた。**2つの fail-closed 挙動を実データで確認**できた。1つ目は
想定どおり正しく機能した。2つ目は**新しい実データパターン**を検出し、
150社拡張の前に対処が必要である。

## 1. accession 未解決の fail-closed（想定どおり）

60社中20社の submissions は `filings.files` に古い履歴の分割アーカイブを持つ
（`recent` window だけでは全 accession が解決できない）。archive 無しで
`build_b9_panel` を実行すると:

```
UnresolvedAccessionError: SEC accession metadata is missing;
fetch filings.files archives before building a PIT panel:
('0001047469-11-006302', ...)
```

これは前回私が指摘した「accn の12.2%が `recent` に無く `filed` へフォールバック
している」問題への直接の修正である。**フォールバックせず例外を投げる**設計が
実データでも正しく動作した。全 archive を取得後、この段階は解消した。

## 2. 新発見: 同日に複数四半期を提出する遅延提出者

archive 取得後、次のエラーで停止した。

```
ValueError: target availability must follow previous availability
for CIK 64472 and period 2025-03-31
```

原因を追ったところ、この企業は **2024-12-31 期と 2025-03-31 期の2本の 10-Q を
同一日（2025-07-25）に、6分差で提出**していた。

| accession | form | reportDate | acceptedDateTime |
|---|---|---|---|
| 0001193125-25-164836 | 10-Q | 2024-12-31 | 2025-07-25T11:30:42Z |
| 0001193125-25-164840 | 10-Q | 2025-03-31 | 2025-07-25T11:36:08Z |

`availability_date` は「acceptance 日の翌営業日」という**日単位**の粒度で計算
されるため、両四半期の availability_date が同一日になり、
`target_available_date > previous_available_date` という厳格な不等号を破る。

`sec_panel.py` はこれを**サイレントに許容せず例外で止めた**。フォールバックして
先に進む設計ではない点は前項と同じで、正しい。

### この現象は例外的ではない

60社サンプルで、同一 filingDate に異なる reportDate の 10-K/10-Q が複数本ある
企業を数えると:

```
14 / 60 社（23.3%）
```

いずれも delinquent filer が未提出分をまとめて一括提出した典型パターンで、
2004年から2025年まで広い期間に分布している。**単一企業を除外して回避できる
規模ではなく、universe 全体に一定確率で存在する構造的パターンである。**

## 3. B9 実装への含意

150社拡張を行う前に、この2ケース目への明示的な方針が要る。選択肢:

1. **availability_date の粒度を日から acceptance timestamp（分単位）へ上げる。**
   `acceptanceDateTime` は既に取得済みなので、同日提出でも提出順は判定できる。
   ただし「翌営業日から利用可能」という保守的な契約と時刻粒度をどう両立するか
   決める必要がある。
2. **同日提出ペアを panel から明示的に除外し、除外件数を品質診断へ記録する。**
   実装コストは低いが、遅延提出企業のデータをそのぶん失う。
3. **strict `>` を `>=` に緩め、同日提出は同時に利用可能だったとみなす。**
   一番簡単だが、「target が strictly 未来でなければならない」という PIT の
   前提をわずかに緩めることになるので、他の不変条件との整合を要確認。

現状のコードは3つのどれも選ばず**エラーで停止する**。これは安全側だが、
150社規模ではこのパターンが約23%の頻度で起きる前提を踏まえると、
「エラーで都度手動除外」より上記いずれかの明示的なルールを contract に
追記するほうが実装的に楽になる。

## 4. 検証環境

- Cache: 8/10–8/11 に取得した60社（`Assets` frame `CY2015Q4I` から決定的抽出）+
  今回追加取得した submissions archive 22ファイル
- 取得: `curl -A "<UA>" https://data.sec.gov/submissions/<archive-name>.json`
- 実行コマンド:
  ```bash
  uv run --no-sync python analytics/quant_research/tools/build_b9_panel.py \
    --cache-root <cache> --output <out> \
    --anchor-period-end 2015-12-31 --anchor-as-of 2016-04-01 \
    --analysis-start 2016-04-01 --minimum-assets-usd 100000000 \
    --time-cutoff 2023-01-01
  ```
- コードは変更していない。cache のファイル命名を `fetch_sec_b9_cache.py` の
  規約（`companyfacts_CIK##########.json` / `submissions_CIK##########.json`）
  へ合わせただけ。

## 5. テストへの示唆

`tests/test_sec_panel.py` の現在のカバレッジは synthetic fixture のみで、
同日複数四半期提出のケースが無い。この実データで見つかったパターンを
regression fixture として追加する価値がある（`treasury_phantom_row.xml` と
同じ発想）。

---

## その後の対応

本レポートで報告した2件（accession 未解決の fail-closed、同日複数四半期提出の
23.3% 発生）への GPT 側の対応と、その後の B9 M6 protocol 実装のレビューは、
レビュー系を1本に集約するため次のノートへ記載した。

→ `_docs/2026-08-10-quant-research-curriculum-alignment-feedback.md` の
**追記5: B9 M6 protocol レビュー（2026-08-11 11:03）**

要点だけ記すと、§3 で挙げた3案のうち **案2（同日提出ペアを除外し件数を診断へ
記録）が採用**され、Sample gate は `hold` → `pass`（strict both split n=413）に
なった。
