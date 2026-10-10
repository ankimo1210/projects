# M6 保存再検算の限定独立レビュー

## 判定

保存された全4クラスの資源観測・薄い検査レポートと元キャッシュの結合を限定承認します。金融精度・正式pilot/main・phase・正式予算・N65536のメモリや時間・全実験の容量予測は承認していません。

## 確認範囲

- 元N1024、節点108/156/520/1344、全2,128節点、元threshold33/65/33/65を保持。
- 全23,408件の11ラベルsample descriptor、元raw参照、physical binding、全配列のshape/dtype、原statusとNaNの扱いを確認しました。root実行のsaved SDE完了・比較flagsと6段階の完了checkpointを保存記録から認証しました。SDEを独立に再実行した判断ではありません。
- 全4クラスの元fullteacherキャッシュと保存薄レポートを許容誤差で比較しました。金融資格はunknownのままです。unknown_underresolved 47,182件はラベル数であり、節点数ではありません。
- 旧M6の独立provenance/resource判断と、原13,157ファイルのterminal manifest認証を再利用しました。今回原fullteacher容器とnative node metadataの必要範囲を再認証し、旧巨大checkerの全decodeと全入力再hashは行っていません。
- 新source81件の前後一致を確認。旧81件との差分は承認済みbounded checkerだけで、旧生成sourceや原rawの改変ではありません。
- 新規SDE・solver・RNG・teacher再生成なし。旧3件の実RSS cap、失敗・partial・unknownを保持しました。

## 保存された実測

| クラス | 節点数 | 元N | 壁時計 秒 | kernel peak RSS B | 薄レポート NPZ B |
|---|---:|---:|---:|---:|---:|
| Heston-coarse | 108 | 1024 | 31.009 | 703,631,360 | 7,715,914 |
| Heston-high | 156 | 1024 | 50.187 | 758,280,192 | 20,695,674 |
| local-coarse | 520 | 1024 | 186.486 | 829,755,392 | 37,656,494 |
| local-high | 1344 | 1024 | 506.164 | 1,490,243,584 | 181,032,462 |

全体費用は外側wall 774.091346913秒、child-tree CPU 777.573424秒。4クラス壁時計合計773.846499319秒、child CPU合計773.493985秒、観測parent CPU合計3.835055791秒です。内側・外側を加算せず、過去の生成・共有driver・失敗検査費用も再加算しません。外側の最終receipt書込み・stdout費用はunknownです。

新観測にcapはありません。最大kernel peak RSSは1,490,243,584 Bです。これは元N1024での保存再検算の実測です。N65536への外挿や旧生成込みの測定との速度比には利用しません。

薄レポート4件合計はNPZ 247,100,544 B、展開NPY 242,001,224 B、metadata/receipt 27,127,740 Bです。原native教師やfullteacher容器は残っており、この差分を全実験の総保存容量と読み替えません。

## 証跡と費用

- 詳細: task-5-M6-saved-recheck-independent-v1-results.json
- 原probeと出力: 同-prefixのprobe.py / probe.log
- 判定: 同-prefixのdecision.json
- 証跡SHA: 同-prefixのmanifest.json
- 独立レビュー外側wall 9.811074431秒、CPU 9.770509秒、peak RSS 1,267,691,520 B。probe内部wall 7.617131396秒・CPU 7.588197205秒は内数です。レビュー外側receiptの最終保存費用はunknownです。

source canonical identityはrun_pilot.runner._digest方式の408f2bc271a3379fb5aa8a1c96be0839f090cd3b2452bcd8b8a94c4af7bb7652、原生成は4e8f8b7bad48b9f6bf89b655cd115de835a9a486d89dd6d9ffafcad2b3cb64b0です。事前行政budget SHAは6e85a12b6ea26c966e390596e797e9a5920a89b993a639a8b7591b8fd92a437b。事前行政budgetの認証を正式金融budget承認へ広げません。
