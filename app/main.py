from fastapi import FastAPI

from app.api.heath import router as health_router


app = FastAPI(
    title="Yu AI Agent Python",
    version="0.1.0",
    description="Python FastAPI version of the Yu AI Agent backend.",
)

app.include_router(health_router)

