from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.llm_client import LLMClientError


router = APIRouter()


def get_chat_service() -> ChatService:
    """FastAPI dependency provider.

    For Java developers: this is similar to asking Spring to inject a service
    bean into a controller method.
    """
    return ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Handle POST /chat and delegate real business work to ChatService.

    For Java developers: keep this layer like a Spring MVC controller: validate
    request DTOs, call the service, and translate service errors into HTTP
    responses.
    """
    try:
        answer = await service.chat(request.message)
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail="Model provider request failed.") from exc
    return ChatResponse(answer=answer)
