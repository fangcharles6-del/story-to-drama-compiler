import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from sdc.runtime import PostgresRuntimeStore


class SessionFactory:
    def __init__(self) -> None:
        self.active: set[int] = set()
        self.created = 0

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[object]:
        self.created += 1
        identity = self.created
        assert identity not in self.active
        self.active.add(identity)
        await asyncio.sleep(0)
        try:
            yield object()
        finally:
            self.active.remove(identity)


def test_runtime_store_keeps_session_factory_not_a_session() -> None:
    factory = SessionFactory()
    store = PostgresRuntimeStore(factory)  # type: ignore[arg-type]
    assert store._sessions is factory


@pytest.mark.asyncio
async def test_concurrent_transactions_get_distinct_sessions() -> None:
    factory = SessionFactory()

    async def transaction() -> None:
        async with factory.begin():
            await asyncio.sleep(0.01)

    await asyncio.gather(transaction(), transaction(), transaction())
    assert factory.created == 3
    assert factory.active == set()
