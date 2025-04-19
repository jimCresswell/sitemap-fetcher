import xml.etree.ElementTree as ET

import pytest
import requests

from sitemap_fetcher.fetcher import SitemapFetcher

# Fixtures like patch_requests are automatically discovered from conftest.py


# --- Tests for SitemapFetcher ---


def test_fetcher_fetch_sitemap_success(patch_requests):
    """Tests fetching a valid sitemap successfully using SitemapFetcher."""
    fetcher = SitemapFetcher()
    root = fetcher.fetch_sitemap("http://example.com/child.xml")
    assert root is not None
    # Use the correct namespace in findall
    assert len(root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")) == 2


def test_fetcher_fetch_sitemap_network_error(patch_requests):
    """Tests SitemapFetcher handles network errors during fetch."""
    fetcher = SitemapFetcher()
    with pytest.raises(requests.exceptions.RequestException):
        fetcher.fetch_sitemap("http://error.com/sitemap.xml")


def test_fetcher_fetch_sitemap_bad_xml(patch_requests):
    """Tests SitemapFetcher handles invalid XML content."""
    fetcher = SitemapFetcher()
    with pytest.raises(ET.ParseError):
        fetcher.fetch_sitemap("http://badxml.com/sitemap.xml")
