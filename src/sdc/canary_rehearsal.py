"""Local-only SDC-CANARY-001 rehearsal with no Provider network adapter."""

from __future__ import annotations

import argparse
import asyncio
from fractions import Fraction
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.contracts import GenerationJob, JobGraph, ProviderProfile, ProviderRequest, RunState
from sdc.persistence import (
    ArtifactRecord,
    AttemptRecord,
    LiveAuthorizationUseRecord,
    RunRecord,
)
from sdc.provider import FakeProvider, request_fingerprint
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import FakeCanaryRehearsalWorkflow

TASK_QUEUE: Final[Literal["sdc-canary-001-v01-rehearsal"]] = (
    "sdc-canary-001-v01-rehearsal"
)
DEFAULT_RUN_ID = "sdc-canary-001-v01-rehearsal-run"
JOB_ID = "sdc-canary-001-v01-rehearsal-job"
GRAPH_ID = "sdc-canary-001-v01-rehearsal-graph"


class RehearsalReport(BaseModel):
    """Deterministic cardinality and safety evidence for one local rehearsal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    task_queue: Literal["sdc-canary-001-v01-rehearsal"] = TASK_QUEUE
    provider: Literal["fake"] = "fake"
    state: RunState
    runs: Literal[1] = 1
    jobs: Literal[1] = 1
    attempts: Literal[1] = 1
    maximum_attempt: Literal[1] = 1
    current_candidates: Literal[1] = 1
    provider_submit_calls: Literal[1] = 1
    provider_http_posts: Literal[0] = 0
    live_authorizations: Literal[0] = 0
    activity_max_concurrency: Literal[1] = 1
    aspect_ratio: Literal["9:16"] = "9:16"
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    fps: Literal[24] = 24
    duration_ms: Literal[4000] = 4000
    text_only: Literal[True] = True
    generate_audio: Literal[False] = False
    artifact_path: str


def build_rehearsal_inputs(run_id: str) -> tuple[JobGraph, ProviderRequest]:
    job = GenerationJob(
        id=JOB_ID,
        shot_id="sdc-canary-001-v01-rehearsal-shot",
        prompt="A paper lantern glows softly against a plain midnight background.",
        duration_ms=4000,
        idempotency_key="sdc-canary-001-v01-rehearsal-candidate",
    )
    graph = JobGraph(id=GRAPH_ID, jobs=(job,))
    draft = ProviderRequest(
        run_id=run_id,
        job_id=job.id,
        attempt=1,
        provider="fake",
        model="fake-v1",
        prompt=job.prompt,
        duration_ms=4000,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        input_materials=(),
        request_fingerprint="0" * 64,
    )
    return graph, draft.model_copy(
        update={"request_fingerprint": request_fingerprint(draft)}
    )


def build_rehearsal_activities(
    sessions: async_sessionmaker[AsyncSession],
    output_root: Path,
) -> tuple[RuntimeActivities, FakeProvider]:
    provider = FakeProvider(width=1080, height=1920, fps=24)
    profile = ProviderProfile(
        provider="fake",
        model="fake-v1",
        aspect_ratio="9:16",
        resolution="1080p",
        min_duration_ms=4000,
        max_duration_ms=4000,
        max_in_flight=1,
        generate_audio=False,
    )
    return (
        RuntimeActivities(
            PostgresRuntimeStore(sessions),
            provider,
            output_root,
            profile,
            live_guard=None,
        ),
        provider,
    )


def _video_evidence(ffprobe: dict[str, object]) -> tuple[int, int, Fraction, int]:
    streams = cast(list[dict[str, object]], ffprobe.get("streams", []))
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("FakeProvider rehearsal produced no video stream")
    width, height = int(str(video.get("width", 0))), int(str(video.get("height", 0)))
    fps = Fraction(str(video.get("avg_frame_rate", "0/1")))
    duration_ms = round(float(str(video.get("duration", 0))) * 1000)
    if duration_ms == 0:
        format_evidence = cast(dict[str, object], ffprobe.get("format", {}))
        duration_ms = round(float(str(format_evidence.get("duration", 0))) * 1000)
    return width, height, fps, duration_ms


async def run_rehearsal(
    *,
    run_id: str,
    database_url: str,
    temporal_address: str,
    output_root: Path,
) -> RehearsalReport:
    graph, request = build_rehearsal_inputs(run_id)
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT 1")) != 1:
                raise RuntimeError("PostgreSQL health query failed")
        client = await Client.connect(
            temporal_address,
            data_converter=pydantic_data_converter,
        )
        await client.service_client.check_health()
        activities, provider = build_rehearsal_activities(sessions, output_root)
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[FakeCanaryRehearsalWorkflow],
            activities=[
                activities.submit_canary_generation,
                activities.watch_generation,
                activities.download_generation,
                activities.set_run_state,
            ],
            max_concurrent_activities=1,
        ):
            results = await client.execute_workflow(
                FakeCanaryRehearsalWorkflow.run,
                args=[run_id, graph, request],
                id=run_id,
                task_queue=TASK_QUEUE,
            )
        if len(results) != 1 or results[0].state is not RunState.SUCCEEDED:
            state = results[0].state.value if results else "NO_RESULT"
            raise RuntimeError(f"FakeProvider rehearsal entered {state}")
        if results[0].attempts != 1:
            raise RuntimeError("FakeProvider rehearsal produced an unexpected Attempt count")

        async with sessions() as session:
            run_count = await session.scalar(
                select(func.count()).select_from(RunRecord).where(RunRecord.id == run_id)
            )
            attempts = await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id)
            )
            maximum_attempt = await session.scalar(
                select(func.max(AttemptRecord.attempt)).where(AttemptRecord.run_id == run_id)
            )
            candidates = await session.scalar(
                select(func.count())
                .select_from(ArtifactRecord)
                .where(ArtifactRecord.run_id == run_id, ArtifactRecord.is_current.is_(True))
            )
            live_authorizations = await session.scalar(
                select(func.count())
                .select_from(LiveAuthorizationUseRecord)
                .where(LiveAuthorizationUseRecord.run_id == run_id)
            )
            artifact = await session.scalar(
                select(ArtifactRecord).where(
                    ArtifactRecord.run_id == run_id,
                    ArtifactRecord.is_current.is_(True),
                )
            )
        if (
            run_count != 1
            or attempts != 1
            or maximum_attempt != 1
            or candidates != 1
            or live_authorizations != 0
            or provider.submit_calls != 1
            or artifact is None
            or artifact.ffprobe is None
        ):
            raise RuntimeError("FakeProvider rehearsal cardinality or safety invariant failed")
        width, height, fps, duration_ms = _video_evidence(artifact.ffprobe)
        if (width, height, fps, duration_ms) != (1080, 1920, Fraction(24), 4000):
            raise RuntimeError(
                "FakeProvider rehearsal media must be 1080x1920, 24 fps, and 4000 ms"
            )
        return RehearsalReport(
            run_id=run_id,
            state=RunState.SUCCEEDED,
            artifact_path=artifact.path,
        )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local zero-Provider-network canary")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://sdc:sdc@127.0.0.1:5432/sdc",
    )
    parser.add_argument("--temporal-address", default="127.0.0.1:7233")
    parser.add_argument("--output-root", type=Path, default=Path(".artifacts/canary-rehearsal"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = asyncio.run(
        run_rehearsal(
            run_id=args.run_id,
            database_url=args.database_url,
            temporal_address=args.temporal_address,
            output_root=args.output_root,
        )
    )
    rendered = report.model_dump_json(indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
