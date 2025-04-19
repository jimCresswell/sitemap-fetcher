# Sitemap URL Fetcher

## Prerequisites

- Python 3.7+ installed on your system
- (Optional but recommended) [virtualenv](https://pypi.org/project/virtualenv/) or `python -m venv`

## Setup

```bash
# 1. Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate     # on macOS/Linux
venv\Scripts\activate.bat    # on Windows

# 2. Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python sitemap_url_fetcher.py <start_sitemap_url> <output_file> [options]
```

- `<start_sitemap_url>`: the root sitemap (e.g. `https://…/sitemap.xml`)
- `<output_file>`: path to write all discovered URLs, one per line

You can also limit for testing:

```bash
python sitemap_url_fetcher.py https://www.thenational.academy/sitemap.xml urls.txt -n 10
```

To resume after interruption:

```bash
python sitemap_url_fetcher.py https://www.thenational.academy/sitemap.xml urls.txt --resume
```

## Testing

1. Make sure your virtualenv is active and deps are installed:

   ```bash
   . venv/bin/activate # Ensure virtual environment is active
   pip install -r requirements.txt # Install/update dependencies
   ```

2. Run tests:

   ```bash
   pytest
   ```

You can also run the test suite via `make test`.

## Linting & Type Checking

This project uses `black` for formatting, `flake8` and `pylint` for linting, and `mypy` for type checking.

Configuration files:
- `.flake8`: Configures flake8 rules (e.g., max line length).
- `.pylintrc`: Configures pylint rules (e.g., disabling specific checks, line length).
- `pyproject.toml`: (Optional) Can be used for `black` and `mypy` configuration if needed.

Run checks using the Makefile:

```bash
make lint       # Run both flake8 and pylint
make lint-flake8 # Run only flake8
make lint-pylint # Run only pylint
make typecheck  # Run mypy
```

## (Optional) Makefile

For quicker setup/run/test:

```makefile
.PHONY: install run test clean lint-flake8 lint-pylint lint typecheck

install:
  python3 -m venv venv
  . venv/bin/activate && pip install -r requirements.txt # Install dependencies

run:
  . venv/bin/activate && python sitemap_url_fetcher.py <start_sitemap_url> <output_file> # Replace placeholders

test:
  . venv/bin/activate && pytest --maxfail=1 --disable-warnings -q # Run pytest

lint-flake8:
  . venv/bin/activate && flake8 sitemap_url_fetcher.py tests/ # Run flake8 linter

lint-pylint:
  . venv/bin/activate && pylint sitemap_url_fetcher.py tests/ # Run pylint linter

lint: lint-flake8 lint-pylint # Run both linters

typecheck:
  . venv/bin/activate && mypy sitemap_url_fetcher.py tests/ # Run mypy type checker

clean:
  rm -rf venv
  rm -f urls.txt
```
