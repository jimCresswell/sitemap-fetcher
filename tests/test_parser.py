import xml.etree.ElementTree as ET

from sitemap_fetcher.parser import SitemapParser


# --- Tests for SitemapParser ---


def test_parser_is_sitemap_index():
    """Tests SitemapParser correctly identifies sitemap index files."""
    parser = SitemapParser()
    index_xml = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" />'
    urlset_xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" />'
    index_root = ET.fromstring(index_xml)
    urlset_root = ET.fromstring(urlset_xml)

    assert parser.is_sitemap_index(index_root)
    assert not parser.is_sitemap_index(urlset_root)


def test_parser_extract_loc_elements():
    """Tests SitemapParser extracts <loc> elements correctly."""
    parser = SitemapParser()

    # Test with sitemap index
    index_xml = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                     <sitemap><loc>http://example.com/sitemap1.xml</loc></sitemap>
                     <sitemap><loc>http://example.com/sitemap2.xml</loc></sitemap>
                   </sitemapindex>"""
    index_root = ET.fromstring(index_xml)
    expected_index_locs = [
        "http://example.com/sitemap1.xml",
        "http://example.com/sitemap2.xml",
    ]
    assert parser.extract_loc_elements(index_root) == expected_index_locs

    # Test with urlset
    urlset_xml = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                      <url><loc>http://example.com/page1.html</loc></url>
                      <url><loc>http://example.com/page2.html</loc></url>
                    </urlset>"""
    urlset_root = ET.fromstring(urlset_xml)
    expected_urlset_locs = [
        "http://example.com/page1.html",
        "http://example.com/page2.html",
    ]
    assert parser.extract_loc_elements(urlset_root) == expected_urlset_locs

    # Test with empty element
    empty_xml = "<root />"
    empty_root = ET.fromstring(empty_xml)
    assert parser.extract_loc_elements(empty_root) == []
