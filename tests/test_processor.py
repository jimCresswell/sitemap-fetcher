import os
import json

from sitemap_fetcher.processor import SitemapProcessor, ProcessorConfig


def test_processor_success(tmp_path, patch_requests):
    """Tests SitemapProcessor runs successfully and produces correct output."""
    output_file = tmp_path / "output_proc_success.txt"
    state_file = tmp_path / "state_proc_success.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/index.xml",
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "http://example.com/page1" in content
        assert "http://example.com/page2" in content
    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as f:
        final_state = json.load(f)
        assert not final_state["sitemap_queue"]
        assert set(final_state["processed_sitemaps"]) == {
            "http://example.com/index.xml",
            "http://example.com/child.xml",
        }
        assert set(final_state["found_urls"]) == {
            "http://example.com/page1",
            "http://example.com/page2",
        }


def test_processor_handles_request_exception(tmp_path, patch_requests, capsys):
    """Tests SitemapProcessor handles RequestException gracefully."""
    output_file = tmp_path / "output_error.txt"
    state_file = tmp_path / "state_error.json"

    config = ProcessorConfig(
        sitemap_url="http://error.com/sitemap.xml",
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    assert "Error fetching sitemap http://error.com/sitemap.xml" in captured.out
    assert "Skipping." in captured.err
    assert os.path.exists(state_file)
    assert os.path.exists(output_file)
    assert output_file.read_text(encoding="utf-8") == ""


def test_processor_handles_parse_error(tmp_path, patch_requests, capsys):
    """Tests SitemapProcessor handles ET.ParseError gracefully."""
    output_file = tmp_path / "output_badxml.txt"
    state_file = tmp_path / "state_badxml.json"

    config = ProcessorConfig(
        sitemap_url="http://badxml.com/sitemap.xml",
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    assert "Error parsing XML from http://badxml.com/sitemap.xml" in captured.out
    assert "Skipping." in captured.err
    assert os.path.exists(state_file)
    assert os.path.exists(output_file)
    assert output_file.read_text(encoding="utf-8") == ""


def test_processor_honors_limit(tmp_path, patch_requests):
    """Tests that the --limit argument correctly limits fetched URLs."""
    output_file = tmp_path / "output_limited.txt"
    state_file = tmp_path / "state_limited.json"
    limit = 2

    config = ProcessorConfig(
        sitemap_url="http://limited.com/sitemap.xml",
        output_file=str(output_file),
        state_file=str(state_file),
        limit=limit,
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        urls = f.read().strip().split("\n")
        assert len(urls) == limit
        assert "http://limited.com/page1" in urls
        assert "http://limited.com/page2" in urls
        assert "http://limited.com/page3" not in urls

    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as f:
        final_state = json.load(f)
        assert len(final_state["found_urls"]) == limit
        assert not final_state["sitemap_queue"]
        assert final_state["processed_sitemaps"] == ["http://limited.com/sitemap.xml"]


def test_processor_resumes_correctly(tmp_path, patch_requests):
    """Tests that the processor resumes correctly using the state file."""
    output_file = tmp_path / "output_resume.txt"
    state_file = tmp_path / "state_resume.json"

    # --- Phase 1: Run partially and save state ---
    limit = 2
    config_phase1 = ProcessorConfig(
        sitemap_url="http://resume.com/index.xml",
        output_file=str(output_file),
        state_file=str(state_file),
        limit=limit,
    )
    processor_phase1 = SitemapProcessor(config=config_phase1)
    processor_phase1.run()

    # Create initial state using the *correct* keys for Phase 2
    initial_state_to_write = {
        "sitemap_queue": ["http://resume.com/child2.xml"],
        "processed_sitemaps": [
            "http://resume.com/index.xml",
            "http://resume.com/child1.xml",
        ],
        "found_urls": ["http://resume.com/pageA", "http://resume.com/pageB"],
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(initial_state_to_write, f)

    # Check intermediate state (read back what was written)
    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as f:
        read_state = json.load(f)
        assert len(read_state["found_urls"]) == limit
        assert "http://resume.com/child2.xml" in read_state["sitemap_queue"]

    # --- Phase 2: Run again with --resume ---
    config_phase2 = ProcessorConfig(
        sitemap_url="http://resume.com/index.xml",
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
        limit=None,
    )
    processor_phase2 = SitemapProcessor(config=config_phase2)

    processor_phase2.run()

    # --- Asserts ---
    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        final_urls = set(f.read().strip().split("\n"))
        assert len(final_urls) == 4
        assert final_urls == {
            "http://resume.com/pageA",
            "http://resume.com/pageB",
            "http://resume.com/pageC",
            "http://resume.com/pageD",
        }

    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as f:
        final_state = json.load(f)
        assert len(final_state["found_urls"]) == 4
        assert not final_state["sitemap_queue"]
        assert set(final_state["processed_sitemaps"]) == {
            "http://resume.com/index.xml",
            "http://resume.com/child1.xml",
            "http://resume.com/child2.xml",
        }


# Test for invalid JSON in state file
def test_processor_resume_invalid_json(tmp_path, capsys):
    """Tests processor handles invalid JSON in state file gracefully."""
    output_file = tmp_path / "output_invalid_json.txt"
    state_file = tmp_path / "state_invalid_json.json"
    # Create invalid JSON file (e.g., trailing comma)
    state_file.write_text(
        '{"sitemap_queue": ["http://example.com/"],}', encoding="utf-8"
    )

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # Use existing mock URL
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    # Need a processor instance to call run
    processor = SitemapProcessor(config=config)
    processor.run()  # Should not raise error, should print warning and start fresh

    captured = capsys.readouterr()
    assert (
        f"Error loading or decoding state file {state_file}" in captured.out
    )  # Check stdout for specific error start
    assert "Starting fresh." in captured.out  # Confirms it didn't use bad state


# Test for invalid data structure in state file
def test_processor_resume_invalid_state_data(tmp_path, capsys):
    """Tests processor handles missing/invalid keys in state file gracefully."""
    output_file = tmp_path / "output_invalid_data.txt"
    state_file = tmp_path / "state_invalid_data.json"
    # Create state file with missing keys
    state_file.write_text('{"missing_key": ["http://example.com/"]}', encoding="utf-8")

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # Use existing mock URL
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    # Need a processor instance to call run
    processor = SitemapProcessor(config=config)
    processor.run()  # Should not raise error, should print warning and start fresh

    captured = capsys.readouterr()
    assert (
        f"Error loading state from {state_file}: Invalid state data format"
        in captured.out
    )  # Check stdout
    assert "Starting fresh." in captured.out  # Confirms it didn't use bad state


# Test for IOError during output writing
def test_processor_write_output_io_error(tmp_path, patch_requests, mocker, capsys):
    """Tests processor handles IOError during output file writing."""
    output_file = tmp_path / "output_io_error.txt"
    state_file = tmp_path / "state_io_error.json"

    # Mock open to raise IOError only when writing to the output file
    # Corrected mocker usage: need original open for state file
    original_open = open

    def mock_open(file, mode="r", **kwargs):
        if file == str(output_file) and "w" in mode:
            raise IOError("Disk full")
        # Ensure state file can still be opened/read/written
        return original_open(file, mode, **kwargs)

    mocker.patch("builtins.open", side_effect=mock_open)

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # Use simple sitemap
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    assert f"Error writing to output file {output_file}: Disk full" in captured.err
    # State should still be saved successfully before the output write fails
    assert os.path.exists(state_file)


# Test that processing stops when URL limit is hit (checks lines 194-195)
def test_processor_stops_processing_at_limit(tmp_path, patch_requests, capsys):
    """Tests processor stops queuing/processing sitemaps when limit is reached."""
    output_file = tmp_path / "output_stop_limit.txt"
    state_file = tmp_path / "state_stop_limit.json"
    limit = 2  # Limit should be hit after processing child1.xml

    config = ProcessorConfig(
        sitemap_url="http://resume.com/index.xml",  # Sitemap index with 2 children (2 URLs each)
        output_file=str(output_file),
        state_file=str(state_file),
        limit=limit,
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    # Check output file has only URLs from the first child
    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        urls = f.read().strip().split("\n")
        assert len(urls) == limit
        assert "http://resume.com/pageA" in urls
        assert "http://resume.com/pageB" in urls
        assert "http://resume.com/pageC" not in urls  # Should not be present

    # Check state file to ensure the second sitemap wasn't processed
    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as f:
        final_state = json.load(f)
        assert len(final_state["found_urls"]) == limit
        # Check that the second child sitemap is NOT in processed list
        assert "http://resume.com/child2.xml" not in final_state["processed_sitemaps"]
        # Check processor output to be sure
        assert "Processing sitemap: http://resume.com/child2.xml" not in captured.out

    assert f"URL limit ({limit}) reached. Stopping." in captured.out
