"""Main-content extraction with a dual strategy.

Autodesk pages are heavily templated: trafilatura extracts product/marketing pages
cleanly but returns ~nothing on many support pages. So:
  1. trafilatura (favor_recall) as primary — best boilerplate removal when it works.
  2. BeautifulSoup fallback when trafilatura underflows — strip nav/header/footer/
     script, then collapse repeated lines (kills "Download free trial" x4 menus).
"""
from __future__ import annotations

import re

import trafilatura
from bs4 import BeautifulSoup

_MIN_TRAFILATURA_CHARS = 400          # below this -> use bs4 fallback
_STRIP_TAGS = ["script", "style", "noscript", "template", "svg", "nav",
               "header", "footer", "form", "iframe"]
_NAV_ROLES = {"navigation", "banner", "contentinfo", "search"}


def _bs4_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    # drop elements explicitly marked as nav/banner/footer chrome
    for el in soup.find_all(attrs={"role": True}):
        if el.get("role", "").lower() in _NAV_ROLES:
            el.decompose()
    text = soup.get_text("\n", strip=True)
    return _collapse_repeats(text)


def _collapse_repeats(text: str) -> str:
    """Remove consecutive duplicate lines and squeeze blank runs."""
    out: list[str] = []
    prev = None
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        if line == prev:           # repeated CTA/menu item
            continue
        out.append(line)
        prev = line
    return "\n".join(out)


def extract_main_text(html: str) -> tuple[str, str]:
    """Return (text, method) where method is 'trafilatura' or 'bs4'."""
    t = trafilatura.extract(
        html, favor_recall=True, include_tables=True,
        include_comments=False, no_fallback=False,
    ) or ""
    if len(t) >= _MIN_TRAFILATURA_CHARS:
        return _collapse_repeats(t), "trafilatura"
    return _bs4_text(html), "bs4"


# Junk detection ----------------------------------------------------------------

_JUNK_MARKERS = ("Request unsuccessful. Incapsula", "Incapsula incident ID")


def is_junk(html: str) -> bool:
    return any(m in html for m in _JUNK_MARKERS)
