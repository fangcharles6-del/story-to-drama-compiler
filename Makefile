.PHONY: bootstrap schemas visual-prompt-profiles visual-prompt-profiles-check lint typecheck test integration demo verify-demo check
bootstrap:
	uv sync --frozen
schemas:
	uv run python -m sdc.schemas
visual-prompt-profiles:
	uv run python -m sdc.visual_prompt_profile_codegen --update
visual-prompt-profiles-check:
	uv run python -m sdc.visual_prompt_profile_codegen --check
lint:
	uv run ruff check .
typecheck:
	uv run mypy
test:
	uv run pytest -q --ignore=tests/integration
integration:
	docker compose up -d --wait
	uv run alembic downgrade base
	uv run alembic upgrade head
	uv run alembic downgrade 0002
	uv run alembic upgrade head
	uv run alembic check
	uv run pytest -q tests/integration
demo:
	uv run python -m sdc.demo
verify-demo:
	uv run python -m sdc.verify .artifacts/demo
check: visual-prompt-profiles-check lint typecheck test demo verify-demo
