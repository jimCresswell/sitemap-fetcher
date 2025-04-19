# Sitemap URL Fetcher

## Project Overview

Sitemap URL Fetcher is a command-line tool that takes a root sitemap URL, recursively fetches child sitemaps, and extracts all URLs to an output file.

## Key Components

- **sitemap_url_fetcher.py**: Main script containing:
  - `fetch_sitemap`: fetches and parses sitemap XML.
  - `is_sitemap_index`: detects sitemap indexes.
  - `extract_loc_elements`: extracts `<loc>` elements.
  - `save_state` / `load_state`: persist and restore crawl state for resuming.
  - `main`: orchestrates fetching, parsing, queue management, and signal handling.
- **tests/**: Contains pytest tests validating fetching and parsing logic.
- **Makefile**: Defines commands for installation, running, testing, linting, and type checking.
- **requirements.txt**: Lists Python dependencies.
- **.flake8**: Configuration file for the flake8 linter.
- **.pylintrc**: Configuration file for the pylint linter.

## Dependencies

- Python 3.7+
- `requests` >= 2.32.3
- `types-requests` >= 2.32.0
- `pytest` >= 8.3.5
- `pytest-cov` >= 4.0.0 (for test coverage)
- `flake8` >= 7.0.0 (linter)
- `pylint` >= 2.15.0 (linter - check version if needed)
- `mypy` >= 1.8.0 (static type checker)
- `black` (formatter - installed via editor extension or pip)

## Usage

```bash
python sitemap_url_fetcher.py <start_sitemap_url> <output_file> [options]
```

- `<start_sitemap_url>`: Root sitemap URL (e.g., `https://example.com/sitemap.xml`).
- `<output_file>`: Path to write discovered URLs, one per line.
- `-n`, `--max-urls`: Limit number of URLs for testing.
- `--resume`: Resume from a previous state file if exists.

## Testing

```bash
pytest
make test # Includes coverage reporting
make coverage # Generates HTML coverage report
```

## Linting & Type Checking

```bash
make lint       # Run flake8 and pylint
make lint-flake8 # Run only flake8
make lint-pylint # Run only pylint
make typecheck  # Run mypy
```

## Project Structure

```text
venv/                   # Virtual environment (gitignored)
.agent/                 # AI agent files
├── project-summary.md  # This summary
├── test-improvement-plan.md # Plan for enhancing tests
Makefile                # Build and test commands
sitemap_url_fetcher.py  # Main CLI script
README.md               # Usage and setup guide
requirements.txt        # Python dependencies
.flake8                 # Flake8 configuration
.pylintrc              # Pylint configuration
tests/                  # Test suite
└── __init__.py         # Makes 'tests' a package
