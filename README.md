# Sitemap URL Fetcher

A command-line tool to recursively fetch all unique page URLs from a starting XML sitemap. It supports resuming interrupted runs, limiting the number of URLs fetched, configurable request throttling, and a custom User-Agent.

## Prerequisites

- Python 3.7+ installed on your system
- (Optional but recommended) [virtualenv](https://pypi.org/project/virtualenv/) or `python -m venv`

## Setup

```bash
# Use the Makefile for convenience
make install

# Manual steps:
# 1. Create & activate a virtual environment
# python3 -m venv venv
# source venv/bin/activate     # on macOS/Linux
# venv\Scripts\activate.bat    # on Windows
#
# 2. Install dependencies
# pip install -r requirements.txt
```

## Configuration (`.env` file)

This tool uses a `.env` file in the project root for configuration. Create a `.env` file by copying `.env.example`:

```bash
cp .env.example .env
```

Then edit `.env` with your desired values:

```dotenv
# .env
EMAIL=your.email@example.com # Used in the User-Agent header for identification
REQUEST_INTERVAL_SECONDS=2   # Minimum seconds between requests (default: 2)
```

The User-Agent will be set to `Sitemap Fetcher: (+EMAIL)` if EMAIL is provided, otherwise just `Sitemap Fetcher`. Requests are automatically throttled to wait at least `REQUEST_INTERVAL_SECONDS` between fetches.

## Usage

```bash
python -m sitemap_fetcher.main <start_sitemap_url> <output_file> [options]
```

- `<start_sitemap_url>`: the root sitemap (e.g. `https://…/sitemap.xml`)
- `<output_file>`: path to write all discovered URLs, one per line

Available options:

- `-l LIMIT`, `--limit LIMIT`: Stop processing after finding LIMIT URLs.
- `-r`, `--resume`: Resume processing from the state file (`<output_file>.state.json` by default).
- `-s STATE_FILE`, `--state-file STATE_FILE`: Specify a custom path for the state file.

Example limiting URLs:

```bash
python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt --limit 10
```

Example resuming after interruption:

```bash
python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt --resume
```

## Testing

Run the full test suite, including coverage reporting, using the Makefile:

```bash
make test
```

(Requires `pytest`, `pytest-cov`, `pytest-mock`, and `python-dotenv`, installed via `make install`)

### Current Quality Snapshot (Apr 2025)

| Metric                           | Value                                         |
| -------------------------------- | --------------------------------------------- |
| Unit / integration tests         | **34**                                        |
| Line coverage (via `pytest‑cov`) | **≈96 %**                                     |
| Quality gates                    | All tests, `flake8`, `mypy` pass via Makefile |

## Linting & Type Checking

This project uses `black` for formatting, `flake8` for linting, and `mypy` for type checking.

Configuration files:

- `setup.cfg`

Run checks using the Makefile:

```bash
make lint       # Run flake8 on the sitemap_fetcher module and tests
make typecheck  # Run mypy on the sitemap_fetcher module and tests
make format     # Run black on the sitemap_fetcher module and tests
```
