.PHONY: install run test clean resume demo coverage lint lint-flake8 lint-pylint typecheck

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && python sitemap_url_fetcher.py https://www.thenational.academy/sitemap.xml urls.txt

resume:
	. venv/bin/activate && python sitemap_url_fetcher.py https://www.thenational.academy/sitemap.xml urls.txt --resume

demo:
	. venv/bin/activate && python sitemap_url_fetcher.py https://www.thenational.academy/sitemap.xml urls.txt -n 10

test:
	. venv/bin/activate && python -m pytest --cov=sitemap_url_fetcher --cov-report term-missing --maxfail=1 --disable-warnings

clean:
	rm -rf venv
	rm -f urls.txt

coverage:
	. venv/bin/activate && python -m pytest --cov=sitemap_url_fetcher --cov-report html --maxfail=1 --disable-warnings
	@echo "Coverage report saved to htmlcov/index.html"

lint-flake8:
	. venv/bin/activate && flake8 sitemap_url_fetcher.py tests/

lint-pylint:
	. venv/bin/activate && pylint sitemap_url_fetcher.py tests/

typecheck:
	. venv/bin/activate && mypy sitemap_url_fetcher.py tests/
