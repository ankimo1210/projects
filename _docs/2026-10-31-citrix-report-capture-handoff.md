# Citrix レポート撮影と Mac 再開の引き継ぎ

更新日: 2026-10-31

Citrix内のブラウザーに表示されたレポートを、冒頭からページ末尾まで17枚の画像に撮影し、
全17ページのPDFにまとめた。次の作業はまだ指定されていない。
Macでは成果物を確認し、ユーザーの次の指示から再開する。

## 完了したもの

- PNG 17枚。各1982 × 1395ピクセル。前後の本文に重なりがある。
- 横向きA4のPDF。1画像を1ページに配置し、元画像の解像度を維持した。
- 画像を順番に開けるローカルHTML一覧。
- 移送後の照合に使うSHA-256の一覧と、Macでも実行できるPDF再作成スクリプト。

画面の画像をまとめたPDFであり、原本PDFのダウンロードではない。
OCRはしていないため、本文の検索や文字の選択には別途OCRが必要。

## Git と成果物の保存先

Git管理対象はこのメモと [再作成スクリプト](citrix-report-capture/images_to_pdf.py)、
[照合用manifest](citrix-report-capture/artifact-manifest.json)。
レポート本文、画像、社内URL、メール、チャット、接続先の識別情報はGitへ入れない。

PDFと画像は別のローカル移送用ZIPにまとめる。展開後の構成は次のとおり。

~~~text
citrix-mac-handoff/
  HANDOFF.md
  COMMIT.txt
  repo-handoff.patch
  repo/_docs/2026-10-31-citrix-report-capture-handoff.md
  repo/_docs/citrix-report-capture/
    images_to_pdf.py
    artifact-manifest.json
  private_artifacts/
    research_report.pdf
    research_report_screenshots/
      index.html
      report_001.png ... report_017.png
~~~

GitのコミットだけではPDFと画像はMacへ届かない。移送用ZIPも取得する。
撮影前のデスクトップ全体、他アプリの画面、PDF検査用の中間画像はZIPに含めない。
Windows側の元の成果物はそのまま残している。

[保存規約](../AGENTS.md) は勤務先・顧客の機密を保存せず、追加ファイルを原則2MB以下とする。
[成果物保存方針](../docs/decisions/0004-artifact-storage-and-evidence.md) に従い、
大きな成果物をGit履歴に埋め込まない。クラウドへのアップロードやpushはしていない。

## Mac での再開

1. 移送用ZIPをローカルに展開し、PDFまたは画像一覧を開く。
2. 展開したフォルダーを作業ディレクトリにして、次の照合を行う。
   照合だけならPython標準ライブラリで動く。

~~~bash
python3 repo/_docs/citrix-report-capture/images_to_pdf.py --verify-only --artifact-root private_artifacts
~~~

成功時は19ファイルのハッシュ一致が表示される。
ZIP内のCOMMIT.txtでWindows側のコミットを確認できる。
Macのリポジトリに未反映なら、既存の変更を確認したうえで同梱のrepo-handoff.patchを取り込める。
既に同期済みなら重ねて適用しない。

## PDF を再作成する場合

PDFは同梱済みなので、閲覧するだけなら再作成は不要。
再作成するときは、依存バージョンを記した単独スクリプトとして実行する。
リポジトリ全体の依存関係や設定を変更する必要はない。

~~~bash
uv run --script repo/_docs/citrix-report-capture/images_to_pdf.py --images private_artifacts/research_report_screenshots --output private_artifacts/research_report_rebuilt.pdf
~~~

既存の出力ファイルは上書きしない。画像の順番、ページ数、埋込画像のピクセル一致を検査する。
原版と再作成版ではPDFのメタデータやファイルハッシュが異なり得るため、
原版そのものの照合にはmanifestを使う。

## 検証済みの範囲

- 全17枚を撮影中に確認し、冒頭、本文・図表、ページ末尾まで取得した。
- 原版PDFは全17ページをPopplerで描画し、一覧と先頭ページを目視確認した。
- 全17ページの埋込画像が対応する元PNGとピクセル単位で一致することを確認した。
- manifestの19ファイルは移送用ZIP作成時にも照合する。
- 再作成スクリプトはWSLの独立した依存環境でも実行し、17ページの生成と元画像との一致を確認した。
- Mac実機の実行とMacでのCitrix画面操作は未検証。
  Windowsの画面操作コードをそのままMacで実行できるとは想定しない。

## 追加撮影時の注意

Windowsでは仮想デスクトップによって取得できるウィンドウ一覧が変わった。
一覧に出ないことだけでCitrixが起動していないとは断定できない。
デスクトップ番号を指定した切り替えは未確認。
今回はCitrixアプリを呼び出すと目的のウィンドウを取得できた。

Citrixを前面にすると表示サイズと解像度が変わり、再描画待ちが必要になった。
表示が安定してから新しい画像を取得し、その画像の座標で操作する。
古い座標やウィンドウ番号を再利用しない。
今回の最終撮影状態は2380 × 1601ピクセル。
左378・上145から幅1982・高さ1395のレポート領域を切り出した。
これは今回の表示に固有であり、Macや別サイズの画面には流用しない。

本文の右側余白をスクロールの起点にすると、図表上の操作ボタンを写さずに済む。
各操作の後に表示を確認し、本文を少し重ねながら進める。
勤務先の内容を共有知識ノートや公開リポジトリに転記しない。
