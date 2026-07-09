# PostgreSQL + pgvector 一键部署

这个目录提供本地开发用的 PostgreSQL + pgvector 部署脚本，并自动初始化会话记忆表。

## 启动

在当前目录执行：

```bash
docker compose up -d
```

服务信息：

- 容器名：`yu_ai_agent_pgvector`
- 数据库：`yu_ai_agent`
- 用户名：`yu_ai_agent`
- 密码：`123456`
- 端口：`5432`

Python 项目 `.env` 配置：

```env
CHAT_MEMORY_TYPE=database
DATABASE_URL=postgresql+asyncpg://yu_ai_agent:123456@localhost:5432/yu_ai_agent
```

## 初始化内容

首次启动时，PostgreSQL 官方入口脚本会自动执行 `init/01-init-pgvector-chat-memory.sql`。

该脚本会创建：

- `vector` 扩展，用于 pgvector。
- `chat_messages` 表，用于当前对话记忆。
- `chat_message_embeddings` 表，预留给后续语义记忆或 RAG。

## 常用命令

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f postgres
```

进入数据库：

```bash
docker exec -it yu_ai_agent_pgvector psql -U yu_ai_agent -d yu_ai_agent
```

停止服务：

```bash
docker compose down
```

停止并删除数据卷：

```bash
docker compose down -v
```

注意：`docker compose down -v` 会删除数据库数据。
