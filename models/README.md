# models — 教科書翻訳パイプライン成果物

洋書教科書（PDF）を OCR → Markdown 抽出 → LLM 翻訳 → オフライン HTML 教科書化
した成果物の置き場。私的学習用。コードは各サブディレクトリの
`build_*.py`（ビルドスクリプト）のみで、大半は生成された Markdown / HTML /
ページ画像です。

## 収録プロジェクト

| ディレクトリ | 内容 |
|---|---|
| `econometrics_hf_ch1_ch7_jp/` | 『Econometrics of Financial High-Frequency Data』第1〜7章の日本語学習版（章別 Markdown + 全訳レポート + HTML 教科書） |
| `optvar_md_ja/` | 『Opt-Var』（OCR 元 PDF 136 ページ）の Markdown-first 日本語版。数式・図表はページ画像を正とする |
| `winning_probability_eu_ja/` | 『Winning Probability』(EU) の Markdown 日本語版（ページ画像付き） |

## 構成の規約

- `pages/` / `pages_ja/` — ページ単位の Markdown（原文 / 日本語）
- `assets/page_images/`, `assets/page_renders/` — 全ページ画像（数式・図表の視覚的な正）
- `html_textbook/` — オフライン閲覧用の静的 HTML 教科書
- `translation_cache/` — LLM 翻訳キャッシュ（**gitignore 対象**。`build_full_translation_report.py` が再生成する）

## 注意

- 生成物が主体のディレクトリのため、エージェントは既定で中身を走査しない
  こと（ルート `AGENTS.md` の Workspace Policy 参照）。
- 元 PDF は git 管理外（ルート `.gitignore` の `*.pdf`）。
