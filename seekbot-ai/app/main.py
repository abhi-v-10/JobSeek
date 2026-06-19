from app.api.chat import router as chat_router
from app.api.health import router as health_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from app.core.openai_client import generate_chat_completion

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    try:
        logger.info("Performing startup model validation...")
        generate_chat_completion([{"role": "user", "content": "ping"}], max_tokens=10)
        logger.info("Startup model validation successful.")
    except Exception as e:
        logger.critical(f"Startup model validation failed: {e}")
    yield

app = FastAPI(title="SeekBot AI", version="1.0.0", description="AI Agent for JobSeek", lifespan=lifespan)

# ── CORS ───────────────────────────────────────────────────────────────────────
# The browser sends a preflight OPTIONS request before every cross-origin POST.
# Without this middleware FastAPI drops the preflight and the browser blocks the
# real request with "Failed to fetch" / "Provisional headers are shown".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (localhost)
        "http://127.0.0.1:5173",  # Vite dev server (loopback)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Authorization, Content-Type, etc.
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
