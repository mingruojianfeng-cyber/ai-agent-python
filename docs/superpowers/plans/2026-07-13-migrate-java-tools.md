# Java 工具迁移实施计划

> 执行方式：使用 executing-plans 按任务顺序实施。步骤使用复选框追踪。

**目标：** 将 Java 的九个本地工具迁移为受限、安全且可注册的 Python 工具。

**架构：** 每个工具用 Pydantic 模型描述入参，并由现有 LocalTool 注册表统一导出和分发。文件系统与终端访问收敛到 app/tools/common.py，网络 I/O 用可替换的 HTTP 请求函数。

**技术栈：** Python 3.12、Pydantic 2、httpx、Beautiful Soup 4、ReportLab、pytest、ruff。

## 全局约束

- 所有代码注释和用户可见工具文本使用中文。
- 文件、下载、PDF 和终端可访问路径仅限项目 tmp/ 目录。
- 不保留 get_order_status、get_weather 及其注册项。
- 网络请求超时固定为 10 秒，测试不得访问真实网络。
- 每项实现严格遵循先失败测试、后最小实现、再回归验证。

---

### 任务 1：建立运行时依赖、配置与受限路径基础设施

**文件：**
- 修改：pyproject.toml、app/core/config.py、.env.example
- 新建：app/tools/common.py、tests/test_tool_common.py

**接口：**
- 产出：get_tool_tmp_dir(category: str) -> Path、resolve_tool_path(category: str, file_name: str) -> Path、resolve_tmp_path(relative_path: str) -> Path。
- 产出：Settings.search_api_key: str，从 SEARCH_API_KEY 读取。

- [ ] 步骤 1：写入失败测试

~~~python
import pytest

from app.tools.common import resolve_tool_path, resolve_tmp_path


def test_resolve_tool_path_uses_project_tmp_directory() -> None:
    path = resolve_tool_path("file", "note.txt")
    assert path.name == "note.txt"
    assert path.parent.name == "file"
    assert path.parents[1].name == "tmp"


@pytest.mark.parametrize("file_name", ["../secret.txt", "nested/file.txt", "C:\\secret.txt"])
def test_resolve_tool_path_rejects_unsafe_file_name(file_name: str) -> None:
    with pytest.raises(ValueError, match="文件名不安全"):
        resolve_tool_path("file", file_name)


def test_resolve_tmp_path_rejects_parent_directory() -> None:
    with pytest.raises(ValueError, match="路径不安全"):
        resolve_tmp_path("../pyproject.toml")
~~~

- [ ] 步骤 2：确认失败

运行：uv run pytest tests/test_tool_common.py -v

预期：测试收集失败，提示 app.tools.common 不存在。

- [ ] 步骤 3：写入最小实现

~~~python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = PROJECT_ROOT / "tmp"


def get_tool_tmp_dir(category: str) -> Path:
    return TMP_ROOT / category


def resolve_tool_path(category: str, file_name: str) -> Path:
    candidate = Path(file_name)
    if not file_name or candidate.name != file_name or candidate.is_absolute():
        raise ValueError("文件名不安全")
    return get_tool_tmp_dir(category) / candidate.name


def resolve_tmp_path(relative_path: str) -> Path:
    candidate = (TMP_ROOT / relative_path).resolve()
    if not relative_path or (candidate != TMP_ROOT and TMP_ROOT not in candidate.parents):
        raise ValueError("路径不安全")
    return candidate
~~~

在 Settings 新增 search_api_key: str = ""，在 .env.example 新增 SEARCH_API_KEY=。将 httpx>=0.27.0 移入运行时依赖，并新增 beautifulsoup4>=4.12.0 与 reportlab>=4.2.0。

- [ ] 步骤 4：确认通过并提交

运行：uv sync --extra dev；uv run pytest tests/test_tool_common.py tests/test_config.py -v

