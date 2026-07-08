# Opt-Var 日本語 HTML テキストブック

`index.html` をブラウザで開くと、生成済みの静的HTMLテキストブックを閲覧できます。

- `full_report_ja.html`: OCR全文日本語訳レポート。


## 生成元

- `TOC_JA.md`: 日本語目次
- `raw_text/page_XXX.txt`: 検索用OCRテキスト
- `assets/page_images/page-XXX.jpg`: 視覚正本のページ画像

## 再生成

プロジェクトルートで以下を実行してください。

```bash
python3 tools/build_html_textbook.py
```

本文OCRは原文英語のままです。数式、表、図は各ページ画像を正本として確認してください。
