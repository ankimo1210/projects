# RB-F06 独立 pilot レビュー

**結論：approved=true。現在の candidate/source と最大4830 solver calls・max_nfev 400/250 を固定して main を実行可能。残 Critical / Important は0。** これは Hagan近似写像の逆問題を調べる実験条件の承認であり、main結果・exact SABR pricing・識別性・95%被覆の受入ではない。

- 時点：2026-10-09T06:55:11.974661+00:00。研究source/Git/元成果は変更していない。
- 対象：最新 `research/RB-F06/pilot/reference.json/.npz`、別保存serialization receipt、確定した runner/protocol/analytics と基礎金融source。旧pilotをpoolしていない。
- 独立 saved checker PASS。独立 fresh は指定10 fits・8 reserved pilot noise vectors PASS。RNG/optimizer禁止hook付き saved audit、in-memory freeze、実saved pilot再確認、main入口pre-draw gateもPASS。実freeze保存/main生成はrootの次工程。
- 原著の近似式を検査する：[Hagan et al. (2002), (2.15)/(2.17)/(2.18)](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf)。main noise・holdoutは生成・閲覧していない。

## 原slot・配列・金融数値

| 検査 | 結果 |
|---|---|
| pilot roster | 30 datasets、270 unrestricted＋116 profile＝386 calls |
| 全attemptとprofile点 | 一意ID、全9 starts、各point4 nuisance starts、割当union一致、余剰attemptなし |
| native arrays | 5870 non-object、NPZ 1,653,381 bytes |
| 独立 Hagan 再評価 | 全386 fits、max IV/residual差1.83e−12、max Q差8.02e−9 |
| 独立 SLSQP | 10件すべて収束、保存最小Qとの差最大2.04e−11 |
| 実3-step J | unrestricted全270：258 stable / 12 numerical_unresolved |
| 元noise/seed | 全40 physical seed一意・SeedSequence一致。8 pilot master noise一致、3群共通、56 scalar draws |
| 停止予算 | noiseless weak/ATMの5 startsがstatus0/nfev400。有限失敗成果を保持 |

SLSQPは ordinary/full、weak/ATM、ordinary/sparse の unrestricted 4件と、ordinary/full の ν=0/.4/閾値近傍 .3703125 の固定ν3点×2starts。profile≤対応feasible sliceを確認した。ν0でρが価格写像から消え、固定ν0の異なるρ startが同じQへ収束する。全大域最適性の証明ではない。

12 unresolvedはすべてweak/ATM。bestでもrep1（ν=.0247672、条件数7.78e6）とrep2（ν=.00675564、条件数9.58e7）が未解決。前者は小singular/推定誤差≈8.59、後者はstep間rank=(2,3,3)。有限condition値を識別成立と解釈しない。予算到達や未解決を保持する設計なので、pilotを理由にbounds/grid/停止予算を拡大する必要は確認されなかった。

## profile・支持の検査

代表は事前指定 ordinary/full/rep0 のν curveのみ。17 initial＋12 refinement＝29点、全116 nuisance fits。両initial crossingを保持し各6点細分化、final bracketは [.36875,.3703125] と [.43551046,.43855657]。unresolved interiorを明示し、連続支持域の全成分・精度確定とはしない。

全失敗有限profile attemptとtruth/slice witnessはdataset baseline監査に含まれる。mainは基準より良い候補やprofile不足を全parameter unknownへ伝播する。元16分母を保持し、known-only Wilsonを元分母の95%被覆と読み替えない。[Raue et al. 原著](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)、[Self & Liang 原著](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf) に照らして、χ²線はpointwise記述的参考値とする。

## 修正済み Important

1. **承認が別条件をfreezeできた**：typed explicitly true approval、candidate/record/typed arrays/sourceの一致、全非fixture pilotの数値checker、review digest、load/main入口の実pilot再確認へ修正。approved=False・旧record digest・条件差替え・未添付・fixture・自己整合digest付きIV改変を独立に全拒否。
2. **nonfinite元slotを検証できず、valid slotをinvalidとして隠せた**：invalid時のみNaN/+Inf/−Inf maskと有限部分の一致を確認し、invalid flagを実master quoteの非finite/非正判定と照合。NaN/±Inf/有限負の正当なslot保持はPASS、有限正のinvalid隠蔽は拒否。
3. **JSON保存後のgroup順序で初回pilotが落ちた**：生成/読込とも決定的sorted group rosterに修正。最新30 datasets/386 attemptsで独立saved/fresh PASS。

## main予算と実費用

最大calls＝918 main＋1200 representative noisy grid＋408 noiselessν grid＋1152 truth-fixed＋864 noisy refinement＋288 noiseless refinement＝**4830**。各curve全12点/各bracket6点、重複点再利用。主max_nfev400／nuisance250でnfev予算総和1,345,200。ただしSciPyのnfevは数値Jacobian用residual呼出を含まないため、実費用として使わない。

| 最新pilot原価 | 実測 |
|---|---:|
| residual calls | 78,776 |
| diagnostic calls | 2,795 |
| scalar IV evaluations（fit） | 288,387 |
| master / slice IV evaluations | 70 / 203 |
| solver / diagnostic seconds | 3.107 / .0543 |
| checkpoint / completed final serialization seconds | 4.263 / .337 |
| invocation wall / CPU seconds | 7.491 / 7.466 |
| 外部process wall / user / sys seconds | 8.29 / 7.92 / .33 |

不明evaluation数と例外は0。pilotはholdout/multi-stepを実験側で計算せず、レビューの270 multi-stepと10 SLSQPは別作業で原推定・原価にpoolしない。mainでは追加の差分・slice・holdout・checkpoint/serialization・外部wall/CPUを保存する。pilotの1曲線から弱ATM profileや非線形圧縮費用のwall上限を推定しない。予算承認は固定call/停止上限と全失敗保持に基づく。

元runtimeのserialization_pendingはsave前の値で、completed receiptがrecord/protocol digestと実final保存時間を別途bindする。レビュー時は同じPython3.12.3/NumPy2.4.6/SciPy1.17.1、NumPy OpenBLAS0.3.31.188.0・SciPy OpenBLAS0.3.30の両実num_threads=1を捕捉。pilot時の直接threadpool記録はなく、環境変数/version記録との補足比較である。

## 承認binding

| 内容 | digest |
|---|---|
| candidate protocol | ef74f705deee2b8bc47dd7344dc20cb560bd0e890bd81ce2c7479cb655383b9b |
| pilot record（canonical） | 675928f59d696667d7bc3e26fc13faa4ff077a4977907dbcda53c2c519bfac8a |
| typed pilot arrays | 594e54bfc735b8c0096033558190b0c3ffe86e1dcc7426f2a2dccab2e4360403 |
| JSON file / NPZ file | 91f9e80934d772ed91051edc66ee099be70078707fa16efe4ed523f44906f910 / 6a8b3fad22b770e00da8acb68b47b3f396770288ef723b0556102341afa7f239 |
| full financial source registry | 028eb8496f68df3b83ba3d33b3bc2cce7f456099e2ebbb20873582dcc1291845 |

typed承認、全source6件のSHA、全検算・ガード・制限は [typed pilot review](pilot_review.json)。freeze後のsource/条件変更はこの承認の範囲外。main結果・有限訪問holdout価格幅・χ²支持は後続レビューで評価する。
