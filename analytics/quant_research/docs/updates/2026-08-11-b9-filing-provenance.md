# 2026-08-11 — B9 filing provenance and retrieval gate

## 結論

ロック済みM6 panelを変更せず、各rowを前回filingへ結ぶprovenance sidecarを実装し、実cacheで
照合した。SEC primary documentの取得ツールとraw integrity監査も実装したが、連絡先を含む
User-Agentを用いた実取得と実documentに対するvisible-text正規化はまだ実行していない。したがってB9 text trackの
90% coverage gateは**未判定**であり、model tournamentはまだ開始しない。

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
- stdlibのHTML parserでscript、style、table、hidden nodeを除き、heading / paragraph順を保持する
  visible-text正規化と、normalized hash / token count / duplicate-family監査を実装した。

raw document SHAの一致は、visible textを正規化した後のduplicate検査の代用ではない。そのためrawと
normalizedのgateを分離し、後者がない場合は`--require-gate`を通さない。

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

fingerprint:

| artifact | SHA-256 |
|---|---|
| locked M6 panel | `6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8` |
| external provenance sidecar | `82dac4788278eda408f0f154dcf70d4293cafe06c438cda186cb760ce4d09e7b` |

sidecarはraw SEC cacheと同じ外部領域に置き、repositoryへcommitしない。生成コマンドは次のとおり。

```bash
uv run --no-sync python analytics/quant_research/tools/build_b9_filing_provenance.py \
  --panel-artifact "$B9_M6_ROOT/full/derived/panel_audit.json" \
  --cache-root "$B9_M6_ROOT/full/cache" \
  --holiday-manifest "$B9_M6_ROOT/derived/us_federal_holidays_1990_2035.json" \
  --preanalysis-contract analytics/quant_research/docs/contracts/b9-preanalysis-v1.json \
  --output "$B9_M6_ROOT/full/derived/previous_filing_provenance.json"
```

実取得時は個人の連絡先をsourceやshell historyへ固定しない方法で`--user-agent`を渡し、外部raw cacheを
`--output-root`へ指定する。取得完了後は`normalize_sec_b9_filing_text.py`を実行し、raw / normalized rootの
両方を渡して`audit_sec_b9_filing_text.py --require-gate`を通す。normalized rootがない場合、正式gateはfailする。

## 次の作業

1. 連絡先入りUser-Agentでprevious documentを外部cacheへ取得し、failure reasonを確定する。
2. 実documentを正規化し、row coverage 90%以上、normalized duplicate familyのpartition非跨ぎ、target exclusionを監査する。
3. gate通過時だけB9 Week 33–36 / ProjectのNotebook実装とcandidate evaluationへ進む。
