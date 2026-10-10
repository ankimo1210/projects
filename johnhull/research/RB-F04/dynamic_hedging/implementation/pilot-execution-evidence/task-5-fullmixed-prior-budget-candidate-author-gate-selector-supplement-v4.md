# Gate・selector再検算予算補足 v4（未承認）

元16gate・2selectorを保持。各gateの213 evidenceには raw教師4件とdomain-selected教師4件があり、両方のsource branchが全saved SDEを別々に再検算する。全8件の既知component推計を足して3倍し、300秒単位へ切上げる。他213rows kernel/I/OはNone。selectorは各modelの原8 executed stageを再検算する実重複として別加算する。

activationはlifecycle計時開始後、実cachekey=(gateID, rawSHA, argumentsSHA)の初回にgateを再検算する。原参照を持つ全potential first jobへ保守予算候補を割り当てたが、初期phaseで不変の同一keyに対するruntime外挿はcache unitごと最大1回。再開/変更された実keyの追加費用はunknown。

known partial prediction=2184772.200348秒（606.881時間）。これは全stage実行を仮定した既知成分の外挿和で、完了時間予測ではない。行政capのsum、potential first job全件への予算割当sumと混同しない。他kernel・保存I/O・最終saved_check・external10/CAS・resumeはunknown。元3138/121/51/20/10、N/軸/閾値/親順を保持。追加finance/RNG/SDE/solver、production/source/docs/Git/CAS操作なし。

rootが実独立審査の後に最終全3138予算を記入する。pending/nullをapprovedへ変換していない。金融精度・正式予算/phase/mainは未承認。
