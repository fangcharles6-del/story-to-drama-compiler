"""Fail-closed speech-synthesis adapter boundary for the 48 kHz master clock."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


class SpeechSynthesisUnavailable(RuntimeError):
    """No approved speech adapter is configured for this request."""


@dataclass(frozen=True, slots=True)
class SpeechSynthesisRequest:
    line_id: str
    text: str
    voice_id: str
    language: str
    target_duration_ms: int | None = None
    sample_rate_hz: int = 48000
    output_format: str = "wav"

    def __post_init__(self) -> None:
        if not _PORTABLE_ID.fullmatch(self.line_id):
            raise ValueError("line_id must be a portable identifier")
        if (
            type(self.text) is not str
            or not self.text.strip()
            or len(self.text) > 10000
            or "\x00" in self.text
        ):
            raise ValueError("text must be non-empty bounded text")
        if (
            type(self.voice_id) is not str
            or not self.voice_id
            or self.voice_id != self.voice_id.strip()
            or len(self.voice_id) > 256
            or any(ord(character) < 32 or ord(character) == 127 for character in self.voice_id)
        ):
            raise ValueError("voice_id must be canonical printable text")
        if type(self.language) is not str or not _LANGUAGE.fullmatch(self.language):
            raise ValueError("language must be a canonical BCP-47-like tag")
        if self.target_duration_ms is not None and (
            type(self.target_duration_ms) is not int or self.target_duration_ms <= 0
        ):
            raise ValueError("target_duration_ms must be an exact positive integer")
        if self.sample_rate_hz != 48000:
            raise ValueError("speech synthesis is pinned to the 48 kHz master clock")
        if self.output_format != "wav":
            raise ValueError("speech synthesis output is pinned to WAV")


@dataclass(frozen=True, slots=True)
class SpeechSynthesisArtifact:
    line_id: str
    path: Path
    sha256: str
    size_bytes: int
    duration_ms: int
    sample_rate_hz: int = 48000

    def __post_init__(self) -> None:
        if not _PORTABLE_ID.fullmatch(self.line_id):
            raise ValueError("line_id must be a portable identifier")
        if not isinstance(self.path, Path):
            raise TypeError("path must be a Path")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must be lowercase SHA-256")
        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("size_bytes must be an exact positive integer")
        if type(self.duration_ms) is not int or self.duration_ms <= 0:
            raise ValueError("duration_ms must be an exact positive integer")
        if self.sample_rate_hz != 48000:
            raise ValueError("speech artifacts must use the 48 kHz master clock")


class SpeechProvider(Protocol):
    async def synthesize(
        self,
        *,
        request: SpeechSynthesisRequest,
        destination: Path,
    ) -> SpeechSynthesisArtifact: ...


class UnavailableSpeechProvider:
    """Safe default that fails before reading credentials or touching the destination."""

    async def synthesize(
        self,
        *,
        request: SpeechSynthesisRequest,
        destination: Path,
    ) -> SpeechSynthesisArtifact:
        del request, destination
        raise SpeechSynthesisUnavailable("no approved speech provider is configured")


__all__ = [
    "SpeechProvider",
    "SpeechSynthesisArtifact",
    "SpeechSynthesisRequest",
    "SpeechSynthesisUnavailable",
    "UnavailableSpeechProvider",
]
