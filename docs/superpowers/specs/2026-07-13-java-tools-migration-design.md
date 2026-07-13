# Java 工具迁移设计

## 目标

将 Java 项目 `src/main/java/com/yupi/yuaiagent/tools` 中的 9 个本地工具迁移到 Python 项目 `app/tools`，并替换现有订单、天气 mock 工具。迁移后的工具继续通过既有的 `LocalTool` 注册表导出 OpenAI 兼容函数定义和执行入口。

## 范围

本次迁移包含以下工具：

- 文件读取与写入。
- PDF 生成。
- 资源下载。
- 受限终端命令执行。
- 网页抓取。
- 百度网页搜索。
- 任务终止标记。
- 当前时间获取。

现有 `get_order_status` 与 `get_weather` mock 工具、对应测试和文档说明不再保留。

## 架构

每个工具模块都定义 Pydantic 入参模型和同步工具函数。`app/tools/registry.py` 集中登记全部迁移工具，`execute_tool()` 保持现有的“名称查找、Pydantic 校验、函数执行”调用链，`get_tool_definitions()` 保持 OpenAI function tools 格式。

文件读取、写入、PDF 生成和资源下载共用受限路径解析逻辑。该逻辑只接受纯文件名，拒绝绝对路径、父级路径和目录分隔符；各工具只能使用项目根目录下的 `tmp/file`、`tmp/pdf` 或 `tmp/download` 子目录。

## 工具契约

| 工具名 | 入参 | 返回行为 |
| --- | --- | --- |
| `read_file` | `file_name` | 返回 `tmp/file` 中的 UTF-8 内容或错误文本。 |
| `write_file` | `file_name`、`content` | 创建目录并写入 UTF-8 文件，返回落盘路径或错误文本。 |
| `generate_pdf` | `file_name`、`content` | 在 `tmp/pdf` 中生成 PDF，返回落盘路径或错误文本。 |
| `download_resource` | `url`、`file_name` | 以 HTTP 超时下载资源至 `tmp/download`，返回路径或错误文本。 |
| `execute_terminal_command` | `command` | 仅执行白名单只读命令，返回标准输出或拒绝/执行错误文本。 |
| `scrape_web_page` | `url` | 获取网页并返回 HTML 文本或错误文本。 |
| `search_web` | `query` | 调用 SearchAPI 的百度引擎并返回前 5 条 organic results 的 JSON 文本。 |
| `terminate` | 无 | 返回任务结束标记，不主动终止 Python 进程。 |
| `get_current_time` | 无 | 返回本地当前时间文本。 |

## 安全与错误处理

所有网络请求使用 10 秒超时。搜索 API Key 从 `SEARCH_API_KEY` 配置读取；未配置时返回明确错误，不在结果或日志中泄露密钥。

终端工具仅接受单条白名单命令：`dir`、`ls`、`pwd`、`type`、`Get-ChildItem`。参数必须是安全的相对路径，且不允许包含管道、重定向、命令连接符、命令替换或换行符。工具不启动 shell 或子进程，而是将这些命令映射为 Python 的目录列举、工作目录返回和 UTF-8 文件读取操作；所有路径均限制在项目 `tmp/` 目录。

工具预期的业务失败保持字符串结果，便于模型消费；参数格式错误继续由 Pydantic `ValidationError` 抛出，未知工具继续由 `ToolNotFoundError` 抛出。

## 依赖与配置

将 `httpx` 移入运行时依赖，用于下载、抓取和搜索；新增 `beautifulsoup4` 用于网页 HTML 解析，新增 `reportlab` 生成 PDF。配置模块增加可选 `search_api_key`，从 `SEARCH_API_KEY` 环境变量加载。

## 测试

新增或更新本地工具测试，使用临时目录覆盖读写、PDF、下载、路径穿越拒绝和注册表替换；使用 mock HTTP transport 覆盖下载、抓取、搜索成功与异常；覆盖终端白名单命令、`tmp/` 路径限制和危险语法拒绝。测试不依赖真实网络、SearchAPI 密钥或项目外文件。

完整回归执行 `uv run pytest` 与 `uv run ruff check app tests`。
