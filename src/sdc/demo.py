"""Offline BUILD-001 vertical slice."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sdc.compiler import compile_story, stable_id
from sdc.contracts import RunEvent, RunState, StoryInput
from sdc.media import assemble, manifest
from sdc.provider import FakeProvider, generate_with_limit
from sdc.qc import verify


def dump(path: Path, value: object) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


async def run() -> None:
    root = Path(".artifacts/demo")
    segments = root / "segments"
    segments.mkdir(parents=True, exist_ok=True)
    story = StoryInput.model_validate_json(Path("examples/minimal_story.json").read_text())
    nir, pir, clock, graph, plan = compile_story(story)
    for name, value in [
        ("nir", nir),
        ("pir", pir),
        ("audio_clock", clock),
        ("job_graph", graph),
        ("assembly_plan", plan),
    ]:
        dump(root / f"{name}.json", value)
    events: list[RunEvent] = []
    paths: list[Path] = []
    attempts: list[int] = []
    for job in graph.jobs:
        result = await generate_with_limit(FakeProvider(), job, segments / f"{job.id}.mp4")
        assert result.path is not None
        paths.append(result.path)
        attempts.append(result.attempts)
        now = datetime.now(UTC).isoformat()
        events.append(
            RunEvent(
                id=stable_id("event", [job.id, "generated"]),
                run_id=graph.id,
                event_type="candidate.generated",
                state=RunState.SUCCEEDED,
                occurred_at=now,
                idempotency_key=job.idempotency_key,
                payload={"job_id": job.id, "attempt": result.attempts},
            )
        )
    output = root / "final.mp4"
    await assemble(paths, clock, output)
    release = manifest(output, clock.duration_ms)
    dump(root / "release_manifest.json", release)
    report = await verify(
        output, clock, release, len(paths), len(graph.jobs), [p.name for p in paths], max(attempts)
    )
    dump(root / "qc_report.json", report)
    dump(root / "run_events.json", [e.model_dump(mode="json") for e in events])
    if not report.passed:
        raise SystemExit("QC failed")
    print(f"demo passed: {output}")


if __name__ == "__main__":
    asyncio.run(run())
