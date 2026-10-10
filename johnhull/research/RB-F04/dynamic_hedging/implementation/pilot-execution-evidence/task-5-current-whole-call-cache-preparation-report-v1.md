# M2/M3 whole call-cache 実測の準備

2026-10-10。**準備のみ完了。金融・RNG・CF/PDE の新規実行は行っていません。** 元の source/tests/docs/Git は編集していません。

## 固定する対象

| Class | 元の実 job | 元全格子 | 原スロット |
|---|---|---|---:|
| M2 | call-current:Heston | 49 dates × 65 spots × 33 Heston states | 105,105 |
| M3 | call-current:local | 49 dates × 65 spots × 7 local states | 22,295 |

元 mixed DAG は 3,138 jobs / 121 cases / 51 attempts。current field は saved v4 の 257×321、producer controls は order1024・frequency_scale512・density_floor1e-10 のままです。全 axes・parameters・planned/resolved arguments の入力 SHA、元 graph/field の全 artifact file SHA、現80ソースを prior に結合しています。保存 field は再計算・補修していません。

Heston cache は現 private default CF1024 と cutoff512/sqrt(1.25-date)、local cache は現 PDE1201/960/width1.8 と全49日付を含む calendar timeline をそのまま消費します。build_call_cache は controls を外から追加する API ではないため、元 job arguments を変更していません。

## 実測 script と行政予算案

最終 script: task-5-current-whole-call-cache-measurement-v3.py  
SHA: 2ca6c134e2cacf0ca76da8bd0142f960f9cf8831c4b0fe6d3813319dbe90aa1b

最終 candidate: task-5-current-whole-call-cache-budget-candidate-v2.json  
SHA: 91d12c89cdfee655d5225a0f1edf224c8bba8b8e9b685f741eb3ce701b82508f

prior 初期記述: task-5-current-whole-call-cache-initial-description-v1.json

**各 class 個別に300秒・4 GiB RSS**。2 classes 合計300秒という意味ではありません。RSS は親/子の個別 process RSS の最大で判定し、virtual memory / RLIMIT_AS を使いません。親子 RSS 合計も観測値として別に保存します。candidate は root_preapproved:false、formal_finance_approved:false、予測実行時間は null です。14 quotes・2 dates の旧速度を全49日付へ読み替えていません。

現 source には run_call_cache_job という関数はありません。script は元の実 typed 経路 run_pilot._dispatch("call_cache", arguments) → _saved_operation → build_call_cache を使います。その後に immutable write/read と check_wrapped_operation の saved call-node 数値検査を行います。

## 原数・失敗・実費

- solver 前に全格子の NaN/unprocessed を immutable artifact として保存します。prior description と native artifact の完了は別々のフラグで記録します。
- monolithic worker が返した全 values、NaN、diagnostics を checker より先に保存します。wall/RSS が途中で止めた場合、partial dirs と prior 全未処理 claim を保持します。
- 実 wall/RSS 超過と source/solver の例外を別々に記録します。例外を cap として閉じません。raw が返っていない計算を、計算済みの NaN として偽装しません。
- 親の入力・source検査、子の起動/import/worker/serialize/read/check/source再照合を実 wall/CPU に含めます。最終 parent receipt/stdout の tail は root の外側 enclosing receipt で測る契約です。
- reference_status は unmeasured、金融資格は unknown のままです。saved transport/interpolation 検査は独立 CF/PDE 精度や正式121/51受入を確定しません。

## 準備の確認・保持した失敗

2 classes の metadata/source/input 検査は PASS。root_preapproved:false の candidate は実行承認 guard で拒否されました。新しい金融 worker、solver、RNG 呼出しは0です。準備の保存入力読取・型配列検証には金融境界の禁止 guard を置き、呼出し0を確認しました。

準備 v1 では system Python の plotly 不足、次に dataclass の誤った import 元を検出しました。両失敗ログを保持し、既存 workspace venv と正しい HestonParameters import 元を使う v2 で準備を完了しています。最終 v3 は、prior description と実 native artifact 完了の表示を分けています。

準備 v2 の親込み実費は wall 2.845 秒 / CPU 2.836 秒。検証 CLI の2区間は合計 wall 0.150 秒です。その他の読取・編集・報告時間を含む全費用とは主張しません。金融 cache の時間は未測定です。

## Root の次の手順

最終 candidate を別名の root-fixed prior budget として保存し、理由・承認を記録したうえで root_preapproved:true を固定してください。false の元 candidate と初期記述は保持してください。その後、既存 workspace venv から script の親側を各 class 1 回ずつ実行します。--child を直接実行せず、root の外側実時計/CPUで終端出力まで包んでください。

実行 interface は --budget-file <root-fixed-budget> --class-id M2 または M3 --output <D直下の新 task-5-current-whole-call-cache-observation-... directory> です。この準備によって正式 pilot/main、金融資格、全体 budget が承認済みにはなりません。

主な確認記録: task-5-current-whole-call-cache-preparation-validation-v3.json / preparation-parent-cost-v2.json。
