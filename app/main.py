from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router


app = FastAPI(
    title="Yu AI Agent Python",
    version="0.1.0",
    description="Python FastAPI version of the Yu AI Agent backend.",
)

app.include_router(health_router)
app.include_router(chat_router)
