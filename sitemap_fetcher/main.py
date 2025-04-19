"""Main entry point for the Sitemap URL Fetcher application."""

import argparse
import sys
import json
import xml.etree.ElementTree as ET
import requests

from .processor import SitemapProcessor, ProcessorConfig


def main():
    """Parses command-line arguments and runs the sitemap processor."""
    parser = argparse.ArgumentParser(
        description="Fetch URLs from sitemaps recursively, handling state and limits."
    )
    parser.add_argument(
        "sitemap_url", help="The root sitemap URL to start fetching from."
    )
    parser.add_argument(
        "output_file", help="Path to the file where found URLs will be written."
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Maximum number of unique URLs to fetch.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved state.",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Path to state file (default: <output_file>.state.json). "
        "Used for saving progress and resuming.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout",
    )

    args = parser.parse_args()

    # --- Argument Validation ---
    if args.limit is not None and args.limit <= 0:
        print("Error: --limit must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # Create the configuration object
    config = ProcessorConfig(
        sitemap_url=args.sitemap_url,
        output_file=args.output_file,
        state_file=args.state_file,
        limit=args.limit,
        resume=args.resume,
        fetcher_timeout=args.timeout,
    )

    # Instantiate the processor with the config object
    processor = SitemapProcessor(config=config)

    try:
        processor.run()
    except (
        requests.exceptions.RequestException,
        ET.ParseError,
        json.JSONDecodeError,
        IOError,
    ) as e:
        print(f"An error occurred during processing: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
