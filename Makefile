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
	. venv/bin/activate && python -m sitemap_fetcher.main https://www.thenational.academy/sitemap.xml urls.txt -n 10

test:
	. venv/bin/activate && python -m pytest --cov=sitemap_fetcher --cov-report term-missing --maxfail=1 --disable-warnings

clean:
	rm -rf venv
	rm -f urls.txt

coverage:
	. venv/bin/activate && python -m pytest --cov=sitemap_fetcher --cov-report html --maxfail=1 --disable-warnings
	@echo "Coverage report saved to htmlcov/index.html"

lint-flake8:
	. venv/bin/activate && python -m flake8 sitemap_fetcher/ tests/

lint-pylint:
	. venv/bin/activate && python -m pylint sitemap_fetcher/ tests/

typecheck:
	. venv/bin/activate && python -m mypy sitemap_fetcher/ tests/
