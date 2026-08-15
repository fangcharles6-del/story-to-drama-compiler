"""Production Temporal worker wiring; adapters are constructed only at process startup."""

import asyncio
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.canary import LiveSubmissionGuard
from sdc.contracts import ProviderProfile
from sdc.provider import FakeProvider, Provider
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import CanaryWorkflow, DramaWorkflow


def provider_from_environment() -> tuple[Provider, ProviderProfile]:
    selected = os.environ.get("SDC_PROVIDER", "fake")
    if selected == "fake":
        return FakeProvider(), ProviderProfile(
            provider="fake", model="fake-v1", min_duration_ms=1, max_duration_ms=60_000
        )
    if selected != "volcengine_ark":
        raise ValueError("SDC_PROVIDER must be fake or volcengine_ark")
    raise ValueError(
        "volcengine_ark worker startup is disabled until an evidence-bound runtime contract "
        "is delivered"
    )


def live_guard_from_environment() -> LiveSubmissionGuard | None:
    if os.environ.get("SDC_PROVIDER", "fake") == "fake":
        return None
    raise ValueError(
        "legacy live authorization loading is disabled until an evidence-bound runtime contract "
        "is delivered"
    )


async def run() -> None:
    provider, profile = provider_from_environment()
    live_guard = live_guard_from_environment()
    database_url = os.environ.get(
        "SDC_DATABASE_URL", "postgresql+asyncpg://sdc:sdc@localhost:5432/sdc"
    )
    temporal_address = os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.environ.get("SDC_TASK_QUEUE", "sdc-generation")
    engine = create_async_engine(database_url)
    activities = RuntimeActivities(
        PostgresRuntimeStore(async_sessionmaker(engine, expire_on_commit=False)),
        # FakeProvider is the safe default. Deployments replace this construction with their
        # provider adapter; workflow code remains unchanged.
        provider,
        Path(os.environ.get("SDC_OUTPUT_ROOT", ".artifacts/runtime")),
        profile,
        live_guard,
    )
    client = await Client.connect(temporal_address, data_converter=pydantic_data_converter)
    try:
        await Worker(
            client,
            task_queue=task_queue,
            workflows=[DramaWorkflow, CanaryWorkflow],
            activities=[
                activities.submit_generation,
                activities.submit_canary_generation,
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
