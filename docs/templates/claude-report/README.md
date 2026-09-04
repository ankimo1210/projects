# claude-report — HTML レポートの既定スタイル

このワークスペースで HTML のレポート／Artifact を作るときの既定。
`tokens.css` が正本、`skeleton.html` が骨格の見本。

## 使い方

1. `skeleton.html` をコピーする
2. `<style>` ブロックに `tokens.css` の**全文を貼る**
   （Artifact は自己完結が必須で、外部 CSS は CSP で読めない。
   外部から読めるのは Google Fonts のスタイルシートだけ）
3. 中身を書く。色は必ず `var(--...)` で参照し、生の hex を直接書かない

Artifact として公開するときは `<!doctype>` / `<html>` / `<head>` / `<body>` を
書かない（ホストが包む）。ディスク上の単体 HTML にするときは自分で包む。

## 何が決まっているか

| | |
|---|---|
| 地色 | `#F0EEE6` クリーム、カードは `#FAF9F5`。ダークは `#1A1917` / `#262624` |
| アクセント | `#C05C33`（ダーク `#E08A6A`）。強調は1色に集中させる |
| 見出し | Source Serif 4 + Zen Old Mincho |
| 本文 | Zen Kaku Gothic New（**JP を先頭に置く**。後述） |
| 数字・ラベル | IBM Plex Mono、`font-variant-numeric: tabular-nums` |
| 角丸 | カード 12px |
| テーマ | light / dark / 未指定（OS）の3状態すべてを定義済み |

## 図を描くときの規則

- **色は `var(--series-1)` / `var(--series-2)` から取る。**
  この2色は dataviz スキルの6チェックを light / dark 両面で通してある
  （`node scripts/validate_palette.js "#C05C33,#2A6DA6" --mode light --surface "#FAF9F5"`）。
  値を変えたら必ず再検証する
- 大小の順序がある軸（面積帯・年代など）は `--s1`〜`--s8` の連続ランプ
- 二軸（y スケール2本）は使わない。パネルを分ける
- `el()` が色を style 経由で流し込むので、テーマ切り替えに図が追従する。
  presentation attribute に `var()` を直接書くと**無言で効かない**
- ホバーツールチップは原則すべての図に付ける（`bind()`）

## JP 組版の落とし穴

`--sans` は **JP フェイスを先頭**に置いてある。Latin フェイスを先頭にすると
`——`（em dash 2つ）が Latin 側から取られ、2本の短い線に割れて
カタカナの「ーー」に見える。英語のみの文書では先頭2つを入れ替える。

## 検証

公開前に必ずレンダリングして目で見る。バリデータは色しか見ない。

```bash
CH=~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
$CH --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1200,9000 --virtual-time-budget=14000 \
    --screenshot=out.png "file://$PWD/wrap.html"
```

`wrap.html` は `<!doctype html><html><head><meta charset="utf-8">…<body>` で
レポートを挟んだだけのもの。`<html data-theme="dark">` にしてダークも見る。

## 実例

`docs/templates/claude-report/` を最初に適用したのは沖縄の賃料レポート
（re_invest_os のデータ、2026-08-30）。図5点＋ヒート表の構成が参考になる。
