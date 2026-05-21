"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import instruments, prices, analytics, data_update, backtest, alerts

app = FastAPI(title="Market Viz API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(instruments.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(data_update.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
