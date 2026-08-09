from pathlib import Path


def test_alembic_online_environment_uses_asyncpg_pattern() -> None:
    source = Path("migrations/env.py").read_text()
    assert "async_engine_from_config" in source
    assert "async with connectable.connect()" in source
    assert "await connection.run_sync(do_run_migrations)" in source
    assert "asyncio.run(run_async_migrations())" in source
    assert "engine_from_config(" not in source.replace("async_engine_from_config(", "")
    assert "postgresql+asyncpg://" in Path("alembic.ini").read_text()
