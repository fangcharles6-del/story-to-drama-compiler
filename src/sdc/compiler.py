"""Pure deterministic compilation pipeline."""

import hashlib
import json

from sdc.contracts import (
    NIR,
    NIRV2,
    PIR,
    PIRV2,
    AssemblyItem,
    AssemblyPlan,
    AudioCue,
    AudioMasterClock,
    CharacterAssetBinding,
    CreativeSampleCompilation,
    CreativeSampleShotSpec,
    CreativeSampleSpec,
    DialogueLine,
    GenerationJob,
    JobGraph,
    NIRScene,
    NIRSceneV2,
    PIRShot,
    StoryboardShotV2,
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


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _creative_prompt(
    spec: CreativeSampleSpec,
    shot: CreativeSampleShotSpec,
    lines: tuple[DialogueLine, ...],
) -> str:
    scene = next(item for item in spec.scene_bibles if item.scene_id == shot.scene_id)
    character_by_id = {item.character_id: item for item in spec.character_bibles}
    parts = [
        f"Scene: {scene.visual_description}",
        f"Narrative: {shot.narrative}",
        f"Visual direction: {shot.visual_direction}",
        f"Action: {shot.action}",
        f"Shot size: {shot.shot_size.value}",
        f"Camera angle: {shot.camera_angle.value}",
        f"Camera movement: {shot.camera_movement.value}",
    ]
    if shot.character_ids:
        parts.append(
            "Characters: "
            + "; ".join(
                f"{character_by_id[item].name}: {character_by_id[item].visual_description}"
                for item in shot.character_ids
            )
        )
        parts.append(
            "Emotion: "
            + "; ".join(
                f"{character_by_id[item].name}: {shot.emotion_by_character[item]}"
                for item in shot.character_ids
            )
        )
        parts.append(
            "Wardrobe: "
            + "; ".join(
                f"{character_by_id[item].name}: {shot.wardrobe_by_character[item]}"
                for item in shot.character_ids
            )
        )
    parts.extend(
        (
            "Props: " + (", ".join(shot.props) if shot.props else "none"),
            f"Continuity notes: {shot.continuity_notes}",
        )
    )
    if lines:
        parts.append(
            "Dialogue: "
            + " | ".join(
                f"{character_by_id[line.character_id].name}: {line.text}" for line in lines
            )
        )
    return "\n".join(parts)


def compile_creative_sample(spec: CreativeSampleSpec) -> CreativeSampleCompilation:
    """Compile one validated creative sample without changing the released v1 pipeline."""
    source = spec.model_dump(mode="json")
    spec_sha256 = _canonical_sha256(source)
    nir_id = stable_id("nirv2", source)
    line_by_id = {item.line_id: item for item in spec.dialogue}
    character_by_id = {item.character_id: item for item in spec.character_bibles}

    nir_scenes: list[NIRSceneV2] = []
    for scene_bible in spec.scene_bibles:
        source_shots = tuple(item for item in spec.shots if item.scene_id == scene_bible.scene_id)
        dialogue_ids = tuple(line_id for shot in source_shots for line_id in shot.dialogue_line_ids)
        character_ids = tuple(
            bible.character_id
            for bible in spec.character_bibles
            if any(bible.character_id in shot.character_ids for shot in source_shots)
        )
        start_ms = source_shots[0].start_ms
        duration_ms = sum(item.duration_ms for item in source_shots)
        narrative = " ".join(item.narrative for item in source_shots)
        scene_content = {
            "character_ids": character_ids,
            "dialogue_line_ids": dialogue_ids,
            "duration_ms": duration_ms,
            "narrative": narrative,
            "nir_id": nir_id,
            "ordinal": scene_bible.ordinal,
            "scene_asset_version_id": scene_bible.active_asset_version_id,
            "scene_bible_id": scene_bible.scene_id,
            "start_ms": start_ms,
        }
        nir_scenes.append(
            NIRSceneV2(
                id=stable_id("nir_scene_v2", scene_content),
                scene_bible_id=scene_bible.scene_id,
                scene_asset_version_id=scene_bible.active_asset_version_id,
                ordinal=scene_bible.ordinal,
                narrative=narrative,
                start_ms=start_ms,
                duration_ms=duration_ms,
                character_ids=character_ids,
                dialogue_line_ids=dialogue_ids,
            )
        )
    nir = NIRV2(
        id=nir_id,
        title=spec.title,
        seed=spec.seed,
        duration_ms=spec.duration_ms,
        character_bibles=spec.character_bibles,
        scene_bibles=spec.scene_bibles,
        dialogue=spec.dialogue,
        scenes=tuple(nir_scenes),
    )

    nir_scene_by_bible_id = {item.scene_bible_id: item for item in nir.scenes}
    storyboard_shots: list[StoryboardShotV2] = []
    for source_shot in spec.shots:
        lines = tuple(line_by_id[item] for item in source_shot.dialogue_line_ids)
        character_assets = tuple(
            CharacterAssetBinding(
                character_id=character_id,
                asset_version_id=character_by_id[character_id].active_asset_version_id,
            )
            for character_id in source_shot.character_ids
        )
        scene_bible = next(
            item for item in spec.scene_bibles if item.scene_id == source_shot.scene_id
        )
        nir_scene = nir_scene_by_bible_id[source_shot.scene_id]
        prompt = _creative_prompt(spec, source_shot, lines)
        shot_content = {
            "action": source_shot.action,
            "camera_angle": source_shot.camera_angle.value,
            "camera_movement": source_shot.camera_movement.value,
            "character_assets": tuple(item.model_dump(mode="json") for item in character_assets),
            "continuity_notes": source_shot.continuity_notes,
            "dialogue_line_ids": source_shot.dialogue_line_ids,
            "duration_ms": source_shot.duration_ms,
            "emotion_by_character": source_shot.emotion_by_character,
            "narrative": source_shot.narrative,
            "nir_scene_id": nir_scene.id,
            "ordinal": source_shot.ordinal,
            "prompt": prompt,
            "props": source_shot.props,
            "scene_asset_version_id": scene_bible.active_asset_version_id,
            "scene_bible_id": scene_bible.scene_id,
            "shot_size": source_shot.shot_size.value,
            "start_ms": source_shot.start_ms,
            "visual_direction": source_shot.visual_direction,
            "wardrobe_by_character": source_shot.wardrobe_by_character,
        }
        storyboard_shots.append(
            StoryboardShotV2(
                id=stable_id("storyboard_shot_v2", shot_content),
                nir_scene_id=nir_scene.id,
                scene_bible_id=scene_bible.scene_id,
                scene_asset_version_id=scene_bible.active_asset_version_id,
                ordinal=source_shot.ordinal,
                narrative=source_shot.narrative,
                visual_direction=source_shot.visual_direction,
                emotion_by_character=source_shot.emotion_by_character,
                action=source_shot.action,
                shot_size=source_shot.shot_size,
                camera_angle=source_shot.camera_angle,
                camera_movement=source_shot.camera_movement,
                wardrobe_by_character=source_shot.wardrobe_by_character,
                props=source_shot.props,
                continuity_notes=source_shot.continuity_notes,
                prompt=prompt,
                start_ms=source_shot.start_ms,
                duration_ms=source_shot.duration_ms,
                character_assets=character_assets,
                dialogue_line_ids=source_shot.dialogue_line_ids,
            )
        )
    pir_content = {
        "duration_ms": spec.duration_ms,
        "nir_id": nir.id,
        "shots": tuple(item.model_dump(mode="json") for item in storyboard_shots),
    }
    pir = PIRV2(
        id=stable_id("pirv2", pir_content),
        nir_id=nir.id,
        duration_ms=spec.duration_ms,
        shots=tuple(storyboard_shots),
    )

    clock = AudioMasterClock(
        id=stable_id("clockv2", [pir.id, spec.duration_ms]),
        duration_ms=spec.duration_ms,
        cues=tuple(
            AudioCue(
                id=stable_id("cuev2", shot.id),
                shot_id=shot.id,
                start_ms=shot.start_ms,
                end_ms=shot.start_ms + shot.duration_ms,
            )
            for shot in pir.shots
        ),
    )
    jobs = tuple(
        GenerationJob(
            id=stable_id("jobv2", shot.id),
            shot_id=shot.id,
            prompt=shot.prompt,
            duration_ms=shot.duration_ms,
            idempotency_key=stable_id("generatev2", shot.id),
        )
        for shot in pir.shots
    )
    graph = JobGraph(id=stable_id("graphv2", pir.id), jobs=jobs)
    plan = AssemblyPlan(
        id=stable_id("assemblyv2", [graph.id, clock.id]),
        clock_id=clock.id,
        items=tuple(
            AssemblyItem(job_id=job.id, start_ms=shot.start_ms, duration_ms=shot.duration_ms)
            for job, shot in zip(jobs, pir.shots, strict=True)
        ),
    )
    compilation_id = stable_id(
        "creative_sample",
        [spec_sha256, nir.id, pir.id, clock.id, graph.id, plan.id],
    )
    return CreativeSampleCompilation(
        id=compilation_id,
        spec_sha256=spec_sha256,
        nir=nir,
        pir=pir,
        audio_clock=clock,
        job_graph=graph,
        assembly_plan=plan,
    )
