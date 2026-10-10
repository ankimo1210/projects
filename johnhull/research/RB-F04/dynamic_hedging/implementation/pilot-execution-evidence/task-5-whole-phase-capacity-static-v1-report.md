# 全phase保存容量の静的整理（2026-10-10）

## 結論

**全20teacher候補を完了して元項目を保持する場合の論理配列の部分下限は 353,606,441,728 B（329.32 GiB）で再現できた。これは圧縮後のCAS容量の下限ではない。** 元3138 jobs、N=1024/4096/16384/65536、独立reserved N65536、原seed/CRN/全ノード/失敗・capの義務は変更していない。progressive選択で未実行になる実証がない候補は、この事前整理から削っていない。

genuine N1024の全2128node metadataを、既存terminal input manifestのbyte SHAへ照合した。既存独立M6 v2の全NPY header/inventoryを再利用し、新NPZ member・金融配列は展開していない。原M6saved-only実測のsource/rawは無変更。

現在のnative codecのnode物理項目を配列の型・shapeで積算すると、20候補のnode配列名目量は **355,868,451,168 B**。共用driver、raw/domain grid、bounded2reportを数えた限定配列小計は **364,185,768,816 B**。metadata/headers、初期義務、他3088jobs、診断full reports、複写、旧失敗履歴、stagingは別なので、これも全phase物理上界・下界ではない。

## 353.606 GBの由来

4 gridのnode数は Hcoarse108/Hhigh156/Lcoarse520/Lhigh1344。各gridのN合計は 1024+4096+16384+65536+reserved65536=152576。全path×nodeは324681728件。date jの残存stepは768−64jで、全step状態は129482096640件。

| 保存する項目 | byte | 依存 |
|---|---:|---|
| 9本のfloat64 primitive vectors | 23,377,084,416 | N×node |
| primitive_status Unicode7 | 9,091,088,384 | N×node |
| failure_reasons Unicode128 | 166,237,044,736 | N×node、空理由も全行 |
| primitive path_mask bool | 324,681,728 | N×node |
| full local_step_status uint8 | 129,482,096,640 | N×node×残存step |
| 元path/cluster IDs int64 | 5,194,907,648 | N×node |
| 3 covariance行列 | 15,166,206,720 | node×K²、Nに依存しないshape |
| price/derivative/joint/f_xの全16block | 983,623,680 | node×16×K |
| 10 shared-driverの2factor normals | 3,749,707,776 | driverごと一回、N×768×2 |
| **部分下限** | **353,606,441,728** | calendar・小配列・重複等を除く |

Covarianceは 8×[2(3K)²+(6K)²]=432K² B/node、全16blockは8×16×(3K+3K+6K+K)=1664K B/node。Kはcoarse33/high65。共有driverはcoarse/highで共用し、nodeごとにはnormalを保存しない。

## codec・cache・checker・metadataの分離

- **N依存**：9 vectors・全status/理由/mask・full step状態・ID。N1024の実全metadataから、各gridのこれらを149倍（全5Nの合計倍率）して計上した。rawのembedded driver IDsとlabel maskは原下限に無い重複として残り、約5.520 GBを追加する。
- **grid固定**：元3covariance、全16blocks、threshold/mean/SE/status、calendar/fixings。各gridは5候補なので5倍。現native node総量355.868 GBのうち、この固定成分をN比例にしていない。
- **step dictionary**：元sourceはUnicode64の辞書と全uint8本体を保持する。今回実辞書形を使ったnode名目量が355.868 GB。sourceの長さ1〜256の条件付きshape範囲では node配列量355,864,412,768〜356,558,991,968 B。これは完成native schemaの論理配列範囲だけで、例外raw・metadata・圧縮容量の保証ではない。
- **shared driver**：normal3.750 GBに、bank自身のtop/chunk IDsとcalendarを含めると3,759,534,160 B。10producerを一回だけ数える。原generation/failed checkの費用を再加算しない。
- **grid/cache**：20rawと20domain-selectionが各1配列payloadを保存する構造シナリオは2,189,570,288 B。元cacheのmean/Greeks/16blocks/statusを保持する。selected inputsやmain wrapperが追加複写する分は別。
- **bounded report**：元全NのSDE/全11sample/全cov/blocks/cache比較は続け、reportには原node/physical bindingと全shape/dtype/検算済descriptorを保存する。raw_checksにN×K sample/cov値を再保存しない。raw_status/SEは168K B/node、cacheは元grid固定shape。20raw+20domainの40reportの配列payload名目量は2,368,213,200 B。
- **旧full reportとの差**：20grid reportを各1回として、11sample1,587,356,762,112 B＋cov15,166,206,720 B＋16blocks983,623,680 B＝**1,603,506,592,512 B**の再保存を避ける。元raw側のprimitive/summary/cov/blocksは残る。teacher_diagnosticのstandalone full reportは別経路であり、勝手に同じ削減を適用しない。
- **metadata/headers/費用/failure**：NPY/ZIP headers、root/pack receipts、全chunk mapping（N/256）、source/driver/case、旧費用とactual cap、未知性を保持する。JSONの実数文字長・例外/ログ・full literal fallbackと追加複写のwhole量は未確定。一般encoderやdtype、原Nを変更して容量を作っていない。

