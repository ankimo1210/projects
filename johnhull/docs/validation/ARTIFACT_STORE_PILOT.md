# 成果物保管庫の小群実証

更新日: 2026-09-28

[ADR 0004](../../../docs/decisions/0004-artifact-storage-and-evidence.md) の保管先で、
§27.4 の Book / portal 画像4件を実証した記録。画像は既存の受入証跡なので
Git から外していない。保管庫の保存・復元を検証する目的で複製した。

- [保存器が読む manifest](artifact-store-pilot.json): `evidence_store.py` の schema 1。
  パスは johnhull 内の相対パスで、公開ファイルにローカルの絶対パスを載せない。
- [出典・生成条件・検証記録](artifact-store-pilot-provenance.json): 元の記録、
  ライセンス、生成 commit、入力ハッシュ、ブラウザー、画面幅、復元方法を記録。
  この補助記録は保存器の manifest と区別する。
- [保存器](../../scripts/evidence_store.py): D1-preflight と共通の実装を使う。

C: の内蔵 SSD と F: の別 SSD に、それぞれ2種類の blob、計37,806 bytesを保存。
manifest の4論理ファイルは計75,612 bytes。両コピーを独立に一時領域へ復元し、
4件すべてのサイズと SHA-256 が元ファイルと一致した。F: では hard link が
`EPERM` となるため、保存器のロック付き一時ファイルからの原子的公開も実機で確認した。
保管庫の読み出しでは常にハッシュを検査する。

再検証する場合は、WSL の `PROJECTS_ARTIFACT_STORE` と
`PROJECTS_ARTIFACT_MIRROR` をそれぞれ正本・第2コピーの**実在する**場所へ設定し、
リポジトリのルートから次を実行する。

```bash
python johnhull/scripts/evidence_store.py verify   johnhull/docs/validation/artifact-store-pilot.json --work "${TMPDIR:-/tmp}/johnhull-artifact-pilot-check"
```

§27.4 の対象テスト15件、台帳のソース照合、release 契約は PASS。
専用 worktree の Book 初回ビルドは CSS URL の版識別子が欠け、
台帳の `--check-artifacts` は FAIL。CSS 配置後に
`jupyter-book build johnhull/book/ --all` で再ビルドすると、
既存 M14 のハッシュと一致して PASS した。既存証跡は書き換えていない。
補助記録の `pending` / `FAIL` は初回ビルド時点の履歴であり、後続の
再ビルド結果は[実証記録](d1-preflight/README.md)に記した。
D1 全体の判定は[実証記録](d1-preflight/README.md)に分ける。
