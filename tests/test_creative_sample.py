from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import json
import os
import shutil
import struct
import subprocess
import zlib
from collections.abc import Callable
from dataclasses import FrozenInstanceError, dataclass
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from sdc import asset_pack as asset_pack_module
from sdc import compiler as compiler_module
from sdc import creative_media, creative_providers
from sdc import creative_sample as creative_sample_module
from sdc.asset_pack import (
    AssetPackError,
    LocalAssetSource,
    freeze_asset_pack,
    verify_asset_pack,
)
from sdc.compiler import compile_creative_sample, compile_story, stable_id
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    CreativeCameraAngle,
    CreativeCameraMovement,
    CreativeSampleDecision,
    CreativeSampleMetrics,
    CreativeSampleShotSpec,
    CreativeSampleSpec,
    CreativeShotSize,
    DialogueLine,
    SceneAssetVersion,
    SceneBible,
    StoryInput,
)
from sdc.creative_media import (
    CreativeMediaError,
    MediaToolchain,
    TimedVoiceTrack,
    assemble_sample,
    inspect_imported_audio,
    inspect_imported_video,
    read_regular_media,
    render_audio_master,
    render_srt,
    resolve_media_toolchain,
    verify_assembled_sample,
    verify_media_toolchain,
)
from sdc.creative_providers import (
    AvatarProvider,
    ImageProvider,
    LocalCreativeArtifact,
    VoiceProvider,
)
from sdc.creative_sample import (
    AssetImport,
    BGMImport,
    CreativeSampleError,
    CreativeSampleImportManifest,
    CreativeSampleRunResult,
    ReviewerAssessment,
    ShotImportReview,
    VoiceImport,
    run_creative_sample,
    verify_creative_sample_output,
)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", *args],
        check=True,
        capture_output=True,
    )


class _FakeMediaProcess:
    def __init__(
        self,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        exit_code: int = 0,
        hangs: bool = False,
    ) -> None:
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.returncode: int | None = None
        self.exit_code = exit_code
        self.hangs = hangs
        self.killed = False
        self.wait_calls = 0
        if not hangs:
            self.stdout.feed_data(stdout)
            self.stdout.feed_eof()
            self.stderr.feed_data(stderr)
            self.stderr.feed_eof()

    async def wait(self) -> int:
        self.wait_calls += 1
        if self.hangs and not self.killed:
            await asyncio.get_running_loop().create_future()
        if self.returncode is None:
            self.returncode = self.exit_code
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
        if not self.stdout.at_eof():
            self.stdout.feed_eof()
        if not self.stderr.at_eof():
            self.stderr.feed_eof()


def _fake_media_tool_paths(root: Path) -> dict[str, Path]:
    tools = root / "tools"
    tools.mkdir()
    paths = {
        "ffmpeg": tools / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        "ffprobe": tools / ("ffprobe.exe" if os.name == "nt" else "ffprobe"),
    }
    for name, path in paths.items():
        path.write_bytes(f"reviewed-test-{name}".encode())
    return paths


