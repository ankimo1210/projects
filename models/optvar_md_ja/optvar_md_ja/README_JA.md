# Opt-Var Markdown Export 日本語版

このフォルダは、`optvar_ocr.pdf` をMarkdown中心で扱えるようにした日本語ローカライズ版です。

## 重要

- PDFは全136ページです。
- 各ページは画像として保存されているため、図表・数式・レイアウトは視覚的に確認できます。
- OCRテキストは原文英語のまま保持しています。
- OCRは数式・表・番号で誤読があるため、厳密確認にはページ画像を正本として使ってください。
- この版は「全文日本語翻訳」ではなく、「日本語UI付きの完全アーカイブ」です。

## 構成

- `document_ja.md`: 日本語版の統合Markdown。全ページ画像と原文OCRテキストを収録。
- `pages_ja/page_XXX_ja.md`: ページ別の日本語版Markdown。
- `assets/page_images/`: 全136ページの画像。
- `raw_text/`: OCRテキスト。
- `html_textbook/`: 日本語UI付きの静的HTMLテキストブック。
- `tools/build_html_textbook.py`: HTMLテキストブック再生成スクリプト。
- `translations_ja/page_XXX_ja.md`: OCR本文のページ別全文日本語訳。
- `full_report_ja.md`: OCR本文の全文日本語訳フルレポート。
- `tools/build_full_ja_report.py`: Ollamaを使った全文日本語訳レポート生成スクリプト。
- `AUDIT_REPORT_JA.md`: 日本語の監査レポート。
- `TRANSLATION_NOTES_JA.md`: 翻訳・精度に関する注意。

## 推奨する使い方

1. 図表・数式・表はページ画像で確認する。
2. OCRテキストは検索用・下書き用として使う。
3. 正式な日本語翻訳を作る場合は、ページ単位でOCR修正後に翻訳する。

## HTMLテキストブック

生成済みのHTML版は `html_textbook/index.html` から開けます。日本語目次、章別ビュー、ページ別ビュー、OCR検索、図表・表・数式候補インデックスを含みます。

全文日本語訳レポートは `full_report_ja.md` と `html_textbook/full_report_ja.html` から参照できます。翻訳はOCRテキスト由来のため、数式・表・図はページ画像を正本として確認してください。

再生成する場合は、プロジェクトルートで以下を実行してください。

```bash
python3 tools/build_html_textbook.py
```

全文日本語訳レポートを再生成する場合は、Ollamaで `qwen2.5:7b` が利用できる状態で以下を実行してください。

```bash
python3 tools/build_full_ja_report.py --model qwen2.5:7b
```
