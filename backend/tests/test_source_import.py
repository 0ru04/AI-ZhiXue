import asyncio
import socket
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from app.api.dependencies import get_quiz_service, get_source_import_service
from app.core.config import Settings
from app.core.exceptions import SourceImportError
from app.db.session import get_optional_db_session
from app.main import create_app
from app.services.source_import_service import (
    FetchedPage,
    ParsedSource,
    PublicAddressResolver,
    SourceImportService,
    MAX_UPLOAD_BYTES,
    _caption_urls,
    _decode_page,
    extract_pdf,
    extract_word,
    parse_html,
    parse_subtitles,
    validate_public_url,
)


def test_extract_pdf_rejects_empty_text():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "A lesson"})
    output = BytesIO()
    writer.write(output)

    try:
        extract_pdf(output.getvalue())
    except SourceImportError as error:
        assert "未提取到可用文本" in error.message
    else:
        raise AssertionError("A blank PDF must not be accepted as study material")


def test_extract_pdf_reads_metadata_and_page_text():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (A public PDF lesson.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "PDF lesson"})
    output = BytesIO()
    writer.write(output)

    parsed = extract_pdf(output.getvalue())

    assert parsed.title == "PDF lesson"
    assert "A public PDF lesson." in parsed.content


def test_extract_word_preserves_headings_and_paragraphs():
    document = Document()
    document.core_properties.title = "Photosynthesis"
    document.add_heading("Light reactions", level=1)
    document.add_paragraph("Chlorophyll absorbs light energy.")
    output = BytesIO()
    document.save(output)

    parsed = extract_word(output.getvalue())

    assert parsed.title == "Photosynthesis"
    assert "Light reactions" in parsed.content
    assert "Chlorophyll absorbs light energy." in parsed.content
    assert parsed.headings == ["Light reactions"]


def test_document_import_runs_ai_knowledge_extraction():
    document = Document()
    document.add_heading("Light reactions", level=1)
    document.add_paragraph("Chlorophyll absorbs light energy.")
    output = BytesIO()
    document.save(output)
    factory = FakeKnowledgeFactory(["Chlorophyll absorbs light"])
    service = SourceImportService(
        settings=Settings(deepseek_api_key="test-key", content_blocklist=""),
        chain_factory=factory,
    )

    parsed = asyncio.run(service.parse_document("lesson.docx", output.getvalue()))

    assert parsed.knowledge_points == ["Chlorophyll absorbs light"]
    assert factory.calls[0][3].inputs["headings"] == "Light reactions"


def test_parse_html_discards_navigation_and_keeps_article_structure():
    parsed = parse_html(
        """
        <html><head><title>Rayleigh scattering</title></head>
        <body><nav>Home Ads</nav><div class="advertisement">Sponsored offer</div>
        <main><h1>Blue sky</h1>
        <p>Air molecules scatter blue light.</p></main>
        <footer>Copyright</footer></body></html>
        """
    )

    assert parsed.title == "Rayleigh scattering"
    assert parsed.headings == ["Blue sky"]
    assert "Air molecules scatter blue light." in parsed.content
    assert "Home Ads" not in parsed.content
    assert "Sponsored offer" not in parsed.content
    assert "Copyright" not in parsed.content


def test_page_decoder_respects_declared_legacy_charset():
    page = FetchedPage(
        url="https://example.com",
        content_type="text/html",
        body="中文网页".encode("gbk"),
        charset="gbk",
    )

    assert _decode_page(page) == "中文网页"


def test_parse_subtitles_reads_webvtt_cues():
    assert parse_subtitles(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello world.\n"
    ) == "Hello world."


def test_video_page_subtitle_url_is_read_from_public_page_data():
    urls = _caption_urls(
        '<script>window.__INITIAL_STATE__ = {"subtitle":{"list":'
        '[{"subtitle_url":"//captions.example.com/track.json"}]}};</script>',
        "https://www.bilibili.com/video",
    )

    assert urls == ["https://captions.example.com/track.json"]


def test_public_url_validation_rejects_private_and_credentialed_urls():
    for url in (
        "http://127.0.0.1/admin",
        "http://192.168.1.10",
        "http://user:password@example.com/",
    ):
        try:
            validate_public_url(url)
        except SourceImportError:
            continue
        raise AssertionError(f"Unsafe URL was accepted: {url}")


def test_public_url_validation_accepts_https_host():
    assert validate_public_url("https://example.com/article").hostname == "example.com"


def test_document_import_rejects_files_over_the_limit():
    service = SourceImportService()

    with pytest.raises(SourceImportError, match="20MB"):
        asyncio.run(
            service.parse_document("lesson.pdf", bytes(MAX_UPLOAD_BYTES + 1))
        )


def test_public_dns_resolver_rejects_private_addresses(monkeypatch):
    class FakeLoop:
        async def getaddrinfo(self, *args, **kwargs):
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("127.0.0.1", 443),
                )
            ]

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())
    resolver = PublicAddressResolver()

    with pytest.raises(SourceImportError, match="公开地址"):
        asyncio.run(resolver.resolve("example.com", 443, socket.AF_INET))


class FakeKnowledgeChain:
    def __init__(self, points):
        self.points = points
        self.inputs = None

    async def ainvoke(self, inputs):
        self.inputs = inputs
        return {"knowledge_points": self.points}


