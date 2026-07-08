morgan stanley                                                                                       機密


          TRAIN     コンポーネント                                    リンク

          TCM                                                    |http ://changereview.webfarm.ms .com/app/#/tcm/   ]
                                                                 602929932
          Jira,                                                  http: //jira3.ms. com/jira/browse/EURAH-2116
                                                                 (EU)
                                                                 |nttp://jira3.ms.com/jira/secure/RapidBoard.
                                                                 jspa?rapidView=48196view=planningSissueLimit= |
                                                                 100 (US)
          Test                                                   http: //changereview.webfarm.ms .com/app/#/tcm/
                                                                 602929932| (テストタブ)
          Bitbucket PR.                                          http: //stashblue.ms.com/atlassian-stash/          ]
                                                                 [proj ects/FIDALGO_MMJ/repos/mmj/pull-             ]
                                                                 requests/3863/overview
          Train release build                                    https://train-portalui-prod.ms.com/#/view/         ]
                                                                 {name space/VMS/meta/fidalgo/project/mmj/          ]
                                                                 release/2023. 10. 10-p425-master|

    11. 生産環境。モデル開発と生産展開の役割分離はTAMによって確保されます。VMSコマンドが新しいバージョンを展開する際に、実行している人物が有効なTAMロールを持っているかどうかを確認します。指定されたGRNに対してTCMまたはTAPが承認されている場合、展開コマンドが進行します。生産実行環境はIR-PMによって管理されます。
    12. 生産展開。変更はまずQAバージョンにデプロイされ、テストが行われます。QAでのテストがパスし、署名されたら、その変更を含むQAバージョンはTCMを通じて生産環境にリリースされます。新しいコードのロールバックが必要な場合は、標準的なTCMロールバックを使用して以前の動作バージョンに戻します。

9       モデル       継続的な性能モニタリング
9.1      指標と閾値
モデルの継続的な性能モニタリングの一環として、以下の指標が監視されます：
   1. 不成功な最適化回数：Opt-Varモデルが最適解を見つけることができなかった回数をカウントします。最適化が不成功だった場合、NAGアルゴリズムは失敗とマークし、それ以外は成功とします。ここでは、成功とは最大イテレーション数を超えないでNAGアルゴリズムが最適解を見つけることを意味します。この特定のモニタリングでは、毎日不成功な最適化回数を追跡し、閾値0を超えた場合に警告します。
      2. 不可能ポートフォリオの数：Autohedger内で実行されるOpt-Var提案されたヘッジ後のポートフォリオが特定の基準を満たすかどうかを確認するポートフォリオの可能性性チェックがあります。どの基準も失敗した場合、Autohedgerは「最適化者が無効な結果を生成しました」という警告メッセージをログに記録します。Opt-Varモデルでチェックされる基準は以下の通りです：
             + 最適化後のネットポートフォリオリスクがヘッジ可能なリスク限度内であるべきです。
             + 各バケットでの最適化後のリスクがバケットリスク限度内であるべきです。
            + 位置増加が許可されていない場合、どのバケットでも位置が増加しないこと。
            + Opt-Var最適化を解くために使用される補助変数は取引変数の絶対値に等しいべきです。

130115: Opt-Var                                                                                 ページ   103 of 136

                           [git] « 分岐：iropt-var@be27d1a = 発行：     (2024-10-31)
