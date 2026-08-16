"""Offline-only media import, subtitle, audio-master, and sample assembly helpers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import shutil
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

SAMPLE_WIDTH = 1080
SAMPLE_HEIGHT = 1920
SAMPLE_FPS = 25
SAMPLE_AUDIO_RATE = 48_000
MAX_IMPORTED_MEDIA_BYTES = 512 * 1024 * 1024
MEDIA_COMMAND_TIMEOUT_SECONDS = 300.0
MAX_MEDIA_STDOUT_BYTES = 4 * 1024 * 1024
MAX_MEDIA_STDERR_BYTES = 64 * 1024

_PROTECTED_COMPONENTS = frozenset(
    {
        "canary",
        "evidence-cas",
        "evidence-current",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
    }
)
_WINDOWS_RESERVED_STEMS = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)


class CreativeMediaError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaFileEvidence:
    path: Path
    sha256: str
    size_bytes: int
    ffprobe: dict[str, object]


@dataclass(frozen=True, slots=True)
class MediaToolchain:
    """One process-local pin of the operator-controlled FFmpeg installation."""

    ffmpeg_path: Path
    ffprobe_path: Path
    ffmpeg_sha256: str
    ffprobe_sha256: str
    ffmpeg_identity: tuple[int, int, int, int]
    ffprobe_identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class TimedVoiceTrack:
    line_id: str
    path: Path
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class TechnicalCheck:
    check: str
    passed: bool
    details: dict[str, str | int | bool]


@dataclass(frozen=True, slots=True)
class CreativeTechnicalQC:
    passed: bool
    checks: tuple[TechnicalCheck, ...]
    media: MediaFileEvidence


def _is_link_like(path: Path, mode: int, file_attributes: int) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return (
        stat.S_ISLNK(mode)
        or bool(file_attributes & 0x400)
        or path.is_symlink()
        or bool(is_junction is not None and is_junction())
    )


def _windows_drive_type(anchor: str) -> int:
    """Return Win32 GetDriveTypeW without resolving or reading the path."""
    if os.name != "nt":
        return 3
    try:
        import ctypes

        kernel32 = cast(Any, ctypes).windll.kernel32
        return int(kernel32.GetDriveTypeW(anchor))
    except (AttributeError, OSError) as exc:
        raise CreativeMediaError("media drive type could not be verified") from exc


def _reject_nonlocal_path(path: Path) -> None:
    rendered = str(path)
    if rendered.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\")):
        raise CreativeMediaError("network and device paths are not supported")
    if path.drive and not path.root:
        raise CreativeMediaError("drive-relative media paths are not supported")
    if os.name == "nt" and path.drive and _windows_drive_type(path.anchor) in {0, 1, 4}:
        raise CreativeMediaError("network or unverified drives are not supported")


def _portable_component(part: str) -> str:
    if part in {"", ".", ".."} or part.rstrip(" .") != part:
        raise CreativeMediaError("media paths must use canonical local components")
    if any(character in '<>:"|?*' for character in part) or any(
        ord(character) < 32 or ord(character) == 127 for character in part
    ):
        raise CreativeMediaError("media paths contain a non-portable component")
    if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_STEMS:
        raise CreativeMediaError("media paths contain a reserved device name")
    return part.casefold()


def _check_components(path: Path) -> None:
    parts = path.parts[1:] if path.anchor else path.parts
    normalized = tuple(_portable_component(part) for part in parts)
    if any(part in _PROTECTED_COMPONENTS for part in normalized):
        raise CreativeMediaError("protected evidence and Canary paths are not sample inputs")


def validate_local_path(path: Path, *, must_exist: bool) -> Path:
    _reject_nonlocal_path(path)
    _check_components(path)
    absolute = path.absolute()
    _reject_nonlocal_path(absolute)
    _check_components(absolute)

    cursor = absolute if os.path.lexists(absolute) else absolute.parent
    while True:
        if os.path.lexists(cursor):
            info = cursor.lstat()
            attributes = int(getattr(info, "st_file_attributes", 0))
            if _is_link_like(cursor, info.st_mode, attributes):
                raise CreativeMediaError("media paths must not traverse links or reparse points")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent

    if must_exist and not os.path.lexists(absolute):
        raise CreativeMediaError(f"media input does not exist: {absolute}")
    try:
        resolved = absolute.resolve(strict=must_exist)
    except OSError as exc:
        raise CreativeMediaError("media path could not be resolved safely") from exc
    _reject_nonlocal_path(resolved)
    _check_components(resolved)
    cursor = resolved if os.path.lexists(resolved) else resolved.parent
    while True:
        if os.path.lexists(cursor):
            info = cursor.lstat()
            attributes = int(getattr(info, "st_file_attributes", 0))
            if _is_link_like(cursor, info.st_mode, attributes):
                raise CreativeMediaError("resolved media paths must not traverse reparse points")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    return resolved


def read_regular_media(path: Path) -> tuple[bytes, os.stat_result]:
    absolute = validate_regular_media_path(path)
    before = absolute.lstat()
    attributes = int(getattr(before, "st_file_attributes", 0))
    if _is_link_like(absolute, before.st_mode, attributes) or not stat.S_ISREG(before.st_mode):
        raise CreativeMediaError("media input must be a regular non-link file")
    if before.st_nlink != 1:
        raise CreativeMediaError("media input must not be a hard link")
    if before.st_size <= 0 or before.st_size > MAX_IMPORTED_MEDIA_BYTES:
        raise CreativeMediaError("media input violates the byte limit")
    with absolute.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise CreativeMediaError("media input changed before it was opened")
        data = handle.read(MAX_IMPORTED_MEDIA_BYTES + 1)
        if len(data) != before.st_size:
            raise CreativeMediaError("media input changed while it was read")
    after = absolute.lstat()
    if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ):
        raise CreativeMediaError("media input changed after it was read")
    return data, before


def validate_regular_media_path(path: Path) -> Path:
    """Validate a declared file identity without opening its bytes."""
    absolute = validate_local_path(path, must_exist=True)
    info = absolute.lstat()
    attributes = int(getattr(info, "st_file_attributes", 0))
    if _is_link_like(absolute, info.st_mode, attributes) or not stat.S_ISREG(info.st_mode):
        raise CreativeMediaError("media input must be a regular non-link file")
    if info.st_nlink != 1:
        raise CreativeMediaError("media input must not be a hard link")
    if info.st_size <= 0 or info.st_size > MAX_IMPORTED_MEDIA_BYTES:
        raise CreativeMediaError("media input violates the byte limit")
    return absolute


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def resolve_media_toolchain() -> MediaToolchain:
    """Resolve, hash and pin the local FFmpeg pair once for one sample run."""
    located: dict[str, tuple[Path, bytes, os.stat_result]] = {}
    for name in ("ffmpeg", "ffprobe"):
        rendered = shutil.which(name)
        if rendered is None:
            raise CreativeMediaError(f"required media tool is unavailable: {name}")
        path = validate_local_path(Path(rendered), must_exist=True)
        expected_names = {name, f"{name}.exe"}
        if path.name.casefold() not in expected_names:
            raise CreativeMediaError("media tool filename does not match its reviewed role")
        data, info = read_regular_media(path)
        located[name] = (path, data, info)
    ffmpeg_path, ffmpeg_data, ffmpeg_info = located["ffmpeg"]
    ffprobe_path, ffprobe_data, ffprobe_info = located["ffprobe"]
    if ffmpeg_path.parent != ffprobe_path.parent:
        raise CreativeMediaError("ffmpeg and ffprobe must come from one local tool directory")
    return MediaToolchain(
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        ffmpeg_sha256=hashlib.sha256(ffmpeg_data).hexdigest(),
        ffprobe_sha256=hashlib.sha256(ffprobe_data).hexdigest(),
        ffmpeg_identity=_stat_identity(ffmpeg_info),
        ffprobe_identity=_stat_identity(ffprobe_info),
    )


def verify_media_toolchain(toolchain: MediaToolchain) -> None:
    """Re-read both binaries and reject drift from the run-start pins."""
    for path, expected_sha256, expected_identity in (
        (
            toolchain.ffmpeg_path,
            toolchain.ffmpeg_sha256,
            toolchain.ffmpeg_identity,
        ),
        (
            toolchain.ffprobe_path,
            toolchain.ffprobe_sha256,
            toolchain.ffprobe_identity,
        ),
    ):
        data, info = read_regular_media(path)
        if (
            _stat_identity(info) != expected_identity
            or hashlib.sha256(data).hexdigest() != expected_sha256
        ):
            raise CreativeMediaError("the pinned local media toolchain drifted during the run")


def _verify_tool_before_exec(
    path: Path,
    expected_identity: tuple[int, int, int, int],
) -> None:
    absolute = validate_local_path(path, must_exist=True)
    info = absolute.lstat()
    if _stat_identity(info) != expected_identity:
        raise CreativeMediaError("the pinned local media tool changed before execution")


def _sanitized_subprocess_environment() -> dict[str, str]:
    environment = {"LC_ALL": "C", "LANG": "C"}
    if os.name == "nt":
        for key in ("SystemRoot", "WINDIR"):
            value = os.environ.get(key)
            if value is not None:
                environment[key] = value
    return environment


async def _bounded_read(
    stream: asyncio.StreamReader | None,
    *,
    limit: int,
) -> bytes:
    if stream is None:
        return b""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await stream.read(min(64 * 1024, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise CreativeMediaError("media command output exceeded its byte limit")


async def _command(
    *args: str,
    _toolchain: MediaToolchain | None = None,
) -> tuple[bytes, bytes]:
    if not args or args[0] not in {"ffmpeg", "ffprobe"}:
        raise CreativeMediaError("only the reviewed FFmpeg tools may be executed")
    toolchain = _toolchain or resolve_media_toolchain()
    if args[0] == "ffmpeg":
        executable = toolchain.ffmpeg_path
        expected_identity = toolchain.ffmpeg_identity
    else:
        executable = toolchain.ffprobe_path
        expected_identity = toolchain.ffprobe_identity
    _verify_tool_before_exec(executable, expected_identity)
    process = await asyncio.create_subprocess_exec(
        str(executable),
        *args[1:],
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_sanitized_subprocess_environment(),
    )
    stdout_task = asyncio.create_task(_bounded_read(process.stdout, limit=MAX_MEDIA_STDOUT_BYTES))
    stderr_task = asyncio.create_task(_bounded_read(process.stderr, limit=MAX_MEDIA_STDERR_BYTES))
    try:
        _, stdout, stderr = await asyncio.wait_for(
            asyncio.gather(process.wait(), stdout_task, stderr_task),
            timeout=MEDIA_COMMAND_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        for task in (stdout_task, stderr_task):
            task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        raise CreativeMediaError("media command exceeded its time limit") from exc
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        for task in (stdout_task, stderr_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        raise
    if process.returncode:
        diagnostic_sha256 = hashlib.sha256(stderr).hexdigest()
        raise CreativeMediaError(f"media command failed (diagnostic_sha256={diagnostic_sha256})")
    _verify_tool_before_exec(executable, expected_identity)
    return stdout, stderr


def _input_format(path: Path) -> str:
    return "wav" if path.suffix.casefold() == ".wav" else "mov"


async def probe_media(
    path: Path,
    *,
    input_format: str | None = None,
    toolchain: MediaToolchain | None = None,
) -> dict[str, object]:
    reviewed_format = input_format or _input_format(path)
    if reviewed_format not in {"mov", "wav"}:
        raise CreativeMediaError("media probing requires a reviewed local container format")
    validate_regular_media_path(path)
    active_toolchain = toolchain or resolve_media_toolchain()
    stdout, _ = await _command(
        "ffprobe",
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-f",
        reviewed_format,
        *(["-enable_drefs", "0", "-use_absolute_path", "0"] if reviewed_format == "mov" else []),
        "-probesize",
        "16777216",
        "-analyzeduration",
        "10000000",
        "-show_entries",
        (
            "stream=index,codec_type,codec_name,pix_fmt,avg_frame_rate,width,height,"
            "sample_rate,channels:format=duration,format_name"
        ),
        "-of",
        "json",
        str(path),
        _toolchain=active_toolchain,
    )
    value = json.loads(stdout)
    if not isinstance(value, dict):
        raise CreativeMediaError("ffprobe returned a non-object payload")
    if len(_streams(value)) > 4:
        raise CreativeMediaError("media input contains too many streams")
    return value


def _streams(probe: dict[str, object]) -> list[dict[str, object]]:
    value = probe.get("streams")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _duration_ms(probe: dict[str, object]) -> int:
    fmt = probe.get("format")
    if not isinstance(fmt, dict):
        return 0
    try:
        seconds = float(fmt.get("duration", 0))
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(seconds) or seconds <= 0:
        return 0
    try:
        return round(seconds * 1000)
    except OverflowError:
        return 0


async def _distinct_sampled_frames(path: Path, *, toolchain: MediaToolchain) -> int:
    stdout, _ = await _command(
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-protocol_whitelist",
        "file",
        "-f",
        "mov",
        "-enable_drefs",
        "0",
        "-use_absolute_path",
        "0",
        "-i",
        str(path),
        "-vf",
        "fps=1,scale=64:64",
        "-f",
        "framemd5",
        "-",
        _toolchain=toolchain,
    )
    hashes: set[str] = set()
    for line in stdout.decode("ascii", errors="strict").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = [part.strip() for part in line.split(",")]
        if len(fields) >= 6:
            hashes.add(fields[-1])
    return len(hashes)


async def inspect_imported_video(
    path: Path,
    *,
    expected_duration_ms: int,
    tolerance_ms: int = 120,
    toolchain: MediaToolchain | None = None,
) -> tuple[MediaFileEvidence, int]:
    data, _ = read_regular_media(path)
    active_toolchain = toolchain or resolve_media_toolchain()
    probe = await probe_media(path, input_format="mov", toolchain=active_toolchain)
    streams = _streams(probe)
    videos = [item for item in streams if item.get("codec_type") == "video"]
    if len(streams) != 1 or len(videos) != 1:
        raise CreativeMediaError("each imported shot must contain exactly one video stream")
    video = videos[0]
    width = video.get("width")
    height = video.get("height")
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width <= 0
        or height <= 0
        or width > 8192
        or height > 8192
        or width * height > 33_177_600
    ):
        raise CreativeMediaError("imported shot dimensions exceed the reviewed decode budget")
    format_value = probe.get("format")
    if not isinstance(format_value, dict) or "mp4" not in str(
        format_value.get("format_name", "")
    ).split(","):
        raise CreativeMediaError("each imported shot must use the reviewed MP4 container")
    actual_duration_ms = _duration_ms(probe)
    if abs(actual_duration_ms - expected_duration_ms) > tolerance_ms:
        raise CreativeMediaError("imported shot duration does not match the approved storyboard")
    distinct_frames = await _distinct_sampled_frames(path, toolchain=active_toolchain)
    if distinct_frames < 2:
        raise CreativeMediaError(
            "solid-color or static placeholder clips cannot be accepted as creative samples"
        )
    confirmed, _ = read_regular_media(path)
    if confirmed != data:
        raise CreativeMediaError("imported shot changed during media inspection")
    return (
        MediaFileEvidence(
            path=path.absolute(),
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            ffprobe=probe,
        ),
        distinct_frames,
    )


async def inspect_imported_audio(
    path: Path,
    *,
    toolchain: MediaToolchain | None = None,
) -> MediaFileEvidence:
    data, _ = read_regular_media(path)
    active_toolchain = toolchain or resolve_media_toolchain()
    probe = await probe_media(path, input_format="wav", toolchain=active_toolchain)
    streams = _streams(probe)
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    if len(streams) != 1 or len(audio) != 1:
        raise CreativeMediaError("an imported audio file must contain exactly one audio stream")
    sample_rate = audio[0].get("sample_rate")
    channels = audio[0].get("channels")
    try:
        sample_rate_value = int(str(sample_rate))
    except ValueError as exc:
        raise CreativeMediaError("imported audio sample rate is invalid") from exc
    if (
        sample_rate_value < 8_000
        or sample_rate_value > 192_000
        or not isinstance(channels, int)
        or isinstance(channels, bool)
        or channels <= 0
        or channels > 8
    ):
        raise CreativeMediaError("imported audio exceeds the reviewed decode budget")
    format_value = probe.get("format")
    if not isinstance(format_value, dict) or format_value.get("format_name") != "wav":
        raise CreativeMediaError("imported audio must use the reviewed WAV container")
    confirmed, _ = read_regular_media(path)
    if confirmed != data:
        raise CreativeMediaError("imported audio changed during media inspection")
    return MediaFileEvidence(
        path=path.absolute(),
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        ffprobe=probe,
    )


async def verify_assembled_sample(
    path: Path,
    *,
    expected_duration_ms: int,
    toolchain: MediaToolchain | None = None,
) -> CreativeTechnicalQC:
    data, _ = read_regular_media(path)
    active_toolchain = toolchain or resolve_media_toolchain()
    probe = await probe_media(path, input_format="mov", toolchain=active_toolchain)
    streams = _streams(probe)
    videos = [item for item in streams if item.get("codec_type") == "video"]
    audios = [item for item in streams if item.get("codec_type") == "audio"]
    subtitles = [item for item in streams if item.get("codec_type") == "subtitle"]
    video = videos[0] if len(videos) == 1 else {}
    audio = audios[0] if len(audios) == 1 else {}
    subtitle = subtitles[0] if len(subtitles) == 1 else {}
    actual_duration_ms = _duration_ms(probe)
    try:
        frame_rate = Fraction(str(video.get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        frame_rate = Fraction(0, 1)
    checks = (
        TechnicalCheck(
            "stream_closure",
            len(streams) == 3 and len(videos) == len(audios) == len(subtitles) == 1,
            {
                "total_streams": len(streams),
                "video_streams": len(videos),
                "audio_streams": len(audios),
                "subtitle_streams": len(subtitles),
            },
        ),
        TechnicalCheck(
            "dimensions",
            video.get("width") == SAMPLE_WIDTH and video.get("height") == SAMPLE_HEIGHT,
            {
                "width": int(str(video.get("width", 0))),
                "height": int(str(video.get("height", 0))),
            },
        ),
        TechnicalCheck(
            "video_profile",
            video.get("codec_name") == "h264"
            and video.get("pix_fmt") == "yuv420p"
            and frame_rate == SAMPLE_FPS,
            {
                "codec": str(video.get("codec_name", "")),
                "pixel_format": str(video.get("pix_fmt", "")),
                "frame_rate": str(video.get("avg_frame_rate", "")),
            },
        ),
        TechnicalCheck(
            "audio_profile",
            audio.get("codec_name") == "aac" and audio.get("sample_rate") == str(SAMPLE_AUDIO_RATE),
            {
                "codec": str(audio.get("codec_name", "")),
                "sample_rate": str(audio.get("sample_rate", "")),
            },
        ),
        TechnicalCheck(
            "subtitle_profile",
            subtitle.get("codec_name") in {"mov_text", "tx3g"},
            {"codec": str(subtitle.get("codec_name", ""))},
        ),
        TechnicalCheck(
            "duration",
            abs(actual_duration_ms - expected_duration_ms) <= 120,
            {
                "actual_ms": actual_duration_ms,
                "expected_ms": expected_duration_ms,
                "tolerance_ms": 120,
            },
        ),
    )
    confirmed, _ = read_regular_media(path)
    if confirmed != data:
        raise CreativeMediaError("assembled sample changed during technical verification")
    evidence = MediaFileEvidence(
        path=path.absolute(),
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        ffprobe=probe,
    )
    return CreativeTechnicalQC(
        passed=all(item.passed for item in checks),
        checks=checks,
        media=evidence,
    )


def _srt_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def render_srt(lines: Sequence[tuple[int, int, str]]) -> bytes:
    previous_end = 0
    rendered: list[str] = []
    for index, (start_ms, end_ms, text) in enumerate(lines, 1):
        if start_ms < previous_end or end_ms <= start_ms:
            raise CreativeMediaError(
                "subtitle timing must be ordered, non-overlapping, and non-empty"
            )
        clean = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        if not clean:
            raise CreativeMediaError("subtitle text must not be empty")
        rendered.extend(
            [
                str(index),
                f"{_srt_timestamp(start_ms)} --> {_srt_timestamp(end_ms)}",
                clean,
                "",
            ]
        )
        previous_end = end_ms
    return ("\n".join(rendered) + "\n").encode("utf-8")


async def render_audio_master(
    *,
    voices: Sequence[TimedVoiceTrack],
    bgm: Path | None,
    duration_ms: int,
    output: Path,
    toolchain: MediaToolchain | None = None,
) -> None:
    if not 60_000 <= duration_ms <= 90_000:
        raise CreativeMediaError("creative sample duration must be 60..90 seconds")
    if tuple(voice.line_id for voice in voices) != tuple(
        dict.fromkeys(voice.line_id for voice in voices)
    ):
        raise CreativeMediaError("voice tracks must have unique line identities")
    previous_end = 0
    for voice in voices:
        if voice.start_ms < previous_end:
            raise CreativeMediaError("voice tracks must use non-overlapping master-clock intervals")
        previous_end = voice.end_ms
    inputs = [voice.path for voice in voices]
    if bgm is not None:
        inputs.append(bgm)
    for path in inputs:
        validate_regular_media_path(path)
    output_absolute = validate_local_path(output, must_exist=False)
    if os.path.lexists(output_absolute):
        raise CreativeMediaError("audio master output must be a new file")
    active_toolchain = toolchain or resolve_media_toolchain()
    canonical_inputs: list[Path] = []
    input_digests: dict[Path, str] = {}
    for path in inputs:
        evidence = await inspect_imported_audio(path, toolchain=active_toolchain)
        canonical = validate_local_path(path, must_exist=True)
        canonical_inputs.append(canonical)
        input_digests[canonical] = evidence.sha256
    if len(canonical_inputs) != len(set(canonical_inputs)):
        raise CreativeMediaError("voice and BGM inputs must use distinct local files")
    output_absolute.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = ["ffmpeg", "-v", "error", "-nostdin", "-n"]
    for voice in voices:
        args.extend(["-protocol_whitelist", "file", "-f", "wav", "-i", str(voice.path)])
    if bgm is not None:
        args.extend(
            [
                "-protocol_whitelist",
                "file",
                "-f",
                "wav",
                "-stream_loop",
                "-1",
                "-i",
                str(bgm),
            ]
        )
    filters: list[str] = []
    labels: list[str] = []
    for index, voice in enumerate(voices):
        if voice.start_ms < 0 or voice.end_ms <= voice.start_ms or voice.end_ms > duration_ms:
            raise CreativeMediaError("voice timing must fit inside the sample master clock")
        duration = (voice.end_ms - voice.start_ms) / 1000
        label = f"voice{index}"
        filters.append(
            f"[{index}:a]aresample={SAMPLE_AUDIO_RATE},atrim=duration={duration:.3f},"
            f"asetpts=PTS-STARTPTS,adelay={voice.start_ms}:all=1,apad,"
            f"atrim=duration={duration_ms / 1000:.3f}[{label}]"
        )
        labels.append(f"[{label}]")
    if bgm is not None:
        bgm_index = len(voices)
        filters.append(
            f"[{bgm_index}:a]aresample={SAMPLE_AUDIO_RATE},volume=0.12,"
            f"atrim=duration={duration_ms / 1000:.3f},asetpts=PTS-STARTPTS[bgm]"
        )
        labels.append("[bgm]")
    if not labels:
        filters.append(
            f"anullsrc=r={SAMPLE_AUDIO_RATE}:cl=stereo,"
            f"atrim=duration={duration_ms / 1000:.3f}[audio_master]"
        )
    elif len(labels) == 1:
        filters.append(f"{labels[0]}anull[audio_master]")
    else:
        filters.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
            "alimiter=limit=0.95[audio_master]"
        )
    args.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[audio_master]",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-filter_complex_threads",
            "2",
            "-threads",
            "2",
            "-c:a",
            "pcm_s16le",
            "-ar",
            str(SAMPLE_AUDIO_RATE),
            "-ac",
            "2",
            "-t",
            f"{duration_ms / 1000:.3f}",
            "-f",
            "wav",
            "-fs",
            str(MAX_IMPORTED_MEDIA_BYTES),
            str(output_absolute),
        ]
    )
    await _command(*args, _toolchain=active_toolchain)
    output_data, _ = read_regular_media(output_absolute)
    if not output_data:
        raise CreativeMediaError("audio master output is empty")
    output_evidence = await inspect_imported_audio(
        output_absolute,
        toolchain=active_toolchain,
    )
    output_streams = _streams(output_evidence.ffprobe)
    output_audio = output_streams[0] if len(output_streams) == 1 else {}
    if (
        output_audio.get("sample_rate") != str(SAMPLE_AUDIO_RATE)
        or output_audio.get("channels") != 2
        or abs(_duration_ms(output_evidence.ffprobe) - duration_ms) > 120
    ):
        raise CreativeMediaError("audio master does not match the reviewed 48 kHz stereo profile")
    for path, digest in input_digests.items():
        confirmed, _ = read_regular_media(path)
        if hashlib.sha256(confirmed).hexdigest() != digest:
            raise CreativeMediaError("audio input changed during master rendering")


async def assemble_sample(
    *,
    videos: Sequence[tuple[Path, int]],
    voices: Sequence[TimedVoiceTrack],
    bgm: Path | None,
    subtitles: Path,
    duration_ms: int,
    output: Path,
    toolchain: MediaToolchain | None = None,
) -> None:
    if not 60_000 <= duration_ms <= 90_000:
        raise CreativeMediaError("creative sample duration must be 60..90 seconds")
    if not 8 <= len(videos) <= 12 or any(duration <= 0 for _, duration in videos):
        raise CreativeMediaError("creative sample assembly requires 8..12 non-empty shots")
    if sum(duration for _, duration in videos) != duration_ms:
        raise CreativeMediaError("creative sample shots must cover the exact master timeline")
    input_paths = [path for path, _ in videos]
    input_paths.extend(voice.path for voice in voices)
    if bgm is not None:
        input_paths.append(bgm)
    input_paths.append(subtitles)
    canonical_inputs: list[Path] = []
    input_digests: dict[Path, str] = {}
    for path in input_paths:
        data, _ = read_regular_media(path)
        canonical = validate_local_path(path, must_exist=True)
        canonical_inputs.append(canonical)
        input_digests[canonical] = hashlib.sha256(data).hexdigest()
    if len(set(canonical_inputs)) != len(canonical_inputs):
        raise CreativeMediaError("each creative sample input must be a distinct local file")
    output_absolute = validate_local_path(output, must_exist=False)
    if os.path.lexists(output_absolute):
        raise CreativeMediaError("creative sample output must be a new file")
    active_toolchain = toolchain or resolve_media_toolchain()
    output_absolute.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = ["ffmpeg", "-v", "error", "-nostdin", "-n"]
    for video, _ in videos:
        args.extend(
            [
                "-protocol_whitelist",
                "file",
                "-f",
                "mov",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-i",
                str(video),
            ]
        )
    for voice in voices:
        args.extend(["-protocol_whitelist", "file", "-f", "wav", "-i", str(voice.path)])
    if bgm is not None:
        args.extend(
            [
                "-protocol_whitelist",
                "file",
                "-f",
                "wav",
                "-stream_loop",
                "-1",
                "-i",
                str(bgm),
            ]
        )
    args.extend(["-protocol_whitelist", "file", "-f", "srt", "-i", str(subtitles)])

    filters: list[str] = []
    video_labels: list[str] = []
    for index, (_, shot_duration_ms) in enumerate(videos):
        label = f"v{index}"
        seconds = shot_duration_ms / 1000
        filters.append(
            f"[{index}:v]scale={SAMPLE_WIDTH}:{SAMPLE_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={SAMPLE_WIDTH}:{SAMPLE_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={SAMPLE_FPS},trim=duration={seconds:.3f},"
            f"setpts=PTS-STARTPTS[{label}]"
        )
        video_labels.append(f"[{label}]")
    filters.append(f"{''.join(video_labels)}concat=n={len(video_labels)}:v=1:a=0[video_master]")

    audio_labels: list[str] = []
    first_audio_index = len(videos)
    for offset, voice in enumerate(voices):
        label = f"voice{offset}"
        delay = voice.start_ms
        voice_duration = (voice.end_ms - voice.start_ms) / 1000
        if voice.start_ms < 0 or voice.end_ms <= voice.start_ms or voice.end_ms > duration_ms:
            raise CreativeMediaError("voice timing must fit inside the sample master clock")
        filters.append(
            f"[{first_audio_index + offset}:a]aresample={SAMPLE_AUDIO_RATE},"
            f"atrim=duration={voice_duration:.3f},asetpts=PTS-STARTPTS,"
            f"adelay={delay}:all=1,"
            f"apad,atrim=duration={duration_ms / 1000:.3f}[{label}]"
        )
        audio_labels.append(f"[{label}]")
    next_index = first_audio_index + len(voices)
    if bgm is not None:
        filters.append(
            f"[{next_index}:a]aresample={SAMPLE_AUDIO_RATE},volume=0.12,"
            f"atrim=duration={duration_ms / 1000:.3f},asetpts=PTS-STARTPTS[bgm]"
        )
        audio_labels.append("[bgm]")
        next_index += 1
    if not audio_labels:
        filters.append(
            f"anullsrc=r={SAMPLE_AUDIO_RATE}:cl=stereo,"
            f"atrim=duration={duration_ms / 1000:.3f}[audio_master]"
        )
    elif len(audio_labels) == 1:
        filters.append(f"{audio_labels[0]}anull[audio_master]")
    else:
        filters.append(
            f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:"
            "duration=longest:normalize=0,alimiter=limit=0.95[audio_master]"
        )

    args.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[video_master]",
            "-map",
            "[audio_master]",
            "-map",
            f"{next_index}:s:0",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-filter_complex_threads",
            "2",
            "-threads",
            "2",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(SAMPLE_FPS),
            "-c:a",
            "aac",
            "-ar",
            str(SAMPLE_AUDIO_RATE),
            "-c:s",
            "mov_text",
            "-t",
            f"{duration_ms / 1000:.3f}",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            "-fs",
            str(MAX_IMPORTED_MEDIA_BYTES),
            str(output_absolute),
        ]
    )
    await _command(*args, _toolchain=active_toolchain)
    for path, digest in input_digests.items():
        confirmed, _ = read_regular_media(path)
        if hashlib.sha256(confirmed).hexdigest() != digest:
            raise CreativeMediaError("creative sample input changed during assembly")


__all__ = [
    "CreativeMediaError",
    "CreativeTechnicalQC",
    "MEDIA_COMMAND_TIMEOUT_SECONDS",
    "MAX_IMPORTED_MEDIA_BYTES",
    "MAX_MEDIA_STDERR_BYTES",
    "MAX_MEDIA_STDOUT_BYTES",
    "MediaFileEvidence",
    "MediaToolchain",
    "SAMPLE_AUDIO_RATE",
    "SAMPLE_FPS",
    "SAMPLE_HEIGHT",
    "SAMPLE_WIDTH",
    "TimedVoiceTrack",
    "TechnicalCheck",
    "assemble_sample",
    "inspect_imported_audio",
    "inspect_imported_video",
    "probe_media",
    "read_regular_media",
    "render_audio_master",
    "render_srt",
    "resolve_media_toolchain",
    "validate_local_path",
    "validate_regular_media_path",
    "verify_media_toolchain",
    "verify_assembled_sample",
]
