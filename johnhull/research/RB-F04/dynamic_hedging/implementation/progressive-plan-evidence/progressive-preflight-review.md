# Progressive teacher DAG — 独立の事前確認

## 判定

**選択用 DAG のメタデータ確認に限り承認。C0 / I0。正式 pilot の実行・金融数値・source freeze・費用予算の承認ではない。**

対象 producer SHA: 0d719eb1379455a12239fbc543c940f1f7913fad00b451812c18664bcd106985。旧 compiler・元の v4 入力・DESIGN §7.4–7.5 / §13 / §15 と照合した。root の元のファイルを編集していない。レビュー用コピー、結果、計測記録のみを scratch に新規作成した。

## 実際に確認したこと

- packed artifact を保存済み reader で読み、producer の独立コピーから再構築した計画と同じ元入力・参照になっていることを確認した。これは入力・計画の provenance 確認であり、金融数値の一致を SHA で判定したものではない。
- 2,748 jobs / 16 stages。モデルごとに N=1024→4096→16384→65536、各 N で coarse→high。288 state / 192 date の実引数が元の18 state・24 queryと対応する。
- 各 stage に SDE / teacher_N / teacher_grid / pnl の16 cellsと position の48 pairs。全1,792 pairsについて actual risk source、dataset indices、shared market、base/refined cache、width、固定 validation roster を照合した。tiny NN は stage 内に含めていない。
- 原121 cases / 51 obligations は descriptor の名前・identity・順序を保持する。これらの正式実行と A bridge はまだ作られていない。
- 8 principal drivers + 2 reserved maximum-reference drivers、20 full teacher producers。元の768-step global calendar・teacher stream、18 state の oracle 3系列と next N / 768・1536の13 query×2 levelsを保持する。最高 N の比較は元の reserved oracle stream、同Nであり、未予約 N262144 を使わない。
- 共有 producer の first activation と全利用先を確認した。両モデルの base1024coarse・call・premium・共通 pilot 市場は無条件。local の高 N driver を Heston の gate で止める結線は現物にはない。段階 gate は同モデルの直前 gate に結線される。
- actual argument の numeric dependency closure と各 producer の cap descendant union を独立に再計算した。現在は selection-only scopeなので case_ids/attempt_ids は空。正式 A bridge で元121/51へ閉じる必要がある。
- field は元257×321、order1024 / frequency_scale512 / density_floor1e-10。callは49の exact dates。独立 compiler 実行では RNG と financial worker を禁止するパッチに到達しなかった。

## 反例による検査の範囲

最初の16改竄コピーは全拒否した。stale evidence による早期拒否と区別するため、別の10コピーでは evidence arguments と cap_scope を改竄後のグラフへ自己整合に更新した。

全10コピーを独立 guard は拒否した。対象は refined cache→base cache、teacher→oracle系列、最高候補の未予約seed/N262144、oracle N縮小、position width、local shared driver→Heston gate、field設定、原121/51のidentity変更。

**root の件数・signature・topology中心の dry-run は、この10コピーをすべて通す。** 現物の結線は正しいが、基本 dry-run の PASS を金融 source や参照identityの承認に拡大できない。正式実行では固定済み whole-source の exact producer/cache/risk binding と保存値の再計算が必要。新しい金融チェック関数の全面承認はこのレビューでは行っていない。

## JSON 報告の修正確認

元 v1 の json と parent-cost は末尾に literal backslash-n があり、JSON parser は Extra data で拒否する。元 bytes は reviewer snapshot と root の v1-original filesに残る。

修正 v2 は両JSONのparse・parent clock差・exit0を確認した。v1/v2 packed graphは同じ。AST差は報告/artifactの出力先と改行修正だけであり、producerは不変。旧初回import失敗、旧報告、失敗費用を消していない。

## 費用

- 独立 baseline + 16 probes：専用child全体15.090570628秒 wall / 15.077635秒 CPU。
- 自己整合10 probes：専用child全体20.276942822秒 wall / 20.268192秒 CPU。
- 内側の計測は上記に含まれ、加算しない。review自己書出しの残余、最初のsource生成SyntaxError、v2読み直しの独立外時計は未測定として残す。実験金融費用や正式A10費用へ流用しない。

## 正式 lock 前の残り

1. 選択後の混合 cache で元121 cases / 51 obligations / 全16比較を改めて実行するDAGと A bridge。
2. selected next/opposite cache と selected N の追加4日付の結線。失敗は実parent cap / unused proofへ結び、cacheや価格の0・holdで埋めない。
3. 原10 expense aliasesを実時計に結び、全work/bytes/rate/prior budgetを固定する。
4. 金融source最終版、失敗/cap/unusedの保存後再検算、全source closureの独立レビュー。
5. 上記の正式pilot→freeze→main→fresh/両保管庫/図/notebook/最終受入。現在 financial qualification は unknown、formal lock / formal execution は falseのまま。

レビュー日：2026-10-10。
