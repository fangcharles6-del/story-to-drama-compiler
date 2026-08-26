"""FFmpeg media assembly and manifest creation."""

import asyncio
import hashlib
from collections.abc import Sequence
from pathlib import Path

from sdc.compiler import stable_id
from sdc.contracts import AudioMasterClock, ReleaseManifest


async def _run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(*args)
    if await proc.wait() != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}")


def _ffconcat_quote(path: Path) -> str:
    """Quote one resolved path for FFmpeg's concat-demuxer text format."""

    if not isinstance(path, Path):
        raise TypeError("FFmpeg concat entries must be Path objects")
    value = path.resolve().as_posix()
    if not value or any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError("FFmpeg concat paths must not contain control characters")
    return "'" + value.replace("'", "'\\''") + "'"


def _ffconcat_document(segments: Sequence[Path]) -> str:
    """Build a deterministic UTF-8/LF concat manifest with safely quoted paths."""

    if not segments:
        raise ValueError("at least one segment is required")
    return "ffconcat version 1.0\n" + "".join(
        f"file {_ffconcat_quote(segment)}\n" for segment in segments
    )


async def assemble(segments: list[Path], clock: AudioMasterClock, output: Path) -> None:
    concat = output.with_name(f".{output.name}.segments.ffconcat")
    concat.write_text(_ffconcat_document(segments), encoding="utf-8", newline="\n")
    duration = f"{clock.duration_ms / 1000:.3f}"
    await _run(
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=48000:cl=stereo",
        "-t",
        duration,
        "-vf",
        "scale=1080:1920:flags=neighbor,fps=25",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output),
    )


def manifest(output: Path, duration_ms: int) -> ReleaseManifest:
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return ReleaseManifest(
        id=stable_id("release", digest),
        media_path=output.name,
        sha256=digest,
        size_bytes=output.stat().st_size,
        duration_ms=duration_ms,
    )
