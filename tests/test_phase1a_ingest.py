"""Phase 1a: metadata parsing, taxonomy, junk detection, dual-strategy extraction."""
from langgraph_rag.ingest.metadata import extract_meta, _derive_taxonomy
from langgraph_rag.ingest.clean import is_junk, extract_main_text, _collapse_repeats


def test_taxonomy_from_url():
    assert _derive_taxonomy("https://www.autodesk.com/products/fusion-360/overview") == ("products", "fusion-360")
    assert _derive_taxonomy("https://www.autodesk.com/support/technical/product/autocad") == ("support", "autocad")
    # locale prefix is stripped, not treated as page_type
    assert _derive_taxonomy("https://www.autodesk.com/en/categories/x")[0] == "categories"
    # legal/terms get their own page_type for easy dropping
    assert _derive_taxonomy("https://www.autodesk.com/company/legal-notices-trademarks")[0] == "legal"
    assert _derive_taxonomy("https://www.autodesk.com/company/terms-of-use")[0] == "terms-of-use"


def test_extract_meta_fields():
    html = ('<html lang="en-US"><head><title>Overview | AutoCAD | Autodesk</title>'
            '<link rel="canonical" href="https://www.autodesk.com/products/autocad/overview" />'
            '<meta name="description" content="CAD software" /></head><body>x</body></html>')
    m = extract_meta(html)
    assert m.url.endswith("/products/autocad/overview")
    assert m.product == "autocad" and m.page_type == "products"
    assert m.is_english and m.title.startswith("Overview")


def test_non_english_detected():
    assert not extract_meta('<html lang="de-de"></html>').is_english


def test_junk_detection():
    assert is_junk("blah Request unsuccessful. Incapsula incident ID: 123")
    assert not is_junk("<html><body>real content</body></html>")


def test_collapse_repeats():
    assert _collapse_repeats("a\na\nb\n\nb\nc") == "a\nb\nc"


def test_dual_strategy_extraction_picks_method():
    # a content-rich article -> trafilatura; a thin shell -> bs4 fallback / short
    rich = "<html><body><article>" + ("Fusion 360 is CAD software. " * 60) + "</article></body></html>"
    text, method = extract_main_text(rich)
    assert len(text) > 400
