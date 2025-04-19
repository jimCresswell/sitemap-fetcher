# Sitemap Fetcher Test Improvement Plan

## 1. Goal

To achieve near-complete test coverage for `sitemap_url_fetcher.py`, fix existing test linting issues, and improve documentation in both the main script and tests. This will increase confidence in the script's robustness, especially for long-running tasks.

## 2. Current State

- **Tests (`tests/test_sitemap_url_fetcher.py`):** Cover basic functionality:
  - `is_sitemap_index`: Covered.
  - `extract_loc_elements`: Covered for index and urlset.
  - `save_state`/`load_state`: Covered.
  - Signal Handling (`SIGINT`/`KeyboardInterrupt`): Basic integration tested (`test_interrupt_handler_saves_state`).
  - `fetch_sitemap`: Success case implicitly tested via mocks.
- **Coverage:** Not currently measured. Significant gaps expected, especially within the `main` function's logic paths and error handling.
- **Linting (Tests):** Several Pylint warnings exist (unused imports, general exception, unused argument).
- **Documentation:** Docstrings exist for most functions but could be more detailed, especially for tests and the `main` function logic.

## 3. Proposed Steps

### Step 3.1: Setup Coverage Reporting

1. **Add Dependency:** Add `pytest-cov` to `requirements.txt`.
2. **Install:** Run `make install` or `pip install -r requirements.txt`.
3. **Update Makefile (`test` target):** Modify the `test` target to include coverage flags:

   ```makefile
   test:
    . venv/bin/activate && python -m pytest --cov=sitemap_url_fetcher --cov-report term-missing --maxfail=1 --disable-warnings
   ```

4. **Add Makefile (`coverage` target):** Add a new target for detailed HTML reports:

   ```makefile
   coverage:
    . venv/bin/activate && python -m pytest --cov=sitemap_url_fetcher --cov-report html --maxfail=1 --disable-warnings
    @echo "Coverage report saved to htmlcov/index.html"
   ```

5. **Baseline:** Run `make test` to get the initial coverage percentage.

### Step 3.2: Fix Test Linting Issues

Address the following Pylint warnings in `tests/test_sitemap_url_fetcher.py`:

- `Unused import json`: Remove the import.
- `Unused NamedTemporaryFile imported from tempfile`: Remove the import.
- `Unused fetch_sitemap imported from sitemap_url_fetcher`: Remove the import.
- `Raising too general exception: Exception` (in `DummyResponse.raise_for_status`): Change to raise `requests.exceptions.HTTPError(response=self)` for better simulation.
- `Unused argument 'url'` (in `fake_fetch_and_signal`): Rename to `_url` or add `# noqa: ARG001`.

### Step 3.3: Improve Test Documentation

1. Add clear, concise docstrings to _all_ test functions (`test_is_sitemap_index_true`, `test_extract_loc_elements_index_and_urlset`, etc.) explaining _what_ specific scenario or behavior each test verifies.
2. Add docstrings to helper classes/functions (`DummyResponse`, `patch_requests`).

### Step 3.4: Enhance `fetch_sitemap` Unit Tests

Create specific unit tests for `fetch_sitemap` (mocking `requests.get`) that verify:

- Handling of `requests.exceptions.HTTPError` (e.g., 404, 500 status codes) via `resp.raise_for_status()`.
- Handling of `xml.etree.ElementTree.ParseError` when response content is invalid XML.
- Handling of `requests.exceptions.Timeout`.
- Handling of `requests.exceptions.ConnectionError`.

### Step 3.5: Expand `main` Function Integration Tests

These tests will simulate running the script with different arguments and conditions, patching external dependencies like `requests.get`, `sys.exit`, `os.kill`, and file system operations where necessary.

1. **Refactor Test Setup:** Consider creating pytest fixtures for common setups (e.g., patching `sys.argv`, `sys.exit`, creating temp directories).
2. **Argument Parsing:**
   - Test running with `--limit N` and verify only N URLs are written.
   - Test using the default state file name (`<output_file>.state.json`).
   - Test using a custom `--state-file` path.
3. **Resume Workflow:**
   - Simulate a run that gets interrupted (using the `os.kill` method from `test_interrupt_handler_saves_state`).
   - Verify the state file is created correctly.
   - Run the script again with the `--resume` flag.
   - Verify that the initial state (queue, seen_sitemaps, urls) is loaded correctly from the state file.
   - Verify the run continues and produces the complete, correct output.
