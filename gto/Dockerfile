# GTO Poker Suite — public deploy image (E1).
# Single container: FastAPI serves the API + Next.js static export + the
# precomputed solution library. CPU-only: gto_cuda is NOT built (GPU routes
# 503 behind PUBLIC_DEPLOY=1); gto_py is built without CUDA.
#
# Build (repo root = ~/projects):
#   docker build -f gto/Dockerfile -t gto-suite .
# Run:
#   docker run -p 8000:8000 \
#     -e PUBLIC_DEPLOY=1 -e SUPABASE_JWT_SECRET=... \
#     -e ALLOWED_ORIGINS=https://your.domain gto-suite

# ---- stage 1: Rust -> gto_py wheel -----------------------------------------
FROM rust:1.87-slim AS rust-build
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages maturin
WORKDIR /src
COPY gto/Cargo.toml gto/Cargo.lock ./
COPY gto/crates ./crates
RUN maturin build --release --manifest-path crates/gto-py/Cargo.toml \
    --out /wheels --interpreter python3

# ---- stage 2: Next.js static export ----------------------------------------
FROM node:22-slim AS web-build
WORKDIR /web
COPY gto/web/package.json gto/web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY gto/web .
# output: 'export' is required for the single-container layout (every page is
# a client component fetching /api on the same origin).
RUN NEXT_PUBLIC_DEPLOY=1 pnpm exec next build

# ---- stage 3: runtime --------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app
COPY gto/pyproject.toml ./gto/pyproject.toml
COPY gto/src ./gto/src
COPY --from=rust-build /wheels /wheels
RUN pip install --no-cache-dir ./gto /wheels/*.whl uvicorn
# Precomputed library (instant-preview tier) + frontend static export
COPY _data/gto/solutions /app/_data/gto/solutions
COPY --from=web-build /web/out /app/static
ENV PUBLIC_DEPLOY=1
EXPOSE 8000
CMD ["uvicorn", "gto.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