~~~powershell
git add pyproject.toml uv.lock app/core/config.py .env.example app/tools/common.py tests/test_tool_common.py
git commit -m "feat: 添加受限工具基础设施"
~~~

### 任务 2：迁移文件、时间、终止与受限终端工具

**文件：**
- 新建：app/tools/file_operations.py、app/tools/system.py
- 新建：tests/test_file_operations.py、tests/test_system_tools.py

**接口：**
- 产出：ReadFileArgs、WriteFileArgs、read_file(args) -> str、write_file(args) -> str。
- 产出：TerminalCommandArgs、NoArgs、execute_terminal_command(args) -> str、terminate(args) -> str、get_current_time(args) -> str。

- [ ] 步骤 1：写入失败测试

~~~python
from app.tools.file_operations import ReadFileArgs, WriteFileArgs, read_file, write_file
from app.tools.system import NoArgs, TerminalCommandArgs, execute_terminal_command, terminate


def test_write_then_read_file_in_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    assert "写入成功" in write_file(WriteFileArgs(file_name="note.txt", content="你好"))
    assert read_file(ReadFileArgs(file_name="note.txt")) == "你好"


def test_terminal_rejects_shell_syntax() -> None:
    result = execute_terminal_command(TerminalCommandArgs(command="dir && whoami"))
    assert "不允许" in result


def test_terminal_lists_only_tmp_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    (tmp_path / "visible.txt").write_text("ok", encoding="utf-8")
    assert "visible.txt" in execute_terminal_command(TerminalCommandArgs(command="dir"))


def test_terminate_returns_completion_marker() -> None:
    assert terminate(NoArgs()) == "任务结束"
~~~

- [ ] 步骤 2：确认失败

运行：uv run pytest tests/test_file_operations.py tests/test_system_tools.py -v

预期：测试收集失败，提示工具模块不存在。

- [ ] 步骤 3：写入最小实现

file_operations.py 调用 resolve_tool_path("file", args.file_name)，写入前创建目录，将预期异常转为中文结果。system.py 只允许 dir、ls、pwd、type、Get-ChildItem，拒绝 |、>、<、&、;、反引号、$ 和换行。目录命令通过 iterdir() 实现，type 通过 UTF-8 读取实现，pwd 返回 TMP_ROOT，全程不得调用 shell 或子进程。

- [ ] 步骤 4：确认通过并提交

运行：uv run pytest tests/test_tool_common.py tests/test_file_operations.py tests/test_system_tools.py -v

~~~powershell
git add app/tools/file_operations.py app/tools/system.py tests/test_file_operations.py tests/test_system_tools.py
git commit -m "feat: 迁移受限文件和系统工具"
~~~

### 任务 3：迁移 PDF 生成工具

**文件：**
- 新建：app/tools/pdf_generation.py、tests/test_pdf_generation.py

**接口：**
- 产出：GeneratePdfArgs 与 generate_pdf(args: GeneratePdfArgs) -> str。

- [ ] 步骤 1：写入失败测试

~~~python
from app.tools.pdf_generation import GeneratePdfArgs, generate_pdf


def test_generate_pdf_writes_pdf_to_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    result = generate_pdf(GeneratePdfArgs(file_name="report.pdf", content="中文内容"))
    created = tmp_path / "pdf" / "report.pdf"
    assert "生成成功" in result
    assert created.read_bytes().startswith(b"%PDF")
~~~

- [ ] 步骤 2：确认失败

运行：uv run pytest tests/test_pdf_generation.py -v

预期：测试收集失败，提示 PDF 工具模块不存在。

- [ ] 步骤 3：写入最小实现

使用 resolve_tool_path("pdf", args.file_name) 创建目标目录；用 UnicodeCIDFont("STSong-Light") 注册中文字体，使用 SimpleDocTemplate、Paragraph 和 XML 转义后的内容写入 PDF。成功返回中文路径，异常返回中文错误文本。

- [ ] 步骤 4：确认通过并提交

