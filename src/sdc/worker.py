"""Production Temporal worker wiring; adapters are constructed only at process startup."""

import asyncio
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.provider import FakeProvider
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import DramaWorkflow


async def run() -> None:
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
        FakeProvider(),
        Path(os.environ.get("SDC_OUTPUT_ROOT", ".artifacts/runtime")),
    )
    client = await Client.connect(temporal_address, data_converter=pydantic_data_converter)
    try:
        await Worker(
            client,
            task_queue=task_queue,
            workflows=[DramaWorkflow],
            activities=[activities.generate, activities.set_run_state],
        ).run()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
