from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.llm_client import LLMClientError


router = APIRouter()


@lru_cache
def get_chat_service() -> ChatService:
    """FastAPI 依赖提供器。

    Java 开发者对照：这类似于让 Spring 把 service bean 注入到 Controller 方法里。
    """
    return ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """处理 POST /chat，并把真实业务委托给 ChatService。

    Java 开发者对照：这一层像 Spring MVC Controller，只做 DTO 校验、调用服务和转换异常。
    """
    try:
        answer = await service.chat(request.message, request.chat_id)
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail="Model provider request failed.") from exc
    return ChatResponse(answer=answer)


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """处理 POST /chat/stream，并用 SSE 格式返回模型片段。"""

    async def event_stream():
        async for chunk in service.stream_chat(request.message, request.chat_id):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
