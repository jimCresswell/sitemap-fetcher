import xml.etree.ElementTree as ET
from unittest.mock import ANY, patch

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


# --- New Tests ---


@patch("requests.get")
def test_fetcher_timeout(mock_get):
    """Tests that the fetcher passes the timeout to requests.get."""
    # Configure the mock to return a basic valid response
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b'<?xml version="1.0"?><root />'
    mock_get.return_value = mock_response

    # Test default timeout
    fetcher_default = SitemapFetcher()
    fetcher_default.fetch_sitemap("http://test.com/sitemap.xml")
    mock_get.assert_called_with("http://test.com/sitemap.xml", timeout=30, headers=ANY)

    # Test custom timeout
    fetcher_custom = SitemapFetcher(timeout=15)
    fetcher_custom.fetch_sitemap("http://test.com/sitemap.xml")
    mock_get.assert_called_with("http://test.com/sitemap.xml", timeout=15, headers=ANY)


def test_fetcher_fetch_sitemap_utf8_fallback(patch_requests):
    """Tests SitemapFetcher handles XML with BOM via UTF-8 fallback."""
    fetcher = SitemapFetcher()
    # This URL is configured in conftest.py to return XML with a BOM
    root = fetcher.fetch_sitemap("http://bom.com/sitemap.xml")
    assert root is not None
    assert len(root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")) == 1
    assert (
        root.findtext(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        == "http://bom.com/page1"
    )


def test_fetcher_fetch_sitemap_http_error(patch_requests):
    """Tests SitemapFetcher handles HTTP errors (e.g., 404 Not Found)."""
    fetcher = SitemapFetcher()
    with pytest.raises(requests.exceptions.HTTPError):
        # This URL is configured in conftest.py to return a 404
        fetcher.fetch_sitemap("http://notfound.com/sitemap.xml")
