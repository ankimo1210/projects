from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gto.api.routers import (
    equity,
    health,
    hu,
    library,
    review,
    simulation,
    solver,
    trainer,
)
from gto.library.store import SOLUTIONS_DIR

app = FastAPI(title="GTO Poker Suite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(equity.router, prefix="/api")
app.include_router(trainer.router, prefix="/api")
app.include_router(solver.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(hu.router, prefix="/api")

# Serve pre-computed solution data (Parquet + JSON cache) for direct browser fetch
SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/solutions", StaticFiles(directory=str(SOLUTIONS_DIR)), name="solutions")
