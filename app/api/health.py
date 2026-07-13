# APIRouter 用于把同一职责的 HTTP 端点聚合后再由 main.py 注册。
from fastapi import APIRouter

# 创建本模块私有路由表，类似独立的 Spring Controller 映射集合。
router = APIRouter()

# 返回类型标注主要服务于 FastAPI 文档和校验，不会像 Java 泛型一样强制运行时转换。


# 装饰器在模块加载时完成 GET /health 与下方协程函数的绑定。
@router.get("/health")
async def health_check() -> dict[str, str]:
    # FastAPI 自动将字典序列化为 application/json 响应体。
    return {"status": "ok", "service": "yu-ai-agent-python"}
