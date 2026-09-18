# 入力の関数化と簡略化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 明示的な連動と保存済み条件の再利用により、日常比較の数値入力を基本7項目＋必要時の社宅期間に整理する。

**Architecture:** 生の入力値と連動モードを持つ `HousingInputs` を、既存の5スクリプトの第3ブロック末尾に追加する。解決済みの33値を従来エンジンに渡し、画面・感応度・CSV・JSONが同じ状態を使う。既存の計算エンジン分割や数式エディタは導入しない。

**Tech Stack:** 既存のHTML / JavaScript / Node.js標準機能。追加パッケージなし。

**Spec:** [入力簡略化の調査と設計案](../../input-simplification-research.md)。特に「推奨する画面と状態の設計」を参照。

**Status:** v2.2として実装。これは着手時の作業計画であり、途中で利用者が許可した社会保険料と保有費用の概算に合わせて実装範囲を拡張した。旧チェックリスト中の3連動限定・社保推計除外などは最終仕様ではない。採用した操作と検証結果は [README](../../../README.md) と [修正状況](../../STATUS.md) を正本とする。

## Global Constraints

- 対象は現在の個人向け・高所得給与モデル。年収3,000万〜1億円、社宅振替後の課税給与1,500万円以上という適用範囲を維持する。
- 通貨の内部単位は円、比率は小数。月額/年額換算は既存の `meta.scale` を使う。
- `original/` の10ファイルは変更しない。
- 単一HTMLをローカルで開けること。追加パッケージなし。
- 旧JSONと手入力モードの既存33項目を維持し、前提が同じなら結果を変えない。新しい概算モードの結果は旧基準値から変わる。
- 税額は前後の給与税額差で計算する。限界税率を家賃に一律乗算する方式に変更しない。
- 税制は2026年固定モデルを維持し、保存データで `taxRuleSet: "jp-2026-fixed"` と識別する。法改正の自動取得はしない。
- 住宅価格から家賃・将来利回りを暗黙に推計しない。所有費用だけ、概算モードでは購入価格の1%/年とし、手入力で固定できる。
- 既存 `HousingModel` / `HousingSensitivity` の関数シグネチャ、Node.jsのエクスポート、`HousingUI.getCurrent()` の解決済みパラメータ形式を維持する。
- 金利変更・修繕・税務特例・IO等の詳細設定は保持する。非表示と無効化を同義にしない。
- 手入力の上書きを尊重し、連動の再開は明示操作とする。
- 新画面には既存の色トークンを使う。レポート全体の配色やレイアウトの刷新を含めない。
- 社保の概算は2026年度・東京の協会けんぽ、給与均等12か月・賞与なし、40歳未満を明示した例示設定とする。年齢帯40〜64歳を選択可能にし、実額上書きも残す。厚生年金は標準報酬月額65万円・健康保険は139万円の上限を使う。
- 他プロジェクトの変更を含めない。コミット/プッシュは実装時の依頼範囲に従う。

---

## ファイルと責務

パスは `housing-buy-vs-rent/` からの相対。

| ファイル | 変更 |
|---|---|
| `current/source/extracted_scripts.js` | 第3ブロックに小さな入力状態/解決関数を追加。第4・5ブロックでUI、感応度、保存・読込を接続 |
| `current/source/full_source.html` | 基本/初回/詳細の表示、連動モードと採用値、税額等の読取表示 |
| `current/source/extracted_styles.css` | 追加UIが必要とする最小限のスタイル。HTML内の対応スタイルとそろえる |
| `current/report/housing_rent_corporate_buy_report_v2.html` | 既存ビルドで生成。直接編集しない |
| `tests/load-model.cjs`（新規） | 現行の先頭3ブロックをVMで読む、DOM非依存のテスト補助 |
| `tests/input-state.test.cjs`（新規） | 連動・上書き・感応度・JSON互換性の振る舞いを検証 |
| `tests/audit.cjs` | 原則既存のまま全36検証を維持。5ブロック構造は変更しない |
| `README.md` / `docs/STATUS.md` | 実装後に使い方、適用範囲、検証結果を更新 |

