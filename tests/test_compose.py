from pathlib import Path


def test_temporal_waits_for_healthy_postgres() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert """    depends_on:
      postgres:
        condition: service_healthy
""" in compose
