"""Evidence-first automatic media quality control."""

import asyncio
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from sdc.compiler import stable_id
from sdc.contracts import AudioMasterClock, QCEvidence, QCReport, ReleaseManifest


async def inspect(media: Path) -> dict[str, object]:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(media),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode:
        return {"streams": [], "format": {}}
    data: dict[str, object] = json.loads(stdout)
    return data


async def verify(
    media: Path,
    clock: AudioMasterClock,
    release: ReleaseManifest,
    segment_count: int,
    expected_segments: int,
    expected_job_ids: list[str],
    current_candidates: dict[str, list[str]],
    max_attempt: int,
) -> QCReport:
    probe = await inspect(media)
    streams = probe.get("streams", [])
    assert isinstance(streams, list)
    video: dict[str, object] = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio: dict[str, object] = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fmt = probe.get("format", {})
    assert isinstance(fmt, dict)
    duration_ms = round(float(fmt.get("duration", 0)) * 1000)
    actual_hash = hashlib.sha256(media.read_bytes()).hexdigest() if media.exists() else ""
    facts: list[tuple[str, bool, dict[str, str | int | bool]]] = [
        ("decodable", bool(video), {"path": str(media)}),
        (
            "dimensions",
            video.get("width") == 1080 and video.get("height") == 1920,
            {"width": int(str(video.get("width", 0))), "height": int(str(video.get("height", 0)))},
        ),
        (
            "frame_rate",
            Fraction(str(video.get("avg_frame_rate", "0/1"))) == 25,
            {"avg_frame_rate": str(video.get("avg_frame_rate", ""))},
        ),
        (
            "codecs",
            video.get("codec_name") == "h264" and audio.get("codec_name") == "aac",
            {"video": str(video.get("codec_name", "")), "audio": str(audio.get("codec_name", ""))},
        ),
        (
            "sample_rate",
            audio.get("sample_rate") == "48000",
            {"sample_rate": str(audio.get("sample_rate", ""))},
        ),
        (
            "segment_coverage",
            segment_count == expected_segments,
            {"actual": segment_count, "expected": expected_segments},
        ),
        (
            "duration",
            abs(duration_ms - clock.duration_ms) <= 40,
            {"actual_ms": duration_ms, "expected_ms": clock.duration_ms, "tolerance_ms": 40},
        ),
        (
            "manifest_checksum",
            actual_hash == release.sha256,
            {"actual": actual_hash, "expected": release.sha256},
        ),
        *current_candidate_facts(expected_job_ids, current_candidates),
        ("no_third_attempt", max_attempt <= 2, {"max_attempt": max_attempt}),
    ]
    evidence = tuple(QCEvidence(check=n, passed=p, details=d) for n, p, d in facts)
    return QCReport(
        id=stable_id("qc", [release.id, [(e.check, e.passed) for e in evidence]]),
        passed=all(e.passed for e in evidence),
        evidence=evidence,
        ffprobe=probe,
    )


def current_candidate_facts(
    expected_job_ids: list[str], current_candidates: dict[str, list[str]]
) -> list[tuple[str, bool, dict[str, str | int | bool]]]:
    """Prove that every and only expected job has exactly one current candidate."""
    expected = set(expected_job_ids)
    actual = set(current_candidates)
    facts: list[tuple[str, bool, dict[str, str | int | bool]]] = [
        (
            "current_candidate_job_set",
            actual == expected,
            {
                "expected_jobs": len(expected),
                "actual_jobs": len(actual),
                "missing_jobs": ",".join(sorted(expected - actual)),
                "unexpected_jobs": ",".join(sorted(actual - expected)),
            },
        )
    ]
    for job_id in sorted(expected):
        candidates = current_candidates.get(job_id, [])
        facts.append(
            (
                f"one_current_candidate:{job_id}",
                len(candidates) == 1,
                {"job_id": job_id, "current_count": len(candidates)},
            )
        )
    return facts
