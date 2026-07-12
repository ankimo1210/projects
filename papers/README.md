# papers

再配布可能なライセンスの論文・教科書 PDF を置く場所。このリポジトリは
public なので、**再配布 OK と確認できたものだけ**を置くこと。

`.gitignore` は `*.pdf` を既定で除外しているが、`papers/**/*.pdf` だけ
例外で追跡対象（`!/papers/**/*.pdf`）。`.pre-commit-config.yaml` の
large-file チェックも `papers/` は対象外（学術 PDF は数MB〜十数MBが普通のため）。

## 置く前に確認すること

- ライセンス／利用規約が再配布を許可しているか（例: CC BY / CC0、著者本人の
  公開許可、arXiv の一部ライセンス等）
- 出版社版 PDF（学術誌の VoR など）は基本 NG。OA (open access) 版か著者の
  self-archiving 版を使う
- 自作物（自分で書いたレポート・ノート）は無条件で OK

## 出典の記録

ファイル名または同名の `.md`（例: `foo.pdf` + `foo.md`）に、取得元 URL・
ライセンス・確認日を残しておくこと。
