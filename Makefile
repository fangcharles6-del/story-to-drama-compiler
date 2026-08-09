.PHONY: bootstrap schemas lint typecheck test demo verify-demo check
bootstrap:
	uv sync --frozen
schemas:
	uv run python -m sdc.schemas
lint:
	uv run ruff check .
typecheck:
	uv run mypy
test:
	uv run pytest -q
demo:
	uv run python -m sdc.demo
verify-demo:
	uv run python -m sdc.verify .artifacts/demo
check: lint typecheck test demo verify-demo

