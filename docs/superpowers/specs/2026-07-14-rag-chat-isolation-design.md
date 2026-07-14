# RAG 会话隔离与延迟初始化设计

## 目标

修复两个已复现的问题：普通聊天会提前初始化 Embedding 客户端；RAG 拒答会写入并污染后续知识库问答的会话历史。

## 设计

### 延迟初始化检索依赖

`get_chat_service()` 仅创建 `ChatService`，不再创建 `EmbeddingClient`、`PgVectorStore` 或 `VectorRetriever`。

新增缓存工厂 `get_rag_retriever()`。`POST /chat` 仅在请求携带 `knowledgeBaseId` 时调用该工厂，再将 Retriever 显式传入 `ChatService.chat_with_rag()`。因此普通聊天不依赖 Embedding 配置、代理或 pgvector。

### RAG 会话隔离

RAG 调用使用内部记忆 ID：

```text
{chatId}:kb:{knowledgeBaseId}
```

该 ID 只用于加载和保存服务端聊天记忆，API 入参和响应中的 `chatId` 保持不变。不同知识库和普通聊天不会共享上下文。

### 拒答历史

当检索为空、Retriever 不可用时，返回固定拒答文本，但不写入聊天记忆。避免配置修正、文档重导或阈值调整后，历史拒答被模型当作事实继续复述。

### Prompt 顺序

RAG Prompt 放在基础系统提示之后、历史消息之前。资料约束在当前用户问题和历史对话之前进入模型上下文。

## 测试

1. `get_chat_service()` 在启用 RAG 时仍可创建，且不构造 Embedding 客户端。
2. 普通会话已有拒答历史时，同一 `chatId` 发起知识库问答不会把该历史传给模型。
3. 检索为空不会保存 RAG 拒答历史。

## 非目标

本次不调整向量阈值、检索算法、数据库表结构或 API 字段。
