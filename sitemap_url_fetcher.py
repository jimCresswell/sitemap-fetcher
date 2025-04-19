"""
Given a sitemap URL, fetch all URLs from it and its child sitemaps recursively,
and write them to an output file.
"""

import xml.etree.ElementTree as ET
import argparse
import json
import os
import signal
import sys
from typing import List, Set, Tuple
import requests

NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Global state variables (consider encapsulating in a class later if complexity grows)
processing_active = False
sitemap_queue: List[str] = []
processed_sitemaps: Set[str] = set()
found_urls: Set[str] = set()
output_file_path: str = ""
state_file_path: str = ""


def fetch_sitemap(url: str) -> ET.Element:
    """Fetches a sitemap from a URL."""
    # Increased timeout for potentially slow responses
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Handle potential encoding issues if response isn't UTF-8
    try:
        return ET.fromstring(resp.content)
    except ET.ParseError:
        # Try decoding explicitly as UTF-8, common for XML
        return ET.fromstring(resp.content.decode("utf-8"))


def is_sitemap_index(element: ET.Element) -> bool:
    """Checks if the given element is a sitemap index."""
    # More robust check considering potential variations
    return element.tag.endswith("}sitemapindex")


def extract_loc_elements(element: ET.Element) -> List[str]:
    """Extracts all <loc> text content from a sitemap or sitemap index."""
    # Ensure namespace is handled correctly
    return [loc.text for loc in element.findall(f".//{{{NAMESPACE}}}loc") if loc.text]


def save_state(filename: str, queue: List[str], processed: Set[str], urls: Set[str]):
    """Saves the current state (queue, processed set, found URLs) to a JSON file."""
    state = {
        "queue": queue,
        # Convert sets to lists for JSON serialization
        "processed": sorted(list(processed)),
        "urls": sorted(list(urls)),
    }
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        print(f"Error saving state file {filename}: {e}", file=sys.stderr)