def _placeholder_media_toolchain() -> MediaToolchain:
    return MediaToolchain(
        ffmpeg_path=Path("reviewed-tools/ffmpeg"),
        ffprobe_path=Path("reviewed-tools/ffprobe"),
        ffmpeg_sha256="a" * 64,
        ffprobe_sha256="b" * 64,
        ffmpeg_identity=(1, 1, 1, 1),
        ffprobe_identity=(1, 2, 1, 1),
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _png_bytes(label: str) -> bytes:
    """Return deterministic, metadata-free 2x2 RGB PNG fixture bytes."""
    color = hashlib.sha256(label.encode()).digest()[:3]
    scanlines = (b"\x00" + color * 2) * 2
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _character_bible(
    label: str,
    *,
    two_versions: bool = False,
    asset_content: Callable[[str], bytes] = _png_bytes,
) -> CharacterBible:
    name = label.replace("-", " ").title()
    visual_description = f"Stable character bible for {label}"
    character_id = CharacterBible.derive_id(name=name, visual_description=visual_description)
    versions: list[CharacterAssetVersion] = []
    for version in range(1, 3 if two_versions else 2):
        content_sha256 = hashlib.sha256(asset_content(f"{label}-asset-v{version}")).hexdigest()
        approval_ref = f"review-{label}-v{version}"
        asset_description = f"Approved immutable look {version} for {label}"
        versions.append(
            CharacterAssetVersion(
                id=CharacterAssetVersion.derive_id(
                    character_id=character_id,
                    version=version,
                    content_sha256=content_sha256,
                    media_type="image/png",
                    approval_ref=approval_ref,
                    visual_description=asset_description,
                ),
                character_id=character_id,
                version=version,
                content_sha256=content_sha256,
                media_type="image/png",
                approval_ref=approval_ref,
                visual_description=asset_description,
            )
        )
    return CharacterBible(
        character_id=character_id,
        name=name,
        visual_description=visual_description,
        asset_versions=tuple(versions),
        active_asset_version_id=versions[-1].id,
    )


def _scene_bible(
    label: str,
    ordinal: int,
    *,
    two_versions: bool = False,
    asset_content: Callable[[str], bytes] = _png_bytes,
) -> SceneBible:
    name = label.replace("-", " ").title()
    visual_description = f"Stable scene bible for {label}"
    scene_id = SceneBible.derive_id(
        ordinal=ordinal,
        name=name,
        visual_description=visual_description,
    )
    versions: list[SceneAssetVersion] = []
    for version in range(1, 3 if two_versions else 2):
        content_sha256 = hashlib.sha256(asset_content(f"{label}-asset-v{version}")).hexdigest()
        approval_ref = f"review-{label}-v{version}"
        asset_description = f"Approved immutable look {version} for {label}"
        versions.append(
            SceneAssetVersion(
                id=SceneAssetVersion.derive_id(
                    scene_id=scene_id,
                    version=version,
                    content_sha256=content_sha256,
                    media_type="image/png",
                    approval_ref=approval_ref,
                    visual_description=asset_description,
                ),
                scene_id=scene_id,
                version=version,
                content_sha256=content_sha256,
                media_type="image/png",
                approval_ref=approval_ref,
                visual_description=asset_description,
            )
        )
    return SceneBible(
        scene_id=scene_id,
        ordinal=ordinal,
        name=name,
        visual_description=visual_description,
        asset_versions=tuple(versions),
        active_asset_version_id=versions[-1].id,
    )


def _creative_spec(
    *,
    duration_ms: int = 60_000,
    shot_count: int = 8,
    character_count: int = 2,
    asset_content: Callable[[str], bytes] = _png_bytes,
) -> CreativeSampleSpec:
    characters = tuple(
        sorted(
            (
                _character_bible(
                    f"character-{chr(ord('a') + index)}",
                    two_versions=index == 0,
                    asset_content=asset_content,
                )
                for index in range(character_count)
            ),
            key=lambda item: item.character_id,
        )
    )
    scenes = (
        _scene_bible("scene-a", 0, two_versions=True, asset_content=asset_content),
        _scene_bible("scene-b", 1, asset_content=asset_content),
    )
    base_duration, remainder = divmod(duration_ms, shot_count)
    durations = [base_duration] * shot_count
    durations[-1] += remainder
    scene_boundary = shot_count // 2
    second_scene_start = sum(durations[:scene_boundary])
    first_character_id = next(
        item.character_id for item in characters if item.name == "Character A"
    )
    second_character_id = (
        next(item.character_id for item in characters if item.name == "Character B")
        if character_count == 2
        else first_character_id
    )
    first_scene_id = scenes[0].scene_id
    second_scene_id = scenes[1].scene_id
    line_a_text = "We start here."
    line_b_text = "We finish there."
    dialogue = (
        DialogueLine(
            line_id=DialogueLine.derive_id(
                ordinal=0,
                scene_id=first_scene_id,
                character_id=first_character_id,
                text=line_a_text,
                start_ms=500,
                end_ms=1_500,
            ),
            ordinal=0,
            scene_id=first_scene_id,
            character_id=first_character_id,
            text=line_a_text,
            start_ms=500,
            end_ms=1_500,
        ),
        DialogueLine(
            line_id=DialogueLine.derive_id(
                ordinal=1,
                scene_id=second_scene_id,
                character_id=second_character_id,
                text=line_b_text,
                start_ms=second_scene_start + 500,
                end_ms=second_scene_start + 1_500,
            ),
            ordinal=1,
            scene_id=second_scene_id,
            character_id=second_character_id,
            text=line_b_text,
            start_ms=second_scene_start + 500,
            end_ms=second_scene_start + 1_500,
        ),
    )
    all_character_ids = tuple(item.character_id for item in characters)
    cursor = 0
    shots: list[CreativeSampleShotSpec] = []
    for ordinal, shot_duration in enumerate(durations):
        in_second_scene = ordinal >= scene_boundary
        scene_id = second_scene_id if in_second_scene else first_scene_id
        line_ids = (
            (dialogue[0].line_id,)
            if ordinal == 0
            else ((dialogue[1].line_id,) if ordinal == scene_boundary else ())
        )
        shots.append(
            CreativeSampleShotSpec(
                ordinal=ordinal,
                scene_id=scene_id,
                narrative=f"Narrative beat {ordinal}",
                visual_direction=f"Dynamic shot direction {ordinal}",
                emotion_by_character={
                    character_id: f"Focused emotion {ordinal} for {character_id}"
                    for character_id in all_character_ids
                },
                action=f"Cross the frame on story beat {ordinal}",
                shot_size=CreativeShotSize.MEDIUM,
                camera_angle=CreativeCameraAngle.EYE_LEVEL,
                camera_movement=CreativeCameraMovement.DOLLY,
                wardrobe_by_character={
                    character_id: f"Continuity wardrobe for {character_id}"
                    for character_id in all_character_ids
                },
                props=("letter", "watch"),
                continuity_notes=f"Maintain eyeline and prop hand on beat {ordinal}",
                start_ms=cursor,
                duration_ms=shot_duration,
                character_ids=all_character_ids,
                dialogue_line_ids=line_ids,
            )
        )
        cursor += shot_duration
    return CreativeSampleSpec(
        title="Offline creative sample",
        seed=19,
        duration_ms=duration_ms,
        character_bibles=characters,
        scene_bibles=scenes,
        dialogue=dialogue,
        shots=tuple(shots),
    )


def _passing_metrics(**updates: object) -> CreativeSampleMetrics:
    values: dict[str, object] = {
        "sample_id": f"creative_sample_{'a' * 20}",
        "revision_id": f"creative_revision_{'b' * 20}",
        "first_pass_usable_rate": Decimal("0.75"),
        "character_continuity_rate": Decimal("0.90"),
        "scene_continuity_rate": Decimal("0.90"),
        "shot_intent_pass_rate": Decimal("0.80"),
        "artifact_free_rate": Decimal("0.90"),
        "critical_identity_breaks": 0,
        "duplicate_media_count": 0,
        "average_attempts": Decimal("1.25"),
        "total_elapsed_ms": 123_456,
        "human_edit_minutes": Decimal("7.5"),
        "cost_cny": Decimal("0"),
        "failure_counts": {"offline.import": 0},
    }
    values.update(updates)
    return CreativeSampleMetrics.model_validate(values)


def _active_asset_sources(
    spec: CreativeSampleSpec,
    directory: Path,
    *,
    asset_content: Callable[[str], bytes] = _png_bytes,
) -> tuple[LocalAssetSource, ...]:
    sources: list[LocalAssetSource] = []
    bibles: tuple[CharacterBible | SceneBible, ...] = (
        *spec.character_bibles,
        *spec.scene_bibles,
    )
    for bible in bibles:
        version = next(
            item for item in bible.asset_versions if item.id == bible.active_asset_version_id
        )
        label = bible.name.lower().replace(" ", "-")
        content = asset_content(f"{label}-asset-v{version.version}")
        assert hashlib.sha256(content).hexdigest() == version.content_sha256
        path = directory / f"{version.id}.asset"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        sources.append(LocalAssetSource(asset_version_id=version.id, path=path))
    return tuple(sorted(sources, key=lambda item: item.asset_version_id))


def _canonical_contract_bytes(
    value: CreativeSampleSpec | CreativeSampleImportManifest,
) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _byte_identity(data: bytes) -> tuple[str, int]:
    return hashlib.sha256(data).hexdigest(), len(data)


def _declared_identity(
    logical_path: str,
    identities: dict[str, tuple[str, int]],
) -> tuple[str, int]:
    return identities.get(logical_path, _byte_identity(logical_path.encode("utf-8")))


def _reviewer_assessment(
    *,
    role: Literal["editor", "independent"],
    shot_id: str,
    character_ids: tuple[str, ...],
    scene_continuity_pass: bool | None,
    first_pass_usable: bool = True,
) -> ReviewerAssessment:
    return ReviewerAssessment(
        reviewer_ref=f"{role}-reviewer",
        review_record_sha256=hashlib.sha256(f"{role}:{shot_id}".encode()).hexdigest(),
        first_pass_usable=first_pass_usable,
        shot_intent_pass=True,
        artifact_free=True,
        character_continuity={character_id: True for character_id in character_ids},
        scene_continuity_pass=scene_continuity_pass,
        critical_identity_break=False,
    )


def _creative_import_manifest(
    spec: CreativeSampleSpec,
    *,
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"] = "SYNTHETIC_FIXTURE",
    identities: dict[str, tuple[str, int]] | None = None,
    revision_number: int = 1,
    predecessor_manifest_sha256: str | None = None,
) -> CreativeSampleImportManifest:
    declared = {} if identities is None else identities
    compilation = compile_creative_sample(spec)
    bibles: tuple[CharacterBible | SceneBible, ...] = (
        *spec.character_bibles,
        *spec.scene_bibles,
    )
    active_versions: list[CharacterAssetVersion | SceneAssetVersion] = []
    for bible in bibles:
        active_versions.append(
            next(
                version
                for version in bible.asset_versions
                if version.id == bible.active_asset_version_id
            )
        )
    asset_imports: list[AssetImport] = []
    for version in sorted(active_versions, key=lambda item: item.id):
        logical_path = f"assets/{version.id}.png"
        parent = next(bible for bible in bibles if bible.active_asset_version_id == version.id)
        label = parent.name.lower().replace(" ", "-")
        png = _png_bytes(f"{label}-asset-v{version.version}")
        digest, size_bytes = declared.get(logical_path, _byte_identity(png))
        assert digest == version.content_sha256
        assert size_bytes == len(png)
        asset_imports.append(
            AssetImport(
                asset_version_id=version.id,
                logical_path=logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                source_kind=source_kind,
            )
        )

    shot_imports: list[ShotImportReview] = []
    seen_scenes: set[str] = set()
    for shot in compilation.pir.shots:
        logical_path = f"shots/{shot.ordinal:02d}.mp4"
        digest, size_bytes = _declared_identity(logical_path, declared)
        first_in_scene = shot.scene_bible_id not in seen_scenes
        seen_scenes.add(shot.scene_bible_id)
        scene_review = None if first_in_scene else True
        character_ids = tuple(sorted(item.character_id for item in shot.character_assets))
        shot_imports.append(
            ShotImportReview(
                shot_id=shot.id,
                logical_path=logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                media_type="video/mp4",
                first_attempt_sha256=digest,
                approval_ref=f"approval-shot-{shot.ordinal:02d}",
                provenance_record_sha256=hashlib.sha256(
                    f"provenance:{logical_path}".encode()
                ).hexdigest(),
                source_kind=source_kind,
                attempts=1,
                editor_review=_reviewer_assessment(
                    role="editor",
                    shot_id=shot.id,
                    character_ids=character_ids,
                    scene_continuity_pass=scene_review,
                ),
                independent_review=_reviewer_assessment(
                    role="independent",
                    shot_id=shot.id,
                    character_ids=character_ids,
                    scene_continuity_pass=scene_review,
                ),
                cost_cny=Decimal("0"),
            )
        )

    voice_imports: list[VoiceImport] = []
    for ordinal, line in enumerate(spec.dialogue):
        logical_path = f"voices/{ordinal:02d}.wav"
        digest, size_bytes = _declared_identity(logical_path, declared)
        voice_imports.append(
            VoiceImport(
                line_id=line.line_id,
                logical_path=logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                media_type="audio/wav",
                approval_ref=f"approval-voice-{ordinal:02d}",
                provenance_record_sha256=hashlib.sha256(
                    f"provenance:{logical_path}".encode()
                ).hexdigest(),
                source_kind=source_kind,
            )
        )
    bgm_path = "bgm/background.wav"
    bgm_digest, bgm_size = _declared_identity(bgm_path, declared)
    return CreativeSampleImportManifest(
        sample_spec_sha256=hashlib.sha256(_canonical_contract_bytes(spec)).hexdigest(),
        revision_number=revision_number,
        predecessor_manifest_sha256=predecessor_manifest_sha256,
        assets=tuple(asset_imports),
        shots=tuple(shot_imports),
        voices=tuple(voice_imports),
        bgm=BGMImport(
            logical_path=bgm_path,
            expected_sha256=bgm_digest,
            expected_size_bytes=bgm_size,
            media_type="audio/wav",
            approval_ref="approval-bgm",
            provenance_record_sha256=hashlib.sha256(f"provenance:{bgm_path}".encode()).hexdigest(),
            source_kind=source_kind,
        ),
        total_elapsed_ms=180_000,
        human_edit_minutes=Decimal("4.5"),
    )


def _write_contract_json(
    path: Path,
    value: CreativeSampleSpec | CreativeSampleImportManifest,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class _SyntheticCreativeRun:
    fixture_root: Path
    spec: CreativeSampleSpec
    manifest: CreativeSampleImportManifest
    result: CreativeSampleRunResult
    report: dict[str, object]


@pytest.fixture(scope="module")
def synthetic_creative_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> _SyntheticCreativeRun:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for the full creative-sample run")
    fixture_root = tmp_path_factory.mktemp("e")
    input_root = fixture_root / "i"
    input_root.mkdir()
    spec = _creative_spec(duration_ms=60_000, shot_count=8)
    spec_path = input_root / "sample-spec.json"
    manifest_path = input_root / "import-manifest.json"
    _write_contract_json(spec_path, spec)

    source_shot = input_root / "source-shot.mp4"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=160x90:rate=8:duration=7.5",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        str(source_shot),
    )
    dynamic_shot = source_shot.read_bytes()
    identities: dict[str, tuple[str, int]] = {}
    for ordinal in range(8):
        logical_path = f"shots/{ordinal:02d}.mp4"
        path = input_root.joinpath(*logical_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dynamic_shot)
        identities[logical_path] = _byte_identity(dynamic_shot)

    for ordinal, frequency in enumerate((440, 660)):
        logical_path = f"voices/{ordinal:02d}.wav"
        path = input_root.joinpath(*logical_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        _ffmpeg(
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000:duration=1",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(path),
        )
        identities[logical_path] = _byte_identity(path.read_bytes())

    bgm_logical_path = "bgm/background.wav"
    bgm_path = input_root.joinpath(*bgm_logical_path.split("/"))
    bgm_path.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:sample_rate=48000:duration=1",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(bgm_path),
    )
    identities[bgm_logical_path] = _byte_identity(bgm_path.read_bytes())

    bibles: tuple[CharacterBible | SceneBible, ...] = (
        *spec.character_bibles,
        *spec.scene_bibles,
    )
    for bible in bibles:
        version = next(
            item for item in bible.asset_versions if item.id == bible.active_asset_version_id
        )
        logical_path = f"assets/{version.id}.png"
        path = input_root.joinpath(*logical_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        label = bible.name.lower().replace(" ", "-")
        png = _png_bytes(f"{label}-asset-v{version.version}")
        path.write_bytes(png)
        identities[logical_path] = _byte_identity(png)

    manifest = _creative_import_manifest(
        spec,
        source_kind="SYNTHETIC_FIXTURE",
        identities=identities,
    )
    _write_contract_json(manifest_path, manifest)
    output_root = fixture_root / "o"
    result = asyncio.run(
        run_creative_sample(
            spec_path=spec_path,
            import_manifest_path=manifest_path,
            output_root=output_root,
        )
    )
    report = verify_creative_sample_output(output_root)
    return _SyntheticCreativeRun(fixture_root, spec, manifest, result, report)


@pytest.mark.parametrize("source_kind", ["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"])
def test_import_manifest_binds_sizes_media_provenance_and_one_source_mode(
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"],
) -> None:
    manifest = _creative_import_manifest(_creative_spec(), source_kind=source_kind)

    assert {item.source_kind for item in manifest.assets} == {source_kind}
    assert {item.source_kind for item in manifest.shots} == {source_kind}
    assert {item.source_kind for item in manifest.voices} == {source_kind}
    assert manifest.bgm is not None and manifest.bgm.source_kind == source_kind
    assert all(item.expected_size_bytes > 0 for item in manifest.assets)
    assert all(
        item.expected_size_bytes > 0
        and item.media_type == "video/mp4"
        and len(item.first_attempt_sha256) == 64
        and len(item.provenance_record_sha256) == 64
        and item.editor_review.reviewer_ref != item.independent_review.reviewer_ref
        for item in manifest.shots
    )
    assert all(
        item.expected_size_bytes > 0
        and item.media_type == "audio/wav"
        and len(item.provenance_record_sha256) == 64
        for item in manifest.voices
    )
    assert manifest.bgm.expected_size_bytes > 0
    assert manifest.bgm.media_type == "audio/wav"
    assert len(manifest.bgm.provenance_record_sha256) == 64


def test_import_manifest_rejects_mixed_real_and_synthetic_sources() -> None:
    manifest = _creative_import_manifest(_creative_spec(), source_kind="SYNTHETIC_FIXTURE")
    payload = manifest.model_dump(mode="python")
    payload["voices"][0]["source_kind"] = "IMPORTED_MEDIA"

    with pytest.raises(ValidationError, match="cannot mix ImportedMedia with synthetic fixtures"):
        CreativeSampleImportManifest.model_validate(payload)


def test_import_manifest_revision_requires_exact_predecessor_semantics() -> None:
    spec = _creative_spec()
    first = _creative_import_manifest(spec)
    predecessor = hashlib.sha256(_canonical_contract_bytes(first)).hexdigest()
    second = _creative_import_manifest(
        spec,
        revision_number=2,
        predecessor_manifest_sha256=predecessor,
    )

    assert first.revision_number == 1 and first.predecessor_manifest_sha256 is None
    assert second.revision_number == 2
    assert second.predecessor_manifest_sha256 == predecessor
    for invalid_revision, invalid_predecessor in ((1, predecessor), (2, None)):
        with pytest.raises(ValidationError, match="only revision 1 may omit"):
            _creative_import_manifest(
                spec,
                revision_number=invalid_revision,
                predecessor_manifest_sha256=invalid_predecessor,
            )


def test_attempt_two_preserves_first_digest_and_requires_two_independent_failures() -> None:
    manifest = _creative_import_manifest(_creative_spec())
    payload = manifest.shots[0].model_dump(mode="python")
    first_attempt_sha256 = "0" * 64
    assert first_attempt_sha256 != payload["expected_sha256"]
    payload["attempts"] = 2
    payload["first_attempt_sha256"] = first_attempt_sha256
    payload["editor_review"]["first_pass_usable"] = False
    payload["independent_review"]["first_pass_usable"] = False

    replacement = ShotImportReview.model_validate(payload)

    assert replacement.attempts == 2
    assert replacement.first_attempt_sha256 == first_attempt_sha256
    assert replacement.first_attempt_sha256 != replacement.expected_sha256
    assert not replacement.editor_review.first_pass_usable
    assert not replacement.independent_review.first_pass_usable

    same_digest = dict(payload, first_attempt_sha256=payload["expected_sha256"])
    with pytest.raises(ValidationError, match="distinct first-attempt digest"):
        ShotImportReview.model_validate(same_digest)

    attempt_one_drift = dict(payload, attempts=1)
    with pytest.raises(ValidationError, match="Attempt 1 must bind"):
        ShotImportReview.model_validate(attempt_one_drift)

    usable_replacement = dict(payload)
    usable_replacement["editor_review"] = dict(payload["editor_review"])
    usable_replacement["independent_review"] = dict(payload["independent_review"])
    usable_replacement["independent_review"]["first_pass_usable"] = True
    with pytest.raises(ValidationError, match="cannot be reported as first-pass usable"):
        ShotImportReview.model_validate(usable_replacement)

    same_reviewer = dict(payload)
    same_reviewer["editor_review"] = dict(payload["editor_review"])
    same_reviewer["independent_review"] = dict(payload["independent_review"])
    same_reviewer["independent_review"]["reviewer_ref"] = same_reviewer["editor_review"][
        "reviewer_ref"
    ]
    with pytest.raises(ValidationError, match="reviewer references must be distinct"):
        ShotImportReview.model_validate(same_reviewer)


def test_real_ffmpeg_sixty_second_synthetic_run_is_stopped_and_fully_verifiable(
    synthetic_creative_run: _SyntheticCreativeRun,
) -> None:
    run = synthetic_creative_run
    result = run.result
    report = run.report
    output_root = result.output_root
    manifest_sha256 = hashlib.sha256(_canonical_contract_bytes(run.manifest)).hexdigest()
    expected_revision_id = stable_id(
        "creative_revision",
        [compile_creative_sample(run.spec).id, manifest_sha256],
    )

    assert run.spec.duration_ms == 60_000
    assert len(run.spec.shots) == 8
    assert result.sample_id == compile_creative_sample(run.spec).id
    assert result.decision is CreativeSampleDecision.STOP
    assert result.revision_id == expected_revision_id
    assert report["revision_id"] == expected_revision_id
    assert report["import_manifest_sha256"] == manifest_sha256
    assert report["decision"] == "STOP"
    assert report["provider_requests"] == 0
    assert report["live_authority"] is False
    assert report["origin_authenticated_by_sdc"] is False
    assert report["completion_marker"] is True
    assert report["metrics"] == {"status": "SYNTHETIC_FIXTURE_NOT_SCORED"}
    metric_counts = cast(dict[str, object], report["metric_counts"])
    assert metric_counts["status"] == "NOT_SCORED_FIXTURE"
    assert all(
        value == 0
        for key, value in metric_counts.items()
        if key != "status" and key != "review_disagreement_count"
    )
    assert metric_counts["review_disagreement_count"] == 0
    assert len(cast(list[object], report["imported_shots"])) == 8
    assert len(cast(list[object], report["imported_voices"])) == 2
    assert all(
        item["source_kind"] == "SYNTHETIC_FIXTURE"
        for item in cast(list[dict[str, object]], report["imported_shots"])
    )
    assert all(
        item["source_kind"] == "SYNTHETIC_FIXTURE"
        for item in cast(list[dict[str, object]], report["imported_voices"])
    )
    imported_bgm = cast(dict[str, object], report["imported_bgm"])
    assert imported_bgm["source_kind"] == "SYNTHETIC_FIXTURE"

    technical = json.loads((output_root / "creative-technical-qc.json").read_text("utf-8"))
    receipt = json.loads((output_root / "assembly-receipt.json").read_text("utf-8"))
    import_evidence = json.loads((output_root / "import-evidence.json").read_text("utf-8"))
    metrics = json.loads((output_root / "metrics.json").read_text("utf-8"))
    assert technical["passed"] is True
    assert receipt["receipt_id"] == report["assembly_receipt_id"]
    assert len(receipt["ordered_shots"]) == 8
    current_toolchain = resolve_media_toolchain()
    assert receipt["ffmpeg_policy"] == {
        "audio_input_format": "wav",
        "audio_rate": 48000,
        "chapters": "stripped",
        "fps": 25,
        "height": 1920,
        "metadata": "stripped",
        "network_protocols": [],
        "subtitle_input_format": "srt",
        "video_input_format": "mov/mp4",
        "width": 1080,
        "ffmpeg_sha256": current_toolchain.ffmpeg_sha256,
        "ffprobe_sha256": current_toolchain.ffprobe_sha256,
        "tool_trust_boundary": "operator-controlled-local-installation",
    }
    assert set(import_evidence) == {
        "document_type",
        "schema_version",
        "sample_id",
        "revision_id",
        "source_mode",
        "imported_shots",
        "imported_voices",
        "imported_bgm",
        "metric_counts",
        "origin_authenticated_by_sdc",
    }
    assert import_evidence["document_type"] == "sdc.creative-sample-import-evidence"
    assert import_evidence["schema_version"] == "1.0.0"
    assert import_evidence["sample_id"] == result.sample_id
    assert import_evidence["revision_id"] == result.revision_id
    assert import_evidence["source_mode"] == "SYNTHETIC_FIXTURE"
    assert import_evidence["origin_authenticated_by_sdc"] is False
    assert import_evidence["imported_shots"] == report["imported_shots"]
    assert import_evidence["imported_voices"] == report["imported_voices"]
    assert import_evidence["imported_bgm"] == report["imported_bgm"]
    assert import_evidence["metric_counts"] == report["metric_counts"]
    assert metrics["status"] == "SYNTHETIC_FIXTURE_NOT_SCORED"
    closure_paths = [
        cast(str, cast(dict[str, object], item)["path"])
        for item in cast(list[object], report["output_closure"])
    ]
    assert closure_paths == sorted(closure_paths)
    assert "sample-report.json" not in closure_paths
    assert "INCOMPLETE.json" not in closure_paths
    assert "import-evidence.json" in closure_paths
    assert verify_creative_sample_output(output_root) == report
    assert result.final_media.is_file()
    assert result.report_path.is_file()
    assert not (output_root / "INCOMPLETE.json").exists()
    assert not (output_root.parent / f".{output_root.name}.creative-stage").exists(), (
        "completed staging data must be removed after report-last publication"
    )


def test_same_spec_different_import_manifest_has_a_distinct_revision_identity(
    synthetic_creative_run: _SyntheticCreativeRun,
) -> None:
    run = synthetic_creative_run
    first_manifest_sha256 = hashlib.sha256(_canonical_contract_bytes(run.manifest)).hexdigest()
    second_payload = run.manifest.model_dump(mode="python")
    second_payload.update(
        revision_number=2,
        predecessor_manifest_sha256=first_manifest_sha256,
        total_elapsed_ms=run.manifest.total_elapsed_ms + 1,
    )
    second = CreativeSampleImportManifest.model_validate(second_payload)
    second_manifest_sha256 = hashlib.sha256(_canonical_contract_bytes(second)).hexdigest()
    second_revision_id = stable_id(
        "creative_revision",
        [run.result.sample_id, second_manifest_sha256],
    )

    assert second.sample_spec_sha256 == run.manifest.sample_spec_sha256
    assert second_manifest_sha256 != first_manifest_sha256
    assert second_revision_id != run.result.revision_id


def _write_self_consistent_minimal_forgery(root: Path) -> None:
    root.mkdir()
    final = b"bounded-final-media"
    final_sha256, final_size = _byte_identity(final)
    (root / "final.mp4").write_bytes(final)
    (root / "sample-report.json").write_text(
        json.dumps(
            {
                "completion_marker": True,
                "release": {
                    "media_path": "final.mp4",
                    "sha256": final_sha256,
                    "size_bytes": final_size,
                },
                "output_closure": [
                    {
                        "path": "final.mp4",
                        "sha256": final_sha256,
                        "size_bytes": final_size,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_output_verifier_rejects_self_consistent_but_incomplete_catalog(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "forged-output"
    _write_self_consistent_minimal_forgery(output_root)

    with pytest.raises(CreativeSampleError, match="omits a required result"):
        verify_creative_sample_output(output_root)


@pytest.mark.parametrize(
    "drift",
    [
        "tamper",
        "receipt-rebind",
        "report-revision",
        "report-safety",
        "report-extra-field",
        "report-imported-shots",
        "report-metric-counts",
        "extra",
        "half-published",
    ],
)
def test_output_verifier_rejects_tamper_extra_and_half_published_closures(
    synthetic_creative_run: _SyntheticCreativeRun,
    drift: str,
) -> None:
    suffix = {
        "tamper": "t",
        "receipt-rebind": "b",
        "report-revision": "r",
        "report-safety": "s",
        "report-extra-field": "x",
        "report-imported-shots": "j",
        "report-metric-counts": "m",
        "extra": "e",
        "half-published": "h",
    }[drift]
    output_root = synthetic_creative_run.fixture_root / suffix
    shutil.copytree(synthetic_creative_run.result.output_root, output_root)
    if drift == "tamper":
        (output_root / "assembly-receipt.json").write_bytes(b'{"tampered":true}\n')
    elif drift == "receipt-rebind":
        receipt_path = output_root / "assembly-receipt.json"
        receipt = json.loads(receipt_path.read_text("utf-8"))
        receipt["ordered_shots"][0]["sha256"] = "0" * 64
        receipt_bytes = (
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        receipt_path.write_bytes(receipt_bytes)
        report_path = output_root / "sample-report.json"
        report = json.loads(report_path.read_text("utf-8"))
        closure_entry = next(
            item for item in report["output_closure"] if item["path"] == "assembly-receipt.json"
        )
        closure_entry.update(
            sha256=hashlib.sha256(receipt_bytes).hexdigest(),
            size_bytes=len(receipt_bytes),
        )
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif drift in {
        "report-revision",
        "report-safety",
        "report-extra-field",
        "report-imported-shots",
        "report-metric-counts",
    }:
        report_path = output_root / "sample-report.json"
        report = json.loads(report_path.read_text("utf-8"))
        if drift == "report-revision":
            report["revision_id"] = f"creative_revision_{'0' * 20}"
        elif drift == "report-safety":
            report["provider_requests"] = 1
        elif drift == "report-extra-field":
            report["unexpected"] = "unreviewed-report-extension"
        elif drift == "report-imported-shots":
            report["imported_shots"][0]["approval_ref"] = "tampered-approval"
        else:
            report["metric_counts"]["review_disagreement_count"] += 1
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif drift == "extra":
        (output_root / "unexpected.bin").write_bytes(b"unexpected")
    else:
        (output_root / "sample-report.json").unlink()
        (output_root / "INCOMPLETE.json").write_bytes(b"{}")

    with pytest.raises(CreativeSampleError):
        verify_creative_sample_output(output_root)


@pytest.mark.parametrize(
    ("duration_ms", "shot_count", "character_count"),
    [
        (60_000, 8, 1),
        (60_000, 12, 2),
        (90_000, 8, 2),
        (90_000, 12, 1),
    ],
)
def test_creative_sample_accepts_only_the_reviewed_envelope_boundaries(
    duration_ms: int,
    shot_count: int,
    character_count: int,
) -> None:
    spec = _creative_spec(
        duration_ms=duration_ms,
        shot_count=shot_count,
        character_count=character_count,
    )

    assert spec.duration_ms == duration_ms
    assert len(spec.shots) == shot_count
    assert len(spec.character_bibles) == character_count
    assert len(spec.scene_bibles) == 2
    assert sum(shot.duration_ms for shot in spec.shots) == duration_ms
    for shot in spec.shots:
        assert set(shot.emotion_by_character) == set(shot.character_ids)
        assert set(shot.wardrobe_by_character) == set(shot.character_ids)
        assert shot.props == tuple(sorted(set(shot.props)))


@pytest.mark.parametrize(
    "drift",
    [
        "duration-low",
        "duration-high",
        "shots-low",
        "shots-high",
        "characters-low",
        "characters-high",
        "scenes-low",
        "scenes-high",
        "dialogue-empty",
    ],
)
def test_creative_sample_rejects_out_of_envelope_specs(drift: str) -> None:
    payload = _creative_spec().model_dump(mode="python")
    if drift == "duration-low":
        payload["duration_ms"] = 59_999
    elif drift == "duration-high":
        payload["duration_ms"] = 90_001
    elif drift == "shots-low":
        payload["shots"] = payload["shots"][:7]
    elif drift == "shots-high":
        payload["shots"] = (*payload["shots"], *(payload["shots"][-1:] * 5))
    elif drift == "characters-low":
        payload["character_bibles"] = ()
    elif drift == "characters-high":
        payload["character_bibles"] = (*payload["character_bibles"], payload["character_bibles"][0])
    elif drift == "scenes-low":
        payload["scene_bibles"] = payload["scene_bibles"][:1]
    elif drift == "scenes-high":
        payload["scene_bibles"] = (*payload["scene_bibles"], payload["scene_bibles"][0])
    else:
        payload["dialogue"] = ()

    with pytest.raises(ValidationError):
        CreativeSampleSpec.model_validate(payload)


def test_asset_versions_are_immutable_and_compilation_binds_only_active_versions() -> None:
    spec = _creative_spec()
    character_asset = spec.character_bibles[0].asset_versions[0]
    with pytest.raises(ValidationError, match="frozen"):
        character_asset.version = 99

    invalid_bible = spec.character_bibles[0].model_dump(mode="python")
    invalid_bible["active_asset_version_id"] = "unreviewed-replacement"
    with pytest.raises(ValidationError, match="active character asset version"):
        CharacterBible.model_validate(invalid_bible)

    compilation = compile_creative_sample(spec)
    active_characters = {
        bible.character_id: bible.active_asset_version_id for bible in spec.character_bibles
    }
    active_scenes = {bible.scene_id: bible.active_asset_version_id for bible in spec.scene_bibles}
    for shot in compilation.pir.shots:
        assert shot.scene_asset_version_id == active_scenes[shot.scene_bible_id]
        assert {
            binding.character_id: binding.asset_version_id for binding in shot.character_assets
        } == {
            binding.character_id: active_characters[binding.character_id]
            for binding in shot.character_assets
        }
    assert compilation.nir.character_bibles == spec.character_bibles
    assert compilation.nir.scene_bibles == spec.scene_bibles


def test_asset_and_storyboard_reference_drift_is_rejected() -> None:
    spec = _creative_spec()
    payload = spec.model_dump(mode="python")
    containing_id = payload["character_bibles"][0]["character_id"]
    foreign_id = next(
        bible["character_id"]
        for bible in payload["character_bibles"]
        if bible["character_id"] != containing_id
    )
    drifted_asset = payload["character_bibles"][0]["asset_versions"][0]
    drifted_asset["character_id"] = foreign_id
    drifted_asset["id"] = CharacterAssetVersion.derive_id(
        character_id=foreign_id,
        version=drifted_asset["version"],
        content_sha256=drifted_asset["content_sha256"],
        media_type=drifted_asset["media_type"],
        approval_ref=drifted_asset["approval_ref"],
        visual_description=drifted_asset["visual_description"],
    )
    with pytest.raises(ValidationError, match="bind its containing character"):
        CreativeSampleSpec.model_validate(payload)

    payload = spec.model_dump(mode="python")
    payload["shots"][0]["character_ids"] = ("unknown-character",)
    payload["shots"][0]["emotion_by_character"] = {"unknown-character": "Unknown emotion"}
    payload["shots"][0]["wardrobe_by_character"] = {"unknown-character": "Unknown wardrobe"}
    with pytest.raises(ValidationError, match="unknown character"):
        CreativeSampleSpec.model_validate(payload)

    payload = spec.model_dump(mode="python")
    payload["shots"][0]["dialogue_line_ids"] = ()
    with pytest.raises(ValidationError, match="exactly one shot"):
        CreativeSampleSpec.model_validate(payload)


def test_creative_ids_reject_manual_or_relabelled_identity() -> None:
    spec = _creative_spec()

    character = spec.character_bibles[0].model_dump(mode="python")
    character["character_id"] = "manual-character"
    with pytest.raises(ValidationError, match="derive from .*canonical content"):
        CharacterBible.model_validate(character)

    scene = spec.scene_bibles[0].model_dump(mode="python")
    scene["scene_id"] = "manual-scene"
    with pytest.raises(ValidationError, match="derive from .*canonical content"):
        SceneBible.model_validate(scene)

    asset = spec.character_bibles[0].asset_versions[0].model_dump(mode="python")
    asset["id"] = "manual-asset"
    with pytest.raises(ValidationError, match="derive from .*canonical content"):
        CharacterAssetVersion.model_validate(asset)

    line = spec.dialogue[0].model_dump(mode="python")
    line["line_id"] = "manual-line"
    with pytest.raises(ValidationError, match="derive from .*canonical content"):
        DialogueLine.model_validate(line)


def test_scene_and_recurring_character_minimums_fail_closed() -> None:
    spec = _creative_spec()
    payload = spec.model_dump(mode="python")
    second_scene_id = spec.scene_bibles[1].scene_id
    payload["shots"][2]["scene_id"] = second_scene_id
    payload["shots"][3]["scene_id"] = second_scene_id
    with pytest.raises(ValidationError, match="each scene must contain at least three shots"):
        CreativeSampleSpec.model_validate(payload)

    payload = spec.model_dump(mode="python")
    character_b_id = next(
        bible.character_id for bible in spec.character_bibles if bible.name == "Character B"
    )
    scene_boundary = len(spec.shots) // 2
    for ordinal, shot in enumerate(payload["shots"]):
        if ordinal not in {0, scene_boundary}:
            shot["character_ids"] = tuple(
                item for item in shot["character_ids"] if item != character_b_id
            )
            shot["emotion_by_character"].pop(character_b_id)
            shot["wardrobe_by_character"].pop(character_b_id)
    with pytest.raises(ValidationError, match="three shots across both scenes"):
        CreativeSampleSpec.model_validate(payload)


def test_shot_expression_maps_use_json_key_closure_and_props_canonical_order() -> None:
    spec = _creative_spec()
    payload = spec.model_dump(mode="python")
    first_shot = payload["shots"][0]
    first_shot["emotion_by_character"] = dict(
        reversed(tuple(first_shot["emotion_by_character"].items()))
    )
    first_shot["wardrobe_by_character"] = dict(
        reversed(tuple(first_shot["wardrobe_by_character"].items()))
    )
    reordered = CreativeSampleSpec.model_validate(payload)
    baseline_compilation = compile_creative_sample(spec)
    reordered_compilation = compile_creative_sample(reordered)
    assert reordered_compilation.id == baseline_compilation.id
    assert reordered_compilation.spec_sha256 == baseline_compilation.spec_sha256
    assert reordered_compilation.pir.shots[0].id == baseline_compilation.pir.shots[0].id
    assert reordered_compilation.pir.shots[0].prompt == baseline_compilation.pir.shots[0].prompt

    shot = spec.shots[0]
    payload = shot.model_dump(mode="python")
    payload["wardrobe_by_character"].pop(shot.character_ids[-1])
    with pytest.raises(ValidationError, match="keys must exactly match character_ids"):
        CreativeSampleShotSpec.model_validate(payload)

    payload = shot.model_dump(mode="python")
    payload["props"] = tuple(reversed(payload["props"]))
    with pytest.raises(ValidationError, match="canonical sorted order"):
        CreativeSampleShotSpec.model_validate(payload)


def test_dialogue_uses_nonoverlapping_shot_bound_master_clock_intervals() -> None:
    spec = _creative_spec()
    payload = spec.model_dump(mode="python")
    overlapping = payload["dialogue"][1]
    overlapping["start_ms"] = 1_000
    overlapping["end_ms"] = 2_000
    overlapping["line_id"] = DialogueLine.derive_id(
        ordinal=overlapping["ordinal"],
        scene_id=overlapping["scene_id"],
        character_id=overlapping["character_id"],
        text=overlapping["text"],
        start_ms=overlapping["start_ms"],
        end_ms=overlapping["end_ms"],
    )
    with pytest.raises(ValidationError, match="non-overlapping master-clock intervals"):
        CreativeSampleSpec.model_validate(payload)

    payload = spec.model_dump(mode="python")
    outside_shot = payload["dialogue"][0]
    outside_shot["start_ms"] = spec.shots[0].duration_ms - 500
    outside_shot["end_ms"] = spec.shots[0].duration_ms + 500
    outside_shot["line_id"] = DialogueLine.derive_id(
        ordinal=outside_shot["ordinal"],
        scene_id=outside_shot["scene_id"],
        character_id=outside_shot["character_id"],
        text=outside_shot["text"],
        start_ms=outside_shot["start_ms"],
        end_ms=outside_shot["end_ms"],
    )
    payload["shots"][0]["dialogue_line_ids"] = (outside_shot["line_id"],)
    with pytest.raises(ValidationError, match="completely within its bound shot"):
        CreativeSampleSpec.model_validate(payload)


def test_asset_pack_is_content_addressed_deterministic_and_active_only(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")

    first = freeze_asset_pack(spec, sources, tmp_path / "packs-a")
    repeated = freeze_asset_pack(spec, sources, tmp_path / "packs-a")
    independent = freeze_asset_pack(spec, sources, tmp_path / "packs-b")
    verified = verify_asset_pack(spec, first.root, expected_pack_id=first.pack_id)

    assert first.created
    assert not repeated.created
    assert independent.created
    assert first.pack_id == repeated.pack_id == independent.pack_id
    assert verified.pack_id == first.pack_id
    assert not verified.created
    assert first.manifest_path.read_bytes() == independent.manifest_path.read_bytes()
    assert first.object_count == len(sources) == 4
    manifest = json.loads(first.manifest_path.read_bytes())
    assert manifest["pack_id"] == first.pack_id
    assert [item["asset_version_id"] for item in manifest["bindings"]] == [
        source.asset_version_id for source in sources
    ]
    assert all(item["logical_path"].startswith("objects/") for item in manifest["bindings"])
    assert not any(str(source.path) in first.manifest_path.read_text() for source in sources)
    for binding in manifest["bindings"]:
        frozen = first.root / binding["logical_path"]
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == binding["object_sha256"]


def test_asset_pack_requires_sorted_exact_sources_and_matching_digests(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")

    with pytest.raises(AssetPackError, match="sorted exact closure"):
        freeze_asset_pack(spec, sources[:-1], tmp_path / "missing-source")
    with pytest.raises(AssetPackError, match="sorted exact closure"):
        freeze_asset_pack(spec, tuple(reversed(sources)), tmp_path / "unsorted-source")

    sources[0].path.write_bytes(b"same-logical-asset-but-different-content")
    with pytest.raises(AssetPackError, match="digest mismatch"):
        freeze_asset_pack(spec, sources, tmp_path / "drifted-source")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("declared-random", "must be PNG bytes"),
        ("metadata", "must not contain metadata or external content"),
        ("trailing", "trailing or polyglot bytes"),
        ("polyglot", "trailing or polyglot bytes"),
    ],
)
def test_asset_pack_rejects_unsanitized_or_polyglot_png(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    def malformed_png(label: str) -> bytes:
        valid = _png_bytes(label)
        if mutation == "declared-random":
            return b"declared-image-png-but-random-bytes:" + label.encode()
        if mutation == "metadata":
            return valid[:-12] + _png_chunk(b"tEXt", b"Comment\x00hidden") + valid[-12:]
        if mutation == "trailing":
            return valid + b"trailing-bytes"
        return valid + b"<script src=https://example.invalid/polyglot></script>"

    spec = _creative_spec(asset_content=malformed_png)
    sources = _active_asset_sources(
        spec,
        tmp_path / "sources",
        asset_content=malformed_png,
    )
    output_parent = tmp_path / "packs"

    with pytest.raises(AssetPackError, match=message):
        freeze_asset_pack(spec, sources, output_parent)
    assert not output_parent.exists()


def test_asset_pack_rejects_bounded_zlib_expansion_bomb(tmp_path: Path) -> None:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    compressed_expansion = zlib.compress(b"\x00" * (4 * 1024 * 1024), level=9)
    bomb = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed_expansion)
        + _png_chunk(b"IEND", b"")
    )
    assert len(bomb) < 64 * 1024

    def zlib_bomb(_: str) -> bytes:
        return bomb

    spec = _creative_spec(asset_content=zlib_bomb)
    sources = _active_asset_sources(
        spec,
        tmp_path / "sources",
        asset_content=zlib_bomb,
    )

    with pytest.raises(AssetPackError, match="pixel closure is invalid"):
        freeze_asset_pack(spec, sources, tmp_path / "packs")


def test_asset_pack_refuses_existing_drift_without_overwriting_it(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")
    pack = freeze_asset_pack(spec, sources, tmp_path / "packs")
    manifest = json.loads(pack.manifest_path.read_bytes())
    object_path = pack.root / manifest["bindings"][0]["logical_path"]
    object_path.write_bytes(b"corrupt-existing-object")

    with pytest.raises(AssetPackError, match="conflicts with its digest"):
        freeze_asset_pack(spec, sources, tmp_path / "packs")
    assert object_path.read_bytes() == b"corrupt-existing-object"


def test_asset_pack_rejects_unexpected_directory_in_existing_pack(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")
    pack = freeze_asset_pack(spec, sources, tmp_path / "packs")
    (pack.root / "unexpected-empty-directory").mkdir()

    with pytest.raises(AssetPackError, match="unexpected directories"):
        freeze_asset_pack(spec, sources, tmp_path / "packs")


def test_asset_pack_rejects_linked_output_parent(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")
    target = tmp_path / "actual-parent"
    target.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(CreativeMediaError, match="links or reparse points"):
        freeze_asset_pack(spec, sources, linked_parent)
    assert list(target.iterdir()) == []


def test_asset_pack_rejects_link_in_existing_pack(tmp_path: Path) -> None:
    spec = _creative_spec()
    sources = _active_asset_sources(spec, tmp_path / "sources")
    pack = freeze_asset_pack(spec, sources, tmp_path / "packs")
    extra_link = pack.root / "unexpected-link"
    try:
        extra_link.symlink_to(sources[0].path)
    except OSError:
        pytest.skip("file symlink creation is unavailable on this host")

    with pytest.raises(AssetPackError, match="link or reparse point"):
        freeze_asset_pack(spec, sources, tmp_path / "packs")


def test_creative_compilation_is_deterministic_and_has_exact_reference_closure() -> None:
    spec = _creative_spec(duration_ms=90_000, shot_count=12)
    first = compile_creative_sample(spec)
    second = compile_creative_sample(spec)

    assert first.model_dump_json() == second.model_dump_json()
    canonical_spec = json.dumps(
        spec.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert first.spec_sha256 == hashlib.sha256(canonical_spec).hexdigest()
    assert first.schema_version == "2.0.0"
    assert first.nir.schema_version == "2.0.0"
    assert first.pir.schema_version == "2.0.0"
    assert first.nir.duration_ms == first.pir.duration_ms == first.audio_clock.duration_ms
    assert tuple(cue.shot_id for cue in first.audio_clock.cues) == tuple(
        shot.id for shot in first.pir.shots
    )
    assert tuple(job.shot_id for job in first.job_graph.jobs) == tuple(
        shot.id for shot in first.pir.shots
    )
    assert tuple(item.job_id for item in first.assembly_plan.items) == tuple(
        job.id for job in first.job_graph.jobs
    )
    assert first.audio_clock.sample_rate_hz == 48_000
    assert tuple(shot.visual_direction for shot in first.pir.shots) == tuple(
        shot.visual_direction for shot in spec.shots
    )
    source_expression = spec.shots[0]
    compiled_expression = first.pir.shots[0]
    assert compiled_expression.emotion_by_character == source_expression.emotion_by_character
    assert compiled_expression.action == source_expression.action
    assert compiled_expression.shot_size is source_expression.shot_size
    assert compiled_expression.camera_angle is source_expression.camera_angle
    assert compiled_expression.camera_movement is source_expression.camera_movement
    assert compiled_expression.wardrobe_by_character == source_expression.wardrobe_by_character
    assert compiled_expression.props == source_expression.props
    assert compiled_expression.continuity_notes == source_expression.continuity_notes
    assert "Scene: Stable scene bible for scene-a" in first.pir.shots[0].prompt
    assert "Action: Cross the frame on story beat 0" in first.pir.shots[0].prompt
    assert "Shot size: MEDIUM" in first.pir.shots[0].prompt
    assert "Camera angle: EYE_LEVEL" in first.pir.shots[0].prompt
    assert "Camera movement: DOLLY" in first.pir.shots[0].prompt
    assert "Props: letter, watch" in first.pir.shots[0].prompt
    assert "Dialogue: Character A: We start here." in first.pir.shots[0].prompt


def test_v2_compilation_does_not_change_released_v1_contract_bytes() -> None:
    story = StoryInput.model_validate_json(Path("examples/minimal_story.json").read_text())

    before = [item.model_dump(mode="json") for item in compile_story(story)]
    compile_creative_sample(_creative_spec())
    after = [item.model_dump(mode="json") for item in compile_story(story)]
    canonical = json.dumps(
        after,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()

    assert after == before
    assert all(item["schema_version"] == "1.0.0" for item in after)
    assert hashlib.sha256(canonical).hexdigest() == (
        "054319f521a69afde2dd91180f48f9af69b3223e34468b47273b04a0773c62c7"
    )


def test_creative_metrics_are_deterministic_at_the_pass_thresholds() -> None:
    sample_id = compile_creative_sample(_creative_spec()).id
    first = _passing_metrics(sample_id=sample_id)
    second = _passing_metrics(sample_id=sample_id)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.sample_id == sample_id
    assert first.decision is CreativeSampleDecision.PASS_SAMPLE


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_pass_usable_rate", Decimal("0.749")),
        ("character_continuity_rate", Decimal("0.899")),
        ("scene_continuity_rate", Decimal("0.899")),
        ("shot_intent_pass_rate", Decimal("0.799")),
        ("artifact_free_rate", Decimal("0.899")),
        ("duplicate_media_count", 1),
    ],
)
def test_each_creative_metric_threshold_fails_closed_to_offline_revision(
    field: str,
    value: object,
) -> None:
    metrics = _passing_metrics(**{field: value})
    assert metrics.decision is CreativeSampleDecision.REVISE_OFFLINE


def test_critical_identity_break_stops_the_sample_revision() -> None:
    metrics = _passing_metrics(critical_identity_breaks=1)
    assert metrics.decision is CreativeSampleDecision.STOP


def test_metrics_reject_noncanonical_failure_taxonomy() -> None:
    with pytest.raises(ValidationError, match="canonical lowercase identifiers"):
        _passing_metrics(failure_counts={"Provider.HTTP": 1})
    with pytest.raises(ValidationError):
        _passing_metrics(sample_id="unbound-sample")
    with pytest.raises(ValidationError):
        _passing_metrics(revision_id="unbound-revision")


def test_media_toolchain_rejects_path_pair_from_different_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = ".exe" if os.name == "nt" else ""
    ffmpeg = tmp_path / "encoder" / f"ffmpeg{suffix}"
    ffprobe = tmp_path / "inspector" / f"ffprobe{suffix}"
    ffmpeg.parent.mkdir()
    ffprobe.parent.mkdir()
    ffmpeg.write_bytes(b"reviewed-ffmpeg")
    ffprobe.write_bytes(b"reviewed-ffprobe")
    paths = {"ffmpeg": ffmpeg, "ffprobe": ffprobe}
    monkeypatch.setattr(shutil, "which", lambda name: str(paths[name]))

    with pytest.raises(CreativeMediaError, match="one local tool directory"):
        resolve_media_toolchain()


def test_media_toolchain_rejects_binary_drift_after_run_start_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fake_media_tool_paths(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: str(paths[name]))
    pinned = resolve_media_toolchain()
    paths["ffmpeg"].write_bytes(b"drifted-ffmpeg-binary-with-a-new-identity")

    with pytest.raises(CreativeMediaError, match="drifted during the run"):
        verify_media_toolchain(pinned)


@pytest.mark.asyncio
async def test_media_runner_uses_reviewed_binary_stdin_null_and_clean_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeMediaProcess(stdout=b"reviewed-runner")
    captured: dict[str, object] = {}
    paths = _fake_media_tool_paths(tmp_path)

    async def spawn(*args: object, **kwargs: object) -> _FakeMediaProcess:
        captured["argv"] = args
        captured.update(kwargs)
        return process

    monkeypatch.setattr(shutil, "which", lambda name: str(paths[name]))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setenv("SYNTHETIC_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("ARK_TEST_MARKER", "must-not-reach-child")

    stdout, stderr = await creative_media._command("ffprobe", "-version")

    assert stdout == b"reviewed-runner"
    assert stderr == b""
    assert captured["argv"] == (str(paths["ffprobe"].resolve()), "-version")
    assert captured["stdin"] is asyncio.subprocess.DEVNULL
    environment = cast(dict[str, str], captured["env"])
    assert environment["LC_ALL"] == environment["LANG"] == "C"
    assert {key.upper() for key in environment} <= {
        "LANG",
        "LC_ALL",
        "SYSTEMROOT",
        "WINDIR",
    }
    assert not any("API_KEY" in key.upper() or "ARK" in key.upper() for key in environment)

    with pytest.raises(CreativeMediaError, match="only the reviewed FFmpeg tools"):
        await creative_media._command("curl", "https://example.invalid")


@pytest.mark.asyncio
async def test_media_runner_timeout_kills_and_reaps_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeMediaProcess(hangs=True)
    paths = _fake_media_tool_paths(tmp_path)

    async def spawn(*args: object, **kwargs: object) -> _FakeMediaProcess:
        return process

    monkeypatch.setattr(shutil, "which", lambda name: str(paths[name]))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(creative_media, "MEDIA_COMMAND_TIMEOUT_SECONDS", 0.001)

    with pytest.raises(CreativeMediaError, match="exceeded its time limit"):
        await creative_media._command("ffmpeg", "-version")

    assert process.killed
    assert process.returncode == -9
    assert process.wait_calls >= 2


@pytest.mark.asyncio
async def test_media_runner_failure_diagnostic_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_prefix = b"SECRET_PREFIX_MUST_BE_DROPPED"
    safe_tail = b"SAFE_DIAGNOSTIC_TAIL"
    stderr = secret_prefix + b"x" * 5_000 + safe_tail
    process = _FakeMediaProcess(
        stderr=stderr,
        exit_code=1,
    )
    paths = _fake_media_tool_paths(tmp_path)

    async def spawn(*args: object, **kwargs: object) -> _FakeMediaProcess:
        return process

    monkeypatch.setattr(shutil, "which", lambda name: str(paths[name]))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

    with pytest.raises(CreativeMediaError, match="media command failed") as caught:
        await creative_media._command("ffprobe", "-version")

    diagnostic = str(caught.value)
    assert len(diagnostic.encode()) <= 1_100
    assert secret_prefix.decode() not in diagnostic
    assert safe_tail.decode() not in diagnostic
    assert diagnostic == (
        f"media command failed (diagnostic_sha256={hashlib.sha256(stderr).hexdigest()})"
    )


@pytest.mark.asyncio
async def test_probe_forces_reviewed_local_container_without_network_protocols(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[tuple[str, ...]] = []
    media_path = tmp_path / "reviewed.mp4"
    media_path.write_bytes(b"reviewed-local-container")

    async def capture(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        return b'{"streams":[],"format":{"duration":"0","format_name":"mov"}}', b""

    monkeypatch.setattr(creative_media, "_command", capture)
    await creative_media.probe_media(media_path, input_format="mov")

    assert len(captured) == 1
    command = captured[0]
    assert command[0] == "ffprobe"
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-f") + 1] == "mov"
    assert "http" not in command and "https" not in command

    with pytest.raises(CreativeMediaError, match="reviewed local container format"):
        await creative_media.probe_media(Path("playlist.m3u8"), input_format="hls")
    assert len(captured) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "playlist",
    [
        "#EXTM3U\n#EXTINF:2,remote\nhttps://example.invalid/segment.ts\n",
        "[playlist]\nFile1=https://example.invalid/segment.mp4\nNumberOfEntries=1\n",
        "ffconcat version 1.0\nfile 'http://example.invalid/segment.mp4'\n",
    ],
    ids=["m3u8", "pls", "ffconcat"],
)
async def test_playlist_shaped_input_cannot_escape_forced_local_mov_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    playlist: str,
) -> None:
    malicious = tmp_path / "malicious-playlist.m3u8"
    malicious.write_text(playlist)
    captured: list[tuple[str, ...]] = []

    async def offline_probe(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        return (
            b'{"streams":[],"format":{"duration":"2.0","format_name":"mov"}}',
            b"",
        )

    monkeypatch.setattr(creative_media, "_command", offline_probe)

    with pytest.raises(CreativeMediaError, match="exactly one video stream"):
        await inspect_imported_video(malicious, expected_duration_ms=2_000)

    assert len(captured) == 1
    command = captured[0]
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-f") + 1] == "mov"
    assert not any("http://" in item or "https://" in item for item in command)


@pytest.mark.asyncio
async def test_external_url_path_is_rejected_before_media_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def must_not_run(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        pytest.fail(f"external URL reached media command: {args!r}")

    monkeypatch.setattr(creative_media, "_command", must_not_run)
    with pytest.raises(CreativeMediaError, match="non-portable component"):
        await inspect_imported_video(
            Path("https://example.invalid/remote.mp4"),
            expected_duration_ms=2_000,
        )


@pytest.fixture
def moving_video(tmp_path: Path) -> Path:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for imported-media verification")
    output = tmp_path / "moving-shot.mp4"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=160x90:rate=8:duration=2",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        str(output),
    )
    return output


@pytest.fixture
def static_video(tmp_path: Path) -> Path:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for imported-media verification")
    output = tmp_path / "static-placeholder.mp4"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:size=160x90:rate=8:duration=2",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        str(output),
    )
    return output


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_stream", ["audio", "subtitle", "data", "attachment"])
async def test_imported_video_requires_exact_single_stream_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_stream: str,
) -> None:
    video = tmp_path / "claimed-video.mp4"
    video.write_bytes(b"locally-imported-video")

    async def extra_stream_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        assert path == video
        assert input_format == "mov"
        return {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": extra_stream},
            ],
            "format": {"duration": "2.0", "format_name": "mov,mp4"},
        }

    async def must_not_sample(path: Path, **kwargs: object) -> int:
        pytest.fail(f"non-closed video reached frame sampling: {path}")

    monkeypatch.setattr(creative_media, "probe_media", extra_stream_probe)
    monkeypatch.setattr(creative_media, "_distinct_sampled_frames", must_not_sample)

    with pytest.raises(CreativeMediaError, match="exactly one video stream"):
        await inspect_imported_video(video, expected_duration_ms=2_000)


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_stream", ["audio", "video", "subtitle", "data"])
async def test_imported_audio_requires_exact_single_stream_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_stream: str,
) -> None:
    audio = tmp_path / "claimed-audio.wav"
    audio.write_bytes(b"locally-imported-audio")

    async def extra_stream_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        assert path == audio
        assert input_format == "wav"
        return {
            "streams": [
                {"codec_type": "audio", "codec_name": "pcm_s16le"},
                {"codec_type": extra_stream},
            ],
            "format": {"duration": "1.0", "format_name": "wav"},
        }

    monkeypatch.setattr(creative_media, "probe_media", extra_stream_probe)

    with pytest.raises(CreativeMediaError, match="exactly one audio stream"):
        await inspect_imported_audio(audio)


@pytest.mark.asyncio
async def test_imported_video_accepts_dynamic_frames_for_technical_import_only(
    moving_video: Path,
) -> None:
    evidence, distinct_frames = await inspect_imported_video(
        moving_video,
        expected_duration_ms=2_000,
    )

    assert evidence.path == moving_video.absolute()
    assert evidence.size_bytes == moving_video.stat().st_size
    assert evidence.sha256 == hashlib.sha256(moving_video.read_bytes()).hexdigest()
    assert distinct_frames >= 2
    streams = cast(list[object], evidence.ffprobe["streams"])
    assert [stream["codec_type"] for stream in streams if isinstance(stream, dict)] == ["video"]


@pytest.mark.asyncio
async def test_solid_or_static_placeholder_is_not_creative_evidence(static_video: Path) -> None:
    with pytest.raises(CreativeMediaError, match="solid-color or static placeholder"):
        await inspect_imported_video(static_video, expected_duration_ms=2_000)


@pytest.mark.asyncio
async def test_imported_audio_records_local_digest_and_48khz_probe(tmp_path: Path) -> None:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for imported-media verification")
    audio = tmp_path / "voice.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=1",
        "-c:a",
        "pcm_s16le",
        str(audio),
    )

    evidence = await inspect_imported_audio(audio)

    streams = evidence.ffprobe["streams"]
    assert isinstance(streams, list)
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    assert len(audio_streams) == 1
    assert audio_streams[0]["sample_rate"] == "48000"
    assert evidence.sha256 == hashlib.sha256(audio.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_audio_master_is_real_48khz_stereo_pcm_with_voice_and_bgm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for audio-master verification")
    voice = tmp_path / "voice.wav"
    bgm = tmp_path / "bgm.wav"
    output = tmp_path / "audio-master.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100:duration=1",
        "-c:a",
        "pcm_s16le",
        str(voice),
    )
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:sample_rate=48000:duration=1",
        "-c:a",
        "pcm_s16le",
        str(bgm),
    )
    commands: list[tuple[str, ...]] = []
    original_command = creative_media._command

    async def record_command(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        commands.append(args)
        return await original_command(
            *args,
            _toolchain=cast(MediaToolchain | None, kwargs.get("_toolchain")),
        )

    monkeypatch.setattr(creative_media, "_command", record_command)

    await render_audio_master(
        voices=(TimedVoiceTrack("line", voice, 500, 1_500),),
        bgm=bgm,
        duration_ms=60_000,
        output=output,
    )
    probe = await creative_media.probe_media(output)
    streams = probe["streams"]
    assert isinstance(streams, list)
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    assert len(audio_streams) == 1
    assert audio_streams[0]["codec_name"] == "pcm_s16le"
    assert audio_streams[0]["sample_rate"] == "48000"
    assert audio_streams[0]["channels"] == 2
    format_info = probe["format"]
    assert isinstance(format_info, dict)
    assert abs(float(format_info["duration"]) - 60.0) <= 0.01
    render_command = next(
        command for command in commands if command[0] == "ffmpeg" and str(output) in command
    )
    assert render_command[:5] == ("ffmpeg", "-v", "error", "-nostdin", "-n")
    assert render_command.count("-protocol_whitelist") == 2
    assert render_command.count("wav") == 3  # two inputs plus explicit WAV output demux/mux
    assert render_command[render_command.index("-map_metadata") + 1] == "-1"
    assert render_command[render_command.index("-map_chapters") + 1] == "-1"
    assert render_command[-5:] == (
        "-f",
        "wav",
        "-fs",
        str(creative_media.MAX_IMPORTED_MEDIA_BYTES),
        str(output.absolute()),
    )


@pytest.mark.asyncio
async def test_audio_master_never_overwrites_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "audio-master.wav"
    output.write_bytes(b"existing-audio-master")

    with pytest.raises(CreativeMediaError, match="new file"):
        await render_audio_master(
            voices=(),
            bgm=None,
            duration_ms=60_000,
            output=output,
        )
    assert output.read_bytes() == b"existing-audio-master"


def test_subtitles_are_utf8_deterministic_and_master_clock_bound() -> None:
    cues = [
        (0, 1_250, " 第一行\n继续 "),
        (59_000, 60_000, "ending"),
    ]

    first = render_srt(cues)
    second = render_srt(cues)

    assert first == second
    assert first.decode("utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,250\n第一行 继续\n\n"
        "2\n00:00:59,000 --> 00:01:00,000\nending\n\n"
    )


@pytest.mark.parametrize(
    "cues",
    [
        [(-1, 1, "negative")],
        [(1, 1, "empty")],
        [(10, 20, "later"), (5, 8, "earlier")],
        [(0, 10, "first"), (5, 15, "overlap")],
        [(0, 1, " \n ")],
    ],
)
def test_subtitles_reject_invalid_timing_or_empty_text(
    cues: list[tuple[int, int, str]],
) -> None:
    with pytest.raises(CreativeMediaError):
        render_srt(cues)


@pytest.mark.asyncio
async def test_audio_master_rejects_duplicate_or_overlapping_voice_clock_bindings(
    tmp_path: Path,
) -> None:
    with pytest.raises(CreativeMediaError, match="unique line identities"):
        await render_audio_master(
            voices=(
                TimedVoiceTrack("same-line", tmp_path / "voice-a.wav", 0, 1_000),
                TimedVoiceTrack("same-line", tmp_path / "voice-b.wav", 1_000, 2_000),
            ),
            bgm=None,
            duration_ms=60_000,
            output=tmp_path / "duplicate.wav",
        )
    with pytest.raises(CreativeMediaError, match="non-overlapping master-clock intervals"):
        await render_audio_master(
            voices=(
                TimedVoiceTrack("line-a", tmp_path / "voice-a.wav", 0, 1_000),
                TimedVoiceTrack("line-b", tmp_path / "voice-b.wav", 500, 1_500),
            ),
            bgm=None,
            duration_ms=60_000,
            output=tmp_path / "overlap.wav",
        )


@pytest.mark.asyncio
async def test_sixty_second_eight_shot_assembly_binds_voice_bgm_and_subtitles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, ...]] = []

    async def capture(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        return b"", b""

    monkeypatch.setattr(creative_media, "_command", capture)
    videos = tuple((tmp_path / f"shot-{index}.mp4", 7_500) for index in range(8))
    voices = (
        TimedVoiceTrack("line-1", tmp_path / "voice-1.wav", 500, 4_000),
        TimedVoiceTrack("line-2", tmp_path / "voice-2.wav", 30_000, 35_000),
    )
    subtitles = tmp_path / "sample.srt"
    bgm = tmp_path / "bgm.wav"
    output = tmp_path / "render" / "sample.mp4"
    for path, content in (
        *((path, f"video-{index}".encode()) for index, (path, _) in enumerate(videos)),
        *((voice.path, voice.line_id.encode()) for voice in voices),
        (subtitles, render_srt(((0, 1_000, "sample"),))),
        (bgm, b"background-music"),
    ):
        path.write_bytes(content)

    await assemble_sample(
        videos=videos,
        voices=voices,
        bgm=bgm,
        subtitles=subtitles,
        duration_ms=60_000,
        output=output,
    )

    assert len(captured) == 1
    command = captured[0]
    filter_graph = command[command.index("-filter_complex") + 1]
    assert command[:5] == ("ffmpeg", "-v", "error", "-nostdin", "-n")
    assert command.count("-i") == 12  # 8 video + 2 voice + BGM + subtitles
    assert command.count("-protocol_whitelist") == 12
    assert all(
        command[index + 1] == "file"
        for index, item in enumerate(command)
        if item == "-protocol_whitelist"
    )
    assert command.count("mov") == 8
    assert command.count("wav") == 3
    assert command.count("srt") == 1
    assert "concat=n=8:v=1:a=0[video_master]" in filter_graph
    assert "scale=1080:1920" in filter_graph
    assert "setsar=1,fps=25" in filter_graph
    assert filter_graph.count("aresample=48000") == 3
    assert "volume=0.12" in filter_graph
    assert "amix=inputs=3:duration=longest:normalize=0" in filter_graph
    assert command[command.index("-ar") + 1] == "48000"
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-c:s") + 1] == "mov_text"
    assert command[command.index("-map_metadata") + 1] == "-1"
    assert command[command.index("-map_chapters") + 1] == "-1"
    assert command[command.index("-f", command.index("-filter_complex")) + 1] == "mp4"
    assert command[command.index("-t") + 1] == "60.000"
    assert command[-1] == str(output.absolute())
    assert output.parent.is_dir()


@pytest.mark.asyncio
async def test_final_assembly_uses_one_audio_master_and_encodes_it_as_aac(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, ...]] = []

    async def capture(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        return b"", b""

    monkeypatch.setattr(creative_media, "_command", capture)
    videos = tuple((tmp_path / f"shot-{index}.mp4", 7_500) for index in range(8))
    for index, (path, _) in enumerate(videos):
        path.write_bytes(f"video-{index}".encode())
    audio_master = tmp_path / "audio-master.wav"
    audio_master.write_bytes(b"48khz-stereo-pcm-master")
    subtitles = tmp_path / "sample.srt"
    subtitles.write_bytes(render_srt(((500, 1_500, "sample"),)))

    await assemble_sample(
        videos=videos,
        voices=(TimedVoiceTrack("audio-master", audio_master, 0, 60_000),),
        bgm=None,
        subtitles=subtitles,
        duration_ms=60_000,
        output=tmp_path / "sample.mp4",
    )

    assert len(captured) == 1
    command = captured[0]
    filter_graph = command[command.index("-filter_complex") + 1]
    assert command.count("-i") == 10  # 8 video + one audio master + subtitles
    assert command.count("-protocol_whitelist") == 10
    assert command.count("mov") == 8
    assert command.count("wav") == 1
    assert command.count("srt") == 1
    assert filter_graph.count("aresample=48000") == 1
    assert "[voice0]anull[audio_master]" in filter_graph
    assert "volume=" not in filter_graph
    assert "amix=" not in filter_graph
    assert command[command.index("-c:a") + 1] == "aac"
    assert command[command.index("-ar") + 1] == "48000"
    assert command[command.index("-map_metadata") + 1] == "-1"
    assert command[command.index("-map_chapters") + 1] == "-1"


@pytest.mark.asyncio
@pytest.mark.parametrize("duration_ms", [59_999, 90_001])
async def test_assembly_rejects_out_of_range_master_clock(
    tmp_path: Path,
    duration_ms: int,
) -> None:
    with pytest.raises(CreativeMediaError, match="60..90 seconds"):
        await assemble_sample(
            videos=((tmp_path / "shot.mp4", duration_ms),),
            voices=(),
            bgm=None,
            subtitles=tmp_path / "sample.srt",
            duration_ms=duration_ms,
            output=tmp_path / "sample.mp4",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("shot_count", [7, 13])
async def test_assembly_requires_eight_to_twelve_nonempty_shots(
    tmp_path: Path,
    shot_count: int,
) -> None:
    with pytest.raises(CreativeMediaError, match="8..12 non-empty shots"):
        await assemble_sample(
            videos=tuple((tmp_path / f"shot-{index}.mp4", 1) for index in range(shot_count)),
            voices=(),
            bgm=None,
            subtitles=tmp_path / "sample.srt",
            duration_ms=60_000,
            output=tmp_path / "sample.mp4",
        )


@pytest.mark.asyncio
async def test_assembly_requires_exact_shot_master_timeline(tmp_path: Path) -> None:
    with pytest.raises(CreativeMediaError, match="exact master timeline"):
        await assemble_sample(
            videos=tuple((tmp_path / f"shot-{index}.mp4", 7_499) for index in range(8)),
            voices=(),
            bgm=None,
            subtitles=tmp_path / "sample.srt",
            duration_ms=60_000,
            output=tmp_path / "sample.mp4",
        )


@pytest.mark.asyncio
async def test_assembly_never_overwrites_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "sample.mp4"
    output.write_bytes(b"existing-user-output")
    videos = tuple((tmp_path / f"shot-{ordinal}.mp4", 7_500) for ordinal in range(8))
    for ordinal, (video, _) in enumerate(videos):
        video.write_bytes(f"video-{ordinal}".encode())
    subtitles = tmp_path / "sample.srt"
    subtitles.write_bytes(render_srt(((0, 1_000, "sample"),)))

    async def must_not_run(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        pytest.fail(f"FFmpeg must not run for an existing output: {args!r}")

    monkeypatch.setattr(creative_media, "_command", must_not_run)
    with pytest.raises(CreativeMediaError, match="new file"):
        await assemble_sample(
            videos=videos,
            voices=(),
            bgm=None,
            subtitles=subtitles,
            duration_ms=60_000,
            output=output,
        )
    assert output.read_bytes() == b"existing-user-output"


@pytest.mark.asyncio
async def test_technical_qc_is_deterministic_and_checks_final_delivery_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = tmp_path / "assembled.mp4"
    sample.write_bytes(b"immutable-assembled-sample")
    probe: dict[str, object] = {
        "format": {"duration": "60.000"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "pix_fmt": "yuv420p",
                "avg_frame_rate": "25/1",
                "width": 1080,
                "height": 1920,
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
            },
            {"codec_type": "subtitle", "codec_name": "mov_text"},
        ],
    }

    async def fixed_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        assert path == sample
        assert input_format == "mov"
        return probe

    monkeypatch.setattr(creative_media, "probe_media", fixed_probe)
    first = await verify_assembled_sample(sample, expected_duration_ms=60_000)
    second = await verify_assembled_sample(sample, expected_duration_ms=60_000)

    assert first == second
    assert first.passed
    assert {check.check: check.passed for check in first.checks} == {
        "stream_closure": True,
        "dimensions": True,
        "video_profile": True,
        "audio_profile": True,
        "subtitle_profile": True,
        "duration": True,
    }
    assert first.media.sha256 == hashlib.sha256(sample.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_technical_qc_reports_profile_drift_without_relabeling_it_passed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = tmp_path / "drifted.mp4"
    sample.write_bytes(b"drifted-sample")

    async def drifted_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        assert path == sample
        assert input_format == "mov"
        return {
            "format": {"duration": "59.500"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "avg_frame_rate": "25/1",
                    "width": 1080,
                    "height": 1920,
                },
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100"},
                {"codec_type": "subtitle", "codec_name": "mov_text"},
            ],
        }

    monkeypatch.setattr(creative_media, "probe_media", drifted_probe)
    result = await verify_assembled_sample(sample, expected_duration_ms=60_000)

    checks = {check.check: check.passed for check in result.checks}
    assert not result.passed
    assert checks["audio_profile"] is False
    assert checks["duration"] is False


@pytest.mark.asyncio
async def test_technical_qc_rejects_extra_data_stream_outside_exact_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = tmp_path / "extra-stream.mp4"
    sample.write_bytes(b"assembled-sample-with-extra-stream")

    async def extra_stream_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        assert path == sample
        assert input_format == "mov"
        return {
            "format": {"duration": "60.000", "format_name": "mov,mp4"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "avg_frame_rate": "25/1",
                    "width": 1080,
                    "height": 1920,
                },
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
                {"codec_type": "subtitle", "codec_name": "mov_text"},
                {"codec_type": "data", "codec_name": "bin_data"},
            ],
        }

    monkeypatch.setattr(creative_media, "probe_media", extra_stream_probe)
    result = await verify_assembled_sample(sample, expected_duration_ms=60_000)

    checks = {check.check: check.passed for check in result.checks}
    assert not result.passed
    assert checks["stream_closure"] is False


def test_local_media_rejects_traversal_protected_and_non_regular_paths(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"media")
    data, info = read_regular_media(clip)
    assert data == b"media"
    assert info.st_size == len(data)

    with pytest.raises(CreativeMediaError, match="canonical local components"):
        read_regular_media(tmp_path / "missing" / ".." / "clip.mp4")

    protected = tmp_path / "canary" / "clip.mp4"
    protected.parent.mkdir()
    protected.write_bytes(b"not-sample-evidence")
    with pytest.raises(CreativeMediaError, match="protected evidence and Canary"):
        read_regular_media(protected)

    directory = tmp_path / "directory.mp4"
    directory.mkdir()
    with pytest.raises(CreativeMediaError, match="regular non-link file"):
        read_regular_media(directory)

    with pytest.raises(CreativeMediaError, match="network and device paths"):
        read_regular_media(Path(r"\\server\share\remote.mp4"))


@pytest.mark.skipif(os.name != "nt", reason="Win32 drive types are Windows-only")
@pytest.mark.asyncio
@pytest.mark.parametrize("blocked_drive_type", [0, 4], ids=["unknown", "remote"])
@pytest.mark.parametrize("blocked_stage", [0, 1, 2], ids=["raw", "absolute", "resolved"])
async def test_windows_drive_type_rejects_before_media_read_or_ffprobe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    blocked_drive_type: int,
    blocked_stage: int,
) -> None:
    clip = (tmp_path / "local-clip.mp4").absolute()
    clip.write_bytes(b"must-not-be-read")
    drive_checks: list[str] = []

    def drive_type(anchor: str) -> int:
        stage = len(drive_checks)
        drive_checks.append(anchor)
        return blocked_drive_type if stage == blocked_stage else 3

    def unexpected_open(*args: object, **kwargs: object) -> object:
        pytest.fail(f"media content was opened before drive rejection: {args!r} {kwargs!r}")

    async def unexpected_probe(
        path: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        pytest.fail(f"ffprobe ran before drive rejection: {path}")

    monkeypatch.setattr(creative_media, "_windows_drive_type", drive_type)
    monkeypatch.setattr(Path, "open", unexpected_open)
    monkeypatch.setattr(creative_media, "probe_media", unexpected_probe)

    with pytest.raises(CreativeMediaError, match="network or unverified drives"):
        await inspect_imported_video(
            clip,
            expected_duration_ms=1_000,
            toolchain=_placeholder_media_toolchain(),
        )
    assert len(drive_checks) == blocked_stage + 1


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["input", "output"])
@pytest.mark.parametrize(
    ("component", "message"),
    [
        ("clip.mp4:alternate-stream", "non-portable component"),
        ("CON.mp4", "reserved device name"),
        ("nul", "reserved device name"),
        ("COM1.mov", "reserved device name"),
        ("Lpt9.wav", "reserved device name"),
        ("bad?.mp4", "non-portable component"),
        ("bad|name.mp4", "non-portable component"),
    ],
    ids=["ads", "con", "nul", "com1", "lpt9", "question-mark", "pipe"],
)
async def test_windows_ambiguous_components_fail_closed_for_inputs_and_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    direction: str,
    component: str,
    message: str,
) -> None:
    path = tmp_path / component

    def unexpected_open(*args: object, **kwargs: object) -> object:
        pytest.fail(f"ambiguous path was opened: {args!r} {kwargs!r}")

    async def unexpected_probe(
        candidate: Path,
        *,
        input_format: str | None = None,
        toolchain: MediaToolchain | None = None,
    ) -> dict[str, object]:
        pytest.fail(f"ambiguous path reached ffprobe: {candidate}")

    async def unexpected_command(*args: str, **kwargs: object) -> tuple[bytes, bytes]:
        pytest.fail(f"ambiguous output reached FFmpeg: {args!r}")

    monkeypatch.setattr(Path, "open", unexpected_open)
    monkeypatch.setattr(creative_media, "probe_media", unexpected_probe)
    monkeypatch.setattr(creative_media, "_command", unexpected_command)

    with pytest.raises(CreativeMediaError, match=message):
        if direction == "input":
            await inspect_imported_video(
                path,
                expected_duration_ms=1_000,
                toolchain=_placeholder_media_toolchain(),
            )
        else:
            await render_audio_master(
                voices=(),
                bgm=None,
                duration_ms=60_000,
                output=path,
                toolchain=_placeholder_media_toolchain(),
            )


def test_local_media_rejects_links(tmp_path: Path) -> None:
    target = tmp_path / "target.mp4"
    target.write_bytes(b"media")
    link = tmp_path / "link.mp4"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(CreativeMediaError, match="links or reparse points"):
        read_regular_media(link)


def test_local_media_rejects_hard_links(tmp_path: Path) -> None:
    target = tmp_path / "target.mp4"
    target.write_bytes(b"media")
    hard_link = tmp_path / "hard-link.mp4"
    try:
        os.link(target, hard_link)
    except OSError:
        pytest.skip("hard-link creation is unavailable on this host")

    with pytest.raises(CreativeMediaError, match="hard link"):
        read_regular_media(hard_link)


def test_provider_boundaries_are_async_local_and_credential_free() -> None:
    assert inspect.iscoroutinefunction(VoiceProvider.synthesize)
    assert inspect.iscoroutinefunction(ImageProvider.render_character_reference)
    assert inspect.iscoroutinefunction(ImageProvider.render_scene_reference)
    assert inspect.iscoroutinefunction(AvatarProvider.render_dialogue_shot)
    for operation in (
        VoiceProvider.synthesize,
        ImageProvider.render_character_reference,
        ImageProvider.render_scene_reference,
        AvatarProvider.render_dialogue_shot,
    ):
        signature = inspect.signature(operation)
        assert signature.parameters["destination"].kind is inspect.Parameter.KEYWORD_ONLY
        assert signature.parameters["destination"].annotation in {"Path", Path}

    artifact = LocalCreativeArtifact(
        artifact_id="voice-line-1",
        path=Path("voice-line-1.wav"),
        sha256="a" * 64,
        size_bytes=123,
        media_type="audio/wav",
    )
    with pytest.raises(FrozenInstanceError):
        artifact.path = Path("replacement.wav")  # type: ignore[misc]


@pytest.mark.parametrize(
    "module",
    [
        asset_pack_module,
        compiler_module,
        creative_media,
        creative_providers,
        creative_sample_module,
    ],
)
def test_creative_loop_has_no_network_key_or_ark_boundary(module: ModuleType) -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.partition(".")[0])
            imported_modules.add(node.module)
    forbidden_imports = {
        "aiohttp",
        "boto3",
        "httpx",
        "requests",
        "socket",
        "temporalio",
        "urllib",
    }
    assert imported_roots.isdisjoint(forbidden_imports)
    assert imported_modules.isdisjoint(
        {
            "sdc.ark_provider",
            "sdc.persistence",
            "sdc.provider",
            "sdc.runtime",
            "sdc.worker",
            "sdc.workflow",
        }
    )
    assert "os.environ[" not in source
    assert source.count("os.environ.get") <= 1
    assert "getenv(" not in source
    assert "api_key" not in source.casefold()
    assert "ark_provider" not in source.casefold()
    assert "authorization_registry" not in source.casefold()
    assert "entitlement_registry" not in source.casefold()
