from pathlib import Path


def test_alembic_online_environment_uses_asyncpg_pattern() -> None:
    source = Path("migrations/env.py").read_text()
    assert "async_engine_from_config" in source
    assert "async with connectable.connect()" in source
    assert "await connection.run_sync(do_run_migrations)" in source
    assert "asyncio.run(run_async_migrations())" in source
    assert "engine_from_config(" not in source.replace("async_engine_from_config(", "")
    assert "postgresql+asyncpg://" in Path("alembic.ini").read_text()


def test_provider_failure_diagnostic_migration_extends_0005_without_backfill() -> None:
    source = Path("migrations/versions/0006_provider_failure_diagnostics.py").read_text()
    assert 'revision = "0006"' in source and 'down_revision = "0005"' in source
    for name in (
        "provider_http_status",
        "provider_error_code",
        "provider_request_id",
        "provider_error_message",
    ):
        assert f'Column("{name}"' in source
    assert "nullable=True" in source
    assert "server_default" not in source
    assert "create_index" not in source
