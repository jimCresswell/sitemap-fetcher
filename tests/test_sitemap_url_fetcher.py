import os
import signal
import sys  # noqa: F401 - Needed for monkeypatching sys.argv and sys.exit # pylint: disable=unused-import
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
import pytest
import requests

import sitemap_url_fetcher
from sitemap_url_fetcher import (
    extract_loc_elements,
    save_state,
    load_state,
)


# Helper class for mocking requests.get
class DummyResponse:
    """Mocks the response object from the requests library."""

    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")


@pytest.fixture
def patch_requests(monkeypatch):
    """Patches requests.get to return controlled responses or raise errors."""

    def fake_get(_url):
        # Existing error/limit cases
        if _url == "http://error.com/sitemap.xml":
            raise requests.exceptions.RequestException("Network error")
        if _url == "http://badxml.com/sitemap.xml":
            return DummyResponse(content=b"<malformed></xml>", status_code=200)
        if _url == "http://limited.com/sitemap.xml":
            xml = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://limited.com/page1</loc></url>
                       <url><loc>http://limited.com/page2</loc></url>
                       <url><loc>http://limited.com/page3</loc></url>
                     </urlset>"""
            return DummyResponse(content=xml.encode("utf-8"))

        # New cases for resume testing
        if _url == "http://resume.com/index.xml":
            xml = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                        <sitemap><loc>http://resume.com/child1.xml</loc></sitemap>
                        <sitemap><loc>http://resume.com/child2.xml</loc></sitemap>
                      </sitemapindex>"""
            return DummyResponse(content=xml.encode("utf-8"))
        if _url == "http://resume.com/child1.xml":
            xml = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://resume.com/pageA</loc></url>
                       <url><loc>http://resume.com/pageB</loc></url>
                     </urlset>"""
            return DummyResponse(content=xml.encode("utf-8"))
        if _url == "http://resume.com/child2.xml":
            xml = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                       <url><loc>http://resume.com/pageC</loc></url>
                       <url><loc>http://resume.com/pageD</loc></url>
                     </urlset>"""
            return DummyResponse(content=xml.encode("utf-8"))

        # Default/fallback cases
        if _url.endswith("index.xml"):
            xml = """
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <sitemap><loc>http://example.com/child.xml</loc></sitemap>
            </sitemapindex>
            """
            return DummyResponse(content=xml.encode("utf-8"))
        if _url.endswith("child.xml"):
            xml = """
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>http://example.com/page1</loc></url>
              <url><loc>http://example.com/page2</loc></url>
            </urlset>
            """
            return DummyResponse(content=xml.encode("utf-8"))

        # Default case (can be adjusted if needed)
        # Return a simple empty urlset
        return DummyResponse(content=b"<urlset></urlset>")

    monkeypatch.setattr(requests, "get", fake_get)
    return fake_get


def test_fetch_sitemap_success(patch_requests):  # pylint: disable=redefined-outer-name
    """Tests fetching a valid sitemap successfully."""
    root = sitemap_url_fetcher.fetch_sitemap("http://example.com/child.xml")
    assert root is not None
    assert len(root.findall(".//{*}url")) == 2


def test_fetch_sitemap_network_error(
    patch_requests,
):  # pylint: disable=redefined-outer-name
    """Tests handling of network errors during fetch."""
    with pytest.raises(requests.exceptions.RequestException):
        sitemap_url_fetcher.fetch_sitemap("http://error.com/sitemap.xml")


def test_fetch_sitemap_bad_xml(patch_requests):  # pylint: disable=redefined-outer-name
    """Tests handling of invalid XML content."""
    with pytest.raises(ET.ParseError):
        sitemap_url_fetcher.fetch_sitemap("http://badxml.com/sitemap.xml")


def test_is_sitemap_index():
    """Tests identification of sitemap index elements."""
    index_xml = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" />'
    urlset_xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" />'
    assert sitemap_url_fetcher.is_sitemap_index(ET.fromstring(index_xml))
    assert not sitemap_url_fetcher.is_sitemap_index(ET.fromstring(urlset_xml))


