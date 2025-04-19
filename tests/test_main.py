# import sys - Removed unused import
from unittest.mock import MagicMock
import pytest
import json
import xml.etree.ElementTree as ET
import requests

from sitemap_fetcher.main import main as sitemap_main


# --- Tests for Main Function (Argument Parsing) ---


def test_main_argparse_missing_args(monkeypatch):
    """Tests that the main script exits if required arguments are missing."""

    args = ["sitemap-fetcher"]  # Missing required arguments
    monkeypatch.setattr("sys.argv", args)

    # Expect SystemExit because argparse should exit
    with pytest.raises(SystemExit):
        sitemap_main()


def test_main_argparse_invalid_limit(tmp_path, monkeypatch):
    """Tests that the main script exits if --limit is not a positive integer."""

    output_file = tmp_path / "output_invalid_limit.txt"
    args = [
        "sitemap-fetcher",
        "http://example.com",
        str(output_file),
        "--limit",
        "-1",
    ]
    monkeypatch.setattr("sys.argv", args)

    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)

    sitemap_main()  # Should exit because of validation in main

    mock_exit.assert_called_once_with(1)  # Check exit code


# Test the main exception handling block (lines 70-77, 81)
@pytest.mark.parametrize(
    "exception_to_raise, expected_error_message",
    [
        pytest.param(
            requests.exceptions.RequestException("Network Error"),
            "Network Error",
            id="request_exception",
        ),
        pytest.param(ET.ParseError("Invalid XML"), "Invalid XML", id="parse_error"),
        pytest.param(
            json.JSONDecodeError("Bad JSON", "", 0), "Bad JSON", id="json_decode_error"
        ),
        pytest.param(IOError("Cannot read file"), "Cannot read file", id="io_error"),
    ],
)
def test_main_processor_run_exceptions(
    mocker, capsys, exception_to_raise, expected_error_message
):
    """Tests that main catches exceptions from processor.run and exits."""
    args = [
        "http://example.com/main_error.xml",
        "output_main_error.txt",
    ]
    mocker.patch("sys.argv", ["sitemap_fetcher"] + args)
    mock_exit = mocker.patch("sys.exit")

    # Mock the Processor's run method to raise the specified exception
    mock_processor_run = mocker.patch(
        "sitemap_fetcher.processor.SitemapProcessor.run", side_effect=exception_to_raise
    )
    # Need to mock the constructor as well to prevent it from running
    mocker.patch(
        "sitemap_fetcher.processor.SitemapProcessor.__init__", return_value=None
    )

    sitemap_main()

    captured = capsys.readouterr()
    # Check that the error message is printed to stderr
    assert (
        f"An error occurred during processing: {expected_error_message}" in captured.err
    )
    # Check that sys.exit(1) was called
    mock_exit.assert_called_once_with(1)
    mock_processor_run.assert_called_once()  # Ensure run was called
