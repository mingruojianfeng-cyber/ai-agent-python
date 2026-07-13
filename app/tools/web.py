import json

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.tools.common import resolve_tool_path


SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"
HTTP_TIMEOUT_SECONDS = 10


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


def download_resource(args: DownloadResourceArgs) -> str:
    """下载资源到 tmp/download。"""
    try:
        response = httpx.get(args.url, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        path = resolve_tool_path("download", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        return f"资源下载成功：{path}"
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return f"下载资源失败：{exc}"


def scrape_web_page(args: ScrapeWebPageArgs) -> str:
    """抓取网页并返回规范化的 HTML 文本。"""
    try:
        response = httpx.get(args.url, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return str(BeautifulSoup(response.text, "html.parser"))
    except httpx.HTTPError as exc:
        return f"抓取网页失败：{exc}"


def search_web(args: SearchWebArgs) -> str:
    """调用 SearchAPI 的百度引擎并返回最多五条自然搜索结果。"""
    api_key = get_settings().search_api_key
    if not api_key:
        return "搜索失败：未配置 SEARCH_API_KEY"

    try:
        response = httpx.get(
            SEARCH_API_URL,
            params={"q": args.query, "api_key": api_key, "engine": "baidu"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json().get("organic_results", [])
        if not isinstance(results, list):
            raise ValueError("搜索结果格式不正确")
        return json.dumps(results[:5], ensure_ascii=False)
    except (httpx.HTTPError, ValueError) as exc:
        return f"搜索失败：{exc}"