def test_extract_loc_elements():
    """Tests extraction of <loc> elements from sitemap and index."""
    sitemap_xml = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://example.com/page1</loc></url>
            <url><loc>http://example.com/page2</loc></url>
        </urlset>
    """
    index_xml = """
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>http://example.com/sitemap1.xml</loc></sitemap>
            <sitemap><loc>http://example.com/sitemap2.xml</loc></sitemap>
        </sitemapindex>
    """
    assert extract_loc_elements(ET.fromstring(sitemap_xml)) == [
        "http://example.com/page1",
        "http://example.com/page2",
    ]
    assert extract_loc_elements(ET.fromstring(index_xml)) == [
        "http://example.com/sitemap1.xml",
        "http://example.com/sitemap2.xml",
    ]


def test_save_state(tmp_path):
    """Tests saving state correctly."""
    state_file = tmp_path / "test_save.json"
    save_state(str(state_file), ["b"], {"a"}, {"c"})

    assert os.path.exists(state_file)
    # Basic check if file is readable JSON
    # More thorough checks in test_load_state
    import json

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "queue" in data


def test_load_state(tmp_path):
    """Tests saving and loading state successfully."""
    state_file = tmp_path / "test_load.json"
    data = {"queue": ["b"], "processed": ["a"], "urls": ["c"]}
    save_state(
        str(state_file), data["queue"], set(data["processed"]), set(data["urls"])
    )

    # Test loading back
    queue, processed, urls = load_state(str(state_file))
    assert queue == ["b"]
    assert processed == {"a"}
    assert urls == {"c"}


def test_load_state_missing_file(tmp_path):
    """Tests loading state from a non-existent file returns empty state."""
    queue, processed, urls = load_state(str(tmp_path / "nonexistent.json"))
    assert queue == []
    assert processed == set()
    assert urls == set()


def test_signal_handler_saves_state(tmp_path, monkeypatch):
    """Tests that the signal handler saves state correctly on SIGINT."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"
    sitemap_url_fetcher.output_file_path = str(output_file)
    sitemap_url_fetcher.state_file_path = str(state_file)

    # Define some state to be saved
    sitemap_url_fetcher.sitemap_queue = ["url2"]  # Simulate items left
    sitemap_url_fetcher.processed_sitemaps = {"url1"}  # Simulate processed
    sitemap_url_fetcher.found_urls = {"urlA"}  # Simulate found URLs
    sitemap_url_fetcher.processing_active = True

    # Mock sys.exit to prevent test runner exit
    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)

    # Mock save_state to check if it's called
    mock_save = MagicMock()
    monkeypatch.setattr(sitemap_url_fetcher, "save_state", mock_save)

    # Trigger the handler
    sitemap_url_fetcher.signal_handler(signal.SIGINT, None)

    # Assertions
    mock_save.assert_called_once_with(
        str(state_file),
        ["url2"],  # Expected queue
        {"url1"},  # Expected processed
        {"urlA"},  # Expected urls
    )
    mock_exit.assert_called_once_with(0)
    assert not sitemap_url_fetcher.processing_active  # Should be false


def test_main_success(tmp_path, monkeypatch, patch_requests):
    """Tests the main function runs successfully with basic arguments."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"
    args = [
        "sitemap_url_fetcher.py",
        "http://example.com/index.xml",
        str(output_file),
        "--state-file",
        str(state_file),
    ]
    monkeypatch.setattr("sys.argv", args)

    sitemap_url_fetcher.main()

    # Check output file content
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
    expected_urls = {"http://example.com/page1", "http://example.com/page2"}
    found_urls = set(line for line in content.strip().split("\n") if line)
    assert found_urls == expected_urls

    # Check state file is removed on successful completion
    assert not state_file.exists()


def test_main_handles_request_exception(tmp_path, monkeypatch, patch_requests, capsys):
    """Tests main function handles RequestException gracefully and continues."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"
    error_url = "http://error.com/sitemap.xml"  # Will raise RequestException
    args = [
        "sitemap_url_fetcher.py",
        error_url,
        str(output_file),
        "--state-file",
        str(state_file),
    ]
    monkeypatch.setattr("sys.argv", args)

    sitemap_url_fetcher.main()

    # Check that error was printed to stderr
    captured = capsys.readouterr()
    assert f"Error fetching sitemap {error_url}: Network error" in captured.err

    # Check output file is empty as no URLs were found
    assert output_file.exists()
    assert output_file.read_text() == ""
    # State file might exist if error happens after first save


