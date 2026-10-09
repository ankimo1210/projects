# RB-F05：不連続payoffの微分教師とDML（軽い設計メモ）

- 日付：2026-09-27。更新2026-10-07。状態：v1 digitalの実装・数値/学習比較・研究3図まで完成。独立レビューImportant1修正済み（Critical/Minor0）。
- 順序：RB-F07の採否記録後。第2段階の離散バリアはM15受入後、0DTEはR4解決後。
- 置き場：`research/RB-F05/`。teacherはhullkit非公開モジュール、学習はdeep_hedge_price。公開API・依存追加は別承認。
- 問い：正しいGreek教師を作る費用を含めても、price-only学習・積分・補間よりDMLに利点があるか。

## 1. 最小実験と代案

| 案 | 利点・制約 | 判断 |
|---|---|---|
| GBM digitalから始める | 価格・deltaの解析解があり、教師biasと学習誤差を分けられる | 採用する最小版 |
| 離散監視バリアから始める | 実用的だが教師・契約・数値参照の誤差が混ざる | digitalの検査後に1商品 |
| rough/0DTEへ直行 | R1/R4、短期LRM分散、学習費用の依存が増える | 後続 |

第1段階は配当なしGBM、cash-or-nothing call、現金額1、$S,K>0,T>0,\sigma>0$。
解析価格 $e^{-rT}N(d_2)$、delta $e^{-rT}\phi(d_2)/(S\sigma\sqrt T)$ を別計算する。
pathwiseの0は負の対照。LRMは割引payoffに $Z/(S\sigma\sqrt T)$ を掛ける。
条件付き期待値による厳密な積分消去と、payoffをrampに置換する近似平滑化は分ける。
LRMの分散は短期に大きくなるため、教師のSEと計算量を価格シナリオごとに保存する。