def load_state(filename: str) -> Tuple[List[str], Set[str], Set[str]]:
    """
    Loads state from a JSON file, returning empty state if file not found or invalid.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Ensure loaded data are correct types
        queue = state.get("queue", [])
        processed = set(state.get("processed", []))
        urls = set(state.get("urls", []))
        if (
            not isinstance(queue, list)
            or not isinstance(processed, set)
            or not isinstance(urls, set)
        ):
            raise ValueError("Invalid state file format")
        return queue, processed, urls
    except (IOError, json.JSONDecodeError, ValueError) as e:
        print(
            f"Error loading state file {filename}: {e}. Starting fresh.",
            file=sys.stderr,
        )
        return [], set(), set()


def signal_handler(sig, frame):
    """
    Handles SIGINT/SIGTERM for graceful shutdown, saving state.
    """
    # Access global state variables (read-only access is implicit)
    global processing_active

    if processing_active:
        print(f"\nSignal {sig} received. Saving state...", frame)
        save_state(state_file_path, sitemap_queue, processed_sitemaps, found_urls)
        processing_active = False  # Prevent further processing
    else:
        print(f"\nSignal {sig} received during shutdown. Exiting immediately.")
    sys.exit(0)


def main():
    """Main function to parse args, fetch sitemaps, and save URLs."""
    # Use global state variables
    global processing_active, sitemap_queue, processed_sitemaps, found_urls, output_file_path, state_file_path  # noqa: E501

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
        help="Maximum number of unique URLs to fetch. Stops after reaching the limit.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume fetching from a previously saved state file.",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Path to state file (default: <output_file>.state.json). "  # noqa: E501
        "Used for saving progress and resuming.",
    )
    args = parser.parse_args()

    # --- Argument Validation ---
    # Validate limit argument
    if args.limit is not None and args.limit <= 0:
        print("Error: --limit must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # --- State Initialization ---
    output_file_path = args.output_file
    # Determine state file path
    state_file_path = args.state_file or f"{output_file_path}.state.json"

    if args.resume:
        print(f"Resuming from state file: {state_file_path}")
        sitemap_queue, processed_sitemaps, found_urls = load_state(state_file_path)
        if not sitemap_queue and not processed_sitemaps and not found_urls:
            # If state file was empty or invalid, start with the root URL
            print("State file empty or invalid, starting from root URL.")
            sitemap_queue = [args.sitemap_url]
    else:
        print("Starting fresh fetch.")
        sitemap_queue = [args.sitemap_url]
        processed_sitemaps = set()
        found_urls = set()
        # Clear output file if not resuming
        try:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("")  # Truncate the file
        except IOError as e:
            print(
                f"Error clearing output file {output_file_path}: {e}", file=sys.stderr
            )
            sys.exit(1)

    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Main Processing Loop ---
    global processing_active
    processing_active = True
    print("Starting sitemap processing...")
    while sitemap_queue:
        # Check limit before processing next sitemap
        if args.limit and len(found_urls) >= args.limit:
            print(f"\nURL limit ({args.limit}) reached during queue processing.")
            break

        current_sitemap_url = sitemap_queue.pop(0)

        if current_sitemap_url in processed_sitemaps:
            print(f"Skipping already processed: {current_sitemap_url}")
            continue

        print(f"Processing: {current_sitemap_url}")
        processed_sitemaps.add(current_sitemap_url)

        try:
            root = fetch_sitemap(current_sitemap_url)
            new_urls_or_sitemaps = extract_loc_elements(root)

            if is_sitemap_index(root):
                print(
                    f"  Found sitemap index, adding {len(new_urls_or_sitemaps)} child sitemaps to queue."  # noqa: E501
                )
                for child_sitemap_url in new_urls_or_sitemaps:  # noqa: E501
                    if child_sitemap_url not in processed_sitemaps:
                        sitemap_queue.append(child_sitemap_url)
            else:
                print(f"  Found sitemap with {len(new_urls_or_sitemaps)} URLs.")
                urls_to_write = []
                for url in new_urls_or_sitemaps:
                    # Check limit before adding URL
                    if args.limit and len(found_urls) >= args.limit:
                        break
                    if url not in found_urls:
                        urls_to_write.append(url)
                        found_urls.add(url)

                if urls_to_write:
                    print(
                        f"    Writing {len(urls_to_write)} new unique URLs to {output_file_path}"  # noqa: E501
                    )
                    try:  # noqa: E501
                        # Append new URLs to the output file
                        with open(output_file_path, "a", encoding="utf-8") as f:
                            for url in urls_to_write:
                                f.write(url + "\n")
                    except IOError as e:
                        print(
                            f"Error writing to output file {output_file_path}: {e}",
                            file=sys.stderr,
                        )
                        # Continue processing other sitemaps if possible

        except requests.exceptions.RequestException as e:
            print(f"Error fetching sitemap {current_sitemap_url}: {e}", file=sys.stderr)
        except ET.ParseError as e:
            print(f"Error parsing sitemap {current_sitemap_url}: {e}", file=sys.stderr)
        except Exception as e:  # Catch other potential errors
            print(
                f"Unexpected error processing {current_sitemap_url}: {e}",
                file=sys.stderr,
            )

        # Save state after processing each sitemap
        save_state(state_file_path, sitemap_queue, processed_sitemaps, found_urls)

        # Check limit again after processing a sitemap and adding URLs
        if args.limit and len(found_urls) >= args.limit:
            print(f"\nURL limit ({args.limit}) reached after processing sitemap.")
            break

    # --- Cleanup ---
    processing_active = False
    print("\nProcessing finished.")
    # Clean up state file on successful completion if it exists
    if os.path.exists(state_file_path):
        try:
            if not sitemap_queue:  # Only remove if queue is empty (completed)
                print(f"Removing state file: {state_file_path}")
                os.remove(state_file_path)
            else:
                print(
                    f"Processing incomplete or limit reached, keeping state file: {state_file_path}"  # noqa: E501
                )
        except OSError as e:  # noqa: E501
            print(f"Error removing state file {state_file_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
