import pytest
import requests
import codecs  # Import codecs for BOM


# Helper class for mocking requests.get
class MockResponse:
    def __init__(self, xml_data, status_code=200, encoding="utf-8"):
        # self.xml_data = xml_data # Store original string if needed elsewhere
        self.text = xml_data  # Store as string for .text access
        # Encode based on the provided encoding
        if isinstance(xml_data, str):
            self.content = xml_data.encode(encoding)
        else:  # Assume bytes if not string (e.g., for BOM)
            self.content = xml_data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def raise_for_status(self):
        if not self.ok:
            raise requests.exceptions.HTTPError(f"{self.status_code} Client Error")

    # Add a way to simulate reading the content as XML element if needed by parser directly
    # Although the fetcher currently uses resp.content directly
    # def xml(self):
    #     try:
    #         return ET.fromstring(self.content)
    #     except ET.ParseError:
    #         raise ET.ParseError("Failed to parse XML")


# Monkeypatch requests.get
@pytest.fixture
def patch_requests(monkeypatch):
    """Patches requests.get to return controlled responses or raise errors."""

    # Define BOM + XML content
    bom_xml_content = (
        codecs.BOM_UTF8
        + """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url><loc>http://bom.com/page1</loc></url>
</urlset>""".encode(
            "utf-8"
        )
    )

    def fake_get(url, **kwargs):  # Accept **kwargs to handle 'timeout'
        # Existing error/limit cases
        if url == "http://error.com/sitemap.xml":
            raise requests.exceptions.RequestException("Network error")
        if url == "http://badxml.com/sitemap.xml":
            # Return genuinely malformed XML to trigger ParseError
            return MockResponse("<root><unclosed-tag</root>")
        if url == "http://bom.com/sitemap.xml":  # Test UTF-8 BOM fallback
            # Return raw bytes including BOM
            return MockResponse(
                bom_xml_content, status_code=200, encoding=None
            )  # Indicate no specific encoding
        if url == "http://notfound.com/sitemap.xml":  # Test 404
            return MockResponse("<error>Not Found</error>", status_code=404)
        if url == "http://limited.com/sitemap.xml":
            return MockResponse(
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url><loc>http://limited.com/page1</loc></url>
                    <url><loc>http://limited.com/page2</loc></url>
                    <url><loc>http://limited.com/page3</loc></url>
                </urlset>"""
            )
        if url == "http://resume.com/index.xml":
            return MockResponse(
                """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <sitemap><loc>http://resume.com/child1.xml</loc></sitemap>
                       <sitemap><loc>http://resume.com/child2.xml</loc></sitemap>
                   </sitemapindex>"""
            )
        if url == "http://resume.com/child1.xml":
            return MockResponse(
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://resume.com/pageA</loc></url>
                       <url><loc>http://resume.com/pageB</loc></url>
                   </urlset>"""
            )
        if url == "http://resume.com/child2.xml":
            return MockResponse(
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://resume.com/pageC</loc></url>
                       <url><loc>http://resume.com/pageD</loc></url>
                   </urlset>"""
            )

        # Default cases for success test
        if url == "http://example.com/index.xml":
            return MockResponse(
                """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <sitemap><loc>http://example.com/child.xml</loc></sitemap>
                   </sitemapindex>"""
            )
        if url == "http://example.com/child.xml":
            return MockResponse(
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://example.com/page1</loc></url>
                       <url><loc>http://example.com/page2</loc></url>
                   </urlset>"""
            )

        # Default fallback for unexpected URLs
        # Keep the original 404 for truly unexpected URLs during testing
        print(f"WARN: Unexpected URL requested in test: {url}")
        return MockResponse("<root/>", status_code=404)

    monkeypatch.setattr(requests, "get", fake_get)
