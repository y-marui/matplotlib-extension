.PHONY: install lint format type test all update-charter

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

type:
	uv run mypy matplotlib_extension

test:
	uv run pytest

all: lint type test

update-charter: ## dev-charter を最新版に更新
	curl -fsSL https://raw.githubusercontent.com/y-marui/dev-charter/main/scripts/install.sh | CHARTER_UPDATE_ONLY=1 bash
