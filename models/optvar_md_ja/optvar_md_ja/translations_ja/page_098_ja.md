morgan stanley                                                                                      機密


            共分散行列がチェックを通過しない場合。
            http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
            mmj/src/main/java/mfire/utils/MathUtils.java#82)
       (i) Opt-Varモデルの入力ネットポートフォリオリスク（PVO1）とパラメータヘッジ可能リスク制限がチェックを通過しない場合、これらの値がnull、NaN、無限大であるか、またはヘッジ可能リスク制限が負の場合は、警告が記録され、ヘッジ取引は返されず実行されません。
            (http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
            mmj/src/main/java/erates/hedging/OptimalHedgeVarCostCalculator.java#1004, 1206,
            下記の入力とパラメータに対するチェックと制御。これらの状況が発生し、値が有効でない場合、警告が記録され、デフォルト値が使用されます。
               + アルファ：指定されていない、null、負の場合、デフォルト値0を使用します。
               + コスト：実行コストの線形部分が指定されていない、null、NaN、無限大の場合、デフォルト値0.05を使用します。
               + 二次コスト：実行コストの二次部分が指定されていない、null、NaN、負の場合、デフォルト値0を使用します。
               + バケットリスク制限：null、NaN、無限大、負の場合、デフォルト値0を使用します。
               + 取引サイズ制限：null、NaN、負の場合、デフォルト値0を使用します。
               + 位置増加を許可するか：nullまたは負の場合、デフォルト値falseを使用します。
               + リスク回避因子：null、NaN、無限大、負の場合、デフォルト値4e-6を使用します。
           (http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
           mmj/src/main/java/erates/hedging/HedgeCalculatorAssistant.java)
       (iv) ヘッジ可能リスク制限と取引サイズ制限の制約が矛盾しないことを確認します。それ以外の場合、Opt-Var最適化オプティマイザを呼び出さず、ヘッジ決定は第     节で説明されたルールに基づいて行われます。この場合、メールアラートも警告として送信されます。
           {http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
           mmj/src/main/java/erates/hedging/OptimalHedgeVarCostCalculator.java#396|
       (v) アルファのチェック。コードはアラファの値を関連する商品のコストの90%に制限します。つまり、製品é € [d]の場合、@はmax(—0.9 x C,, min(a,,0.9 x C,))で置き換えられます。
            (http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
            mmj/src/main/java/erates/hedging/HedgeCalculatorAssistant.java)
       (vi) CRB最適化入力のチェックを以前に行います。つまり、共分散行列、ポートフォリオリスク、ヘッジ可能リスク制限、バケットリスク制限、コスト、アルファとリスク回避因子。
            http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
            mmj/src/main/java/erates/corvo/OptimizerInputService.java|
 モデル出力制御
        (i) Opt-Varモデルの出力に対するチェック。コードはOpt-Varモデルの出力が指定された限界内であることを確認します。これらのチェックが通過しない場合、AutohedgerはOpt-Var提案取引を取引しません。
              + 提案取引がNaNまたは無限大でない。
              + オプティマイゼーション後のネットポートフォリオリスクはヘッジ可能リスク制限内にあります。
              + オプティマイゼーション後の各バケットのリスクはバケットリスク制限内です。
              + 位置増加が許可されていない場合、オプティマイゼーション後どのバケットでも位置が増加しない。
              + 解決Opt-Var最適化に使用された補助変数は取引変数の絶対値と等しいべきです。
            http://stashblue.ms.com:11990/atlassian-stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
            mmj/src/main/java/erates/hedging/OptimalHedgeVarCostCalculator.java#619)


2024年10月31日：Opt-Var                                                                                   第98ページ目／136ページ

                        [git] * 分岐: r.opt-var@bc27d1a = 発行: (2024-10-31)
