from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.models.db import init_db
from backend.routers import analysis, chat, pages, proposals, reviews, rfps, comparisons

# ...




app = FastAPI(title="RFP AI Review", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (primary)
        "http://localhost:5174",  # Vite dev server (fallback)
        "http://localhost:5175",  # Vite dev server (fallback)
        "http://localhost:3000",  # Alternative dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets (CSS/JS) for server-rendered templates - disabled after consolidation
# app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

# HTML page routes (no /api prefix).
# app.include_router(pages.router)

# API routers
app.include_router(rfps.router, prefix="/api")
app.include_router(proposals.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(comparisons.router, prefix="/api")


@app.get("/")
def root():
    """Redirect to the frontend."""
    return RedirectResponse(url="http://localhost:5173")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.env}


@app.on_event("startup")
def on_startup():
    init_db()
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)

