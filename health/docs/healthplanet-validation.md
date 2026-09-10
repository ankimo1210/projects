# Health Planet連携の検証（2026-09-07）

公式契約: [Health Planet API仕様](https://www.healthplanet.jp/apis/api.html)。
取得対象は体重・体脂肪率、血圧・脈拍、歩数の3経路。
Googleの保存・認可とは独立させ、取得時の全応答本文をローカルに保存する。

- Python全体: 523テスト成功。Ruff lint・format検証成功。
- Web: 96テスト成功、TypeScript・ESLint成功。
- Next.jsの静的ビルド成功。一時コピーで`next build --webpack`を実行。
- 架空の84測定を使い、日付指定で12測定に絞られることと全件CSV出力をブラウザで確認。
- 実データを使った7画面の読み込み・JavaScriptエラーなしを確認。
- 390px表示で画面全体の横はみ出しなし。測定表は横スクロールと100件単位の表示。
- Windows側のlocalhostから身体ページのHTTP 200を確認。

主な回帰テストは、原本のbyte一致、未知項目の保持、同日複数測定と同一レコードの
出現回数保持、再取得の重複抑制、日付の区間境界、再開、再取得の未完了区間、
永続的な60回/時間制限、HTTP失敗時の原本保存、秘密情報の非出力、初期化失敗時の再試行、
Google系列の不変性、quota待機後の再開とAPIエラー時の停止を対象とする。

原本が取得できた区間と、アカウント全履歴の証明は別扱い。
API対象外の項目は取得済みにならない。ネットワークを使う試験は自動テストに含めない。

一度限りの長期取り込みには`sync-healthplanet --wait --export-dir ...`を使える。
今回のローカルジョブ情報は非公開の`data/healthplanet/backfill-job.json`、
進捗・終了理由は`data/healthplanet/backfill.log`にある。
ジョブはPC/WSLの実行中のみ継続し、指定した区間を完了すると終了する。
中断した場合は同じ開始日・終了日のCLIで再開できる。
