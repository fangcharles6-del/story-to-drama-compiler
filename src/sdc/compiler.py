"""Pure deterministic compilation pipeline."""

import hashlib
import json

from sdc.contracts import (
    NIR,
    PIR,
    AssemblyItem,
    AssemblyPlan,
    AudioCue,
    AudioMasterClock,
    GenerationJob,
    JobGraph,
    NIRScene,
    PIRShot,
    StoryInput,
)


def stable_id(kind: str, value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{kind}_{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def compile_story(story: StoryInput) -> tuple[NIR, PIR, AudioMasterClock, JobGraph, AssemblyPlan]:
    source = story.model_dump(mode="json")
    nir_id = stable_id("nir", source)
    scenes = tuple(
        NIRScene(
            id=stable_id("scene", [nir_id, i]),
            ordinal=i,
            narrative=b.text,
            duration_ms=b.duration_ms,
        )
        for i, b in enumerate(story.beats)
    )
    nir = NIR(id=nir_id, title=story.title, scenes=scenes)
    cursor = 0
    shots: list[PIRShot] = []
    for scene in scenes:
        shots.append(
            PIRShot(
                id=stable_id("shot", scene.id),
                scene_id=scene.id,
                ordinal=scene.ordinal,
                prompt=scene.narrative,
                start_ms=cursor,
                duration_ms=scene.duration_ms,
            )
        )
        cursor += scene.duration_ms
    pir = PIR(id=stable_id("pir", nir_id), shots=tuple(shots))
    cues = tuple(
        AudioCue(
            id=stable_id("cue", s.id),
            shot_id=s.id,
            start_ms=s.start_ms,
            end_ms=s.start_ms + s.duration_ms,
        )
        for s in shots
    )
    clock = AudioMasterClock(id=stable_id("clock", pir.id), duration_ms=cursor, cues=cues)
    jobs = tuple(
        GenerationJob(
            id=stable_id("job", s.id),
            shot_id=s.id,
            prompt=s.prompt,
            duration_ms=s.duration_ms,
            idempotency_key=stable_id("generate", s.id),
        )
        for s in shots
    )
    graph = JobGraph(id=stable_id("graph", pir.id), jobs=jobs)
    plan = AssemblyPlan(
        id=stable_id("assembly", [graph.id, clock.id]),
        clock_id=clock.id,
        items=tuple(
            AssemblyItem(job_id=j.id, start_ms=s.start_ms, duration_ms=s.duration_ms)
            for j, s in zip(jobs, shots, strict=True)
        ),
    )
    return nir, pir, clock, graph, plan
