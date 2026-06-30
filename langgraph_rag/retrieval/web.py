"""Optional web retriever for Phase 5.

The retriever is deliberately small and swappable. It returns normal `Chunk`
objects with `source="web"`, so the rest of the graph can merge, rerank, cite,
and judge web contexts exactly like corpus contexts.

Default provider is DuckDuckGo HTML search because it needs no API key. For a
production deployment, replace `_search_duckduckgo_html` with a zero-retention
provider client behind the same `retrieve()` interface.
"""
from __future__ import annotations

import hashlib
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from ..core.config import load_config
from ..core.interfaces import BaseRetriever
from ..core.registry import register
from ..core.state import Chunk
from ..ingest.clean import extract_main_text
from ..ingest.metadata import _derive_taxonomy, extract_meta


def _is_allowed_url(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = urlparse(url).netloc.lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in allowed_domains)


def _normalize_result_url(href: str) -> str:
    """Resolve DuckDuckGo redirect URLs to their target URL when possible."""
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    if "uddg" in qs:
        return unquote(qs["uddg"][0])
    return href


@register("retriever", "web")
class WebRetriever(BaseRetriever):
    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        wc = self.cfg.get_path("web", {})
        self.provider = wc.get("provider", "duckduckgo_html")
        self.allowed_domains = wc.get("allowed_domains", ["autodesk.com"])
        self.fetch_pages = wc.get("fetch_pages", True)
        self.timeout = wc.get("timeout_s", 8)
        self.max_chars = wc.get("max_chars_per_page", 4500)
        self.search_url = wc.get("search_url", "https://duckduckgo.com/html/")

    def retrieve(self, query: str, top_k: int) -> list[Chunk]:
        if self.provider in {"disabled", "none"}:
            return []
        if self.provider != "duckduckgo_html":
            raise ValueError(f"Unsupported web provider: {self.provider}")

        try:
            results = self._search_duckduckgo_html(query, top_k)
        except Exception:  # noqa: BLE001 - web fallback should never kill corpus RAG
            return []
        chunks: list[Chunk] = []
        for rank, item in enumerate(results, 1):
            text = item.get("snippet", "").strip()
            fetched = False
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            product = ""
            page_type = "web"

            if self.fetch_pages and url:
                page = self._fetch_page(url)
                if page:
                    html, extracted = page
                    meta = extract_meta(html)
                    title = meta.title or title
                    product = meta.product
                    page_type = meta.page_type or "web"
                    if extracted:
                        text = extracted
                        fetched = True
            if not text:
                continue
            if not product or page_type == "web":
                page_type2, product2 = _derive_taxonomy(url)
                page_type = page_type if page_type != "web" else (page_type2 or "web")
                product = product or product2

            cid = "web::" + hashlib.md5(url.encode("utf-8")).hexdigest()
            chunks.append(
                Chunk(
                    id=cid,
                    text=text[: self.max_chars],
                    url=url,
                    title=title or url,
                    product=product,
                    page_type=page_type,
                    source="web",
                    score=0.0,
                    extra={"search_rank": rank, "fetched": fetched},
                )
            )
        return chunks[:top_k]

    def _search_duckduckgo_html(self, query: str, top_k: int) -> list[dict]:
        q = query
        if self.allowed_domains:
            q = f"site:{self.allowed_domains[0]} {query}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; local-rag-eval/1.0)"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            resp = client.get(self.search_url, params={"q": q})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        out: list[dict] = []
        seen: set[str] = set()
        for result in soup.select(".result"):
            link = result.select_one("a.result__a") or result.find("a", href=True)
            if not link:
                continue
            url = _normalize_result_url(link.get("href", ""))
            if not url.startswith("http") or not _is_allowed_url(url, self.allowed_domains):
                continue
            if url in seen:
                continue
            seen.add(url)
            snippet_el = result.select_one(".result__snippet")
            out.append(
                {
                    "title": link.get_text(" ", strip=True),
                    "url": url,
                    "snippet": snippet_el.get_text(" ", strip=True) if snippet_el else "",
                }
            )
            if len(out) >= top_k:
                break
        return out

    def _fetch_page(self, url: str) -> tuple[str, str] | None:
        if not _is_allowed_url(url, self.allowed_domains):
            return None
        headers = {"User-Agent": "Mozilla/5.0 (compatible; local-rag-eval/1.0)"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                resp.raise_for_status()
            text, _method = extract_main_text(resp.text)
            return resp.text, text[: self.max_chars]
        except Exception:  # noqa: BLE001 - web fallback should never kill corpus RAG
            return None