运行：uv run pytest tests/test_pdf_generation.py -v

~~~powershell
git add app/tools/pdf_generation.py tests/test_pdf_generation.py
git commit -m "feat: 迁移 PDF 生成工具"
~~~

### 任务 4：迁移下载、抓取与搜索工具

**文件：**
- 新建：app/tools/web.py、tests/test_web_tools.py

**接口：**
- 产出：DownloadResourceArgs、ScrapeWebPageArgs、SearchWebArgs。
- 产出：download_resource(args) -> str、scrape_web_page(args) -> str、search_web(args) -> str。

- [ ] 步骤 1：写入失败测试

~~~python
import httpx

from app.tools.web import DownloadResourceArgs, SearchWebArgs, download_resource, search_web


def test_download_resource_writes_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(200, content=b"data"),
    )
    result = download_resource(DownloadResourceArgs(url="https://example.com/a", file_name="a.bin"))
    assert "下载成功" in result
    assert (tmp_path / "download" / "a.bin").read_bytes() == b"data"


def test_search_web_returns_at_most_five_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.web.get_settings",
        lambda: type("Settings", (), {"search_api_key": "key"})(),
    )
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            200, json={"organic_results": [{"n": index} for index in range(6)]}
        ),
    )
    assert search_web(SearchWebArgs(query="Python")) == '[{"n": 0}, {"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}]'
~~~

- [ ] 步骤 2：确认失败

运行：uv run pytest tests/test_web_tools.py -v

预期：测试收集失败，提示 app.tools.web 不存在。

- [ ] 步骤 3：写入最小实现

三个函数都调用 httpx.get(..., timeout=10) 和 response.raise_for_status()。下载使用 resolve_tool_path("download", args.file_name) 写入 response.content；抓取将 response.text 交给 BeautifulSoup(..., "html.parser") 并返回 str(soup)；搜索缺失 API key 时返回中文错误，否则请求 SearchAPI，传入 q、api_key、engine="baidu" 并以 json.dumps(results[:5], ensure_ascii=False) 返回。网络错误必须转为中文结果。

- [ ] 步骤 4：确认通过并提交

运行：uv run pytest tests/test_web_tools.py -v

~~~powershell
git add app/tools/web.py tests/test_web_tools.py
git commit -m "feat: 迁移网络工具"
~~~

### 任务 5：替换注册表并完成回归文档

**文件：**
- 修改：app/tools/registry.py、tests/test_tools.py、docs/step10-local-tools.md

**接口：**
- 产出：get_tool_registry() 仅包含九个 Java 迁移工具。
- 保持：get_tool_definitions() 和 execute_tool() 的公开签名不变。

- [ ] 步骤 1：写入失败测试

~~~python
from app.tools.registry import get_tool_registry


def test_tool_registry_contains_only_migrated_java_tools() -> None:
    assert set(get_tool_registry()) == {
        "read_file",
        "write_file",
        "generate_pdf",
        "download_resource",
        "execute_terminal_command",
        "scrape_web_page",
        "search_web",
        "terminate",
        "get_current_time",
    }
~~~

- [ ] 步骤 2：确认失败

运行：uv run pytest tests/test_tools.py -v

预期：失败，因为注册表仍包含订单和天气工具。

- [ ] 步骤 3：写入最小注册表与文档更新

替换订单、天气导入和注册项为前四个任务产出的工具；无入参工具复用 NoArgs。更新 tests/test_tools.py 的 schema 与分发测试，删除订单、天气断言。将 docs/step10-local-tools.md 改写为九个工具、路径限制、终端白名单、SEARCH_API_KEY 与真实 HTTP/PDF 行为的说明。

- [ ] 步骤 4：运行全量验证并提交

运行：uv run pytest；uv run ruff check app tests

~~~powershell
git add app/tools/registry.py tests/test_tools.py docs/step10-local-tools.md
git commit -m "feat: 注册 Java 迁移工具"
~~~
