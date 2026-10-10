# M4/M5 独立参照表：実測準備

- 準備完了。金融 solver / RNG / 正式 pilot / main は今回実行していない。金融資格は unknown。
- 採用スクリプト: task-5-current-independent-call-table-measurement-v3.py
- 事前上限候補: task-5-current-independent-call-table-budget-candidate-v2.json（root_preapproved: false）
- 初期記録: task-5-current-independent-call-table-initial-description-v1.json
- production source / tests / docs / Git は変更していない。本成果物は D 内のみ。

## 元 job と実 API

| クラス | 元 full graph job | 元幾何・全枠 | 行政上限 |
|---|---|---|---|
| M4 | independent-table:state00:Heston | 3 levels × 1 date × 7 spots × 33 states = 693 | 120 s / 4 GiB RSS |
| M5 | independent-table:state00:local | 4 levels × 1 date × 7 spots × 7 states = 196 | 300 s / 4 GiB RSS |

元 full graph は 3138 jobs / 121 cases / 51 attempts。currentfield は保存済み 257 × 321、order=1024 / frequency_scale=512 / density_floor=1e-10 をそのまま使用する。

call_table の実 dispatch は run_pilot._dispatch → reference_methods.independent_call_table。_saved_operation は経由しない。返り値の native schema は rb-f04-independent-call-table-v1、保存再検査は check_pilot.check_call_table。存在しないラッパー API は要求しない。

元 graph の両 job は controls={}。元 job arguments の SHA を保持したまま、実測対象のコピーだけに、別途保存済み candidate-v2 の controls を事前指定する。幾何・field・元 jobs・level 数は変えない。元 arguments / 計画 arguments / 解決後 arguments の SHA を別々に保存する。

## 事前 controls

CF は次の 3 段階を固定する。flat quadrature_limit / epsabs / epsrel を渡すことは禁止し、第 3 段階の厳しい許容差を保つ。

| 段階 | upper | quadrature_limit | epsabs | epsrel |
|---|---:|---:|---:|---:|
| base | 250 | 800 | 1e-12 | 1e-11 |
| cutoff | 500 | 800 | 1e-12 | 1e-11 |
| quadrature | 500 | 1600 | 1e-13 | 1e-12 |

PDE の 4 段階は base(2401,1920,1.8)、space(4801,1920,1.8)、time(2401,3840,1.8)、domain(2401,1920,2.25)。括弧は space_nodes / time_steps / log_half_width。

## 保存・停止契約

1. root は false の候補を保ち、別名の固定事前 budget に承認・根拠を書いてから実行する。候補のままでは financial dispatch を拒否する。
2. 全 slots は NaN / unprocessed / processed=0 として初期記録し、worker 前に native 保存する。親の事前 description も import 前から保存する。
3. 実 dispatch の returned raw は、入力や checker の検査前に immutable 保存する。元 NaN・CF/PDE receipts・failure を残し、保存再読込と node checker を実行する。
4. wall / RSS の実停止と source / solver 例外を分ける。例外は cap に転換しない。hard stop 中の未処理枠は初期全枠として保ち、戻っていない数値を生成しない。
5. 親 clock は prior 検査、子 import、solver、保存・再読込・node checker、source/input 検査を含む。親＋子 CPU と個別 peak RSS を保存する。最終親 receipt/stdout の tail は root の外側 receipt で包含する。
6. source 80 files / dynamic imports 0 の入力出所を封鎖し、script / original inputs / currentfield / planned controls の SHA を照合する。金融数値比較は既存 saved checker の許容誤差を用いる。source/input SHA は出所認証にだけ使う。
7. native financial_qualification=unchecked を保持し、計測全体は unknown。正式 pilot・精度・121/51 の金融資格を付けない。

## 保存入力だけの検査

- preparation v2: PASS、solver/RNG guard 呼び出し 0、source 80 files / dynamic imports 0。
- M4/M5 --verify-preparation-only: 両方 PASS、金融 module を import せず source/input/budget を検査。
- root_preapproved=false を通常 validation が拒否することを確認。
- strict 第 3 CF level / 全 slots / 元 currentfield / 全 producer input SHA は保持。
- 最初の準備 v1 は dates が list だったため .tolist が失敗。金融前の失敗ログ・実費を保存し、準備 adapter を np.asarray に直した v2 で PASS。元 artifacts は上書きしていない。
- 準備検査の実費: 失敗 v1 outer wall 4.166620s、成功 v2 outer wall 3.702421s、静的検査 wall 0.287176s。これは記録された準備 command の費用のみ。編集・全履歴費用・金融 runtime の推計ではない。

## 固定値

- measurement script SHA256: b314b5a97a826d9d952e690332ca55acf1f0d9d372e088b4bc4293404c9440c6
- candidate SHA256: decb97179fcafceaade69c6da5910ee0cbbf0429e3678dcfed5d23f2852e725c
- initial description SHA256: 89356240df21d6a74b3393eea2429366f32941e534e8e717b1b20c1ca90a8135
- execution source identity SHA256: b04ce2e63dce80eb17e5dae917369e04d661c6dba0d3dc6a08e7178da2610688
- M4 resolved arguments SHA256: 7b8110554bdc6cc6392c25baee7e9ad65a2488e7a0bff4347488a198522352b6
- M5 resolved arguments SHA256: b1ecda75d026de90a1fd8042fc0d58f033742ea9ff71964110bbd2de58d93d73

## root 実行例

承認後、/home/kazumasa/projects/.venv/bin/python を使用し、外側親込み receipt で包含する。

python D/task-5-current-independent-call-table-measurement-v3.py --budget-file D/ROOT_FIXED_BUDGET.json --class-id M4 --output D/task-5-current-independent-call-table-observation-M4-ROOT_NEW_NAME

M5 は class-id / output のみ対応する名称に変える。実測所要時間はまだ不明。M2/M3 や一部 quotes の実測から全 independent table の時間へ換算していない。
