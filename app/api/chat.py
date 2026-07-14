# 缓存依赖工厂的返回值，使 Service 在当前进程内被复用。
from functools import lru_cache

# Annotated 将“Python 类型”和“FastAPI 注入元数据”放在同一个参数声明中。
from typing import Annotated

# Depends 声明依赖注入，HTTPException 用于转换为受控 HTTP 错误响应。
from fastapi import APIRouter, Depends, HTTPException

# StreamingResponse 支持边生成边写出响应，适合大模型逐 token 输出。
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.intent import IntentClassification
from app.services.chat_service import ChatService
from app.services.intent_service import IntentClassificationError, IntentService
from app.services.llm_client import LLMClientError

from app.core.config import get_settings
from app.rag.embedding_client import EmbeddingClient
from app.rag.retriever import RetrievalError, VectorRetriever
from app.rag.vector_store import PgVectorStore

# 当前模块的聊天 Controller 路由集合。
router = APIRouter()

# Java 对照：APIRouter 类似 Spring MVC 中按功能拆分的 @RestController 路由集合。


# 依赖提供器被缓存后，多个请求不会反复构造 ChatService 及其依赖。
@lru_cache
def get_chat_service() -> ChatService:
    """FastAPI 依赖提供器。

    Java 开发者对照：这类似于让 Spring 把 service bean 注入到 Controller 方法里。
    """
    # FastAPI 调用此函数并将结果注入标注 Depends 的参数。
    return ChatService()


@lru_cache
def get_rag_retriever() -> VectorRetriever | None:
    """按需创建 RAG 检索器，避免普通聊天初始化向量检索依赖。"""
    settings = get_settings()
    if not settings.rag_enabled:
        return None

    vector_store = PgVectorStore(
        database_url=settings.database_url,
        embedding_dimensions=settings.embedding_dimensions,
    )
    return VectorRetriever(
        embedding_client=EmbeddingClient(settings=settings),
        vector_store=vector_store,
        min_score=settings.rag_min_score,
    )


# 意图识别服务也作为进程内单例复用。
@lru_cache
def get_intent_service() -> IntentService:
    """提供意图识别服务实例，供 FastAPI 依赖注入复用。"""
    return IntentService()


# response_model 同时约束输出序列化格式并生成 OpenAPI 响应文档。
@router.post(
    "/chat",
    response_model=ChatResponse,
    response_model_exclude_none=True,
)
async def chat(
    # FastAPI 自动从 JSON 请求体构建并校验 ChatRequest。
    request: ChatRequest,
    # 该参数不来自 HTTP；Depends 指示框架调用工厂注入 ChatService。
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """处理 POST /chat，并把真实业务委托给 ChatService。

    Java 开发者对照：这一层像 Spring MVC Controller，只做 DTO 校验、调用服务和转换异常。
    """
    try:
        if request.knowledge_base_id is not None:
            try:
                retriever = get_rag_retriever()
                result = await service.chat_with_rag(
                    message=request.message,
                    chat_id=request.chat_id,
                    knowledge_base_id=str(request.knowledge_base_id),
                    retriever=retriever,
                )
            except RetrievalError as exc:
                raise HTTPException(
                    status_code=502,
                    detail="Knowledge base retrieval failed.",
                ) from exc

            return ChatResponse(
                answer=result.answer,
                sources=list(result.sources) or None,
            )

        # await 让出事件循环，等待模型网络请求完成后恢复执行。
        answer = await service.chat(request.message, request.chat_id)
    except LLMClientError as exc:
        # 供应商调用失败映射为 502；from 保留底层异常链便于日志定位。
        raise HTTPException(status_code=502, detail="Model provider request failed.") from exc
    # 显式构造响应 DTO，避免服务层内部结构泄漏到 API。
    return ChatResponse(answer=answer)


# 流式接口不设置 response_model，因为响应体是持续产生的 SSE 文本事件。
@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """处理 POST /chat/stream，并用 SSE 格式返回模型片段。"""

    # 异步生成器会边收到模型片段边 yield，不必等待完整答案才开始响应。
    # 内嵌异步生成器是该 HTTP 响应的数据源。
    async def event_stream():
        async for chunk in service.stream_chat(request.message, request.chat_id):
            # SSE 规定每个事件以 data: 开头，并以连续两个换行结束。
            yield f"data: {chunk}\n\n"

    # StreamingResponse 持续消费生成器，把每个 yield 的内容写入 SSE 响应。
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 该端点把自然语言转换为后续 Agent 编排可消费的固定 JSON 结构。
@router.post("/classify-intent", response_model=IntentClassification)
async def classify_intent(
    request: ChatRequest,
    service: Annotated[IntentService, Depends(get_intent_service)],
) -> IntentClassification:
    """把用户消息识别成 RAG、工具调用、MCP、YuAgent 委托或普通聊天意图。"""
    try:
        # 服务层负责提示词、模型调用和 Schema 校验，Controller 只处理协议转换。
        return await service.classify(request.message)
    except IntentClassificationError as exc:
        # 422 表示模型返回了文本，但其内容无法满足约定的业务数据结构。
        raise HTTPException(
            status_code=422, detail="Model structured output parse failed."
        ) from exc
