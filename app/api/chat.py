from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.llm_client import LLMClientError


router = APIRouter()


def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        answer = await service.chat(request.message)
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail="Model provider request failed.") from exc
    return ChatResponse(answer=answer)
