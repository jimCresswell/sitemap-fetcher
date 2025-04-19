# Sitemap URL Fetcher

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

To generate an HTML coverage report:

```bash
make coverage
```

(Requires `pytest` and `pytest-cov`, installed via `make install`)

### Current Quality Snapshot (Apr 2025)

| Metric | Value |
| ------ | ----- |
| Unit / integration tests | **24** |
| Line coverage (via `pytest‑cov`) | **≈94 %** |
| Quality gates | All tests, `flake8`, `pylint`, `mypy` pass via Makefile |

## Linting & Type Checking

This project uses `black` for formatting, `flake8` and `pylint` for linting, and `mypy` for type checking.

Configuration files:

- `.flake8`: Configures flake8 rules.
- `.pylintrc`: Configures pylint rules.
- `pyproject.toml`: Configures black formatting rules.

Run checks using the Makefile:

```bash
make lint       # Run both flake8 and pylint on the sitemap_fetcher module and tests
make lint-flake8 # Run only flake8
make lint-pylint # Run only pylint
make typecheck  # Run mypy on the sitemap_fetcher module and tests
```

## (Optional) Makefile

The Makefile provides convenient shortcuts for common tasks.

```makefile
# Simplified Makefile snippet (see full file for details)
.PHONY: install run test clean resume demo coverage lint lint-flake8 lint-pylint typecheck update-deps

install:
    python3 -m venv venv
    . venv/bin/activate && pip install -r requirements.txt

update-deps:
    . venv/bin/activate && pur -r requirements.txt && make install

run:
    . venv/bin/activate && python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt

resume:
    . venv/bin/activate && python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt --resume

demo:
    . venv/bin/activate && python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt --limit 10

test:
    . venv/bin/activate && python -m pytest --cov=sitemap_fetcher --cov-report term-missing --maxfail=1 --disable-warnings

coverage:
    . venv/bin/activate && python -m pytest --cov=sitemap_fetcher --cov-report html --maxfail=1 --disable-warnings
    @echo "Coverage report saved to htmlcov/index.html"

lint-flake8:
    . venv/bin/activate && flake8 sitemap_fetcher/ tests/

lint-pylint:
    . venv/bin/activate && pylint sitemap_fetcher/ tests/

lint: lint-flake8 lint-pylint

typecheck:
    . venv/bin/activate && mypy sitemap_fetcher/ tests/

clean:
    rm -rf venv
    rm -f urls.txt urls.txt.state.json
    rm -rf htmlcov .pytest_cache .mypy_cache
    find . -type f -name '*.pyc' -delete
    find . -type d -name '__pycache__' -delete