def test_main_handles_parse_error(tmp_path, monkeypatch, patch_requests, capsys):
    """Tests main function handles ET.ParseError gracefully and continues."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"
    bad_xml_url = "http://badxml.com/sitemap.xml"  # Returns malformed XML
    args = [
        "sitemap_url_fetcher.py",
        bad_xml_url,
        str(output_file),
        "--state-file",
        str(state_file),
    ]
    monkeypatch.setattr("sys.argv", args)

    sitemap_url_fetcher.main()

    # Check that error was printed to stderr
    captured = capsys.readouterr()
    assert f"Error parsing sitemap {bad_xml_url}:" in captured.err

    # Check output file is empty
    assert output_file.exists()
    assert output_file.read_text() == ""


def test_main_argparse_missing_args(monkeypatch):
    """Tests that the script exits if required arguments are missing."""
    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)

    # Missing output_file
    args_missing_output = ["sitemap_url_fetcher.py", "http://example.com"]
    monkeypatch.setattr("sys.argv", args_missing_output)
    with pytest.raises(SystemExit):
        sitemap_url_fetcher.main()
    # Argparse calls sys.exit(2) for usage errors
    mock_exit.assert_called_with(2)

    # Missing sitemap_url
    mock_exit.reset_mock()
    args_missing_url = ["sitemap_url_fetcher.py", "output.txt"]
    monkeypatch.setattr("sys.argv", args_missing_url)
    with pytest.raises(SystemExit):
        sitemap_url_fetcher.main()
    mock_exit.assert_called_with(2)


def test_main_argparse_invalid_limit(tmp_path, monkeypatch):
    """Tests that the script exits if --limit is not a positive integer."""
    output_file = tmp_path / "output.txt"
    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)

    # Test with zero limit
    args_zero_limit = [
        "sitemap_url_fetcher.py",
        "http://example.com/index.xml",
        str(output_file),
        "-n",
        "0",
    ]
    monkeypatch.setattr("sys.argv", args_zero_limit)
    sitemap_url_fetcher.main()
    # Should exit with status 1 due to our validation
    mock_exit.assert_called_once_with(1)

    # Test with negative limit
    mock_exit.reset_mock()
    args_neg_limit = [
        "sitemap_url_fetcher.py",
        "http://example.com/index.xml",
        str(output_file),
        "-n",
        "-5",
    ]
    monkeypatch.setattr("sys.argv", args_neg_limit)
    sitemap_url_fetcher.main()
    mock_exit.assert_called_once_with(1)


def test_main_honors_limit(tmp_path, monkeypatch, patch_requests):
    """Tests that the --limit argument correctly limits fetched URLs."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"
    limit = 2
    args = [
        "sitemap_url_fetcher.py",
        "http://limited.com/sitemap.xml",
        str(output_file),
        "--state-file",
        str(state_file),
        "-n",
        str(limit),  # Limit to 2 URLs
    ]
    monkeypatch.setattr("sys.argv", args)
    sitemap_url_fetcher.main()

    # Check output file has exactly {limit} URLs
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
    urls_in_output = set(line for line in content.strip().split("\n") if line)
    assert len(urls_in_output) == limit
    expected_urls = {"http://limited.com/page1", "http://limited.com/page2"}
    assert urls_in_output == expected_urls

    # Check state file has the correct final state
    assert state_file.exists()  # State file should remain if limit hit
    queue, processed, urls_found_in_state = load_state(str(state_file))
    assert queue == []  # Queue should be empty
    assert processed == {"http://limited.com/sitemap.xml"}  # Sitemap processed
    # State should record the URLs found up to the limit
    assert urls_found_in_state == expected_urls


def test_main_resumes_correctly(tmp_path, monkeypatch, patch_requests):
    """Tests resuming correctly using the --resume flag and state file."""
    output_file = tmp_path / "output.txt"
    state_file = tmp_path / "state.json"

    # --- First Run (limited) ---
    args_run1 = [
        "sitemap_url_fetcher.py",
        "http://resume.com/index.xml",
        str(output_file),
        "--state-file",
        str(state_file),
        "-n",
        "2",  # Limit to find only 2 URLs (should process child1.xml)
    ]
    monkeypatch.setattr("sys.argv", args_run1)
    sitemap_url_fetcher.main()

    # Check intermediate state
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
    urls_run1 = set(line for line in content.strip().split("\n") if line)
    assert len(urls_run1) == 2
    assert urls_run1 == {"http://resume.com/pageA", "http://resume.com/pageB"}

    assert state_file.exists()
    queue1, processed1, urls1 = load_state(str(state_file))
    # child2.xml should be in the queue, index and child1 processed
    assert queue1 == ["http://resume.com/child2.xml"]
    assert processed1 == {"http://resume.com/index.xml", "http://resume.com/child1.xml"}
    assert urls1 == {"http://resume.com/pageA", "http://resume.com/pageB"}

    # --- Second Run (resume) ---
    args_run2 = [
        "sitemap_url_fetcher.py",
        # This URL isn't strictly needed for resume, but argparse requires it
        "http://resume.com/index.xml",
        str(output_file),
        "--state-file",
        str(state_file),
        "--resume",
        # No limit this time
    ]
    monkeypatch.setattr("sys.argv", args_run2)
    sitemap_url_fetcher.main()

    # Check final output (script appends during resume)
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
    urls_final = set(line for line in content.strip().split("\n") if line)
    # Should contain all 4 URLs A, B, C, D
    assert len(urls_final) == 4
    expected_all_urls = {
        "http://resume.com/pageA",
        "http://resume.com/pageB",
        "http://resume.com/pageC",
        "http://resume.com/pageD",
    }
    assert urls_final == expected_all_urls

    # Check final state (state file should be removed on completion)
    assert not state_file.exists()
    # We can also load the state *before* main removes it to double-check
    # (Requires modification to test or main, maybe less ideal)
