モルガン・スタンレー                                                                                         機密


(ii) CRB最適化出力が制約を満たしていることを確認することも行います。もし制約に違反している場合、取引は行われません。
http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.inmj/src/main/java/erates/hedging/CrbOptimalMatcher.java#535|
http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.mmj/src/main/java/erates/corvo/CorvoOrderExecutor.java#209|

(iii) CRBスイングエンジンの制御は、セクション「リスク変更制御」で説明されています。
http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.mnj/src/main/java/erates/corvo/CorvoOrderExecutor.java#243 およびそのテスト http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.mmj/src/test/java/erates/corvo/CorvoOrderExecutorTest.java#

「ヘッジしない」の意図 http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.mmj/src/main/java/erates/corvo/CorvoOrderExecutor.java#246 およびそのテスト http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.mmj/src/test/java/erates/corvo/CorvoOrderExecutorTest.java#717

8.3 モデルコード変更管理とバージョン管理
モデル研究およびテストコードはPythonで書かれています。Opt-Varモデルを実装するソフトウェアは、Firmのソフトウェア開発ライフサイクル（SDLC）ポリシーに従って開発されました [J]。以下の表はソースコードの場所とライフサイクル管理を要約しています。
                        モデル開発システム名およびリンク
                      Tech管理制御              モデル開発 Jiraボード（EU）
                                                           モデル開発 Jiraボード（US）
                      コードバージョン制御                 モデルテストソースコードリポジトリ

8.4 ソフトウェア開発ライフサイクル（SDLC）
EUとUSでは同じ構造でソフトウェア開発ライフサイクルが進行しており、本節でその内容を説明します。

1. GRN: Opt-Varモデルはモルガン・スタンレーの電子取引ビジネスにおけるAutohedgerアルゴリズムによって国債のために使用されます。AutohedgerのGRNは/ms/fid/bondtrading/fidalgoです。また、CRBスイングエンジンによりCRB最適化にも使用されています。
2. 高レベルアプリケーションアーキテクチャ。図[77]はEU Autohedgerの高レベルアーキテクチャを示し、図[78]はUS AIMの高レベルアーキテクチャを示します。図に示すように、両地域においてOpt-VarモデルはAutohedgerアルゴリズム内のヘッジ計算機コンポーネント内に埋め込まれています。高レベルで見ると、Autohedgerアルゴリズムは取引書のポジションを監視し、リスク管理のためにヘッジ注文を出力します。USではOptVarモデルもCRB最適化 (stashblue.ms.com) に使用されています。



130115: Opt-Var                                                                                    第99ページ目/136ページ
