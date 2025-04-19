# Sitemap URL Fetcher

## Project Overview

Sitemap URL Fetcher is a command-line tool that takes a root sitemap URL, recursively fetches child sitemaps, and extracts all unique page URLs to an output file. It supports resuming interrupted runs, limiting the number of URLs fetched, polite request throttling, and a configurable User-Agent via a `.env` file.

## Key Components

- **`sitemap_fetcher/`**: Main package directory.
  - `__init__.py`: Makes the directory a package.
  - `main.py`: Handles command-line argument parsing (`argparse`) and orchestrates the overall process by instantiating and running `SitemapProcessor`.
  - `processor.py`: Defines `SitemapProcessor` class which manages the main processing loop, state (queue, processed sitemaps, found URLs), configuration (`ProcessorConfig` dataclass), signal handling, state saving/loading, and output writing.
  - `fetcher.py`: Contains the `SitemapFetcher` class responsible for retrieving sitemap content via HTTP (`requests`), managing a polite request interval (throttling) between requests, and setting a custom User-Agent header. Reads configuration (`EMAIL`, `REQUEST_INTERVAL_SECONDS`) from a `.env` file using `python-dotenv`.
  - `parser.py`: Contains functions (`is_sitemap_index`, `extract_loc_elements`) for parsing XML content (`xml.etree.ElementTree`) to identify sitemap types and extract relevant URLs.
  - `state_manager.py`: Defines `StateManager` class for saving and loading application state (queue, processed sitemaps, found URLs) to/from a JSON file, enabling the resume functionality.
- **`tests/`**: Contains pytest tests (`test_*.py`) validating the functionality of individual components and the integrated workflow.
  - `conftest.py`: Contains shared pytest fixtures (e.g., mocking HTTP requests).
- **`Makefile`**: Defines commands for installation, running, testing, linting, type checking, and cleaning.
- **`requirements.txt`**: Lists Python dependencies.
- **`setup.cfg`**: Configuration file for the black formatter.

## Dependencies

- Python 3.7+
- `requests` >= 2.32.3
- `types-requests` >= 2.32.0
- `pytest` >= 8.3.5
- `python-dotenv` >= 1.1.0
- `pytest-cov` >= 6.1.1
- `pytest-mock` >= 3.14.0
- `flake8` >= 7.2.0
- `mypy` >= 1.15.0
- `black` (formatter - typically used via editor integration or pre-commit hook)

## Usage

```bash
python -m sitemap_fetcher.main <start_sitemap_url> <output_file> [options]
```

- `<start_sitemap_url>`: Root sitemap URL (e.g., `https://example.com/sitemap.xml`).
- `<output_file>`: Path to write discovered URLs, one per line.
- `-l`, `--limit`: Limit number of URLs to fetch.
- `-r`, `--resume`: Resume from the state file.
- `-s`, `--state-file`: Specify a custom state file path.

## Testing

```bash
make test      # Run tests with coverage reporting (text summary)
```

## Linting & Type Checking

```bash
make lint
make typecheck
make format
```

## Project Structure

```text
.git/
.venv/                  # Virtual environment (gitignored)
.agent/
├── project-summary.md # This summary
├── test-improvement-plan.md
├── test-improvement-prompt-generation.md
├── .env.example         # Example environment variables file
htmlcov/                # HTML Coverage reports (gitignored)
.pytest_cache/          # Pytest cache (gitignored)
.mypy_cache/            # MyPy cache (gitignored)
sitemap_fetcher/
├── __init__.py
├── fetcher.py
├── main.py
├── parser.py
├── processor.py
├── state_manager.py
tests/
├── __init__.py
├── conftest.py
├── test_fetcher.py
├── test_main.py
├── test_parser.py
└── test_processor.py
.flake8
.gitignore
.env                    # Environment variables (gitignored by default, but may be checked in)
.pylintrc
LICENSE
Makefile
README.md
requirements.txt
pyproject.toml
```
