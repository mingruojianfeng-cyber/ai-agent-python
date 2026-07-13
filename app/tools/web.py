# json 用于把搜索结果列表序列化为工具协议可返回的字符串。
import json
# ipaddress 用于判断 IP 是否为公网地址，是 SSRF 防护的核心标准库。
import ipaddress
# socket 用于把域名解析为实际 IP，防止仅检查域名文本被 DNS 绕过。
import socket
# urlsplit 结构化拆分 URL，不依赖易错的字符串前缀判断。
from urllib.parse import urlsplit

# httpx 是同步 HTTP 客户端；本工具函数当前按同步方式执行。
import httpx
# BeautifulSoup 解析并规范化 HTML 文本。
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.tools.common import resolve_tool_path


# 搜索服务地址、请求超时和下载上限均定义为常量，便于集中审计安全边界。
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
    # getaddrinfo 可返回 IPv4/IPv6 等多条记录，type 限定为 TCP 流式套接字。
    addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    # address[4][0] 是 socket 地址中的 IP；集合去重后再转列表。
    return list({address[4][0] for address in addresses})


def _is_safe_http_url(url: str) -> bool:
    # 先拆分协议、主机、认证信息等字段，再逐项校验。
    parsed = urlsplit(url)
    if (
        # 只允许 HTTP(S)，拒绝 file://、ftp:// 等非网络协议及带认证信息的 URL。
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.hostname.lower() == "localhost"
    ):
        # 任一基础规则不通过即拒绝，后续不会触发 DNS 解析。
        return False
    try:
        # 主机名本身若是 IP，直接标准化为 IP 字符串，无需 DNS 查询。
        addresses = [str(ipaddress.ip_address(parsed.hostname))]
    except ValueError:
        try:
            # 域名需要解析出所有地址，不能只信任第一个结果。
            addresses = _resolve_host_addresses(parsed.hostname)
        except OSError:
            return False
    try:
        # 只有地址非空且全部为公网地址才允许访问，拒绝内网、回环与保留地址。
        return bool(addresses) and all(
            ipaddress.ip_address(address).is_global for address in addresses
        )
    except ValueError:
        return False


def _is_response_too_large(response: httpx.Response) -> bool:
    # Content-Length 是可选响应头，只能作为提前拒绝优化，不能代替流式累计校验。
    content_length = response.headers.get("Content-Length")
    # 服务端声明的长度已超限时无需开始写文件。
    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
        return True
    return False


def download_resource(args: DownloadResourceArgs) -> str:
    """下载资源到 tmp/download。"""
    # 所有外部 URL 入口均先通过 SSRF 校验，再发起网络请求。
    if not _is_safe_http_url(args.url):
        return "下载资源失败：URL 不安全"
    try:
        # 输出路径只允许位于 tmp/download，防止模型借文件名覆盖项目文件。
        path = resolve_tool_path("download", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 再次解析作为 TOCTOU 防护：若路径状态在目录创建后变化则拒绝写入。
        if resolve_tool_path("download", args.file_name) != path:
            return "下载资源失败：路径不安全"
        # stream 不会一次性把响应体加载进内存，适合受限大小的下载。
        with httpx.stream(
            "GET",
            args.url,
            timeout=HTTP_TIMEOUT_SECONDS,
            # 禁止自动跳转，避免安全 URL 重定向到内网地址绕过前置校验。
            follow_redirects=False,
        ) as response:
            # 4xx/5xx 响应转换为 HTTPStatusError，统一由外层捕获。
            response.raise_for_status()
            if _is_response_too_large(response):
                return "下载资源失败：资源超过大小限制"
            # 累计真实接收字节数，防范缺失或伪造 Content-Length 的响应。
            downloaded_bytes = 0
            with path.open("wb") as file:
                # 分块读取并立即写盘，内存占用与资源总大小无关。
                for chunk in response.iter_bytes():
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > MAX_DOWNLOAD_BYTES:
                        # 超限时关闭文件并删除已下载的部分内容，避免留下误导性残文件。
                        file.close()
                        path.unlink(missing_ok=True)
                        return "下载资源失败：资源超过大小限制"
                    file.write(chunk)
        return f"资源下载成功：{path}"
    # 网络、文件系统和路径解析异常均转为稳定的工具返回文本。
    except (httpx.HTTPError, OSError, ValueError):
        return "下载资源失败：请求未成功"


def scrape_web_page(args: ScrapeWebPageArgs) -> str:
    """抓取网页并返回规范化的 HTML 文本。"""
    if not _is_safe_http_url(args.url):
        return "抓取网页失败：URL 不安全"
    try:
        # 页面抓取不跟随重定向，保持与下载工具一致的 SSRF 防护策略。
        response = httpx.get(args.url, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        # 解析后再转回字符串，可得到格式更规范的 HTML 而非原始响应字节。
        return str(BeautifulSoup(response.text, "html.parser"))
    except httpx.HTTPError:
        return "抓取网页失败：请求未成功"


def search_web(args: SearchWebArgs) -> str:
    """调用 SearchAPI 的百度引擎并返回最多五条自然搜索结果。"""
    # 搜索密钥从 Settings 获取，绝不写入源码或工具参数。
    api_key = get_settings().search_api_key
    if not api_key:
        return "搜索失败：未配置 SEARCH_API_KEY"

    try:
        if not _is_safe_http_url(SEARCH_API_URL):
            return "搜索失败：URL 不安全"
        # params 会由 httpx 安全编码为查询字符串，避免手工拼接 URL。
        response = httpx.get(
            SEARCH_API_URL,
            params={"q": args.query, "api_key": api_key, "engine": "baidu"},
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
        response.raise_for_status()
        # 将 JSON 响应转字典，取自然搜索结果；字段缺失时以空列表回退。
        results = response.json().get("organic_results", [])
        if not isinstance(results, list):
            raise ValueError("搜索结果格式不正确")
        # 仅返回前五条控制模型上下文长度；ensure_ascii=False 保留中文可读性。
        return json.dumps(results[:5], ensure_ascii=False)
    except (httpx.HTTPError, ValueError):
        return "搜索失败：请求未成功"