S002 v2 の原PDFには、式(3)のGBMドリフトの1/2欠落、式(18)の密度分母の変数違いがある。
教師は上記の独立導出式を用いる（[原典確認記録](../sources/sources_S001-S031.md#s002)）。
著者の実験コードが同じ式を使ったかは未確認で、学習結果の誤りとは断定しない。

## 2. 再利用できるものと不足

| 既存資産 | 使い方・不足 |
|---|---|
| `hullkit.exotics:cash_or_nothing` | digital価格オラクル。deltaは独立な式で確認 |
| `hullkit.aad:pathwise_greeks`, `hullkit.aad:likelihood_ratio_greeks` | 欧州コール専用。digital/barrier教師の実装と見なさない |
| `hullkit.aad:bump_greeks` | 閉形式BSMのbump。MCのCRN bumpは別途必要 |
| §26.9のbarrier参照・M15成果物 | 連続/離散監視、初回・満期の監視、接触、rebateを契約fixtureで合わせる |
| vol18・deep_hedge_price | 学習・artifact契約の再利用候補。保存値依存2項目の根拠配列を同時に設計 |

## 3. 比較規約

1. 入力領域、train/validation/testのscenario ID、乱数streamを先に固定する。隣接点や同じpathの流用でtest情報をtrainへ入れない。
2. digitalで価格・deltaの式に対してLRM/CRN bump/条件付き期待値を確認し、biasとSEを分離する。
3. price-onlyとDMLは同じ教師生成を含む費用枠・同じ小型ネット・複数学習seedで比較する。損失の単位・正規化はtrainだけで決める。
4. 強い比較器として解析式、決定論的積分、価格とGreekの補間を置く。digitalでMLが速度に勝てると想定しない。
5. バリアは離散監視・無rebateの1契約に限定。連続barrier解析式を離散契約の正解にはしない。

| 保存する評価 | 単位・判定 |
|---|---|
| 価格・deltaのRMSEとtail誤差 | 通貨/現金額、通貨/spot単位。満期・strike/barrier距離別にも表示 |
| 教師のbias/SE、seed分散 | 解析解または独立参照からの差。低価格でrelative誤差だけを使わない |
| 費用 | 教師生成・学習・検証・OOD判定・fallbackの総秒数、hardware/threads |
| hard checks | digitalの価格範囲・極限。exoticに一律の非負vegaを要求しない |

許容差は固定pilotで参照誤差と教師SEを測ってから、本実験を見ずに確定する。
学習結果を良く見せるためにseedや領域を除外しない。分母が正でない費用回収式は「回収不能」と記録する。

## 4. 成果物・採否

- teacherの条件と単位、契約、全seed、誤差配列、総費用、小さなJSON+NPZ、負の結果。
- 図3本：教師bias/分散、距離×満期の誤差、総費用と誤差。
- 教材採用と標準器への昇格を分ける。教師biasが残る、独立参照に合わない、費用を回収できない場合は速度の採用理由にしない。
- 出典：[S002記録](../sources/sources_S001-S031.md#s002)。論文のdigital/barrier実験は実市場での優位を示すものではない。
- 残る設計事項：離散バリアの監視日・参照精度、学習予算、学習側担当とのartifact境界。実装着手時に確定する。

## 5. v1の実施条件（2026-10-07）

- digitalのみ。K=100、r=3%、sigma=20%、S=80–120、T=0.05–2年。train512/validation128、独立testは距離×満期の格子。split別のscenario IDと独立乱数streamを固定し、同一pathをsplit間で共有しない。
- teacher→小型CPUネット→JSON/NPZ・artifact-only notebookの順。LRM/CRN/厳密条件付き期待値/rampと解析・積分を比較。pathwise=0は負の対照。
- paired seed 11/29/47、同じ2層32幅tanhネット。price-onlyとLRM-DMLは教師生成込み各8秒の上限（最後の1 updateの超過を記録）。重み/正規化はtrainだけ、validationは診断、testを設定選択に使わない。固定pilotで6SE＋参照数値誤差の教師判定を先に固定する。
- 独立解析・積分・価格/Greek補間、OOD判定＋解析fallbackも総費用に含める。教師配列・全seedの予測/誤差・重みを小さなNPZに保存し、checkは再学習せず根拠配列から指標と推論を再計算する。速度の採用は費用回収と誤差を見て決める。
- Ruling: 最小版をdigitalに固定する — 教師biasと学習誤差を分離する既存設計に従う — バリア/0DTEの性能はこの結果から判断できず、後続実験が必要。

## 6. v1の実測（2026-10-07）

- 新規32 tests、既存aad/exotics/quote-risk/pricing-lossと両packageの索引/docstringを含む807 tests PASS。変更Python7ファイルruff/format、独立積分・MC再生成・保存重みからのNumPy推論・4種改竄検査PASS。artifact-only notebook3図をfresh実行し目視確認。
- 3seedすべてでDMLの価格/delta RMSE改善、deltaは約32–71%減。解析約0.12µs/件、ネット約1.3µs/件、補間もより高精度/高速。速度での標準採用は不採用、教師と教育比較は採用。入力・全seedの誤差/SE/重み/総費用は[研究資料](../../../research/RB-F05/README.md)に保存。
- 本編台帳/教材/既存vol18配列には変更なし。レビュー修正の検証後にv1をmainへ反映する。離散バリアの監視日/精度は次段階、0DTE/roughは後続。

## 7. 離散バリア段階の具体化（2026-10-09）

状態：2026-10-09に実装・pilot・本比較・独立最終レビューを完了。[離散バリアv1結果](../../../research/RB-F05/discrete/README.md)。元の以下の設計条件と主実験前freezeを保持し、標準高速器採用は見送る。
本人の研究ロードマップ完遂指示に従い、quote DMLの採否記録後に実施する。
目的は、経路の途中の不連続性が微分教師と学習・費用へどう影響するかを切り分けること。
digitalの結果や論文の性能倍率を、この契約の結果として使わない。

### 契約と対象

- 配当なしGBM、K=100、固定H=120、r=3%、sigma=20%、rebate=0のup-and-out call。
- 主比較は正時点m=12回の等間隔監視に時点0を加える。
  監視集合={0,T/m,2T/m,...,T}、計13時点。接触S>=HでKO。
  S=80–119、T=.25–2年を候補領域とし、pilotで参照と教師の数値成立を確認する。
- spot Deltaのみ。Sを動かしてもK/H/満期/監視回数は固定する。
  満期方向のNN導関数は契約日程の変更を含むため、Delta教師やヘッジとして評価しない。
- 監視頻度の診断ではTを固定してm=1/4/12/48を比較し、初回t1=T/mと教師SEを保存する。
  連続監視への収束を、固定m=12契約の数値参照の収束と区別する。
- S=Hでは時点0のKOによるジャンプがあり、通常のDeltaを定義しない。
  Hの下側で価格を強制的に0へ接続するNN制約を入れない。
  固定H>K・満期監視の価格範囲は0から(H-K)exp(-rT)。Deltaの非負性は要求しない。

### 独立参照と教師

1. **m=1検算。** 満期にK<ST<Hだけ支払うcallの正規CDF式、切断lognormal積分、S中央差分を照合する。
   通常callを別契約として比較する。Hのindicatorを微分しないPW期待値はPhi(d1K)-Phi(d1H)で、通常call Deltaそのものではない。
   正しいDeltaは、このPW期待値から(H-K)exp(-rT)phi(d2H)/(S*sigma*sqrt(T))を引く。
   この密度境界項を直接検算して、接触を落とした負の対照を検出する。
2. **主参照。** log-priceの正規Markov遷移を、監視時点だけkillして逐次積分する。
   価格と最初のtransition密度のS微分を別に積分する。
   積分領域・次数・strikeでの分割の収束を保存し、監視集合mは変えない。
3. **独立数値検算。** log-priceのGBM PDEを、監視日間はHの上も含む領域で解き、監視日にだけKOする。
   空間・時間格子を別に倍増し、S bumpの幅を変える。
   Hを区間内の吸収境界にしない。BGK近似と全node吸収treeは誤差比較器として扱う。
4. **教師。** raw LRM、最終増分を条件付けしたLRM、途中のindicatorを微分しないPW負対照、one-step survivalを比較する。
   LRMのscoreは初回Z1/(S*sigma*sqrt(t1))。
   conditioned LRMはm>=2で最終増分だけを消去し、初回scoreを保持する。m=1は独立解析を使う別の検算。
   one-step survivalは生存確率の重みと条件付き状態の両方を微分する。
   指示関数だけを平滑化した教師を不偏と呼ばない。
5. teacher bias、IID MC SE、CRN bumpのsamplingと幅依存、参照の積分/PDE誤差を分離する。
   rare survival、SE=0、逆正規CDFのendpoint、重みunderflowは明示的に記録する。
   pilotは独立streamで、参照次数・許容差・学習budgetを本比較前に固定する。

### 学習と成果の閉じ方

- 主比較は同じconditioned price教師を使うprice-only対conditioned-LRM DML。
  S/T入力、同じ小型CPU float64ネット、同じ初期/batch seed11/29/47、train-only正規化、共通update/時間budget。
  同一pathをsplit間で共有しない。validationは診断に使い、testで設定・seedを選ばない。
- OSSを学習へ追加する場合は、同じOSS価格教師のprice-only対照も追加し、教師平滑化と微分lossを分離する。
  原典教師の比較・検算を省略して、解析ラベルだけの学習へ置き換えない。
- 強い比較器は収束した逐次積分、価格と同じ補間器の導関数を使う補間。
  NN/補間の教師生成・学習・load・OOD判断・fallbackを含む総費用を別々に記録する。
  参照数値精度または費用回収が不足すれば、速度での採用はしない。
- 保存成果：契約/全入力/monitoring/stream、教師mean/SE、参照収束、全seed重み/予測/誤差、raw/safe/費用。
  再学習しないcheck、artifact-only3図、独立レビューと採否記録で完了を判定する。
- private金融計算はhullkit、torch学習はdeep_hedge_price、記録と教材はresearch/RB-F05/discrete/。
  公開API、依存、本編台帳、既存digital v1を変更しない。
  0DTE・rough・動的ヘッジは後続の研究として残す。

出典と確認範囲は[追加調査](RB-F05_DISCRETE_RESEARCH.md)に記録。
S002のbarrierは中間時点のみのdown-and-outであり、本設計と同じ契約の再現とは呼ばない。
