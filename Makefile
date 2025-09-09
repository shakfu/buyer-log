.PHONY: all web test coverage diagram clean

all: test


web: 
	@uv run python -m buyer.web

test:
	@echo "running tests"
	@uv run pytest

coverage:
	@echo "generating test coverage report"
	@uv run pytest --cov-report=html:cov_html --cov-report=term-missing --cov=buyer buyer/tests

diagram:
	@echo "generating entity-relation diagram to 'doc' folder"
	@uv run python buyer/models.py

clean:
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$/)" | xargs rm -rf
	@rm -rf .pytest_cache
	@rm -rf .coverage cov_html
	@rm -rf dist build


