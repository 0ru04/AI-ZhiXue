import asyncio
import codecs
import ipaddress
import json
import re
import socket
import zipfile
from dataclasses import dataclass, replace
from io import BytesIO
from logging import getLogger
from pathlib import PurePath
from typing import Callable
from urllib.parse import SplitResult, urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver
from bs4 import BeautifulSoup
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pydantic import ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIProviderError,
    ContentBlockedError,
    LLMConfigurationError,
    SourceImportError,
)
from app.llm.factory import create_structured_chain
from app.models.source_knowledge import KnowledgePointsOutput
from app.prompts.source_knowledge_prompt import SOURCE_KNOWLEDGE_PROMPT
from app.utils.content_filter import ensure_content_allowed


logger = getLogger(__name__)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FETCH_BYTES = 2 * 1024 * 1024
MAX_SOURCE_CHARS = 30_000
MAX_PDF_PAGES = 30
MAX_REDIRECTS = 3
VIDEO_HOSTS = {
    "bilibili.com",
    "b23.tv",
    "douyin.com",
    "iesdouyin.com",
    "channels.weixin.qq.com",
    "finder.video.qq.com",
}
IGNORED_HTML_TAGS = ("script", "style", "nav", "header", "footer", "aside", "noscript")
AD_MARKER = re.compile(r"(?:^|[-_])(ad|ads|advert|advertisement|sponsor)(?:$|[-_])", re.I)
SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx"}


@dataclass(frozen=True)
class ParsedSource:
    source_type: str
    title: str
    content: str
    headings: list[str]
    knowledge_points: list[str]
    source_url: str | None


@dataclass(frozen=True)
class FetchedPage:
    url: str
    content_type: str
    body: bytes
    charset: str | None = None


def validate_public_url(value: str) -> SplitResult:
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as error:
        raise SourceImportError("链接格式不正确") from error

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 80, 443}
    ):
        raise SourceImportError("仅支持公开的 HTTP/HTTPS 网页链接")

    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return parsed
    if not address.is_global:
        raise SourceImportError("链接目标不是公开地址")
    return parsed


class PublicAddressResolver(AbstractResolver):
    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: int = socket.AF_INET,
    ) -> list[dict[str, object]]:
        try:
            records = await asyncio.get_running_loop().getaddrinfo(
                host,
                port,
                family=family,
                type=socket.SOCK_STREAM,
            )
        except OSError as error:
            raise SourceImportError("无法解析网页地址") from error

        resolved: list[dict[str, object]] = []
        for address_family, _, protocol, _, address in records:
            ip = ipaddress.ip_address(address[0])
            if not ip.is_global:
                raise SourceImportError("链接目标不是公开地址")
            resolved.append(
                {
                    "hostname": host,
                    "host": address[0],
                    "port": port,
                    "family": address_family,
                    "proto": protocol,
                    "flags": socket.AI_NUMERICHOST,
                }
            )
        if not resolved:
            raise SourceImportError("无法解析网页地址")
        return resolved

    async def close(self) -> None:
        return None


def _clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    text = "\n".join(line for line in lines if line).strip()
    if len(text) > MAX_SOURCE_CHARS:
        raise SourceImportError(
            "提取内容超过 30,000 字，请拆分材料后重新导入"
        )
    return text


def _decode_page(page: FetchedPage) -> str:
    charset = page.charset
    if not charset:
        match = re.search(
            br"<meta[^>]+charset\s*=\s*[\"']?\s*([a-zA-Z0-9._-]+)",
            page.body[:2048],
            re.IGNORECASE,
        )
        if match:
            charset = match.group(1).decode("ascii")
    if charset:
        try:
            codecs.lookup(charset)
        except LookupError:
            charset = None
    return page.body.decode(charset or "utf-8", errors="replace")


def _candidate_points(headings: list[str], content: str) -> list[str]:
    candidates: list[str] = []
    for value in [*headings, *re.split(r"(?<=[。！？.!?])\s*", content)]:
        point = re.sub(r"\s+", " ", value).strip(" \t\r\n-•·")
        if len(point) < 4 or point in candidates:
            continue
        candidates.append(point[:80])
        if len(candidates) == 10:
            break
    if not candidates and content.strip():
        candidates.append(content.strip()[:80])
    return candidates


def _parsed_source(
    source_type: str,
    title: str,
    content: str,
    headings: list[str],
    source_url: str | None = None,
) -> ParsedSource:
    clean_content = _clean_text(content)
    if not clean_content:
        raise SourceImportError("未提取到可用文本，请更换材料后重试")
    clean_headings = list(dict.fromkeys(
        heading.strip()[:120] for heading in headings if heading.strip()
    ))[:30]
    return ParsedSource(
        source_type=source_type,
        title=title.strip()[:120] or "未命名学习材料",
        content=clean_content,
        headings=clean_headings,
        knowledge_points=_candidate_points(clean_headings, clean_content),
        source_url=source_url,
    )


