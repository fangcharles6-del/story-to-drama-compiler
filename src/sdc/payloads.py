"""Pydantic payloads shared across the Temporal client, workflow, and worker."""

from pydantic import BaseModel, ConfigDict

from sdc.contracts import RunState


class DurableResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: RunState
    path: str | None
    attempts: int
