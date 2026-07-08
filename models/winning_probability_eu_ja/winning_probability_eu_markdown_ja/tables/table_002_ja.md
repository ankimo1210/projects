# Table 2 - 日本語版

セグメンテーション軸を増やすと、segment countは急増し、各segmentのrecord countは急減します。データ期間は文書上、2024/01/01から2024/11/28のEUGV/UKGV RFQです。

| Segmentation | Segment count | Median record count | Min record count | Max record count |
|---|---:|---:|---:|---:|
| none | 1 | 1,331,524 | 1,331,524 | 1,331,524 |
| country | 11 | 47,366 | 5,894 | 350,265 |
| country-tier | 75 | 3,498 | 8 | 162,871 |
| country-tier-notional | 220 | 1,263 | 1 | 90,986 |

## 解釈

細かく分割すると曲線の形状をセグメント別に表現しやすくなりますが、サンプル数が不足して係数が不安定になります。この表は、RFQ factorをモデルに入れて曲線を平行移動させる設計と、データをsegmentに分けて傾きまで変える設計のトレードオフを示しています。
