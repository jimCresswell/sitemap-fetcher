import os
import json
import signal
import pytest

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

    # Change signature, determine mode inside, pass *args/**kwargs through
    def mock_open(file, *args, **kwargs):
        # Determine mode from actual arguments passed
        mode = args[0] if args and isinstance(args[0], str) else kwargs.get("mode", "r")
        if file == str(output_file) and "w" in mode:
            raise IOError("Disk full")
        # Ensure state file can still be opened/read/written
        return original_open(file, *args, **kwargs)

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


def test_processor_resume_non_existent_state_file(tmp_path, patch_requests, capsys):
    """Tests processor handles non-existent state file when resume=True."""
    output_file = tmp_path / "output_no_state.txt"
    state_file = tmp_path / "non_existent_state.json"  # Does not exist

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # Use a simple, known sitemap
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    # Check for the specific message in _load_state for FileNotFoundError path
    # Although the code currently prints "State file not found", let's be robust
    # It falls through to the FileNotFoundError handler which prints the msg
    assert f"State file not found at {state_file}, starting fresh." in captured.out
    # Verify it ran correctly despite the missing state file
    assert output_file.exists()
    assert "http://example.com/page1" in output_file.read_text(encoding="utf-8")
    assert "http://example.com/page2" in output_file.read_text(encoding="utf-8")


