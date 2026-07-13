import json
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.tools.common import resolve_tool_path


SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"
HTTP_TIMEOUT_SECONDS = 10
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024


class DownloadResourceArgs(BaseModel):
    """下载资源工具的入参。"""

    url: str = Field(min_length=1, description="要下载资源的 URL")
    file_name: str = Field(min_length=1, description="保存资源的文件名")


class ScrapeWebPageArgs(BaseModel):
    """网页抓取工具的入参。"""

    url: str = Field(min_length=1, description="要抓取网页的 URL")


class SearchWebArgs(BaseModel):
    """网页搜索工具的入参。"""

    query: str = Field(min_length=1, description="搜索关键词")


def _resolve_host_addresses(host: str) -> list[str]:
    addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return list({address[4][0] for address in addresses})


def _is_safe_http_url(url: str) -> bool:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.hostname.lower() == "localhost"
    ):
        return False
    try:
        addresses = [str(ipaddress.ip_address(parsed.hostname))]
    except ValueError:
        try:
            addresses = _resolve_host_addresses(parsed.hostname)
        except OSError:
            return False
    try:
        return bool(addresses) and all(
            ipaddress.ip_address(address).is_global for address in addresses
        )
    except ValueError:
        return False


def _is_response_too_large(response: httpx.Response) -> bool:
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
        return True
    return len(response.content) > MAX_DOWNLOAD_BYTES


def download_resource(args: DownloadResourceArgs) -> str:
    """下载资源到 tmp/download。"""
    if not _is_safe_http_url(args.url):
        return "下载资源失败：URL 不安全"
    try:
        response = httpx.get(args.url, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        if _is_response_too_large(response):
            return "下载资源失败：资源超过大小限制"
        path = resolve_tool_path("download", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        return f"资源下载成功：{path}"
    except (httpx.HTTPError, OSError, ValueError):
        return "下载资源失败：请求未成功"


def scrape_web_page(args: ScrapeWebPageArgs) -> str:
    """抓取网页并返回规范化的 HTML 文本。"""
    if not _is_safe_http_url(args.url):
        return "抓取网页失败：URL 不安全"
    try:
        response = httpx.get(args.url, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        return str(BeautifulSoup(response.text, "html.parser"))
    except httpx.HTTPError:
        return "抓取网页失败：请求未成功"


def search_web(args: SearchWebArgs) -> str:
    """调用 SearchAPI 的百度引擎并返回最多五条自然搜索结果。"""
    api_key = get_settings().search_api_key
    if not api_key:
        return "搜索失败：未配置 SEARCH_API_KEY"

    try:
        if not _is_safe_http_url(SEARCH_API_URL):
            return "搜索失败：URL 不安全"
        response = httpx.get(
            SEARCH_API_URL,
            params={"q": args.query, "api_key": api_key, "engine": "baidu"},
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
        response.raise_for_status()
        results = response.json().get("organic_results", [])
        if not isinstance(results, list):
            raise ValueError("搜索结果格式不正确")
        return json.dumps(results[:5], ensure_ascii=False)
    except (httpx.HTTPError, ValueError):
        return "搜索失败：请求未成功"