`scripts/build-report.cjs` は5ブロック同期の既存構造を維持する。追加のビルドシステムを作らない。

## データと関数の契約

`Parameters` は現在の `BASE_PARAMS` と同じ33キー・型・単位。

```js
// InputState: 全項目に元の手入力値を保持。連動中に values の子を破壊しない。
{
  values: { /* BASE_PARAMS と同じ33個の値 */ },
  modes: {
    social_corp: 'manual', // または 'same_as_normal'
    corp_years: 'manual',  // または 'full_residence'
    owner_growth: 'manual' // または 'same_as_rent'
  }
}
```

上のコメントは型の説明であり、実装では33個の既存値を `BASE_PARAMS` または読込データから複製する。モードなしの新規既存基準・旧ファイルでは全て `manual`。同値という理由で連動を推測しない。

`HousingInputs` の内部関数を以下に固定する。JSON/CSV等へ文字列を描画する際は既存のエスケープを使う。

| 関数 | 契約 |
|---|---|
| `create(parameters)` | 33値を複製し、全手入力の `InputState` を返す |
| `setMode(state, key, mode)` | 許可した3キーのモードのみ変更し、新しい状態を返す。未知キー/モードはエラー |
| `update(state, patch)` | 内部単位の既知値だけを反映。子キーを直接編集したときはそのモードを `manual` にする |
| `resolve(state)` | `{parameters, provenance}` を返す。3種類の連動を適用し、33値を既存 `validate` で検証する。不正状態はエラー |
| `scenario(state, patch, mode='linked')` | `linked` は現在の連動を維持してpatchを適用。`independent` は解決済み値から全手入力の試算を作る。入力状態は変更しない |
| `evaluate(state)` | `resolve(state).parameters` を `HousingSensitivity.evaluate` に渡す。既存評価のフィールドに `inputState` / `provenance` を付記 |
| `serialize(state)` | 下記の新JSON形式をJSON文字列として生成。現行の33値スナップショットも含める |
| `deserialize(document)` | 旧JSON/新JSONのどちらも検証して `InputState` を返す。未知バージョン/型/税制版を黙認しない |

`provenance` は各キーに `{mode, dependsOn}` を持ち、`manual` または各連動モード、参照キー配列を返す。手入力というだけで実額確認済みとは扱わない。出典/確認状況は現行のメタデータと併記する。

新JSONは次の項目を持つ。数値の採用値より `inputs` を正本とし、読込時に再解決する。

```js
{
  model: 'housing-input-state',
  schemaVersion: 1,
  taxRuleSet: 'jp-2026-fixed',
  units: 'JPY and decimal rates',
  inputs: state,
  parameters: HousingInputs.resolve(state).parameters
}
```

新形式の `parameters` と再計算結果が異なる場合は読込を拒否し、現在の状態を保持する。旧形式の既知モデル `housing-tax-comparison-v2-2026-09-17` は33値を全手入力として移行する。現行読込が受理していたモデルタグなしの `{parameters}` も維持し、未知の明示モデルタグは拒否する。

## Task 1: 連動・上書きの解決関数

**Files:** JS第3ブロック、新規テスト補助、新規 `input-state.test.cjs`。

**Consumes:** `BASE_PARAMS`、`HousingSensitivity.meta/validate/evaluate`。
**Produces:** `HousingInputs.create/createDefault/setMode/update/resolve/scenario/evaluate`。

- [ ] 次の読み込み補助を `tests/load-model.cjs` に用意する。既存エクスポートを書き換えない。

```js
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
module.exports = function loadModel() {
  const source = fs.readFileSync(path.join(__dirname,
    '../current/source/extracted_scripts.js'), 'utf8');
  const context = vm.createContext({});
  vm.runInContext(source.split('// ===== script block 4 =====')[0] +
    '\nglobalThis.loaded={M:HousingModel,S:HousingSensitivity,p:BASE_PARAMS,I:HousingInputs}', context);
  return context.loaded;
};
```

