"""Module for parsing sitemap XML content."""

import xml.etree.ElementTree as ET
from typing import List

# Namespace for sitemap XML files
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


class SitemapParser:
    """Parses XML content to extract URLs and identify sitemap types."""

    def is_sitemap_index(self, element: ET.Element) -> bool:
        """Checks if the given XML element is a sitemap index.

        Args:
            element: The root XML element of the fetched content.

        Returns:
            True if the element is a sitemap index, False otherwise.
        """
        # Checks if the tag ends with '}sitemapindex', accommodating potential
        # variations in namespace prefixes.
        return element.tag.endswith("}sitemapindex")

    def extract_loc_elements(self, element: ET.Element) -> List[str]:
        """Extracts all <loc> text content from a sitemap or sitemap index element.

        Args:
            element: The root XML element (sitemap or sitemapindex).

        Returns:
            A list of URLs found within <loc> tags.
        """
        # Uses the defined NAMESPACE to find all 'loc' elements correctly.
        # Filters out elements where loc.text is None or empty.
        locations = element.findall(f".//{{{NAMESPACE}}}loc")
        return [loc.text for loc in locations if loc.text]
