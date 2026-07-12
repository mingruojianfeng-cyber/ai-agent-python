from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router


app = FastAPI(
    title="Yu AI Agent Python",
    version="0.1.0",
    description="Python FastAPI version of the Yu AI Agent backend.",
)

# Java 对照：这里相当于创建应用上下文并注册 Controller 路由。
# FastAPI 会根据函数签名和 Pydantic 模型自动生成 OpenAPI 文档。
app.include_router(health_router)
app.include_router(chat_router)
