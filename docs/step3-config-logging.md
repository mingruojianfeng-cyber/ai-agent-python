# Step 3: 配置与日志系统

## 学习目标

本步骤对应 Java 项目里的 `application.yml`、`@Value` 和 `slf4j` 日志配置。Python 版本使用 `.env` 保存环境变量，用 `pydantic-settings` 读取配置，用标准库 `logging` 初始化应用日志。

## 文件说明

| 文件 | 作用 |
|---|---|
| `.env.example` | 环境变量示例，不放真实密钥 |
| `app/core/config.py` | 定义 `Settings` 配置对象和 `get_settings()` |
| `app/core/logging.py` | 定义统一日志格式和 `configure_logging()` |
| `tests/test_config.py` | 验证配置读取和密钥脱敏 |
| `tests/test_logging.py` | 验证日志级别和 handler 不重复 |

## Java 到 Python 的映射

Java 里常见写法：

```yaml
spring:
  ai:
    dashscope:
      api-key: your-api-key
      chat:
        options:
          model: qwen-plus
```

Python 里改成 `.env`：

```text
LLM_API_KEY=
LLM_MODEL=qwen-plus
REQUEST_TIMEOUT_SECONDS=60
```

Java 里用 `@Value("${search-api.api-key}")` 注入配置；Python 里用：

```python
from app.core.config import get_settings

settings = get_settings()
print(settings.llm_model)
```

## 为什么要脱敏

Agent 服务会频繁调用外部模型和工具，日志里不能直接输出 API Key。`mask_secret()` 会保留少量前后缀用于排查配置是否加载正确，但隐藏中间内容：

```python
mask_secret("sk-test-secret")
# sk-t******cret
```

## 验证命令

```powershell
.\.venv\Scripts\python -m pytest tests\test_config.py tests\test_logging.py -v
.\.venv\Scripts\python -m pytest -v
.\.venv\Scripts\python -m ruff check .
```





![image-20260708164025240](E:/Typora/images/image-20260708164025240.png)
