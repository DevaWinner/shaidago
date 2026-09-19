"""Inert text extraction from fetched public pages, with provenance.

Fetched material is untrusted data. Extraction keeps only visible text: scripts, styles,
templates, frames, forms, SVG, hidden elements, and comments are discarded, and nothing in the page
has any authority over the system. Text that looks like an instruction to a model is *flagged*, not
obeyed, so later stages can treat the page with extra caution. Only a short excerpt and a content
hash are kept, never the full page, and every date is recorded with where it came from and whether
sources disagree.
"""

import contextlib
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Final
from urllib.parse import urlsplit

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from shaidago.discovery.dedupe import canonical_url, content_sha256, simhash64

EXTRACTION_VERSION: Final = "extract-v1"
MAX_TEXT_CHARS: Final = 60_000
EXCERPT_CHARS: Final = 1200
MAX_PDF_PAGES: Final = 12
_SKIP: Final = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "iframe",
        "object",
        "embed",
        "form",
        "svg",
        "select",
        "textarea",
        "button",
        "head",
        "canvas",
        "audio",
        "video",
        "nav",
        "footer",
    }
)
_VOID: Final = frozenset(
    {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "base", "col"}
)
_BLOCK: Final = frozenset(
    {
        "p", "div", "section", "article", "li", "ul", "ol", "tr", "table", "h1", "h2", "h3",
        "h4", "h5", "h6", "blockquote", "pre", "main", "aside", "header",
    }
)  # fmt: skip
_HIDDEN_STYLE: Final = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0", re.I
)
_INJECTION: Final = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) (?:instructions|prompts?)|disregard (?:the )?"
    r"(?:above|previous|system)|system prompt|you are (?:now )?(?:an? )?(?:ai|assistant|chatbot)|"
    r"(?:reveal|print|output) (?:your|the) (?:instructions|prompt)|new instructions:|"
    r"act as (?:an? )?(?:system|admin)",
    re.I,
)
_ISO_DATE: Final = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_PDF_DATE: Final = re.compile(r"D:(\d{4})(\d{2})(\d{2})")


