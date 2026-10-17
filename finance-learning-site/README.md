# Folio — 金融工学のはじめかた

日本語の金融工学入門サイト。複利、分散投資、オプションを、ブラウザ内の計算とクイズで学ぶ。

```bash
node build.mjs
node verify.mjs
python3 -m http.server 4318 --directory dist
```

- `index.html`: 全画面、スタイル、対話処理、学習コンテンツ。外部依存なし。
- `build.mjs`: 配信用の `dist/index.html` を生成。
- `verify.mjs`: 計算例・境界値、JavaScript構文、生成物の一致を検証。
- `.openai/hosting.json`: Sitesの識別子と静的配信設定。

学習記録はブラウザのlocalStorageに保存。アクセス不能時はメモリ内で学習を継続する。
計算は学習用の仮定に基づく。複利は年1回の再投資、分散は各資産の年率標準偏差20%、オプションは原資産1単位の買い手の満期損益を扱う。

内容参照：SEC Investor.gov、OCC/OIC Options Education。出典リンクは該当レッスン内に掲載。
デザインはワークスペース標準 `docs/templates/claude-report/tokens.css` をインラインで使用。

2026-10-17 にワークスペースの Git へ取り込んだ。それまでの単独リポジトリ（1コミット、リモートなし）の `.git` は `_data/finance-learning-site/inner-git` に退避してある。
