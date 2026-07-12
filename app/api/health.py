from fastapi import APIRouter

router = APIRouter()

# 返回类型标注主要服务于 FastAPI 文档和校验，不会像 Java 泛型一样强制运行时转换。


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "yu-ai-agent-python"}
