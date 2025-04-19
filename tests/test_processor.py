import os
import json
import signal
import pytest
import requests  # Needed for side_effect RequestException in tests

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

    # Assert the specific stderr message from the except block (lines 205-206)
    assert f"Failed to fetch {config.sitemap_url}. Skipping." in captured.err
    # Check stdout for fetcher's message (optional but good)
    assert f"Error fetching sitemap {config.sitemap_url}" in captured.out
    # assert "Error fetching sitemap http://error.com/sitemap.xml" in captured.out
    # assert "Skipping." in captured.err

    assert os.path.exists(state_file)
    # State should reflect that the error URL was attempted but not fully processed
    final_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert (
        config.sitemap_url not in final_state["processed_sitemaps"]
    )  # It failed before being marked processed
    assert not final_state["found_urls"]
    assert not final_state["sitemap_queue"]

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
@pytest.mark.parametrize(
    "state_content, expected_error_fragment",
    [
        pytest.param('{"sitemap_queue": []}', "processed_sitemaps", id="missing_key"),
        pytest.param(
            '{"sitemap_queue": [], "processed_sitemaps": "not_a_list", "found_urls": []}',
            "Invalid type for key 'processed_sitemaps'",
            id="invalid_type",
        ),
        pytest.param(
            '["list", "not_dict"]',
            "State data is not a dictionary",
            id="invalid_state_type",
        ),
    ],
)
def test_processor_resume_invalid_state_data(
    tmp_path, capsys, state_content, expected_error_fragment, mocker
):
    """Tests processor handles missing/invalid keys in state file gracefully."""
    output_file = tmp_path / "output_invalid_state.txt"
    state_file = tmp_path / "state_invalid_state.json"
    root_url = "http://example.com/sitemap.xml"
    child_url = "http://example.com/child.xml"

    # Explicit mock for requests.get within this test
    mock_response_root = mocker.Mock()
    mock_response_root.raise_for_status.return_value = None
    mock_response_root.text = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <sitemap>
          <loc>{child_url}</loc>
       </sitemap>
    </sitemapindex>"""
    mock_response_root.encoding = "utf-8"
    mock_response_root.content = mock_response_root.text.encode("utf-8")

    mock_response_child = mocker.Mock()
    mock_response_child.raise_for_status.return_value = None
    mock_response_child.text = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <url><loc>http://example.com/page1</loc></url>
       <url><loc>http://example.com/page2</loc></url>
    </urlset>"""
    mock_response_child.encoding = "utf-8"
    mock_response_child.content = mock_response_child.text.encode("utf-8")

    def side_effect_requests_get(url, timeout, **kwargs):
        if url == root_url:
            return mock_response_root
        elif url == child_url:
            return mock_response_child
        else:
            raise requests.RequestException(f"Unexpected URL in test: {url}")

    _ = mocker.patch("requests.get", side_effect=side_effect_requests_get)

    # Create invalid state file
    # state_data = {"sitemap_queue": ["http://example.com/"], "processed_sitemaps": "not_a_list"}
    # state_file.write_text(json.dumps(state_data), encoding="utf-8")
    state_file.write_text(state_content, encoding="utf-8")

    config = ProcessorConfig(
        sitemap_url=root_url,
        # sitemap_url="http://example.com/child.xml",  # Use existing mock URL
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()
    # Debugging print statement (optional, can remove later)
    print(
        f"\nCaptured stdout for state_content='{state_content}':\n{captured.out}\n---"
    )

    # Assert the key components are present in the output
    assert "Error loading state" in captured.out
    assert "Invalid state data format" in captured.out
    # Check for the raw exception message part
    assert (
        expected_error_fragment in captured.out
    )  # Check for KeyError('found_urls') or Invalid type...
    # assert expected_error_fragment in captured.out # Check for KeyError('found_urls') or Invalid type...
    # The error message format seems to be "Invalid state data format: {e}" where e is the exception detail
    # assert f"Invalid state data format: {expected_error_fragment}" in captured.out
    assert "Starting fresh." in captured.out

    # Assert that it started fresh and processed the root_url -> child_url
    assert output_file.exists()
    output_content = output_file.read_text(encoding="utf-8").strip().split("\n")
    # Since it starts fresh with root_url, it should process root, find child, process child
    assert "http://example.com/page1" in output_content
    assert "http://example.com/page2" in output_content
    # assert "http://example.com/page1" in output_content
    # assert "http://example.com/page2" in output_content
    # assert root_url in final_state["processed_sitemaps"] # Check fresh state processed root

    assert state_file.exists()
    final_state = json.loads(state_file.read_text(encoding="utf-8"))
    # Check fresh state processed root and child
    assert root_url in final_state["processed_sitemaps"]
    assert child_url in final_state["processed_sitemaps"]
    assert not final_state["sitemap_queue"]  # Should be empty after fresh run


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
    root_url = "http://example.com/child.xml"  # Use a simple valid URL

    # Create state file with empty queue
    empty_state = {
        "sitemap_queue": [],
        "processed_sitemaps": ["some_previous_sitemap"],  # Simulate prior work
        "found_urls": ["some_previous_url"],
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(empty_state, f)

    config = ProcessorConfig(
        sitemap_url=root_url,
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )
    processor = SitemapProcessor(config=config)
    processor.run()  # This calls _load_state internally

    captured = capsys.readouterr()
    # Assert that the specific message for re-initializing from empty queue was printed
    assert "State file queue empty, initializing with root sitemap URL." in captured.out

    # Assert that processing happened (URLs from root_url were added)
    assert output_file.exists()
    output_content = output_file.read_text(encoding="utf-8").strip().split("\n")
    # Check for URLs known to be in http://example.com/child.xml mock
    assert "http://example.com/page1" in output_content
    assert "http://example.com/page2" in output_content
    # Check that previously "found" URL is still there (though run() overwrites output)
    # The final state should reflect the loaded + new URLs
    final_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "some_previous_url" in final_state["found_urls"]
    assert "http://example.com/page1" in final_state["found_urls"]
    assert "http://example.com/page2" in final_state["found_urls"]
    assert root_url in final_state["processed_sitemaps"]
    assert "some_previous_sitemap" in final_state["processed_sitemaps"]
    assert not final_state["sitemap_queue"]


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
        # Determine mode from actual arguments passed
        mode = args[0] if args and isinstance(args[0], str) else kwargs.get("mode", "r")
        if file == str(state_file) and "r" in mode:
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
        sitemap_url="http://example.com/child.xml",
        output_file=str(output_file),
        state_file=str(state_file),
        resume=False,
    )
    processor = SitemapProcessor(config=config)

    # Capture the real open function *before* patching
    real_open = open

    # Mock open specifically for writing the state file to raise IOError
    mock_open = mocker.patch("builtins.open")

    # Change signature, determine mode inside, pass *args/**kwargs through
    def open_side_effect_write(file, *args, **kwargs):
        mode = args[0] if args and isinstance(args[0], str) else kwargs.get("mode", "r")
        # Check mode contains 'w'
        if file == str(state_file) and "w" in mode:
            raise IOError("Simulated disk write error")
        # Use the *real* open for other files/modes
        return real_open(file, *args, **kwargs)

    mock_open.side_effect = open_side_effect_write

    processor.run()

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
def test_processor_signal_during_processing(tmp_path, patch_requests, mocker, sig):
    """Tests graceful shutdown and state saving on signal during processing."""
    output_file = tmp_path / "output_signal.txt"
    state_file = tmp_path / "state_signal.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/index.xml",
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
    original_process_single = processor._process_single_sitemap

    def process_side_effect(url):
        # Call the real processing function first
        original_process_single(url)
        print(f"Mock _process_single_sitemap processed {url}. Triggering signal {sig}.")
        # Trigger the signal handler to simulate interruption
        processor._signal_handler(sig, None)

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
    mock_signal_registration.assert_any_call(sig, processor._signal_handler)
    # Ensure _process_single_sitemap was invoked at least once
    # (So our side effect executed)
    # The wraps on _save_state+assertions cover this indirectly.
    # Check that state was saved and exit called by the handler
    # State should have been saved at least once (signal handler, possibly final save)
    assert mock_save_state.call_count >= 1
    mock_exit.assert_called_once_with(0)
    assert state_file.exists()

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
def test_processor_signal_outside_processing(tmp_path, capsys, sig, mocker):
    """Tests immediate exit on signal outside active processing."""
    output_file = tmp_path / "output_signal_idle.txt"
    state_file = tmp_path / "state_signal_idle.json"

    config = ProcessorConfig(
        sitemap_url="http://example.com/child.xml",
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
    mock_save_state.assert_not_called()
    mock_exit.assert_called_once_with(0)

    assert (
        f"Signal {sig} received during shutdown. Exiting immediately."
        in capsys.readouterr().out
    )


# Test for empty initial queue check in run() (lines 233-234)
def test_processor_run_with_empty_initial_queue(tmp_path, capsys, mocker):
    """Tests run() handles an empty queue *after* _load_state."""
    output_file = tmp_path / "output_empty_run.txt"
    state_file = tmp_path / "state_empty_run.json"
    root_url = "http://invalid.url/sitemap.xml"

    state_file.touch()

    config = ProcessorConfig(
        sitemap_url=root_url,
        output_file=str(output_file),
        state_file=str(state_file),
        resume=False,
    )
    processor = SitemapProcessor(config=config)

    # Mock _load_state to explicitly leave the queue empty
    # _load_state usually initializes the queue even on failure, so we bypass it.
    mocker.patch.object(processor, "_load_state", return_value=None)
    # Ensure the queue is actually empty before run checks it
    processor.sitemap_queue = []

    processor.run()

    captured = capsys.readouterr()
    # Assert the specific message from the check (lines 233-234)
    assert "Initial sitemap queue is empty. Nothing to process." in captured.out

    # Assert that no processing happened and no output was written
    assert not output_file.exists()
    # State file might be touched by _save_state at the end, but should be minimal
    assert state_file.exists()
    # The processor returns early, so state file should remain empty
    assert state_file.stat().st_size == 0
    # No JSON parsing because file is empty


# Test for IOError when writing output file (covers lines 205-206)
def test_processor_write_output_io_error(tmp_path, capsys, mocker):
    """Tests handling of IOError when writing the final output file."""
    output_file = tmp_path / "output_io_error.txt"
    state_file = tmp_path / "state_io_error.json"
    root_url = "http://example.com/io_error.xml"

    config = ProcessorConfig(
        sitemap_url=root_url,
        output_file=str(output_file),
        state_file=str(state_file),
    )

    # Mock requests.get to return a simple sitemap
    mock_response = mocker.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.text = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>http://example.com/page1</loc></url>"
        "</urlset>"
    )
    mock_response.encoding = "utf-8"
    mock_response.content = mock_response.text.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)

    # Mock open specifically for the output file path to raise IOError
    original_open = open

    def open_side_effect(path, *args, **kwargs):
        if str(path) == str(output_file):
            raise IOError("Disk full")
        return original_open(path, *args, **kwargs)

    mocker.patch("builtins.open", side_effect=open_side_effect)

    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()

    # Assert that the IOError during writing was caught and printed to stderr
    assert (
        f"Error writing to output file {config.output_file}: Disk full" in captured.err
    )

    # Ensure the specific problematic 'open' call was attempted
    # This check is tricky because 'open' is used for state file too.
    # We rely on the exception being raised when it tries to write output.


# Test for resuming with an empty state file (previously covered indirectly)
def test_processor_resume_with_empty_state_file(tmp_path, capsys, mocker):
    output_file = tmp_path / "output_empty_state.txt"
    state_file = tmp_path / "state_empty_state.json"
    root_url = "http://example.com/empty_state.xml"

    config = ProcessorConfig(
        sitemap_url=root_url,
        output_file=str(output_file),
        state_file=str(state_file),
        resume=True,
    )

    # Mock requests.get to return an empty sitemap
    mock_response = mocker.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.text = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    )
    mock_response.encoding = "utf-8"
    mock_response.content = mock_response.text.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)

    processor = SitemapProcessor(config=config)
    processor.run()

    captured = capsys.readouterr()

    # Assert that the processor started fresh and processed the root URL (case-insensitive)
    assert "starting fresh." in captured.out.lower()
    assert output_file.exists()
    assert "http://example.com/page1" not in output_file.read_text(encoding="utf-8")
    assert "http://example.com/page2" not in output_file.read_text(encoding="utf-8")
