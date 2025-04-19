.PHONY: install run test clean resume demo lint typecheck update-deps format

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
	. venv/bin/activate && python -m pytest --cov=sitemap_fetcher --cov-report term-missing

clean:
	rm -rf venv
	rm -f urls.txt

format:
	. venv/bin/activate && python -m black sitemap_fetcher/ tests/

# Lint target (flake8 only, configs in setup.cfg)
lint:
	. venv/bin/activate && python -m flake8 sitemap_fetcher/ tests/

typecheck:
	. venv/bin/activate && python -m mypy sitemap_fetcher/ tests/
