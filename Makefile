.PHONY: bootstrap schemas visual-prompt-profiles visual-prompt-profiles-check visual-reference-prompt-compiler visual-reference-prompt-compiler-check generated-reference-candidate generated-reference-candidate-check lint typecheck test integration demo verify-demo check
bootstrap:
	uv sync --frozen
schemas:
	uv run python -m sdc.schemas
visual-prompt-profiles:
	uv run python -m sdc.visual_prompt_profile_codegen --update
visual-prompt-profiles-check:
	uv run python -m sdc.visual_prompt_profile_codegen --check
visual-reference-prompt-compiler:
	uv run python -m sdc.visual_reference_prompt_compiler_codegen --update
visual-reference-prompt-compiler-check:
	uv run python -m sdc.visual_reference_prompt_compiler_codegen --check
generated-reference-candidate:
	uv run python -m sdc.generated_reference_candidate_codegen --update
generated-reference-candidate-check:
	uv run python -m sdc.generated_reference_candidate_codegen --check
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
check: visual-prompt-profiles-check visual-reference-prompt-compiler-check generated-reference-candidate-check lint typecheck test demo verify-demo
