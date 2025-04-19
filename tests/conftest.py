import pytest
import requests


# Helper class for mocking requests.get
class MockResponse:
    def __init__(self, xml_data, status_code=200):
        # self.xml_data = xml_data # Store original string if needed elsewhere
        self.text = xml_data  # Store as string for .text access
        self.content = xml_data.encode("utf-8")  # Encode to bytes for .content access
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

    def fake_get(url, **kwargs):  # Accept **kwargs to handle 'timeout'
        # Existing error/limit cases
        if url == "http://error.com/sitemap.xml":
            raise requests.exceptions.RequestException("Network error")
        if url == "http://badxml.com/sitemap.xml":
            # Return genuinely malformed XML to trigger ParseError
            return MockResponse("<root><unclosed-tag</root>")
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
        return MockResponse("<root/>", status_code=404)

    monkeypatch.setattr(requests, "get", fake_get)
