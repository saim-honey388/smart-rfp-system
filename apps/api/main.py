from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from apps.api.config.settings import settings
from apps.api.models.db import init_db
from apps.api.routers import chat, pages, proposals, reviews, rfps


app = FastAPI(title="RFP AI Review", version="0.1.0")

# Static assets (CSS/JS) for server-rendered templates.
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

# HTML page routes (no /api prefix).
app.include_router(pages.router)

# API routers
app.include_router(rfps.router, prefix="/api")
app.include_router(proposals.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    """Redirect to the dashboard."""
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.env}


@app.on_event("startup")
def on_startup():
    init_db()
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)

