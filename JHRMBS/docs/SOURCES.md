# 公開データソース

確認日: 2026-07-20。すべて無償・認証不要の公式公開ソースを使用する。

| ID | 提供者・データ | 形式 / 更新 | MVP での利用 | 取得 URL |
|---|---|---|---|---|
| `jhf_monthly` | JHF ファクター等毎月開示情報 | 年度別 XLS、原則毎月25日 | 回号 metadata、予定／実績 Factor、WAC、WAM、任意 CPR、WALA、長期延滞・その他解約 | [JHF](https://www.jhf.go.jp/about/investor/shisan_tanpo/kihatsu/m_f_monthly.html) |
| `mof_jgb` | 財務省 国債金利情報 | 全期間 CSV、営業日 | 月末営業日の JGB 10年を金利 proxy に使用 | [財務省](https://www.mof.go.jp/jgbs/reference/interest_rate/index.htm) |
| `flat35_current` | JHF フラット35 現行金利 | HTML、月次 | 21–35年・融資率9割以下の最低／最高／最頻金利を snapshot 蓄積 | [JHF simulation](https://www.simulation.jhf.go.jp/flat35/kinri/index.php/rates/top) |
| `mlit_housing_starts` | 国交省 建築着工統計 | XLS、月次 | 新設住宅着工戸数と前年比 | [国交省](https://www.mlit.go.jp/sogoseisaku/jouhouka/sosei_jouhouka_tk4_000002.html) |
| `boj_m3` | 日銀 M3 平均残高 | code API CSV、月次 | M3 と前年比 | [日銀 API 案内](https://www.boj.or.jp/statistics/outline/notice_2026/not260218a.htm) |
| `psj` | 日本証券業協会 標準期限前償還モデル | 定義文書 | WALA 60か月 ramp の固定 PSJ baseline | [JSDA](https://www.jsda.or.jp/shiryoshitsu/toukei/psj/index.html) |

## JHF workbook の解釈

- 取得ページから `.xls` / `.xlsx` link を発見し、固定 file 名に依存しない。
- 各 sheet の先頭20行から `債券年月` header を探索する。回号 sheet でない支払状況表等は記録して
  skip する。
- 列は位置でなく、日本語 header の正規化・alias で識別する。必須列は支払月、当初予定 Factor、
  実績 Factor。
- workbook bytes は無加工で content-addressed raw store に保存し、parser version を各行に残す。

## フラット35履歴の制約

公式サイトで確認できる過去推移は PDF グラフで、MVP が必要とする精度・定義を保った月次 CSV / XLS
の代替公式ソースは確認できなかった。このため PDF 座標抽出は行わず、現行 HTML を取得のたびに
snapshot として履歴化する。既定 model run は定義を混在させず、全期間で `WAC - JGB 10年` を
`rate_feature_is_proxy=true` として使う。同一定義の mortgage rate が学習行の90%以上を覆ったら、
設定を `mortgage_rate` に切り替えた別 run で比較する。任意 CSV の境界は README に記載する。

## 取得契約

- HTTPS かつ設定済み host のみ許可し、redirect 後も再検査する。
- timeout、指数 backoff、最大 retry、最大 file size を設定する。
- ETag / Last-Modified があれば条件付き GET を行う。同一 bytes は SHA-256 object を再利用する。
- manifest に source/final URL、取得 UTC、元 file 名、SHA-256、bytes、media type、対象期間、
  定義、HTTP validator、加工履歴、取得設定 file の SHA-256 を保存する。
- `ingest --source` の部分更新では、未選択 source の record を直前の snapshot から引き継ぎ、
  `build-dataset` が参照する latest manifest を完全な source set に保つ。
- source format drift は silent fallback せず `SourceFormatError` として停止する。
