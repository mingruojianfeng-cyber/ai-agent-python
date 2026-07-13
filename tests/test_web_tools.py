import json

import httpx

from app.tools.web import (
    DownloadResourceArgs,
    ScrapeWebPageArgs,
    SearchWebArgs,
    download_resource,
    scrape_web_page,
    search_web,
)


def test_download_resource_writes_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            200,
            content=b"data",
            request=httpx.Request("GET", "https://example.com/a"),
        ),
    )

    result = download_resource(
        DownloadResourceArgs(url="https://example.com/a", file_name="a.bin")
    )

    assert "下载成功" in result
    assert (tmp_path / "download" / "a.bin").read_bytes() == b"data"


def test_scrape_web_page_returns_html(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            200,
            text="<main><h1>标题</h1></main>",
            request=httpx.Request("GET", "https://example.com"),
        ),
    )

    result = scrape_web_page(ScrapeWebPageArgs(url="https://example.com"))

    assert "<h1>标题</h1>" in result


def test_search_web_returns_at_most_five_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.web.get_settings",
        lambda: type("Settings", (), {"search_api_key": "key"})(),
    )
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={"organic_results": [{"n": index} for index in range(6)]},
            request=httpx.Request("GET", "https://www.searchapi.io/api/v1/search"),
        ),
    )

    result = search_web(SearchWebArgs(query="Python"))

    assert json.loads(result) == [{"n": index} for index in range(5)]


def test_search_web_returns_error_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.web.get_settings",
        lambda: type("Settings", (), {"search_api_key": ""})(),
    )

    result = search_web(SearchWebArgs(query="Python"))

    assert result == "搜索失败：未配置 SEARCH_API_KEY"


def test_download_resource_returns_error_on_network_failure(monkeypatch) -> None:
    def raise_network_error(*args, **kwargs):
        raise httpx.ConnectError("网络不可用")

    monkeypatch.setattr("app.tools.web.httpx.get", raise_network_error)

    result = download_resource(
        DownloadResourceArgs(url="https://example.com/a", file_name="a.bin")
    )

    assert result.startswith("下载资源失败：")
