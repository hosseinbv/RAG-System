"""Extract provenance metadata from a raw HTML page.

The crawl preserved `<link rel="canonical">` with the real autodesk.com URL, plus
`<title>` and `<html lang>`. The URL *path* gives us free taxonomy:
  https://www.autodesk.com/support/technical/product/autocad
   -> page_type="support", product="autocad"
"""
from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from urllib.parse import urlparse

_CANONICAL = re.compile(r'rel="canonical"\s+href="([^"]+)"', re.I)
_OG_URL = re.compile(r'og:url"\s+content="([^"]+)"', re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_HTML_LANG = re.compile(r"<html[^>]*\blang=\"([^\"]+)\"", re.I)
_META_DESC = re.compile(r'name="description"\s+content="([^"]*)"', re.I)

# URL path segment -> coarse page_type. First segment unless it's a known wrapper.
_PRODUCT_PARENTS = {"products", "product"}
# leading path segment that is a locale (e.g. "en", "en-us", "de-de") -> skip it
_LOCALE = re.compile(r"^[a-z]{2}(-[a-z]{2})?$", re.I)


@dataclass
class PageMeta:
    url: str = ""
    title: str = ""
    description: str = ""
    lang: str = ""
    product: str = ""
    page_type: str = ""

    @property
    def is_english(self) -> bool:
        return self.lang.lower().startswith("en")


def _first(pattern: re.Pattern, html: str) -> str:
    m = pattern.search(html)
    return m.group(1).strip() if m else ""


def _derive_taxonomy(url: str) -> tuple[str, str]:
    """Return (page_type, product) from the canonical URL path."""
    if not url:
        return "", ""
    parts = [p for p in urlparse(url).path.split("/") if p]
    if parts and _LOCALE.match(parts[0]):   # strip leading locale segment
        parts = parts[1:]
    if not parts:
        return "home", ""
    page_type = parts[0].lower()
    product = ""
    # product is the segment following a products/product wrapper
    for i, seg in enumerate(parts[:-1]):
        if seg.lower() in _PRODUCT_PARENTS:
            product = parts[i + 1].lower()
            break
    # legal/terms pages live under /company -> mark page_type for easy dropping
    if page_type == "company" and any("legal" in p or "terms" in p for p in parts):
        page_type = "legal"
    if "terms-of-use" in parts:
        page_type = "terms-of-use"
    return page_type, product


def extract_meta(html: str) -> PageMeta:
    url = _first(_CANONICAL, html) or _first(_OG_URL, html)
    title = html_lib.unescape(re.sub(r"\s+", " ", _first(_TITLE, html)).strip())
    lang = _first(_HTML_LANG, html)
    desc = html_lib.unescape(_first(_META_DESC, html))
    page_type, product = _derive_taxonomy(url)
    return PageMeta(
        url=url, title=title, description=desc, lang=lang,
        product=product, page_type=page_type,
    )