def extract_pdf(content: bytes) -> ParsedSource:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise SourceImportError("PDF 已加密，暂不支持解析")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise SourceImportError(
                "PDF 超过 30 页处理范围，请拆分文档或仅上传前 30 页"
            )
        page_count = min(len(reader.pages), MAX_PDF_PAGES)
        page_text = [
            reader.pages[index].extract_text() or ""
            for index in range(page_count)
        ]
        title = str((reader.metadata or {}).title or "")
        headings = _pdf_outline_titles(reader.outline)
    except SourceImportError:
        raise
    except (PdfReadError, ValueError, OSError) as error:
        raise SourceImportError("PDF 文件损坏或格式不受支持") from error

    return _parsed_source("document", title, "\n".join(page_text), headings)


def _pdf_outline_titles(outline: list) -> list[str]:
    titles: list[str] = []
    for item in outline:
        if isinstance(item, list):
            titles.extend(_pdf_outline_titles(item))
        elif getattr(item, "title", None):
            titles.append(item.title)
    return titles


def extract_word(content: bytes) -> ParsedSource:
    try:
        document = Document(BytesIO(content))
    except (PackageNotFoundError, ValueError, zipfile.BadZipFile, KeyError) as error:
        raise SourceImportError("Word 文件损坏或格式不受支持") from error

    paragraphs: list[str] = []
    headings: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        paragraphs.append(text)
        if paragraph.style and (
            paragraph.style.name == "Title"
            or paragraph.style.name.startswith("Heading")
        ):
            headings.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    title = document.core_properties.title or ""
    return _parsed_source("document", title, "\n".join(paragraphs), headings)


def _html_metadata(soup: BeautifulSoup) -> tuple[str, list[str]]:
    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = (
        title_tag.get("content", "").strip()
        if title_tag is not None
        else (soup.title.get_text(" ", strip=True) if soup.title else "")
    )
    removals = []
    for tag in soup.find_all(True):
        classes = tag.get("class", []) or []
        label = str(tag.get("id", "")) + " " + " ".join(classes)
        aria_label = str(tag.get("aria-label", ""))
        if (
            tag.name in IGNORED_HTML_TAGS
            or tag.has_attr("hidden")
            or tag.get("aria-hidden") == "true"
            or AD_MARKER.search(label)
            or "广告" in aria_label
        ):
            removals.append(tag)
    for tag in removals:
        if tag.parent is not None:
            tag.decompose()
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2", "h3"])
    ]
    return title, headings


def parse_html(markup: str, source_url: str | None = None) -> ParsedSource:
    soup = BeautifulSoup(markup, "html.parser")
    title, headings = _html_metadata(soup)
    article = soup.find("article") or soup.find("main") or soup.body or soup
    content = article.get_text("\n", strip=True)
    return _parsed_source("web", title, content, headings, source_url)


def parse_subtitles(payload: str) -> str:
    text = payload.lstrip("\ufeff").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        cues = data.get("body") or data.get("events") or data.get("segments")
        if isinstance(cues, list):
            values = [
                cue.get("content") or cue.get("text") or ""
                for cue in cues
                if isinstance(cue, dict)
            ]
            return _clean_text("\n".join(values))

    lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if (
            not line
            or line.upper() == "WEBVTT"
            or line.isdigit()
            or "-->" in line
            or line.startswith(("NOTE ", "STYLE"))
        ):
            continue
        lines.append(re.sub(r"<[^>]+>", "", line))
    return _clean_text("\n".join(lines))