4. **Main Loop Logic:**
   - Test skipping a sitemap URL that is already in `seen_sitemaps`.
   - Test the `try/except` block around `fetch_sitemap`: Simulate `RequestException` or `ParseError` and verify the error is printed to `stderr` and the loop continues.
   - Test processing of a sitemap index: Verify child sitemap URLs are correctly extracted and added to the queue (including relative URLs resolved with `urljoin`).
   - Test processing of a regular URL set: Verify page URLs are correctly extracted and added to the `urls` set (including relative URLs resolved with `urljoin`).
   - Test `--limit` being reached _during_ processing of a URL set (verify loop termination/queue clearing).
5. **Successful Completion:**
   - Test a full successful run (small example) and verify the content of the output file is exactly as expected (sorted, correct URLs, respecting limit if applied).
   - Verify the state file is removed upon successful completion.
6. **Intermittent `save_state`:** Evaluate if the `save_state` call _after_ the main loop is necessary, given the signal handler. If kept, add a test to verify its behavior; otherwise, remove it.

### Step 3.6: Improve Source Code Documentation

1. Review and enhance docstrings in `sitemap_url_fetcher.py`, particularly for `main` (explaining its overall flow, argument handling, loop logic, state management) and `handle_exit`.
2. Add inline comments `#` within `main` to clarify complex sections (e.g., state loading logic, loop conditions, URL processing branches).

### Step 3.7: Iterate with Coverage

1. After implementing fixes and new tests, run `make coverage`.
2. Open `htmlcov/index.html` in a browser.
3. Analyze the report, focusing on lines/branches marked as missed in `sitemap_url_fetcher.py`.
4. Write targeted tests specifically to cover these missed lines/branches.
5. Repeat steps 1-4 until coverage reaches the desired level (e.g., >95%) or remaining gaps are deemed unreasonable/unnecessary to cover.

## 4. Tools

- `pytest`
- `pytest-cov`
- `pytest` fixtures
- `monkeypatch` (pytest fixture)
- Mocking (`unittest.mock` or similar, if needed beyond monkeypatch)

## 5. Success Metrics

- Test coverage for `sitemap_url_fetcher.py` significantly increased (target >95%).
- All test linting warnings resolved.
- Clear and comprehensive docstrings/comments in tests and source code.
- A robust test suite that covers main functionality, error handling, and edge cases.

## Step 4: Code Refactoring (Next Phase)

Once the test suite provides sufficient confidence (Steps 3.1 - 3.7), the next major phase involves refactoring the core `sitemap_url_fetcher.py` script for better organization, maintainability, and testability.

### 4.1 Goals

- Improve code structure by separating concerns into different modules/classes.
- Enhance encapsulation to manage state and dependencies more effectively.
- Maintain compatibility with existing functionality and command-line interface.
- Ensure development environment tools (IDE linters) and CI checks (Makefile commands) remain consistent.

### 4.2 Proposed Actions

1. **Identify Core Components:** Analyze `sitemap_url_fetcher.py` to identify distinct responsibilities (e.g., argument parsing, network fetching, XML parsing, state management, URL processing, file output).
2. **Design Class Structure:**
   - Define classes to encapsulate state and related logic (e.g., a `SitemapProcessor` class to manage the queue, processed sets, and main loop; a `SitemapFetcher` class for network interactions; potentially a `StateManager` class).
   - Plan the interaction between these classes.
3. **Create New Modules:** Split the code into logical Python files (e.g., `fetcher.py`, `parser.py`, `state.py`, `main.py` or `cli.py`).
4. **Implement Refactoring:**
   - Move existing functions and logic into the new classes and modules.
   - Adapt the entry point (`main` function in the new `main.py`/`cli.py`) to use the new class structure.
   - Pass dependencies (like the fetcher or state manager) explicitly where possible (dependency injection) instead of relying solely on global variables.
5. **Update Tests:** Refactor existing tests and add new ones to align with the new class/module structure. Tests should target individual classes (unit tests) and the overall application flow (integration tests).
6. **Verify Makefile:** Ensure all `make` targets (`run`, `test`, `lint`, `typecheck`) still function correctly with the new file structure. This might involve updating paths in the Makefile commands (e.g., `pylint sitemap_fetcher/ tests/` might become `pylint sitemap_fetcher/ tests/ --recursive=y` or similar depending on the new structure).
7. **Confirm Linter Consistency:** Double-check that VS Code uses the project's `.flake8` and `.pylintrc` configurations so that IDE feedback matches the `make lint` results.

### 4.3 Considerations

- Perform refactoring incrementally, running tests frequently.
- Ensure type hints are updated and maintained throughout the refactored code.
- Update documentation ([README.md](cci:7://file:///Users/jim/code/oak/sitemap_fetcher/README.md:0:0-0:0), [.agent/project-summary.md](cci:7://file:///Users/jim/code/oak/sitemap_fetcher/.agent/project-summary.md:0:0-0:0)) to reflect the new structure upon completion.
