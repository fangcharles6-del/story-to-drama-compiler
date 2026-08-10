"""Pydantic payloads shared across the Temporal client, workflow, and worker."""

from pydantic import BaseModel, ConfigDict

from sdc.contracts import ProviderFailureClass, ProviderTaskState, RunState


class DurableResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: RunState
    path: str | None
    attempts: int


class SubmitResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: RunState
    attempt: int
    provider_task_id: str | None = None


class WatchResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    attempt: int
    provider_task_id: str
    task_state: ProviderTaskState
    failure_class: ProviderFailureClass | None = None