completed Hcoarse/Hhigh/Lcoarseの新bounded report metadataを静的に観測した。物理file総量は9,057,520 / 22,704,743 / 44,108,269 B、raw_checksには全N sample/cov配列無し。cache＋status/SEの配列shapeが上記算術と一致する。これはmetadata/既存file-size観測で、新NPZ物理認証・数値検査の独立承認ではない。Lhigh稼働中のrawには触れず、容量予測に部分完了を代入していない。

## genuine N1024の実量と保証の限界

元nodeのみのpayload / compressed NPZ byte：
Hcoarse 178,031,088 / 32,862,385、
Hhigh 479,200,176 / 137,347,851、
Lcoarse 849,936,752 / 154,528,323、
Lhigh 4,097,911,504 / 1,192,068,216。
全metadata/receipt byteは別。旧巨大checkerも原履歴として残す。

これらはN1024・現field/状態/数値の実物だけである。Unicode空理由・statusは圧縮しやすいが、全N/全model/state/失敗文字列/高N統計への同一圧縮率は保証しない。synthetic N65536/status I/Oの圧縮率もgenuine最大Nの代用にしない。

**確定**：指定shape/dtypeの論理部分下限、既存genuineの物理量、全元metadata由来、完成native schemaの限定論理範囲。
**未確定**：全3138jobsのcompressed物理総量T、全phaseの物理上界、追加copies/old history、staging/restoreピーク、genuine最大NのRSS/速度/圧縮率。元graphのexpanded_bytes=Noneを数値0や都合のよい圧縮比で埋めていない。

## C/F各保管庫の独立した必要空き

純read-onlyの現在観測：**C 314,778,112,000 B、F 185,710,804,992 B、WSL 595,309,969,408 B**。Cは旧記録から25,788,346,368 B減っている。これは観測値であり、実行直前の予算固定には再確認が必要。

CとFにはそれぞれ同じ完全corpus Tを一コピー保持する。各volumeの必要空きはそれぞれ

F_required,C = T + staging_C + retained_old_history_C + reserve_C
F_required,F = T + staging_F + retained_old_history_F + reserve_F

で、CとFの空きを足して一方の不足を補えない。全Tが未確定なので、現容量で両vaultが足りる保証はまだ無い。

| 単独volume | 現在空きB | 353.606 GB論理部分との不足B（無圧縮比較のみ） |
|---|---:|---:|
| C | 314,778,112,000 | 38,828,329,728 |
| F | 185,710,804,992 | 167,895,636,736 |
| WSL | 595,309,969,408 | 単一部分下限は収まるがwholeは未確定 |

364.186 GBの限定配列小計との無圧縮不足はC49,407,656,816 B/F178,474,963,824 Bで、他job/headers/stagingは別。物理圧縮corpusへの必要増設量としては使わない。

WSLは原本T＋逐次一復元Tなら2T、二つ同時復元なら3T＋各work/staging/history。単に論理部分を2コピーするだけでも707,212,883,456 Bで現在WSL空きを超えるが、実compressed Tによる成立条件は別。復元RAMの展開配列とディスク保持量を混同しない。

## 次に必要な限定実測候補（未承認）

元 teacher:local:N65536:high:raw の date0/node17（spot100、state1）、N65536/K65、seed1345225788、769点calendar=arange(769)/768、chunk256、16blocks、元field257×321を候補として特定した。entrypointは既存run_teacher_job。原driver teacher-driver:local:N65536（normal payload805,306,368 B）を共用し、無い場合は原全driverの費用・保存も含める。

candidateはroot_preapproved=false、wall/RSS/source-approval予算null。まだ生成/RNG/solver/SDE/金融decodeは実行しない。原全status/失敗/cap/expenseを保持し、一節点の成立を全20候補の圧縮保証・whole金融資格へ広げない。最大shapeのI/O/RSSを確認してから他job/staging/両vault予算を合計する判断材料になる。

## 検証・費用・範囲

全2128 metadata SHA、旧genuine payload/header集計、元20/10/3138 roster、別式でpath/step総数、353606441728の整数合計を確認。Ruff/format PASS。主計算・save/logを含む親込みwall1.172152秒、childCPU1.175198秒、RSS226856960 B。読取準備・report・最終receiptの未測定tailはunknown。金融実測の時間には換算しない。

D内の計算結果・候補・reportだけを追加した。production source/docs/tests/Git/CAS、稼働中M6raw/source、原N/全case/費用/資格を変更していない。
