# Page 068 - 全文日本語訳

![Page 68](../assets/page_images/page_068.png)

## 日本語全文訳

モルガン・スタンレー
機密

9. 再校正：オフラインモデルの校正は毎日行われており、オンライン実装に使用される係数は一般的に月ごとに更新されます。
オンラインでのモデル係数の更新は、必要な係数csvファイルを生産用javaアプリケーションにアップロードすることで行います。これは新しい係数のパフォーマンス検証後に行われる手動プロセスです。詳細については10節参照。

** TRAINへのオンボード：モデルが実稼働しているアプリケーションはTRAINにオンボードされます。以下に生産リリースの例を示します（EUGV確率曲線モデルとは関連ありません）。**

- 例：JIRA: http://jira3.ms.com/jira/browse/AIMEXPNEGB-6934
- 例：テスト: http://train-zipviewer-prod.ms.com:5000/zipviewer/docs/afs/fidalyo/erates/06958_fidalgo_erates_master-2023.12.04-p13_test-results.tar.xz
- 例：TCM: http://changereview.webfarm.ms.com/app/#/tcm/602975777
- 例：PR: http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_ERATES/repos/erates/pull-requests/5952/overview

11. 生産サポート：モデル開発と生産展開の役割分離はTAMによって確保されます。VMSコマンドを実行して新しいコードバージョンをデプロイする際には、実施者が有効なTAMロールが割り当てられているかどうかのチェックが行われます。
指定されたGRNで与えられた役職に対するTCMまたはTAPが承認されている場合、デプロイコマンドは進行します。生産実行環境はIR-PMによって管理されます。

12. 生産展開：展開はSDLCサイクルに従って行われます。
QAサイクルを経て段階的に進み、その後は以前説明したように無作為/アクティブな生産インスタンスの交代が行われます。モデルを含むコンポーネントの無作為/アクティブインスタンスへの切り替え（ストラッツによって管理）または必要に応じて前のリリースビルドへの指し分ける（テクノロジーによって管理）により、瞬間的なロールバックが可能となります。

9.継続的なモデルパフォーマンス監視
9.1 監視されているメトリクス
MRMとの議論に基づき、モデルの継続的なパフォーマンス監視において以下のメトリクスが監視されます：
- ヒット率差（HR diff）
- APスコア差

ここで、ヒット率差は以下で定義されます：
\[ \text{hit RateDif f} = | \text{predictedHit Rate} - \text{realizedHit Rate} | \]

129576: EUGV RFQ価格設定用勝率モデル
ページ 68 / 73

[git]
- 分岐:
ir.eugy-hit-rate-curve @9676cba
- 発行日:
(2025-03-12)

## 翻訳ソース

- OCR: `source_en_pages/page_068.md`
- ページ画像: `../assets/page_images/page_068.png`
- 注意: OCR崩れがある箇所は、ページ画像を正として確認してください。
