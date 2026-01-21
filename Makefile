.PHONY: all web test coverage diagram lint format typecheck clean

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
	@rm -rf dist build


