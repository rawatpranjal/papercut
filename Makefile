.PHONY: install install-dev install-all test lint typecheck check build clean publish-test publish

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src/papercutter --cov-report=term-missing

# Code quality
lint:
	ruff check src/

lint-fix:
	ruff check src/ --fix

typecheck:
	mypy src/

check: lint typecheck test

# Building
build:
	pip install build
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Publishing
publish-test:
	pip install twine
	twine upload --repository testpypi dist/*

publish:
	pip install twine
	twine upload dist/*

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000
