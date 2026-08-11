# 2026-08-11 — B9 filing provenance and retrieval gate

## 結論

ロック済みM6 panelを変更せず、各rowを前回filingへ結ぶprovenance sidecarを実装・照合した。
連絡先入りUser-Agentで4,631件のSEC primary documentを外部cacheへ取得し、raw / normalized manifest、
coverage、duplicate、target-text exclusionを監査した。正式なtext modeling gateは**pass**した。

これはB9の入力開始permissionであり、candidate modelの優劣やdeep learningの追加価値を示す結果ではない。
outer testは未開封のままである。

## 実装した境界

- `b9-sec-panel-v1`へ列を足さず、`b9-previous-filing-provenance-v1`を別artifactとして生成する。
- 各rowについてprevious/targetのAssets、period end、availability dateをraw SEC cacheから再構築し、
  ロック済みrowと一致しなければfail closedにする。
- sidecarは`previous_accession`、form、filing date、timezone付きacceptance、availability、
  primary document、監査専用`target_accession`を保持する。
- downloaderはprevious primary documentだけをSEC Archivesから取得する。429 / 5xx / network errorだけを
  bounded exponential backoffで再試行し、404等は即時failureにする。
- raw documentとmanifestはstaging fileからatomic publishする。連絡先入りUser-Agentは検証するが
  manifestへ保存しない。
- raw監査はfile hash / byte count、row coverage、exact raw duplicate familyのpartition跨ぎ、
  `previous_accession == target_accession`を検査する。
- stdlibのHTML parserでscript、style、hidden node、markupを除き、heading / paragraph順と可視table
  cell textを保持するvisible-text正規化と、normalized hash / token count / duplicate-family監査を実装した。

raw document SHAの一致は、visible textを正規化した後のduplicate検査の代用ではない。そのためrawと
normalizedのgateを分離し、後者がない場合は`--require-gate`を通さない。

### candidate評価前のinput-quality amendment

最初の正規化は`table` subtree全体を除外したため、80文書が100 tokens未満になった。同じ80文書は
可視table cell textを保持すると全て500 tokens以上になった。旧filingがlayout table内へ本文を置くためである。
candidateを評価する前に、table構造だけを除き可視cell textを保持するようcleaning contractを修正した。
split、candidate family、metric、selection ruleは変更していない。

## 実データ照合

| 項目 | 結果 |
|---|---:|
| M6 panel rows | 4,631 |
| sidecar rows | 4,631 |
| unique previous documents | 4,631 |
| duplicate row keys | 0 |
| missing primary document rows | 0 |
| previous / target accession一致 | 0 |
| sidecar gate | pass |
| raw retrieval success | 4,631 / 4,631 |
| raw / normalized row coverage | 100% / 100% |
| empty normalized documents | 0 |
| normalized exact duplicate families | 0 |
| partitionを跨ぐduplicate families | 0 |
| normalized token count min / median / p90 / max | 917 / 30,012 / 68,654 / 155,540 |
| text modeling gate | pass |

fingerprint:

| artifact | SHA-256 |
|---|---|
| locked M6 panel | `6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8` |
| input-quality amendment時点のpre-analysis contract | `fbe69fdf3b3bccba7fab70bcbb726d0df61685901cc0322d76fc66be1d7bbd6e` |
| external provenance sidecar | `9ff2efef335357ff53bb1e4ba5c57f4b2e8799fc4ee5d830c55843a50026fbbc` |
| raw retrieval manifest | `5c63ba733f9ab3814bea37eb76aa921d8c36d5a3dc09cb4272edeb3d42ae9ba2` |
| normalized text manifest | `1283b9cb0992cfd2caaa942f6c869e212762c90a9abbc9a050173f5e3963daba` |
| text gate audit | `58c5a891e31f50236715336a24ed9e15f8f542351d2c149623cd2bba4312f1de` |

sidecarはraw SEC cacheと同じ外部領域に置き、repositoryへcommitしない。生成コマンドは次のとおり。

その後のteaching-fixture診断でpooled driftより強いfixed baselineが確認されたため、full candidate
evaluation、nominee freeze、outer accessより前にselection gateをamendした。現在のcontract SHA-256は
`0aa180acbcd2b685509d6ec65fdf40f9edfcfc544ecec62c930facd0d4615b20`である。入力品質、split、feature、
candidate family、budget、bootstrap、locked outerは変更していない。

```bash
uv run --no-sync python analytics/quant_research/tools/build_b9_filing_provenance.py \
  --panel-artifact "$B9_M6_ROOT/full/derived/panel_audit.json" \
  --cache-root "$B9_M6_ROOT/full/cache" \
  --holiday-manifest "$B9_M6_ROOT/derived/us_federal_holidays_1990_2035.json" \
  --preanalysis-contract analytics/quant_research/docs/contracts/b9-preanalysis-v1.json \
  --output "$B9_M6_ROOT/full/derived/previous_filing_provenance.json"
```

個人の連絡先はsource、manifest、Gitへ保存していない。raw response、normalized text、各manifestは外部cacheに
だけ置く。正式判定はraw / normalized rootの両方を渡す`audit_sec_b9_filing_text.py --require-gate`で行った。

## 次の作業

1. B9 Week 33–36 / Projectを`curriculum_map.yml`へ追加する。
2. feature pipelineとnumeric ridge / TF-IDF ridgeを実装し、active training partitionだけでfitするtestを追加する。
3. NumPy MLP / LSTM / TCN / small self-attentionを実装し、nominee manifestを固定するまでouterを開かない。
