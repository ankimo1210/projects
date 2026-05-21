# 開発起動手順

## バックエンド (FastAPI)
```bash
source ~/.cargo/env
uv run maturin develop --manifest-path crates/gto-py/Cargo.toml  # Rust変更時のみ
uv run uvicorn gto.api.main:app --reload --port 8000
```

## フロントエンド (Next.js)
```bash
cd web
pnpm exec next dev  # または: NODE_ENV=development pnpm exec next dev
```

## URL
- フロントエンド: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