class FakeKnowledgeFactory:
    def __init__(self, points):
        self.points = points
        self.calls = []

    def __call__(self, schema, prompt, temperature):
        chain = FakeKnowledgeChain(self.points)
        self.calls.append((schema, prompt, temperature, chain))
        return chain


def test_parse_url_extracts_public_article_content():
    async def fetcher(url: str, *, max_bytes: int = 0) -> FetchedPage:
        return FetchedPage(
            url=url,
            content_type="text/html",
            body=b"<html><title>Science</title><main><h1>Light</h1><p>Light travels in waves.</p></main></html>",
        )

    factory = FakeKnowledgeFactory(["Light travels in waves"])
    parsed = asyncio.run(
        SourceImportService(
            fetcher=fetcher,
            settings=Settings(deepseek_api_key="test-key", content_blocklist=""),
            chain_factory=factory,
        ).parse_url("https://example.com/article")
    )

    assert parsed.source_type == "web"
    assert parsed.title == "Science"
    assert "Light travels in waves." in parsed.content
    assert parsed.knowledge_points == ["Light travels in waves"]
    assert factory.calls[0][3].inputs["headings"] == "Light"


def test_parse_url_uses_public_video_subtitles_only():
    async def fetcher(url: str, *, max_bytes: int = 0) -> FetchedPage:
        if url.endswith("/video"):
            body = b'<html><head><title>Lesson</title></head><body><track kind="captions" src="/captions.vtt"></body></html>'
            content_type = "text/html"
        else:
            body = b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nA useful video transcript."
            content_type = "text/vtt"
        return FetchedPage(url=url, content_type=content_type, body=body)

    parsed = asyncio.run(
        SourceImportService(
            fetcher=fetcher,
            settings=Settings(deepseek_api_key="test-key", content_blocklist=""),
            chain_factory=FakeKnowledgeFactory(["Video summary"]),
        ).parse_url(
            "https://www.bilibili.com/video"
        )
    )

    assert parsed.source_type == "video"
    assert parsed.title == "Lesson"
    assert parsed.content == "A useful video transcript."


def test_parse_video_url_without_public_subtitles_fails_explicitly():
    async def fetcher(url: str, *, max_bytes: int = 0) -> FetchedPage:
        return FetchedPage(
            url=url,
            content_type="text/html",
            body=b"<html><title>Lesson</title><p>Some video description</p></html>",
        )

    try:
        asyncio.run(
            SourceImportService(fetcher=fetcher).parse_url(
                "https://www.douyin.com/video"
            )
        )
    except SourceImportError as error:
        assert "不支持无字幕视频" in error.message
    else:
        raise AssertionError("A video without public subtitles must fail clearly")


class FakeSourceImportService:
    async def parse_document(self, filename: str, content: bytes) -> ParsedSource:
        assert filename == "notes.docx"
        assert content == b"docx"
        return ParsedSource(
            source_type="document",
            title="Study notes",
            content="Important learning material.",
            headings=["Key idea"],
            knowledge_points=["Key idea"],
            source_url=None,
        )

    async def parse_url(self, url: str) -> ParsedSource:
        return ParsedSource(
            source_type="web",
            title="Public article",
            content="Article content.",
            headings=["Section"],
            knowledge_points=["Section"],
            source_url=url,
        )


def test_document_parse_route_rejects_unsupported_word_format():
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/source/parse/document",
            files={"file": ("notes.doc", b"legacy Word", "application/msword")},
        )

    assert response.status_code == 400
    assert response.json()["data"] is None


def test_document_parse_route_returns_extracted_material():
    app = create_app()
    app.dependency_overrides[get_source_import_service] = (
        lambda: FakeSourceImportService()
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/source/parse/document",
            data={"file_name": "notes.docx"},
            files={"file": ("upload", b"docx", "application/octet-stream")},
        )

    assert response.status_code == 200
    assert response.json()["data"]["knowledge_points"] == ["Key idea"]


def test_url_parse_route_returns_standard_envelope():
    app = create_app()
    app.dependency_overrides[get_source_import_service] = (
        lambda: FakeSourceImportService()
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/source/parse/url",
            json={"url": "https://example.com/article"},
        )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["source_type"] == "web"


def test_source_generation_route_uses_polling_task_and_confirmed_points(
    quiz,
    task_database,
):
    class FakeSourceQuizService:
        async def generate_from_source(
            self,
            *,
            source_type: str,
            title: str,
            content: str,
            knowledge_points: list[str],
        ):
            assert title == "Public article"
            assert content == "Article content."
            assert knowledge_points == ["Section"]
            return quiz.model_copy(
                update={
                    "source_type": source_type,
                    "user_input": "网页：Public article",
                }
            )

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_quiz_service] = FakeSourceQuizService
    app.dependency_overrides[get_optional_db_session] = task_database.dependency
    app.state.db_session_factory = task_database.session_factory

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/source/generate",
            json={
                "source_type": "web",
                "title": "Public article",
                "content": "Article content.",
                "headings": ["Section"],
                "knowledge_points": ["Section"],
            },
        )
        assert created.status_code == 200
        task_id = created.json()["data"]["task_id"]
        response = client.get(f"/api/v1/quiz/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "completed"
    assert response.json()["data"]["quiz"]["source_type"] == "web"
    assert response.json()["data"]["quiz"]["user_input"] == "网页：Public article"