def _is_video_host(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    return any(host == domain or host.endswith(f".{domain}") for domain in VIDEO_HOSTS)


def _caption_urls(markup: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(markup, "html.parser")
    urls = [
        urljoin(page_url, str(track["src"]))
        for track in soup.find_all("track")
        if track.get("src")
        and str(track.get("kind", "")).lower() in {"captions", "subtitles"}
    ]
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text()
        if not script_text or "subtitle" not in script_text.lower():
            continue
        json_start = script_text.find("{")
        json_end = script_text.rfind("}")
        if json_start < 0 or json_end <= json_start:
            continue
        try:
            payload = json.loads(script_text[json_start : json_end + 1])
        except json.JSONDecodeError:
            continue
        urls.extend(
            urljoin(page_url, caption_url)
            for caption_url in _find_caption_urls(payload)
        )
    return list(dict.fromkeys(urls))


def _find_caption_urls(value: object) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, item in value.items():
            if (
                key.lower() in {"subtitle_url", "subtitleurl"}
                and isinstance(item, str)
                and item.strip()
            ):
                found.append(item.strip())
            else:
                found.extend(_find_caption_urls(item))
        return found
    if isinstance(value, list):
        return [
            caption_url
            for item in value
            for caption_url in _find_caption_urls(item)
        ]
    return []


async def fetch_public_page(
    value: str,
    *,
    max_bytes: int = MAX_FETCH_BYTES,
) -> FetchedPage:
    current_url = value
    timeout = aiohttp.ClientTimeout(total=12, connect=5, sock_read=8)
    headers = {"User-Agent": "AIStudyLearning/1.0", "Accept": "text/html,*/*;q=0.5"}
    for redirect_count in range(MAX_REDIRECTS + 1):
        validate_public_url(current_url)
        connector = aiohttp.TCPConnector(
            resolver=PublicAddressResolver(),
            use_dns_cache=False,
            limit=4,
        )
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=False,
            ) as session:
                async with session.get(
                    current_url,
                    allow_redirects=False,
                    headers=headers,
                ) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_count == MAX_REDIRECTS:
                            raise SourceImportError("网页跳转次数过多或地址无效")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status < 200 or response.status >= 300:
                        raise SourceImportError("网页暂时无法访问，请检查链接后重试")
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        try:
                            declared_length = int(content_length)
                        except ValueError as error:
                            raise SourceImportError("网页响应格式无效") from error
                        if declared_length > max_bytes:
                            raise SourceImportError("网页内容过大，暂不支持解析")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise SourceImportError("网页内容过大，暂不支持解析")
                    return FetchedPage(
                        url=str(response.url),
                        content_type=response.headers.get("Content-Type", ""),
                        body=bytes(body),
                        charset=response.charset,
                    )
        except SourceImportError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as error:
            raise SourceImportError("网页抓取失败，请稍后重试或更换链接") from error
    raise SourceImportError("网页跳转次数过多或地址无效")


class SourceImportService:
    def __init__(
        self,
        fetcher=fetch_public_page,
        settings: Settings | None = None,
        chain_factory: Callable = create_structured_chain,
    ) -> None:
        self.fetcher = fetcher
        self.settings = settings or get_settings()
        self.chain_factory = chain_factory

    async def _extract_knowledge_points(
        self,
        source: ParsedSource,
    ) -> ParsedSource:
        ensure_content_allowed(
            [source.title, source.content],
            self.settings.blocked_terms,
        )
        last_error: Exception | None = None
        for attempt in range(1, self.settings.llm_max_attempts + 1):
            try:
                chain = self.chain_factory(
                    KnowledgePointsOutput,
                    SOURCE_KNOWLEDGE_PROMPT,
                    0.2,
                )
                result = await chain.ainvoke(
                    {
                        "title": source.title,
                        "headings": "、".join(source.headings),
                        "content": source.content,
                    }
                )
                output = KnowledgePointsOutput.model_validate(result)
                ensure_content_allowed(
                    output.knowledge_points,
                    self.settings.blocked_terms,
                )
                return replace(source, knowledge_points=output.knowledge_points)
            except (ContentBlockedError, LLMConfigurationError):
                raise
            except (ValidationError, ValueError) as error:
                last_error = error
                logger.warning(
                    "Source knowledge point output failed validation on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                    exc_info=True,
                )
            except Exception as error:
                last_error = error
                logger.exception(
                    "Source knowledge point extraction failed on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                )
        raise AIProviderError() from last_error

    async def parse_document(self, filename: str, content: bytes) -> ParsedSource:
        if len(content) > MAX_UPLOAD_BYTES:
            raise SourceImportError("单个文件不能超过 20MB", status_code=413)
        extension = PurePath(filename.replace("\\", "/")).suffix.lower()
        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise SourceImportError("仅支持 PDF 和 .docx 文件，旧版 .doc 暂不支持")
        if extension == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise SourceImportError("文件内容与 PDF 格式不匹配")
            parsed = extract_pdf(content)
        else:
            if not content.startswith(b"PK"):
                raise SourceImportError("文件内容与 .docx 格式不匹配")
            parsed = extract_word(content)
        if parsed.title == "未命名学习材料":
            fallback_title = PurePath(filename.replace("\\", "/")).stem
            parsed = replace(parsed, title=fallback_title or parsed.title)
        return await self._extract_knowledge_points(parsed)

    async def parse_url(self, value: str) -> ParsedSource:
        validate_public_url(value)
        page = await self.fetcher(value)
        if "html" not in page.content_type.lower():
            raise SourceImportError("链接不是可读取的网页内容")
        markup = _decode_page(page)
        hostname = urlsplit(page.url).hostname or ""
        if not _is_video_host(hostname):
            return await self._extract_knowledge_points(parse_html(markup, page.url))

        for caption_url in _caption_urls(markup, page.url):
            validate_public_url(caption_url)
            caption = await self.fetcher(caption_url, max_bytes=MAX_FETCH_BYTES)
            transcript = parse_subtitles(_decode_page(caption))
            if transcript:
                video_title, headings = _html_metadata(
                    BeautifulSoup(markup, "html.parser")
                )
                return await self._extract_knowledge_points(
                    _parsed_source(
                        "video",
                        video_title,
                        transcript,
                        headings,
                        page.url,
                    )
                )
        raise SourceImportError(
            "未找到无需登录即可读取的字幕；当前暂不支持无字幕视频"
        )
