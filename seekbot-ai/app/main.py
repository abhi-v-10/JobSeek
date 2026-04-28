from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router

app = FastAPI(
    title="SeekBot AI",
    version="1.0.0",
    description="AI Agent for JobSeek"
)


app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(chat_router,  prefix="/chat", tags=["Chat"])

