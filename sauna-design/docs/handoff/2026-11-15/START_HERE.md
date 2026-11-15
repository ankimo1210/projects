# ChatGPT分析用引き継ぎ — 最初に読む
作成日: 2026-11-15（日本時間）。この文書のパスはZIP展開後のルートを基準とする。

## 最短の読み順
1. [01_HANDOFF.md](01_HANDOFF.md)：目的、採用要件、変更履歴、現状、次の分析。
2. [02_DESIGN_AND_ENGINEERING.md](02_DESIGN_AND_ENGINEERING.md)：寸法、3D、動線、設備、構造/法令の未確認。
3. [03_FINANCE_AND_PROPERTY.md](03_FINANCE_AND_PROPERTY.md)：予算、収益式、候補/除外物件、ONE GINZA。
4. [04_DATA_DICTIONARY.md](04_DATA_DICTIONARY.md)、[05_ASSET_GUIDE.md](05_ASSET_GUIDE.md)：単位・データ型・モデルの使い方。
5. [analysis/requirements_and_decisions.json](analysis/requirements_and_decisions.json)、[analysis/open_issues.csv](analysis/open_issues.csv)、[analysis/revenue_model.json](analysis/revenue_model.json)。
6. デザイン確認は artifacts/fable-v8/diagrams/sauna_floor_map_v8.png と artifacts/fable-v8/renders/、建築重ね合わせは artifacts/fable-v9/renders/。

## 読み違えないための現状
- 内装の現行はV8。V9はV8へ仮の建築条件を重ねた試作。ONE GINZAの物件対応版ではない。
- 男性専用1系統、館内同時40人という計画、3サ室、冷水2槽＋炭酸泉。40人/席数は営業定員の認定ではない。
- 20×14m=280㎡は仮の原型。物件にそのまま入ると未確認。
- 当初の総額1〜2億円上限は現在一旦解除。山手線又は千代田線の駅から広告徒歩10分以内。大崎/いちご神宮前は今回の候補から除外。
- ONE GINZA B101の347.21㎡は広告の専有表示。実賃料・浴場/朝〜22/23時営業・支持/設備・分割避難は未確認。
- 約3.19億円は仮家賃/契約/追加工事枠の資金例、約117人/日の分岐点は仮の収益式。実募集額・工事見積・需要予測ではない。
- nullを0円/不可/適合にしない。原型の計算・メッシュの検証成功を構造安全や営業許可へ読み替えない。
- 収録内容は保存資料とこのチャットで確認可能な議論を統合した要約・データであり、全会話の逐語録ではない。

## ChatGPTへ渡す開始文
```text
添付ZIPを、ZIP展開・コード実行が利用可能なら展開してください。
まず00_START_HERE.mdと01_HANDOFF.md、次に02/03/04/05を読み、
analysis/requirements_and_decisions.json、analysis/open_issues.csvと
analysis/revenue_model.jsonを照合してください。
project_sourceとartifactsは根拠資料のスナップショットです。
古い予算上限や廃止案を復活させず、仮定・広告表示・未取得の実条件を区別してください。
最初に、今の計画の成立を左右する論点を、根拠ファイル・未取得資料・判断への影響とともに整理してください。
収益の350円/人の固定/変動配分と税区分を監査し、
需要予測と供給能力（40人、希望営業時間、滞在時間、ピーク）を分離して分析してください。
モデルや画像だけで構造・メーカー離隔・避難・衛生・費用の成立を保証しないでください。
物件未確定のまま図面を創作せず、40人/3室/3槽やデザイン要件の変更は変更案として明示してください。
```

ZIPを扱えない場合は展開し、この5文書とJSON/CSV、必要なPDF/PNGを個別に添付する。BLEND/GLBの直接表示やBlenderの実行が利用できるとは限らないため、PNGとGLBのJSONメタデータも同梱する。[OpenAIのファイル利用説明](https://help.openai.com/en/articles/8555545-uploading-files-and-audio-to-chatgpt)は、ZIP展開がData Analysisと利用ツールに依存することを案内（確認2026-11-15）。このZIPを外部へ自動アップロードしてはいない。

## 完全性・適用範囲
- FILE_INDEX.csv：全収録ファイル、役割、元の場所、バイト数、SHA256。
- PACKAGE_MANIFEST.json：選択/除外範囲、作成条件、元ファイルからのコピー一致等。
- ZIP横の.sha256：ZIP本体のSHA256。内部SELF/manifestの自己ハッシュ循環は作らない。
- project_source/は元ソースの保存コピー。絶対パス/当時の指示・状態は履歴で、現在の実行環境や採用条件としない。
- reports/は基本計画文書のリンクを同梱パスへ置換した閲覧コピー。変換前/後のSHAは索引へ記録。
- raw Fable会話、端末ログ、試写、旧版の全バイナリ、重複ZIPは同梱しない。原本は元環境で保持し、会話IDとバックアップのハッシュ/所在はSESSION_PROVENANCE.jsonへ記録。
