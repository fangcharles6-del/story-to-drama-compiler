"""FFmpeg media assembly and manifest creation."""

import asyncio
import hashlib
from pathlib import Path

from sdc.compiler import stable_id
from sdc.contracts import AudioMasterClock, ReleaseManifest


async def _run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(*args)
    if await proc.wait() != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}")


async def assemble(segments: list[Path], clock: AudioMasterClock, output: Path) -> None:
    concat = output.parent / "segments.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in segments))
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