- [ ] 以下を起点に振る舞いテストを作り、`node --test tests/input-state.test.cjs` で未実装による失敗を確認する。

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const {I, p} = require('./load-model.cjs')();
test('manual override survives parent edits, relinking is explicit', () => {
  const base = I.create(p);
  const linked = I.setMode(base, 'social_corp', 'same_as_normal');
  const changed = I.update(linked, {social: 2000000});
  assert.equal(I.resolve(changed).parameters.social_corp, 2000000);
  const overridden = I.update(changed, {social_corp: 1600000});
  const later = I.update(overridden, {social: 2400000});
  assert.equal(I.resolve(later).parameters.social_corp, 1600000);
  assert.equal(I.resolve(base).parameters.social_corp, 1500000);
  assert.equal(I.resolve(I.setMode(later, 'social_corp', 'same_as_normal'))
    .parameters.social_corp, 2400000);
});
```

- [ ] `HousingInputs` を第3ブロック末尾に追加する。既存 `module.exports=HousingSensitivity` は維持する。解決規則は次の3つだけとする。

```js
if (modes.social_corp === 'same_as_normal') parameters.social_corp = values.social;
if (modes.corp_years === 'full_residence') parameters.corp_years = values.years;
if (modes.owner_growth === 'same_as_rent') parameters.owner_growth = values.rent_growth;
```

- [ ] 数値の型、有限性、モード、既知キーを検証する。0円/0年/0%を未入力扱いしない。子の手入力値の型は保存時に検証し、採用値の範囲は既存 `validate` に一本化する。
- [ ] 追加ケース: 家賃増加率−2%への連動、社宅0年の手入力、社宅全期間選択→比較15年、未知モード、`NaN`、元状態不変。エラー時に保存状態が変わらないことを確認する。
- [ ] `node scripts/build-report.cjs`、`node --test tests/input-state.test.cjs`、`node tests/audit.cjs` の順に実行し、既存基準値が変わらないことを確認する。実装依頼にコミットが含まれる場合のまとまり: `feat(housing): resolve explicit input links and manual overrides`。

## Task 2: 全ての計算経路で連動を維持

**Files:** JS第4・5ブロック、`input-state.test.cjs`。

**Consumes:** Task 1の `InputState` / `scenario` / `evaluate`。
**Produces:** 基本比較、1変数感応度、ヒートマップ、トルネード、月次CSVが共通状態から計算される。

- [ ] 次のテストで「期間連動」と「社宅10年固定」の違いを固定する。

```js
test('duration scenarios recompute links and preserve explicit fixed years', () => {
  const linked = I.setMode(I.create(p), 'corp_years', 'full_residence');
  const a = I.evaluate(I.scenario(linked, {years: 15}));
  const b = I.evaluate(I.scenario(linked, {years: 15}, 'independent'));
  assert.equal(a.p.corp_years, 15);
  assert.equal(b.p.corp_years, 10);
  assert.ok(a.corp.growth > b.corp.growth);
  assert.equal(I.resolve(linked).parameters.years, 10);
});
```

- [ ] フォーム変更は単位変換後に `HousingInputs.update` を通し、採用値を再計算する。`fill()` は全数値を毎回手入力状態にしない。利用者が編集したキーと、画面同期による値の書込みを区別する。
- [ ] 1変数・トルネードは各試算で `I.scenario(state, patch)`→`I.evaluate` とする。表示単位の試算値は `S.byKey[key].scale` で内部単位へ変換する。
- [ ] `years`を動かす試算は社宅全期間モードに従う。`corp_years`を直接動かす試算は、その試算だけ社宅モードを手入力にする。
- [ ] 期間×社宅期間ヒートマップは二軸を独立に指定するため `independent` とする。「社宅全期間の連動を外した比較」を見える場所に表示する。家賃×価格等の他の二軸は親を変更した後に連動を再解決する。
- [ ] 上部と下部の結果、比較表、月次CSV、全感応度CSV、クイックシナリオ、リセットの経路を列挙して接続する。CSVには従来の33採用値列を残し、連動モード列を末尾追加する。月次CSVにも設定JSONと対応するモード/税制版の識別情報を持たせる。
- [ ] 同じ試算値を画面・CSVで評価した結果が一致するテストを追加する。最終g*を再投入した純資産差が0.01円以内となる既存検証を維持する。
- [ ] 手入力の基準6ケースを既存値と照合する。価格感応度で家賃・保有費用が変わらないことも確認する。

## Task 3: 基本入力8項目と採用値の表示

**Files:** JS UI、`full_source.html`、必要時CSS、生成レポート。

**Consumes:** Task 2までの共通状態、`resolve().provenance`、既存 `tax/housingTax/pmt`。
**Produces:** 基本/初回/詳細の画面と、条件連動を利用者が確認・変更できる操作。

- [ ] 基本画面の数値欄を `price, rent, years, mortgage_rate, ltv, owner_cost, invest, corp_years` にする。社宅全期間・利用なしを選択した場合は `corp_years` を読取表示にする。
- [ ] 個人・会社・ローン契約の条件は初回設定、価格予想や金利変更・一時修繕・費用率等は詳細設定に配置する。33項目全てへの編集経路を残す。同じ値の独立した入力欄を二組増設しない。
- [ ] 3個の連動スイッチに参照元・採用値を表示する。手入力へ切替えたときは、利用者が値を編集できる。明示的に連動を再開するまで手入力値を保つ。
- [ ] 税率入力欄は作らず、税額の通常/社宅比較、税額差、実質家賃、借入額・頭金を結果として表示する。限界税率を表示するなら所得税の値であることを示す。
- [ ] 非表示項目を空欄としてパースしない。現在の有効な状態を維持し、`step_year=0`では変更後金利、`extra_repair=0`では修繕年を折りたたむ。依存項目の元の数値は残す。
- [ ] 成長率0%、年収5,000万円、費用率、3,000万円控除等の採用済み仮定を要約に表示する。「自動計算」と「同じ値を使う仮定」「未確認の例示値」を区別する。
- [ ] ブラウザで以下を確認する。連動の実装前後はスクリーンショットと数値を比較する。

| 操作 | 期待結果 |
|---|---|
| 現行基準を開く | 手入力モードで従来のg* +0.1406% / +2.4576%を維持 |
| 社保同額を選択→通常社保200万円 | 社宅時も200万円、税額/結果が更新 |
| 社宅社保160万円を手入力→通常社保240万円 | 社宅社保160万円を維持 |
| 全期間利用→比較15年 | 社宅15年、感応度/CSVも同条件 |
| 社宅10年固定→比較15年 | 社宅10年、従来の15年ケースを再現 |
| 金利変更なし/修繕0 | 不使用の年・金利欄でエラーにならない |
| 基本/詳細を往復 | 値やモードを消去しない |
| 不正入力→修正 | 直前の有効結果とエラー表示を保ち、修正後に復帰 |
| 狭い画面、キーボード操作 | 入力/ラベルの欠落や重なりなし |

- [ ] `node scripts/build-report.cjs` と `node tests/audit.cjs` を実行する。生成したHTMLの5スクリプトとJS編集元が一致することを確認する。

## Task 4: JSONの再利用・移行・出力の整合性

**Files:** JS `serialize/deserialize`、既存保存/読込ハンドラー、テスト。

**Consumes:** `InputState`と旧JSONの `parameters`。
**Produces:** 値と連動の両方が復元される設定ファイル。旧JSONの数値互換性。

- [ ] 次の往復/移行テストを実装前に追加する。

```js
test('legacy values stay fixed, new files preserve linking', () => {
  const old = I.deserialize({model:'housing-tax-comparison-v2-2026-09-17', parameters:p});
  assert.equal(I.resolve(I.update(old, {years:15})).parameters.corp_years, 10);
  const linked = I.setMode(I.create(p), 'corp_years', 'full_residence');
  const restored = I.deserialize(JSON.parse(I.serialize(linked)));
  assert.equal(I.resolve(I.update(restored, {years:15})).parameters.corp_years, 15);
  assert.equal(I.evaluate(old).corp.growth, I.evaluate(I.create(p)).corp.growth);
});
```

- [ ] 上記データ契約の新形式を実装する。旧33値は全手入力で取り込み、値の一致による連動推定をしない。`taxRuleSet`の違いはエラーにする。
- [ ] 既存の1MB上限、JSON/型/範囲検証を維持する。不正/欠落キー、未知モード、未知版、採用値改変で読込を拒否し、現在のUI状態を変更しないテストを追加する。
- [ ] `parameters`は必ず解決済み値、`inputs.values`は元の手入力値とする。連動していた項目の手入力値が往復後にも残ることを確認する。
- [ ] 実ブラウザで保存→ページ再読込→ファイル読込→親の編集を行い、連動が継続することを確認する。旧JSONも実ファイルで読み込み、結果を確認する。
- [ ] 自動的なブラウザ永続保存やクラウド同期は追加しない。利用者が既存のローカルJSONを再利用する運用とする。

## Task 5: 回帰検証と利用説明

**Files:** README、STATUS、必要時監査記録、生成HTML。

**Consumes:** Task 1〜4の完成状態。
**Produces:** 再実行可能な検証と利用者向けの入力/連動説明。

- [ ] 次の順で確認する。

```sh
node scripts/build-report.cjs
node --test tests/input-state.test.cjs
node tests/audit.cjs
```

- [ ] ビルドを再実行して内容が変わらないこと、元の36検証が全て通ること、原本SHA-256が変わらないことを確認する。広いワークスペースのテストはこの変更の検証に代用しない。
- [ ] ブラウザ確認はTask 3の操作表と、Task 4の実ファイル往復を実施する。JavaScriptエラーがないこと、CSVの代表行と画面の計算値が一致することを確認する。
- [ ] READMEに基本8項目、初回設定、3連動の意味、手入力への切替、旧JSON互換性、2026固定税制を記載する。STATUSは実装/検証済み/未確認を区別して更新する。
- [ ] 変更したファイルだけを対象に差分を確認する。原本と他プロジェクトが変更対象に入っていないことを確かめる。

## 後段候補と着手条件

第1段階の完了に以下は必要ない。それぞれ別の成果物として追加計画を作る。

| 候補 | 着手条件・必要な設計 |
|---|---|
| 頭金額入力→LTV | 「頭金固定」と「LTV固定」の価格感応度を定義。逆算する買値ごとにLTVも解決する。銀行審査の代用にしない |
| 費用内訳→`buy_cost/basis_cost/sell_cost` | 支出と税務算入額を分離。固定額/価格比例/税抜価格の区別。売却の分岐探索中にも再計算 |
| 社保の制度推計 | 加入保険、年齢、月給/賞与、対象年月、現物報酬の情報を揃え、実額優先と誤差表示を設計 |
| 社宅の現物利益推計 | 固定資産税資料・本人徴収額・役員/使用人区分を取得。給与振替と本人徴収を分離 |
| 一般年収・家族構成対応 | 年度別給与税/住民税/控除・非課税基準・住宅ローン控除等の独立した検証計画 |

## 完了条件

- 初回設定後、基本画面の数値入力は8項目、社宅年数を省略できる設定では7項目。
- 全33個の詳細条件は編集/保存でき、現在の採用値と連動の根拠が確認できる。
- 3種類の連動・上書き・復帰が全計算経路とJSONで一貫している。
- 旧JSONと全手入力条件の結果を維持し、既存36検証と新規の連動/互換性検証が成功する。
- 推計や利用者の選んだ仮定を、制度上確定した自動計算と誤認させない。
