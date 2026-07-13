import pytest
from pydantic import ValidationError

from app.tools.registry import (
    ToolNotFoundError,
    execute_tool,
    get_tool_definitions,
    get_tool_registry,
)


MIGRATED_TOOL_NAMES = {
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


def test_tool_registry_contains_only_migrated_java_tools() -> None:
    assert set(get_tool_registry()) == MIGRATED_TOOL_NAMES


def test_tool_definitions_export_all_migrated_tool_names() -> None:
    definitions = get_tool_definitions()

    assert {definition["function"]["name"] for definition in definitions} == MIGRATED_TOOL_NAMES
    assert all(definition["type"] == "function" for definition in definitions)
    assert all(definition["function"]["parameters"]["type"] == "object" for definition in definitions)


def test_execute_tool_validates_arguments_and_dispatches_function(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)

    result = execute_tool("write_file", {"file_name": "note.txt", "content": "内容"})

    assert "写入成功" in result
    assert (tmp_path / "file" / "note.txt").read_text(encoding="utf-8") == "内容"


def test_execute_tool_dispatches_no_argument_tool() -> None:
    assert execute_tool("terminate", {}) == "任务结束"


def test_execute_tool_rejects_invalid_arguments() -> None:
    with pytest.raises(ValidationError):
        execute_tool("write_file", {"file_name": "", "content": "内容"})


def test_execute_tool_rejects_unknown_tool_name() -> None:
    with pytest.raises(ToolNotFoundError):
        execute_tool("unknown_tool", {})
