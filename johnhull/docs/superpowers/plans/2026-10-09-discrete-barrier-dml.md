# RB-F05 離散バリアDML — 実施計画

更新2026-10-09。研究ロードマップ完遂指示に基づく実施計画。
既存[設計§7](../../prep/design/RB-F05_DESIGN.md)と[追加調査](../../prep/design/RB-F05_DISCRETE_RESEARCH.md)の契約を実装する。
金融教師はtorch-free hullkit、学習はdeep_hedge_price、成果はresearch/RB-F05/discrete/。
既存digital v1・本編台帳・公開API・依存は変更しない。

## 完了条件

1. `{0,T/m,...,T}`、m=12、接触KO、固定K/HのDelta、S=Hの未定義をコードと独立参照で確認。
2. m=1解析/密度、m=12 Markov積分/PDE、LRM/conditioned LRM/OSSの価格・Deltaを照合。PWは負対照。
3. pilotで積分・PDE・MC・bump誤差を分離し、主実験前にprotocol/許容差/予算を固定。
4. noisy MC教師によるprice-only/DMLを全3seed・同初期/batch・同update/時間上限で比較。解析ラベルだけへ置換しない。
5. 同じ価格補間のDelta、逐次積分を強い対照にし、raw/safe/境界/総費用を保存。
6. 学習を起動しない成果再検査、artifact-only3図、独立レビュー、採否記録、main統合/push。

## 工程

| 工程 | 実装・検証 | 状態 |
|---|---|---|
| 1 | private教師・m1・独立PDE、scoped TDD | 完了・独立レビュー済み |
| 2 | OSSの状態と重みの微分、CRN・oracle対照 | 完了・batch共有を含む44 tests PASS |
| 3 | 数値pilot、主条件freeze | 完了・独立再検査後freeze |
| 4 | 6fits、強い補間対照、保存重みreplay、改変検査 | 完了・6fits/fresh保存replayと独立200点PDE PASS |
| 5 | price+Deltaの20反復、offline/load・safe費用、3図 | 完了・32測定/100load/3図実行・目視 |
| 6 | 対象/全関連suite、独立レビュー、採否・main反映 | 独立最終レビュー・関連3suite7104 PASS/6 skip。main統合済み |

## 候補protocolとfreeze

[protocol.json](../../../research/RB-F05/discrete/protocol.json)が設定の正本。
候補: S80–119、T.25–2、K100/H120/r.03/sigma.2、m12（時点0を含む13時点）。
主学習はtrain512/validation128、1入力4096 IID paths、test25 spot×8 maturity。
train/validation/pilot/diagnosticでscenario/path streamを分離。testでは学習条件を選ばない。
conditioned payoffと初回scoreのDelta教師を同じtrain配列から使用する。
OSSは教師・分散比較で検証する。OSS学習は今回の主比較に加えず、加えるならprice-only対照を必要とする。

NNは物理S/T入力、内部S/logT、2→32→32→1 tanh、CPU float64、train-only尺度、unbounded価格出力。
価格をHの左でゼロへ接続せず、Delta非負制約を入れない。3 seeds11/29/47、512 updates、batch128、Adam lr.003、fit cap120秒。
capはsetup/fitを対象とし、教師・export・load・検証・ベンチマークは別の実測費用へ保存。
途中失敗は部分成果と理由を残す。勝利を研究完了条件にしない。

pilot固定入力はS80/100/115/119×T.25/1/2。
GLの次数32/64/128/256、tail10/12、PDEのspace/time/domain/phase、Delta bumpを別に診断。
候補許容差はGL price1e-7/Delta1e-8、独立PDE price5e-4/Delta2e-4。
pilot後に達成を確認し、条件変更があれば理由をここへ記載して主学習前にfreezeする。
MCは6SE＋積分誤差で判定。SE=0、positive payoff数、生存数、OSS underflow/未支持を別に保存。
監視頻度m1/4/12/48の比較は固定m12の数値収束とは別に扱う。

## 成果・検査・採否

JSONにはprotocol/環境/ソース由来/全fit状態/費用/採否、NPZには入力・stream・teacher mean/SE・参照/収束・重み・予測・raw計時を保存。
20MB超なら既存両保管庫とsmall manifestを使用。必要な再計算では保存重みを読み、再学習しない。
補間はspot65×logT33のCubicHermite/線形blend、Deltaは同じ価格曲面の導関数。
OODは数値成立したMarkov積分へfallback、変更契約はunsupported、Hの通常Deltaはundefinedとする。
全比較器のprice+Deltaをbatch1/32、warmup3後20反復、median/p95・raw/safe別で測る。
総費用は教師/共通初期化/fit elapsed/export/loadとfull batch呼出回数を分離し、setup/trainingをelapsedへ二重加算しない。loadは計時配列追加前の主fit bundleのwarm decodeで、最終archiveの計測ではない。未測定範囲は0に置かず、p95の和を総費用のp95と呼ばない。H接触の未定義Deltaを含むsafe32はlatencyだけを保持し費用回収をunsupportedにする。
3図: 教師bias/SEと収束、全seedの価格/Delta精度、raw/safe/総費用と境界。

対象pytestとruff/formatを先に実行。索引guardはmodule登録と同時に通す。
章教材・台帳・共有実装を変更しない研究なのでD1全復元や全306節再受入をこの研究のgateへ追加しない。
最終関連3suite/releaseをmain統合前後の必要な時点で確認し、独立レビューの指摘を解消して採否を記録する。

## Freezeの実測根拠

2026-10-09、full pilotを実行し通常checkerで再計算。独立reviewerも保存draw/summaryを再検査。
PDE最大差price1.55596e-4／Delta3.11899e-5、MC72＋頻度44比較を6SE＋積分誤差で確認。
m1解析定数をMCから分離し、通常checkerでも4streamのdrawを再生成する指摘をRED→GREENで是正。
phase0は価格最大0.0258／Delta0.00249のaliasingを示すため、midpoint phase=.5だけをoracle候補にする。
候補許容差・学習budgetは変更せずprotocolをfreeze。全test領域の独立確認は主成果fresh gateに残す。
158,401,006 bytesのpilot NPZはC/F別physical diskの保管庫へ置き、各コピーから復元PASS。

## 統合の確認

2026-10-09、関連3suite7104 PASS/6 skip（366.24秒）、fresh MC/PDE200点と32計時/会計check、3図実行/目視、独立最終レビューを完了。09b8c1afをmainへfast-forward統合し、mainでrelease --require-tracked、pilotのprimary復元、保存成果/計時checkを確認した。公開API・依存・本編台帳は不変。研究教材を保持し標準高速器採用を見送る。次はRB-F04。
