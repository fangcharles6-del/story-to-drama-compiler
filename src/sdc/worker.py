"""Production Temporal worker wiring; adapters are constructed only at process startup."""

import asyncio
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.contracts import ProviderProfile
from sdc.provider import ARK_BASE_URL, ARK_MODEL, FakeProvider, Provider
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import DramaWorkflow


def provider_from_environment() -> tuple[Provider, ProviderProfile]:
    selected = os.environ.get("SDC_PROVIDER", "fake")
    if selected == "fake":
        return FakeProvider(), ProviderProfile(
            provider="fake", model="fake-v1", min_duration_ms=1, max_duration_ms=60_000
        )
    if selected != "volcengine_ark":
        raise ValueError("SDC_PROVIDER must be fake or volcengine_ark")
    key = os.environ.get("SDC_ARK_API_KEY", "")
    if not key:
        raise ValueError("SDC_ARK_API_KEY is required for volcengine_ark")
    model = os.environ.get("SDC_ARK_MODEL", ARK_MODEL)
    if model != ARK_MODEL:
        raise ValueError(f"SDC_ARK_MODEL is pinned to {ARK_MODEL}")
    # Worker-only import keeps httpx outside the workflow sandbox import graph.
    from sdc.ark_provider import VolcengineArkProvider

    return VolcengineArkProvider(
        key, model=model, base_url=os.environ.get("SDC_ARK_BASE_URL", ARK_BASE_URL)
    ), ProviderProfile(provider="volcengine_ark", model=ARK_MODEL)


async def run() -> None:
    database_url = os.environ.get(
        "SDC_DATABASE_URL", "postgresql+asyncpg://sdc:sdc@localhost:5432/sdc"
    )
    temporal_address = os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.environ.get("SDC_TASK_QUEUE", "sdc-generation")
    engine = create_async_engine(database_url)
    provider, profile = provider_from_environment()
    activities = RuntimeActivities(
        PostgresRuntimeStore(async_sessionmaker(engine, expire_on_commit=False)),
        # FakeProvider is the safe default. Deployments replace this construction with their
        # provider adapter; workflow code remains unchanged.
        provider,
        Path(os.environ.get("SDC_OUTPUT_ROOT", ".artifacts/runtime")),
        profile,
    )
    client = await Client.connect(temporal_address, data_converter=pydantic_data_converter)
    try:
        await Worker(
            client,
            task_queue=task_queue,
            workflows=[DramaWorkflow],
            activities=[
                activities.submit_generation,
                activities.watch_generation,
                activities.download_generation,
                activities.generate,
                activities.set_run_state,
            ],
            max_concurrent_activities=int(os.environ.get("SDC_ARK_MAX_IN_FLIGHT", "2")),
        ).run()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