class ExtractionError(Exception):
    """A page could not be turned into inert text. ``code`` is stable and content-free."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DateClaim:
    value: date
    provenance: str


@dataclass(frozen=True)
class ExtractedPage:
    canonical_url: str
    publisher_domain: str
    title: str | None
    excerpt: str
    text_sha256: str
    simhash: int
    published_on: date | None
    published_provenance: str
    date_conflict: bool
    content_type: str
    injection_flag: bool
    preliminary_type: str
    extraction_version: str
    char_count: int


class _Visible(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: str | None = None
        self.canonical: str | None = None
        self.dates: list[DateClaim] = []
        self._skip_depth = 0
        self._stack: list[bool] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        self._metadata(tag, values)
        if tag in _VOID:
            return
        hidden = (
            tag in _SKIP
            or "hidden" in values
            or values.get("aria-hidden", "").lower() == "true"
            or bool(_HIDDEN_STYLE.search(values.get("style", "")))
        )
        self._stack.append(hidden)
        self._skip_depth += hidden
        if tag == "title":
            self._in_title = True
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID or not self._stack:
            return
        self._skip_depth -= self._stack.pop()
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title and self.title is None and data.strip():
            self.title = " ".join(data.split())[:300]
        if self._skip_depth == 0 and not self._in_title:
            self.parts.append(data)

    def _metadata(self, tag: str, values: dict[str, str]) -> None:
        if tag == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href") or None
        if tag == "meta":
            name = (values.get("property") or values.get("name") or "").lower()
            if name in {"article:published_time", "date", "dc.date", "citation_publication_date"}:
                self._claim(values.get("content", ""), "meta_published")
        if tag == "time" and "datetime" in values:
            self._claim(values["datetime"], "time_element")

    def _claim(self, raw: str, provenance: str) -> None:
        match = _ISO_DATE.search(raw)
        if match is None:
            return
        try:
            self.dates.append(DateClaim(date(*(int(g) for g in match.groups())), provenance))
        except ValueError:
            return


def _collapse(parts: list[str]) -> str:
    # Control and format characters (NUL, bidi overrides, zero-width joiners) carry no meaning here.
    text = "".join(
        ch
        for ch in "".join(parts)
        if ch in "\n\t" or unicodedata.category(ch) not in {"Cc", "Cf", "Cs"}
    )
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)[:MAX_TEXT_CHARS]


def _preliminary_type(domain: str) -> str:
    """A first guess from the domain alone. It is never a verification of anything."""
    if domain.endswith((".gov.ng", ".gov", ".gov.uk")) or ".gov." in domain:
        return "government_publication"
    if domain.endswith((".edu", ".ac.uk", ".edu.ng")):
        return "civic_research"
    return "other_public_source"


def _resolve_dates(claims: list[DateClaim]) -> tuple[date | None, str, bool]:
    if not claims:
        return None, "none", False
    distinct = {c.value for c in claims}
    first = claims[0]
    return first.value, first.provenance, len(distinct) > 1


def _finish(  # noqa: PLR0913 - one page's provenance fields, named explicitly
    text: str, *, url: str, title: str | None, claims: list[DateClaim], content_type: str,
    canonical: str | None,
) -> ExtractedPage:  # fmt: skip
    if not text.strip():
        raise ExtractionError("no_text")
    final = canonical_url(url)
    chosen = canonical_url(canonical) if canonical and _same_site(canonical, url) else final
    published, provenance, conflict = _resolve_dates(claims)
    domain = (urlsplit(final).hostname or "").lower()
    return ExtractedPage(
        canonical_url=chosen,
        publisher_domain=domain,
        title=title,
        excerpt=text[:EXCERPT_CHARS],
        text_sha256=content_sha256(text),
        simhash=simhash64(text),
        published_on=published,
        published_provenance=provenance,
        date_conflict=conflict,
        content_type=content_type,
        injection_flag=bool(_INJECTION.search(text)),
        preliminary_type=_preliminary_type(domain),
        extraction_version=EXTRACTION_VERSION,
        char_count=len(text),
    )


def _same_site(canonical: str, url: str) -> bool:
    """A page may name its own canonical URL, but only on its own host."""
    try:
        return (urlsplit(canonical).hostname or "").lower() == (
            urlsplit(url).hostname or ""
        ).lower()
    except ValueError:
        return False


def extract_html(body: bytes, url: str) -> ExtractedPage:
    parser = _Visible()
    try:
        parser.feed(body.decode("utf-8", "replace"))
        parser.close()
    except AssertionError, ValueError:
        raise ExtractionError("malformed_html") from None
    return _finish(
        _collapse(parser.parts), url=url, title=parser.title, claims=parser.dates,
        content_type="text/html", canonical=parser.canonical,
    )  # fmt: skip


def extract_pdf(body: bytes, url: str) -> ExtractedPage:
    try:
        reader = PdfReader(io.BytesIO(body))
        if reader.is_encrypted:
            raise ExtractionError("encrypted_pdf")
        pages = [(page.extract_text() or "") for page in reader.pages[:MAX_PDF_PAGES]]
        info = reader.metadata
        title = str(info.title)[:300] if info is not None and info.title else None
        raw_date = str(info.get("/CreationDate", "")) if info is not None else ""
    except ExtractionError:
        raise
    except PyPdfError, ValueError, KeyError, OSError, RecursionError:
        raise ExtractionError("malformed_pdf") from None
    claims: list[DateClaim] = []
    match = _PDF_DATE.search(raw_date)
    if match is not None:
        with contextlib.suppress(ValueError):  # an impossible date is simply not a claim
            claims.append(DateClaim(date(*(int(g) for g in match.groups())), "pdf_metadata"))
    return _finish(
        _collapse(["\n".join(pages)]), url=url, title=title, claims=claims,
        content_type="application/pdf", canonical=None,
    )  # fmt: skip


def extract_text(body: bytes, url: str) -> ExtractedPage:
    return _finish(
        _collapse([body.decode("utf-8", "replace")]), url=url, title=None, claims=[],
        content_type="text/plain", canonical=None,
    )  # fmt: skip


def extract(content_type: str, body: bytes, url: str) -> ExtractedPage:
    """Dispatch on the (already allowlisted) content type."""
    if content_type in {"text/html", "application/xhtml+xml"}:
        return extract_html(body, url)
    if content_type == "application/pdf":
        return extract_pdf(body, url)
    if content_type == "text/plain":
        return extract_text(body, url)
    raise ExtractionError("unsupported_content_type")
