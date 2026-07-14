# 导入 FastAPI 应用类；它承担 Java Spring Boot 应用上下文和 Web 框架入口的角色。
from fastapi import FastAPI

# 为聊天接口路由起别名，避免和下面的健康检查路由混淆。
from app.api.chat import router as chat_router
# 导入健康检查路由，用于负载均衡器或部署平台探活。
from app.api.health import router as health_router

from app.api.knowledge import router as knowledge_router


# 创建 ASGI 应用实例；Uvicorn 通过 `app.main:app` 找到的正是这个变量。
app = FastAPI(
    # 以下元数据会显示在 FastAPI 自动生成的 OpenAPI/Swagger 文档中。
    title="Yu AI Agent Python",
    version="0.1.0",
    description="Python FastAPI version of the Yu AI Agent backend.",
)

# Java 对照：这里相当于创建应用上下文并注册 Controller 路由。
# FastAPI 会根据函数签名和 Pydantic 模型自动生成 OpenAPI 文档。
# 将各功能模块的路由表挂载到应用，作用接近 Spring 扫描并注册 Controller 的 RequestMapping。
app.include_router(health_router)
app.include_router(chat_router)

app.include_router(knowledge_router)
