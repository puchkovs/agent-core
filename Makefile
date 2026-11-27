PYTHON ?= python3

.PHONY: check test lint types examples build benchmark
check: lint types test examples
lint:
	$(PYTHON) -m ruff check src tests examples evaluation
	$(PYTHON) -m ruff format --check src tests examples evaluation
types:
	$(PYTHON) -m mypy src
test:
	$(PYTHON) -m pytest --cov=agent_core --cov-report=term-missing --cov-report=json --cov-fail-under=90
	$(PYTHON) evaluation/check_coverage.py coverage.json
examples:
	$(PYTHON) examples/offline_research.py
	$(PYTHON) examples/approved_workspace.py
	$(PYTHON) examples/uncertain_external.py
build:
	$(PYTHON) -m build
benchmark:
	$(PYTHON) evaluation/benchmark.py --output evaluation/results/overhead.json
