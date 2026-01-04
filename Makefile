DEPS_MANAGER := uv
EXECUTOR := $(DEPS_MANAGER) run

.PHONY: all help test pc pci lint format x

help: ## Show this help.
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

sync:
	$(DEPS_MANAGER) sync --all-groups --all-extras

test: ## Run tests with pytest
	$(EXECUTOR) pytest $(ARGS)

test-integration: ## Run integration tests with pytest
	$(EXECUTOR) pytest -m "py_moov_integration" -n auto --no-cov $(ARGS)

pc: pre-commit ## Run pre-commit on all files
pre-commit:
	$(EXECUTOR) pre-commit run --all-files $(ARGS)

pci: pre-commit-install ## Install pre-commit hooks
pre-commit-install:
	$(EXECUTOR) pre-commit install $(ARGS)
	$(EXECUTOR) pre-commit install -t commit-msg $(ARGS)

types: ## Run type checking with pyright
	$(EXECUTOR) pyright $(ARGS)

lint: ## Lint code with ruff
	$(EXECUTOR) ruff check $(ARGS)

format: ## Check formatting with ruff
	$(EXECUTOR) ruff format --check $(ARGS)

x: lx fx ## Fix lint and formatting (ruff)

lx: lint-fix
lint-fix:
	$(EXECUTOR) ruff check --fix $(ARGS)

fx: format-fix
format-fix:
	$(EXECUTOR) ruff format $(ARGS)

docs-serve: ## Serve the documentation locally
	$(EXECUTOR) mkdocs serve

docs-build: ## Build the documentation site
	$(EXECUTOR) mkdocs build --clean