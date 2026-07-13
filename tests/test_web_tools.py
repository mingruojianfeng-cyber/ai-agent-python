import json

import httpx
import pytest

from app.tools.web import (
    DownloadResourceArgs,
    ScrapeWebPageArgs,
    SearchWebArgs,
    download_resource,
    scrape_web_page,
    search_web,
)


@pytest.fixture(autouse=True)
def mock_public_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.web._resolve_host_addresses",
        lambda host: ["93.184.216.34"],
    )


def test_download_resource_writes_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)

    class Response:
        headers: dict[str, str] = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"data"

    monkeypatch.setattr("app.tools.web.httpx.stream", lambda *args, **kwargs: Response())

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

    monkeypatch.setattr("app.tools.web.httpx.stream", raise_network_error)

    result = download_resource(
        DownloadResourceArgs(url="https://example.com/a", file_name="a.bin")
    )

    assert result.startswith("下载资源失败：")


def test_download_resource_rejects_private_network_url() -> None:
    result = download_resource(
        DownloadResourceArgs(url="http://127.0.0.1/private", file_name="a.bin")
    )

    assert result == "下载资源失败：URL 不安全"


def test_scrape_web_page_rejects_non_http_url() -> None:
    result = scrape_web_page(ScrapeWebPageArgs(url="file:///etc/passwd"))

    assert result == "抓取网页失败：URL 不安全"


def test_search_web_does_not_leak_api_key_in_http_error(monkeypatch) -> None:
    secret = "search-test-secret"
    monkeypatch.setattr(
        "app.tools.web.get_settings",
        lambda: type("Settings", (), {"search_api_key": secret})(),
    )
    monkeypatch.setattr(
        "app.tools.web.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            401,
            request=httpx.Request(
                "GET",
                f"https://www.searchapi.io/api/v1/search?api_key={secret}",
            ),
        ),
    )

    result = search_web(SearchWebArgs(query="Python"))

    assert result == "搜索失败：请求未成功"
    assert secret not in result


def test_download_resource_rejects_content_larger_than_limit(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.MAX_DOWNLOAD_BYTES", 3)

    class Response:
        headers: dict[str, str] = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"data"

    monkeypatch.setattr("app.tools.web.httpx.stream", lambda *args, **kwargs: Response())

    result = download_resource(
        DownloadResourceArgs(url="https://example.com/a", file_name="a.bin")
    )

    assert result == "下载资源失败：资源超过大小限制"


def test_download_resource_stops_when_stream_exceeds_limit(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.MAX_DOWNLOAD_BYTES", 3)

    class Response:
        headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"ab"
            yield b"cd"

    monkeypatch.setattr("app.tools.web.httpx.stream", lambda *args, **kwargs: Response())

    result = download_resource(
        DownloadResourceArgs(url="https://example.com/a", file_name="a.bin")
    )

    assert result == "下载资源失败：资源超过大小限制"
