# Wireframes (Phase 2-6 着手前の青写真)

作成日: 2026-05-12
基調: Bloomberg Terminal 系 (`docs/design/design_principles.md`)
形式: ASCII テキストワイヤー (Figma 等の高忠実度モックは Phase 6 で必要に応じて)

## 一覧

| ファイル | 画面 | 対応Phase |
|---|---|---|
| `lp.md` | ランディングページ | 6 |
| `upload.md` | 資料アップロード / URL投入 | 3 |
| `extraction_confirm.md` | 抽出結果確認 | 3 |
| `analyses_list.md` | 分析履歴一覧 | 4 |
| `comparison_board.md` | 比較ボード | 6 |
| `pricing.md` | 料金プラン | 6 |

各ファイルは:
- ASCIIワイヤー (固定幅 100文字目安)
- 操作フロー
- 採用コンポーネント (`@/components/bloomberg.tsx` のもの)
- データ依存

## 既に実装済み

- 結果画面: `apps/web/src/app/page.tsx` (サンプル) + `apps/web/src/app/new/page.tsx` (フォーム→結果)
- ナビ: `CmdKey` (F1 ANLY / F4 SAMPLE)
- 共通: `Panel` / `Row` / `KpiCell` / `Badge` / `Btn` / `Field` / `Input` / `Select`
