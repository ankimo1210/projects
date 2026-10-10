# 全20教師の保存検算予算補足 v3（未承認）

元v1の固定3600秒を変更せず、root指摘へのoverlayを追加した。生成と保存SDE/全11label・統計/16block/cov検算を別job予算で扱う。全N/格子/node数とgenuine cap親の原scopeは保持。

N1024全class実測をN比で外挿し、local-highだけはN65536 node17の39.414秒×原node数×N比との大きい方を使う。3倍して300秒単位へ切り上げる。単一nodeのbank/importを反復含む保守recipeであり、時間/RSS/容量の保証ではない。

| class | N | 原nodes | 生成cap候補 s | 保存検算推計 s | 保存検算cap候補 s |
|---|---:|---:|---:|---:|---:|
| Heston-coarse | 1024 | 108 | 300 | 31.009 | 300 |
| local-coarse | 1024 | 520 | 600 | 186.486 | 600 |
| Heston-coarse | 4096 | 108 | 600 | 124.035 | 600 |
| Heston-high | 1024 | 156 | 300 | 50.187 | 300 |
| Heston-high | 4096 | 156 | 900 | 200.749 | 900 |
| Heston-coarse | 16384 | 108 | 1800 | 496.138 | 1500 |
| Heston-high | 16384 | 156 | 3000 | 802.998 | 2700 |
| Heston-coarse | 65536 | 108 | 6300 | 1984.553 | 6000 |
| Heston-high | 65536 | 156 | 11100 | 3211.990 | 9900 |
| Heston-coarse | 65536 | 108 | 6300 | 1984.553 | 6000 |
| Heston-high | 65536 | 156 | 11100 | 3211.990 | 9900 |
| local-coarse | 4096 | 520 | 2400 | 745.946 | 2400 |
| local-high | 1024 | 1344 | 2100 | 827.692 | 2700 |
| local-high | 4096 | 1344 | 7500 | 3310.770 | 10200 |
| local-coarse | 16384 | 520 | 9300 | 2983.783 | 9000 |
| local-high | 16384 | 1344 | 29100 | 13243.080 | 39900 |
| local-coarse | 65536 | 520 | 36900 | 11935.130 | 36000 |
| local-high | 65536 | 1344 | 116400 | 52972.318 | 159000 |
| local-coarse | 65536 | 520 | 36900 | 11935.130 | 36000 |
| local-high | 65536 | 1344 | 116400 | 52972.318 | 159000 |

全20parent cap limitに反映する際は、その親に属する全static optionのexact-plan decision SHAを作り直す。旧承認decisionを流用しない。rootの新consumer/source closure結合は後続。最大Nの全母1344-node実行、金融精度、全op速度、whole物理容量、正式予算/phase/mainは未承認。

他の未測定opのruntimeはNone、行政cap候補と区別。全域domain-selected保存I/Oと母grid intermediate RSSは未確定のまま。原4GiB失敗・元生成費用を新39.414秒へ加算しない。追加金融測定やゲートを提案していない。