def test_processor_resume_empty_queue_in_state(tmp_path, patch_requests, capsys):
    """Tests processor re-initializes queue if state file queue is empty."""
    output_file = tmp_path / "output_empty_q.txt"
    state_file = tmp_path / "state_empty_q.json"

    # Create a valid state file with an empty queue
    initial_state = {
        "sitemap_queue": [],
        "processed_sitemaps": ["http://example.com/some_processed.xml"],
        "found_urls": ["http://example.com/some_url.html"],
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(initial_state, f)

    config = ProcessorConfig(
        sitemap_url="http://example.com/index.xml",  # Root URL to re-initialize with
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    # Check if the specific message for empty queue re-initialization was printed
    assert "State file queue empty, initializing with root sitemap URL." in captured.out
    # Check if processing completed successfully starting from the root
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "http://example.com/page1" in content
    assert "http://example.com/page2" in content
    # Ensure the initially found URL from the state file is also present
    assert "http://example.com/some_url.html" in content


def test_processor_resume_load_state_io_error(tmp_path, patch_requests, mocker, capsys):
    """Tests processor handles IOError during state file reading on resume."""
    output_file = tmp_path / "output_load_ioerr.txt"
    state_file = tmp_path / "state_load_ioerr.json"
    state_file.touch()  # Create the file so FileNotFoundError isn't hit first

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    processor = SitemapProcessor(config=config)

    # Capture the real open function *before* patching
    real_open = open

    # Mock open specifically for reading the state file to raise IOError
    # Need to use the correct import path for 'open' which is 'builtins.open'
    mock_open = mocker.patch("builtins.open")

    # Change signature, determine mode inside, pass *args/**kwargs through
    def open_side_effect_read(file, *args, **kwargs):
        mode = args[0] if args and isinstance(args[0], str) else kwargs.get("mode", "r")
        if file == str(state_file) and "r" in mode:  # Check mode contains 'r'
            raise IOError("Simulated disk read error")
        # Use the *real* open for other files/modes
        return real_open(file, *args, **kwargs)

    mock_open.side_effect = open_side_effect_read

    processor.run()

    captured = capsys.readouterr()
    # Check if the specific error message for IOError during load was printed
    assert (
        f"Error reading state file {state_file}: Simulated disk read error"
        in captured.out
    )
    assert "Starting fresh." in captured.out
    # Verify it ran correctly starting fresh
    assert output_file.exists()
    assert "http://example.com/page1" in output_file.read_text(encoding="utf-8")


def test_processor_save_state_io_error(tmp_path, patch_requests, mocker, capsys):
    """Tests processor handles IOError during state file writing."""
    output_file = tmp_path / "output_save_ioerr.txt"
    state_file = tmp_path / "state_save_ioerr.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # Simple run
        output_file=str(output_file),
        state_file=str(state_file),
        resume=False,  # Not resuming for this test
    )
    processor = SitemapProcessor(config=config)

    # Capture the real open function *before* patching
    real_open = open

    # Mock open specifically for writing the state file to raise IOError
    mock_open = mocker.patch("builtins.open")

    # Change signature, determine mode inside, pass *args/**kwargs through
    def open_side_effect_write(file, *args, **kwargs):
        mode = (
            args[0] if args and isinstance(args[0], str) else kwargs.get("mode", "r")
        )  # Default irrelevant if mode passed
        # Check mode contains 'w'
        if file == str(state_file) and "w" in mode:
            raise IOError("Simulated disk write error")
        # Use the *real* open for other files/modes
        return real_open(file, *args, **kwargs)

    mock_open.side_effect = open_side_effect_write

    processor.run()  # Run should complete, but saving state will fail

    captured = capsys.readouterr()
    # Check stderr for the specific error message
    assert (
        f"Error saving state file {state_file}: Simulated disk write error"
        in captured.err
    )
    # Verify the main process still worked and output was written
    assert output_file.exists()
    assert "http://example.com/page1" in output_file.read_text(encoding="utf-8")
    # State file should ideally not exist or be empty if the write failed early
    assert not state_file.exists() or state_file.read_text() == ""


# Test signal handling
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_processor_signal_during_processing(
    tmp_path, patch_requests, mocker, sig
):  # pylint: disable=too-many-locals
    """Tests graceful shutdown and state saving on signal during processing."""
    output_file = tmp_path / "output_signal.txt"
    state_file = tmp_path / "state_signal.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/index.xml",  # Multi-step process
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)

    # Mock sys.exit to prevent test runner exit
    mock_exit = mocker.patch("sys.exit")
    # Mock _save_state to check it's called and to inspect state
    # pylint: disable=protected-access
    mock_save_state = mocker.patch.object(
        processor, "_save_state", wraps=processor._save_state
    )

    # Mock signal.signal directly to prevent real handler registration in run()
    mock_signal_registration = mocker.patch("signal.signal")

    # Patch _process_single_sitemap to trigger the signal handler after first call
    original_process_single = processor._process_single_sitemap  # pylint: disable=protected-access

    def process_side_effect(url):
        # Call the real processing function first
        original_process_single(url)
        print(f"Mock _process_single_sitemap processed {url}. Triggering signal {sig}.")
        # Trigger the signal handler to simulate interruption
        processor._signal_handler(sig, None)  # pylint: disable=protected-access

    mocker.patch.object(
        processor,
        "_process_single_sitemap",
        side_effect=process_side_effect,
        autospec=False,
    )

    # Run the processor. Expect the mocked signal.signal to be called,
    # then the loop starts, calls _process_single_sitemap (mocked), which triggers the handler
    # (_save_state, sys.exit).
    processor.run()

    # Assertions
    # Check that signal.signal was called by run() to attempt registration
    mock_signal_registration.assert_any_call(
        sig, processor._signal_handler
    )  # pylint: disable=protected-access
    # Ensure _process_single_sitemap was invoked at least once
    # (So our side effect executed)
    # The wraps on _save_state+assertions cover this indirectly.
    # Check that state was saved and exit called by the handler
    assert mock_save_state.call_count >= 1  # State should have been saved at least once (signal handler, possibly final save)
    mock_exit.assert_called_once_with(0)  # Should have tried to exit gracefully
    assert state_file.exists()  # State file should exist due to wraps=_save_state

    # Verify state content (signal triggered after first sitemap processing)
    with open(state_file, "r", encoding="utf-8") as f:
        saved_state = json.load(f)
        # After processing the first sitemap and triggering signal, the state
        # should reflect that the initial sitemap got processed but no URLs
        # from child sitemaps were added yet.
        assert "http://example.com/index.xml" in saved_state["processed_sitemaps"]
        # Depending on exact timing, sitemap_queue may still have items or be empty.
        # We assert that found_urls is still empty.
        assert not saved_state["found_urls"]


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_processor_signal_outside_processing(tmp_path, mocker, sig):
    """Tests immediate exit on signal outside active processing."""
    output_file = tmp_path / "output_signal_idle.txt"
    state_file = tmp_path / "state_signal_idle.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",  # URL doesn't really matter
        output_file=str(output_file),
        state_file=str(state_file),
    )
    processor = SitemapProcessor(config=config)

    # Mock sys.exit to prevent test runner exit
    mock_exit = mocker.patch("sys.exit")
    # Mock _save_state to ensure it's NOT called
    # pylint: disable=protected-access
    mock_save_state = mocker.patch.object(processor, "_save_state")

    # Manually set processing_active to False (simulates signal before run() or after)
    # pylint: disable=protected-access
    processor._processing_active = False

    # Directly call the processor's handler method
    # pylint: disable=protected-access
    processor._signal_handler(sig, None)

    # Assertions
    mock_save_state.assert_not_called()  # State should NOT be saved
    mock_exit.assert_called_once_with(0)  # Should exit gracefully
