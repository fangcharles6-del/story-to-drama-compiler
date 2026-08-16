"""Replaceable creative-provider boundaries for the offline sample loop.

This module intentionally contains protocols only.  Networked implementations and
credentials require a later, separately approved delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sdc.contracts import (
    CharacterAssetVersion,
    DialogueLine,
    SceneAssetVersion,
    StoryboardShotV2,
)


@dataclass(frozen=True, slots=True)
class LocalCreativeArtifact:
    """Credential-free artifact returned by a creative-provider implementation."""

    artifact_id: str
    path: Path
    sha256: str
    size_bytes: int
    media_type: str


class VoiceProvider(Protocol):
    async def synthesize(
        self,
        line: DialogueLine,
        *,
        destination: Path,
    ) -> LocalCreativeArtifact: ...


class ImageProvider(Protocol):
    async def render_character_reference(
        self,
        asset: CharacterAssetVersion,
        *,
        destination: Path,
    ) -> LocalCreativeArtifact: ...

    async def render_scene_reference(
        self,
        asset: SceneAssetVersion,
        *,
        destination: Path,
    ) -> LocalCreativeArtifact: ...


class AvatarProvider(Protocol):
    async def render_dialogue_shot(
        self,
        shot: StoryboardShotV2,
        *,
        voice: LocalCreativeArtifact,
        references: tuple[LocalCreativeArtifact, ...],
        destination: Path,
    ) -> LocalCreativeArtifact: ...


__all__ = [
    "AvatarProvider",
    "ImageProvider",
    "LocalCreativeArtifact",
    "VoiceProvider",
]
