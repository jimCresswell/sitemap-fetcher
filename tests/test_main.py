# import sys - Removed unused import
from unittest.mock import MagicMock

import pytest

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
