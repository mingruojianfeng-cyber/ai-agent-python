import pytest
from pydantic import BaseModel, Field, ValidationError

from app.services.structured_output import parse_structured_output


class ExampleItem(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)


class ExampleItems(BaseModel):
    items: list[ExampleItem]


def test_parse_structured_output_validates_model_object() -> None:
    result = parse_structured_output(
        '{"items":[{"name":"rag","score":95},{"name":"tool","score":88}]}',
        ExampleItems,
    )

    assert result.items[0].name == "rag"
    assert result.items[1].score == 88


def test_parse_structured_output_validates_bare_collection_for_internal_use() -> None:
    result = parse_structured_output(
        '[{"name":"mcp","score":91},{"name":"yuagent","score":86}]',
        list[ExampleItem],
    )

    assert [item.name for item in result] == ["mcp", "yuagent"]


def test_parse_structured_output_rejects_invalid_schema() -> None:
    with pytest.raises(ValidationError):
        parse_structured_output('{"items":[{"name":"bad","score":101}]}', ExampleItems)
