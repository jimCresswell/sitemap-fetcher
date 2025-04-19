"""Module for fetching sitemap content."""

import xml.etree.ElementTree as ET
import requests


class SitemapFetcher:
    """Fetches sitemap content from a given URL."""

    def __init__(self, timeout: int = 30):
        """Initialize the fetcher with a request timeout."""
        self.timeout = timeout

    def fetch_sitemap(self, url: str) -> ET.Element:
        """Fetches and parses a sitemap from a URL.

        Args:
            url: The URL of the sitemap to fetch.

        Returns:
            The parsed XML root element of the sitemap.

        Raises:
            requests.exceptions.RequestException: If the request fails.
            ET.ParseError: If the XML content cannot be parsed.
        """
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            # Attempt to parse directly first
            try:
                return ET.fromstring(resp.content)
            except ET.ParseError:
                # If direct parsing fails, try decoding explicitly as UTF-8
                # This handles cases where the server doesn't specify encoding correctly
                # but the content is valid UTF-8 XML.
                return ET.fromstring(resp.content.decode("utf-8"))

        except requests.exceptions.RequestException as e:
            print(f"Error fetching sitemap {url}: {e}")
            raise
        except ET.ParseError as e:
            print(f"Error parsing XML from {url}: {e}")
            raise
