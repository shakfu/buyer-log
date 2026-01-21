.PHONY: all test coverage diagram lint format typecheck clean build check upload-test upload

all: test

test:
	@echo "running tests"
	@uv run pytest

coverage:
	@echo "generating test coverage report"
	@uv run pytest --cov-report=html:cov_html --cov-report=term-missing --cov=buylog buylog/tests

diagram:
	@echo "generating entity-relation diagram to 'doc' folder"
	@uv run python buylog/models.py

lint:
	@uv run ruff check --fix src/

typecheck:
	@uv run mypy src/

format:
	@uv run ruff format src/

clean:
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$/)" | xargs rm -rf
	@rm -rf .pytest_cache
	@rm -rf .coverage cov_html
	@rm -rf dist build *.egg-info src/*.egg-info

build: clean
	@echo "building wheel and sdist"
	@uv build

check: build
	@echo "checking distribution with twine"
	@uv run twine check dist/*

upload-test: check
	@echo "uploading to TestPyPI"
	@uv run twine upload --repository testpypi dist/*

upload: check
	@echo "uploading to PyPI"
	@uv run twine upload dist/*
