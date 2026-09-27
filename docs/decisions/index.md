# Architecture Decision Records

Workspace-level decisions whose rationale git log can't recover. Format:
`NNNN-slug.md` with Status / Context / Decision / Consequences. Write one only
when a future reader can't reconstruct the "why" from the diff/log; otherwise
leave the history to git log.

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-workspace-docs-and-knowledge-layers.md) | Workspace docs and knowledge layers | Accepted; wiki placement superseded by 0003 | 2026-07-08 |
| [0002](0002-workspace-green-and-declared-dependencies.md) | The workspace is green, and every package declares what it imports | Accepted | 2026-08-01 |
| [0003](0003-keep-knowledge-in-repository.md) | 知識を開発リポジトリ内に保持する | Accepted | 2026-09-16 |
| [0004](0004-artifact-storage-and-evidence.md) | 大容量成果物を Git 外の検証可能な保管庫へ分離する | Accepted; migration pending | 2026-09-27 |
