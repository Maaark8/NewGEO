from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .content import normalize_markdown


DEFAULT_IGNORED_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


@dataclass(slots=True)
class CrawlSeed:
    url: str
    label: str | None = None


@dataclass(slots=True)
class CrawlRequest:
    project_id: str
    base_url: str | None = None
    seeds: list[CrawlSeed] = field(default_factory=list)
    max_pages: int = 25
    max_depth: int = 1
    same_domain_only: bool = True
    include_sitemap_variants: bool = True
    fetch_live_urls: bool = False
    raw_html_by_url: dict[str, str] = field(default_factory=dict)
    markdown_by_url: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IngestedPage:
    url: str
    title: str
    markdown: str
    source: str = "manual"
    content_type: str = "docs_article"


def normalize_url(url: str, base_url: str | None = None, keep_fragment: bool = False) -> str:
    """Return a canonical, comparison-friendly URL string."""
    resolved = urljoin(base_url, url) if base_url else url
    parsed = urlparse(resolved.strip())

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_items = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in DEFAULT_IGNORED_QUERY_KEYS]
    query = urlencode(sorted(query_items))
    fragment = parsed.fragment if keep_fragment else ""
    return urlunparse((scheme, netloc, path, "", query, fragment))


def root_domain(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    return f"{parsed.scheme}://{parsed.netloc}"


def same_domain(url: str, base_url: str) -> bool:
    return urlparse(normalize_url(url)).netloc == urlparse(normalize_url(base_url)).netloc


def sitemap_seed_variants(url: str) -> list[str]:
    """Generate conservative crawl seed variants around a URL."""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    base = f"{parsed.scheme}://{parsed.netloc}"
    variants = [normalized]

    for candidate in (
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/robots.txt",
        f"{base}/feed.xml",
        f"{base}/index.xml",
    ):
        if candidate not in variants:
            variants.append(candidate)

    segments = [segment for segment in parsed.path.split("/") if segment]
    if segments:
        prefix = "/".join(segments[:-1])
        if prefix:
            variants.append(f"{base}/{prefix}/")
        else:
            variants.append(f"{base}/")

    return variants


def expand_crawl_request(request: CrawlRequest) -> list[CrawlSeed]:
    """Expand crawl seeds into a conservative offline-friendly queue."""
    expanded: list[CrawlSeed] = []
    seen: set[str] = set()

    for seed in request.seeds:
        candidates = [normalize_url(seed.url, base_url=request.base_url)]
        if request.include_sitemap_variants:
            candidates.extend(sitemap_seed_variants(seed.url))

        for candidate in candidates:
            if request.same_domain_only and request.base_url and not same_domain(candidate, request.base_url):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            expanded.append(CrawlSeed(url=candidate, label=seed.label))
            if len(expanded) >= request.max_pages:
                return expanded

    return expanded


class _MarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.tag_stack: list[str] = []
        self.link_href: str | None = None
        self.list_depth = 0
        self.in_pre = False
        self.ignored_depth = 0

    def _push(self, text: str) -> None:
        if text:
            self.parts.append(text)

    def _newline(self, count: int = 1) -> None:
        if not self.parts:
            return
        tail = self.parts[-1]
        if tail.endswith("\n" * count):
            return
        self.parts.append("\n" * count)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        self.tag_stack.append(tag)

        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
            return
        if tag in {"p", "div", "section", "article", "header", "footer", "blockquote"}:
            self._newline(2)
        elif tag in {"br"}:
            self._newline(1)
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline(2)
            level = int(tag[1])
            self._push("#" * level + " ")
        elif tag == "li":
            self._newline(1)
            self._push(("  " * max(0, self.list_depth - 1)) + "- ")
        elif tag in {"ul", "ol"}:
            self.list_depth += 1
            self._newline(1)
        elif tag == "pre":
            self.in_pre = True
            self._newline(2)
            self._push("```")
            self._newline(1)
        elif tag == "code" and self.in_pre:
            return
        elif tag == "a":
            self.link_href = attr_map.get("href") or None
        elif tag == "img":
            alt = attr_map.get("alt", "").strip()
            src = attr_map.get("src", "").strip()
            if src:
                self._push(f"![{alt}]({src})" if alt else f"![]({src})")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored_depth > 0:
            self.ignored_depth -= 1
            return
        if tag in {"p", "div", "section", "article", "header", "footer", "blockquote"}:
            self._newline(2)
        elif tag in {"ul", "ol"}:
            self.list_depth = max(0, self.list_depth - 1)
            self._newline(1)
        elif tag == "pre":
            self._newline(1)
            self._push("```")
            self._newline(2)
            self.in_pre = False
        elif tag == "a":
            self.link_href = None

        while self.tag_stack and self.tag_stack[-1] != tag:
            self.tag_stack.pop()
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.ignored_depth > 0:
            return
        text = unescape(data)
        if not text.strip():
            if self.in_pre and data:
                self._push(data)
            return
        if self.in_pre:
            self._push(text)
            return

        if self.link_href:
            self._push(f"[{text.strip()}]({self.link_href})")
            return

        self._push(text)

    def handle_comment(self, data: str) -> None:
        return

    def get_markdown(self) -> str:
        raw = "".join(self.parts)
        lines = [line.rstrip() for line in raw.splitlines()]
        cleaned: list[str] = []
        blank_seen = False
        for line in lines:
            if line.strip():
                blank_seen = False
                cleaned.append(line)
            elif not blank_seen:
                cleaned.append("")
                blank_seen = True
        return normalize_markdown("\n".join(cleaned))


def html_to_markdown(html: str) -> str:
    """Convert a raw HTML string into readable Markdown without external deps."""
    parser = _MarkdownHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.get_markdown()


def extract_title_from_html(html: str) -> str:
    lower = html.lower()
    start = lower.find("<title>")
    end = lower.find("</title>")
    if start != -1 and end != -1 and end > start:
        return unescape(html[start + 7 : end]).strip()

    parser = _MarkdownHTMLParser()
    parser.feed(html)
    parser.close()
    markdown = parser.get_markdown()
    for line in markdown.splitlines():
        stripped = line.lstrip("# ").strip()
        if stripped:
            return stripped
    return "Untitled page"


def guess_content_type(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    path = parsed.path.lower()
    if any(marker in path for marker in ("/blog/", "/articles/", "/docs/", "/guide/", "/help/")):
        return "docs_article"
    if path.endswith((".xml", ".json")):
        return "machine_feed"
    if path.endswith((".pdf", ".doc", ".docx")):
        return "document"
    return "web_page"


def create_ingested_page(
    url: str,
    html: str | None = None,
    markdown: str | None = None,
    title: str | None = None,
    source: str = "manual",
    base_url: str | None = None,
) -> IngestedPage:
    """Build a normalized page payload from HTML or Markdown input."""
    normalized_url = normalize_url(url, base_url=base_url)
    if markdown is None and html is not None:
        markdown = html_to_markdown(html)
    markdown = normalize_markdown(markdown or "")
    inferred_title = title or (extract_title_from_html(html) if html else normalized_url.rstrip("/").rsplit("/", 1)[-1]) or "Untitled page"
    return IngestedPage(
        url=normalized_url,
        title=inferred_title,
        markdown=markdown,
        source=source,
        content_type=guess_content_type(normalized_url),
    )


def fetch_html(url: str, timeout_seconds: int = 10, user_agent: str = "NewGEOBot/0.1") -> str | None:
    """Fetch raw HTML using stdlib only. Returns None on network failure."""
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (URLError, ValueError, TimeoutError):
        return None


def collect_seed_urls(urls: Iterable[str], include_variants: bool = True) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for url in urls:
        for candidate in [normalize_url(url)] + (sitemap_seed_variants(url) if include_variants else []):
            if candidate in seen:
                continue
            seen.add(candidate)
            collected.append(candidate)
    return collected
