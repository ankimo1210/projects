# Volatility Surface Viewer Implementation Plan

## 目的と設計

同じ満期・マネーネス・年率IVの格子データを、Plotly / React Three Fiber / Babylon.jsで表示。
`web/app/volatility/page.tsx` を追加し、既存ORBITは保持する。
Viewerを最初の画面に出す。既存の暗い背景とライム色を継承し、チャートには共通の連続色尺度を使う。
単独表示の切り替えと3画面比較、回転・ズーム・視点初期化、点の確認、満期断面を実装する。
同じ数値配列・軸域・カラースケールを渡す。描画エンジンや投影実装による見た目の完全一致は主張しない。

## データとチャートの契約

- 粒度: 1つの (tenor_years, moneyness) に年率IVを1つ。moneyness = K/F。
- 内部単位: Tは年、K/FとIVは小数。画面はK/FとIVを%で表示。金額・銘柄・観測日時は仮定しない。
- 初期データ: 25列×24行の解析式による模擬格子。市場データ・較正済みモデルではないことを表示。
- 模擬データのプリセットとレベル、スキュー、曲率、期間傾斜を操作できる。
- CSV: `tenor_years,moneyness,iv`。完全な矩形格子だけ受理。有限・正値、重複、欠損、格子上限5000点・ファイル1MBを検証。
- 失敗したCSVは現在の正しいデータを保持。CSVはブラウザ内で処理し、サーバーに送らない。
- 主図は3D surface、補助図は選択満期のsmileと選択K/Fのterm structure。数値確認用の選択点を共通化。
- 模擬データの軸は全プリセットで固定: K/F 70〜130%、T 1/12〜2年、IV 0〜70%。CSVは全格子から共通範囲を一度決定。
- 連続色尺度は低IVから高IVへ明度を上げる。共通凡例、軸ラベル、数値、選択マーカーも併用。
- 3D表示が失敗しても値・断面・CSV出力を利用できる。

## ファイルと順序

1. `web/components/volatility/model.ts` と `tests/volatility-model.test.ts`: 模擬生成、CSV検証/往復、格子と単位のテスト。実装前に失敗を確認。
2. `web/components/volatility/contract.ts`: 共通軸、色、座標、視点、renderer props。
3. `three-surface.tsx` / `babylon-surface.tsx` / `plotly-surface.tsx`: 同じ格子の描画、選択、視点、破棄。
4. `viewer.tsx` / `slices.tsx` / `styles.css` と `/volatility`: Viewer、共通パラメーター、CSV、補助断面。
5. `tests/volatility.spec.ts`: 各エンジンの実Canvas表示、切り替え、同一値の選択、パラメーター、CSVの受理/拒否、比較表示、モバイル。
6. 型・lint・本番ビルドと実ブラウザ確認、スクリーンショット、README/検証記録。

## 制約

- 既存の未コミットのORBIT比較実装を保持。今回も公開・コミット・pushしない。
- 必要な追加依存はPlotlyの3D部分ビルドとその型定義だけ。
- サイトコードは所有エージェントが編集。別担当は読み取り専用API調査とレビューのみ。
- 実機GPU性能を推定しない。自動表示確認はLinux Chromium + SwiftShader。
