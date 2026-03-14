"""
Smart Wardrobe — FastAPI Backend
Application setup, middleware, router registration, and global endpoints.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from models.database import init_db
from models.user import User  # noqa: F401 — registers User with SQLAlchemy Base
from services.embeddings import get_embedding_index
from config import UPLOAD_DIR, THUMBNAIL_DIR

# Load .env from project root
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Wardrobe API",
    description="Intelligent wardrobe assistant with AI-powered clothing classification and outfit recommendations",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────

from routers.auth import router as auth_router
from routers.items import router as items_router
from routers.recommendations import router as recommendations_router
from routers.shopping import router as shopping_router
from routers.search import router as search_router

app.include_router(auth_router)
app.include_router(items_router)
app.include_router(recommendations_router)
app.include_router(shopping_router)
app.include_router(search_router)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    idx = get_embedding_index()
    logger.info("FAISS index loaded: %d items indexed", idx.index.ntotal)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Smart Wardrobe API",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "weather_configured": bool(os.getenv("OPENWEATHER_API_KEY")),
        "google_auth_configured": bool(os.getenv("GOOGLE_CLIENT_ID")),
    }
