"""Module for processing sitemaps, managing state, and orchestrating fetch/parse."""

import json
import signal
import sys
import time
from typing import List, Optional, Set
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import requests

# Assuming fetcher and parser are in the same directory or package
from .fetcher import SitemapFetcher
from .parser import SitemapParser
from .state_manager import StateManager


@dataclass
class ProcessorConfig:
    """Configuration for the SitemapProcessor."""

    sitemap_url: str
    output_file: str
    state_file: Optional[str] = None
    limit: Optional[int] = None
    resume: bool = False
    fetcher_timeout: int = 30

    def __post_init__(self):
        # Automatically determine state_file if not provided
        if self.state_file is None:
            self.state_file = f"{self.output_file}.state.json"


class SitemapProcessor:
    """Orchestrates the fetching, parsing, and processing of sitemaps.

    The class now supports *dependency injection* for the fetcher and parser
    components, which enables simpler unit‑testing (you can pass lightweight
    mocks instead of patching at the module level):

    >>> mock_fetcher = Mock(fetch_sitemap=lambda url: xml_root)
    >>> processor = SitemapProcessor(cfg, fetcher=mock_fetcher)
    """

    def __init__(
        self,
        config: ProcessorConfig,
        *,
        fetcher: Optional[SitemapFetcher] = None,
        parser: Optional[SitemapParser] = None,
    ):
        self.config = config

        # Use injected dependencies or fall back to concrete implementations
        self.fetcher = (
            fetcher
            if fetcher is not None
            else SitemapFetcher(timeout=self.config.fetcher_timeout)
        )
        self.parser = parser if parser is not None else SitemapParser()

        # State variables (kept separate from config)
        self.sitemap_queue: List[str] = []
        self.processed_sitemaps: Set[str] = set()
        self.found_urls: Set[str] = set()
        self._processing_active = False  # Internal flag for signal handler

    # --- State Management ---
    def _save_state(self):
        """Saves the current processing state to the state file."""
        state = {
            "sitemap_queue": self.sitemap_queue,
            "processed_sitemaps": list(self.processed_sitemaps),
            "found_urls": list(self.found_urls),
        }
        try:
            StateManager.save_state(self.config.state_file, state)
            print(f"Saved state to {self.config.state_file}")
        except IOError as e:
            print(
                f"Error saving state file {self.config.state_file}: {e}",
                file=sys.stderr,
            )

    def _load_state(self):
        """Loads state from the state file."""
        if not self.config.resume:
            print("Resume flag not set, starting fresh.")
            # Initialize queue with root URL only if not resuming
            self.sitemap_queue = [self.config.sitemap_url]
            return

        try:
            state = StateManager.load_state(self.config.state_file)

            # Assign validated state
            self.sitemap_queue = state["sitemap_queue"]
            self.processed_sitemaps = set(state["processed_sitemaps"])
            self.found_urls = set(state["found_urls"])

            print(f"Resumed state from {self.config.state_file}:")
            print(f"  Queue size: {len(self.sitemap_queue)}")
            print(f"  Processed sitemaps: {len(self.processed_sitemaps)}")
            print(f"  Found URLs: {len(self.found_urls)}")

            # If queue is empty after loading, likely means previous run completed
            # or initial state was empty. Re-initialize with root if needed.
            if not self.sitemap_queue:
                print("State file queue empty, initializing with root sitemap URL.")
                self.sitemap_queue = [self.config.sitemap_url]

        except FileNotFoundError:
            # This case should theoretically be caught by os.path.exists, but added for robustness
            print(f"State file not found at {self.config.state_file}, starting fresh.")
            self.sitemap_queue = [self.config.sitemap_url]  # Initialize queue
            return  # Exit method
        except json.JSONDecodeError as e:
            print(f"Error loading or decoding state file {self.config.state_file}: {e}")
            print("Starting fresh.")
            self.sitemap_queue = [self.config.sitemap_url]  # Initialize queue
            return  # Exit method
        except (KeyError, ValueError) as e:
            print(
                f"Error loading state from {self.config.state_file}: Invalid state data format: {e}"
            )
            print("Starting fresh.")
            self.sitemap_queue = [self.config.sitemap_url]  # Initialize queue
            return  # Exit method
        except IOError as e:
            print(f"Error reading state file {self.config.state_file}: {e}")
            print("Starting fresh.")
            self.sitemap_queue = [self.config.sitemap_url]  # Initialize queue
            return  # Exit method

    # --- Signal Handling ---
    def _signal_handler(self, sig, frame):
        """Handles termination signals for graceful shutdown."""
        print(f"\nSignal {sig} received. Shutting down gracefully...")
        if self._processing_active:
            print(f"\nSignal {sig} received. Saving state...")
            self._save_state()
            self._processing_active = False  # Prevent further processing
        else:
            print(f"\nSignal {sig} received during shutdown. Exiting immediately.")
        sys.exit(0)

    # --- Output ---
    def _write_urls_to_output(self):
        """Writes the found URLs to the output file."""
        try:
            with open(self.config.output_file, "w", encoding="utf-8") as f:
                for url in sorted(list(self.found_urls)):
                    f.write(url + "\n")
            print(f"Wrote {len(self.found_urls)} URLs to {self.config.output_file}")
        except IOError as e:
            print(
                f"Error writing to output file {self.config.output_file}: {e}",
                file=sys.stderr,
            )

    # --- Core Processing Logic ---
    def _handle_sitemap_index(self, root: ET.Element):
        """Adds sub-sitemaps found in a sitemap index to the queue."""
        print("  Sitemap index detected. Extracting sub-sitemaps...")
        loc_elements = self.parser.extract_loc_elements(root)
        new_sitemaps = 0
        for loc in loc_elements:
            # Add only if not already processed and not already in queue
            if loc not in self.processed_sitemaps and loc not in self.sitemap_queue:
                self.sitemap_queue.append(loc)
                new_sitemaps += 1
        print(f"  Added {new_sitemaps} new sitemaps to the queue.")

    def _handle_regular_sitemap(self, root: ET.Element):
        """Extracts URLs from a regular sitemap file, respecting limits."""
        print("  Regular sitemap detected. Extracting URLs...")
        loc_elements = self.parser.extract_loc_elements(root)
        new_urls = 0
        for loc in loc_elements:
            # Check limit before adding each URL
            if (
                self.config.limit is not None
                and len(self.found_urls) >= self.config.limit
            ):
                print(
                    f"  URL limit ({self.config.limit}) reached during URL extraction."
                )
                self._processing_active = False  # Signal outer loop to stop
                break  # Exit inner URL loop

            if loc not in self.found_urls:
                self.found_urls.add(loc)
                new_urls += 1
        print(f"  Found {new_urls} new URLs.")

    def _process_single_sitemap(self, sitemap_url: str):
        """Fetches, parses, and processes a single sitemap URL."""
        # Skip if already processed
        if sitemap_url in self.processed_sitemaps:
            print(f"Skipping already processed sitemap: {sitemap_url}")
            return

        print(f"Processing sitemap: {sitemap_url}")
        try:
            root = self.fetcher.fetch_sitemap(sitemap_url)
            self.processed_sitemaps.add(sitemap_url)

            if self.parser.is_sitemap_index(root):
                self._handle_sitemap_index(root)
            else:
                self._handle_regular_sitemap(root)

        except requests.exceptions.RequestException:
            print(f"Failed to fetch {sitemap_url}. Skipping.", file=sys.stderr)
            # Optionally add retry logic here
        except ET.ParseError:
            print(f"Failed to parse {sitemap_url}. Skipping.", file=sys.stderr)

    def run(self):
        """Starts the sitemap processing workflow."""
        start_time = time.time()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._load_state()  # Load state or initialize queue

        if not self.sitemap_queue:
            print("Initial sitemap queue is empty. Nothing to process.")
            return

        self._processing_active = True
        print("Starting sitemap processing...")

        while self.sitemap_queue and self._processing_active:
            # Check URL limit before processing next sitemap
            if (
                self.config.limit is not None
                and len(self.found_urls) >= self.config.limit
            ):
                print(f"\nURL limit ({self.config.limit}) reached. Stopping.")
                break

            current_sitemap_url = self.sitemap_queue.pop(0)
            self._process_single_sitemap(current_sitemap_url)

        # --- Post-processing ---
        self._processing_active = False  # Ensure flag is false after loop finishes
        total_time = time.time() - start_time
        print(f"\nFinished processing in {total_time:.2f} seconds.")

        # Final save and write, regardless of whether loop completed naturally or stopped early
        self._save_state()  # Re-add state saving for normal completion
        self._write_urls_to_output()
