# Repository guidance

- Python source lives in `src/sdc`; tests mirror public behavior in `tests`.
- Contracts are immutable Pydantic v2 models. Never add wall-clock values to compiled artifacts.
- Run `make check` before committing. Regenerate schemas with `make schemas` after contract changes.
- Runtime adapters must remain replaceable and tests must not call paid or remote generation services.

