"""Module for fetching sitemap content with polite defaults.

Adds the following improvements:

* Custom "User‑Agent" header that explains the purpose of the script and
  includes a contact e‑mail address
* Throttling so we make **≤ 1 request every *N* seconds** (default 2s) to avoid
  overwhelming the origin or triggering bot mitigation (e.g. Cloudflare).

The contact e‑mail and request interval can be configured through a ``.env``
file placed in the project root:

```env
# .env
EMAIL=webmaster@thenational.academy
REQUEST_INTERVAL=2.5
```

The variables are loaded via *python‑dotenv*.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

# --- Environment configuration ------------------------------------------------

# Load variables from .env if present; silently ignore missing file
load_dotenv()

_DEFAULT_EMAIL = os.getenv("EMAIL", "contact@example.com")
_DEFAULT_USER_AGENT = f"Oak Sitemap Fetcher (+{_DEFAULT_EMAIL})"
# Delay between requests in seconds (float allowed for sub‑second resolution)
_DEFAULT_REQUEST_INTERVAL = float(os.getenv("REQUEST_INTERVAL_SECONDS", "2"))


class SitemapFetcher:
    """Fetches sitemap XML documents politely (custom UA + throttling)."""

    _last_request_ts: float | None = None  # Class‑level to share across instances

    def __init__(
        self,
        *,
        timeout: int = 30,
        user_agent: str | None = None,
        request_interval: float | None = None,
    ):
        """Create a new ``SitemapFetcher``.

        Parameters
        ----------
        timeout
            Maximum seconds to wait for an HTTP response.
        user_agent
            Custom *User‑Agent* header value. If *None*, a default string
            containing a contact e‑mail derived from the ``EMAIL`` env var is
            used.
        request_interval
            Minimum delay **in seconds** between consecutive requests (across
            *all* instances). Defaults to the ``REQUEST_INTERVAL_SECONDS`` env var or
            2 seconds.
        """

        self.timeout = timeout
        self.user_agent = user_agent or _DEFAULT_USER_AGENT
        self.request_interval = (
            request_interval
            if request_interval is not None
            else _DEFAULT_REQUEST_INTERVAL
        )

        # Prepared headers dict reused across requests
        self._headers = {"User-Agent": self.user_agent}

    def _throttle(self) -> None:
        """Sleep as necessary to respect ``self.request_interval``."""
        now = time.monotonic()
        if self._last_request_ts is not None:
            elapsed = now - self._last_request_ts
            sleep_for = self.request_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_request_ts = time.monotonic()

    def fetch_sitemap(self, url: str) -> ET.Element:
        """Fetch and parse a sitemap from *url* with politeness guarantees."""

        # Throttle before making the network request
        self._throttle()

        try:
            resp = requests.get(url, timeout=self.timeout, headers=self._headers)
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
