"""Content-addressed local asset packs for the offline creative sample loop."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sdc.contracts import (
    CharacterAssetVersion,
    CreativeSampleSpec,
    SceneAssetVersion,
)
from sdc.creative_media import (
    CreativeMediaError,
    read_regular_media,
    validate_local_path,
)

ASSET_PACK_MANIFEST: Final = "asset-pack.json"
_PACK_DOMAIN = b"sdc:creative-asset-pack:1.0.0\0"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_PNG_DIMENSION = 4096
_MAX_PNG_PIXELS = 16_000_000
_MAX_ASSET_MANIFEST_BYTES = 1024 * 1024


class AssetPackError(CreativeMediaError):
    pass


@dataclass(frozen=True, slots=True)
class LocalAssetSource:
    asset_version_id: str
    path: Path


@dataclass(frozen=True, slots=True)
class FrozenAssetPack:
    pack_id: str
    root: Path
    manifest_path: Path
    object_count: int
    created: bool


def _reject_json_constant(value: str) -> None:
    raise AssetPackError(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AssetPackError(f"duplicate asset-pack JSON key is forbidden: {key}")
        result[key] = value
    return result


def _validate_sanitized_png(data: bytes) -> None:
    """Accept a small, self-contained 8-bit RGB/RGBA PNG without metadata."""
    if not data.startswith(_PNG_SIGNATURE):
        raise AssetPackError("creative assets declared as image/png must be PNG bytes")
    offset = len(_PNG_SIGNATURE)
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        if len(chunks) >= 64 or offset + 12 > len(data):
            raise AssetPackError("creative PNG has an invalid or excessive chunk layout")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if length > 32 * 1024 * 1024 or end > len(data):
            raise AssetPackError("creative PNG chunk exceeds its bounded file")
        payload = data[offset + 8 : offset + 8 + length]
        observed_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        expected_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if observed_crc != expected_crc:
            raise AssetPackError("creative PNG chunk CRC is invalid")
        chunks.append((chunk_type, payload))
        offset = end
        if chunk_type == b"IEND":
            break
    if offset != len(data):
        raise AssetPackError("creative PNG contains trailing or polyglot bytes")
    if not chunks or chunks[0][0] != b"IHDR" or chunks[-1] != (b"IEND", b""):
        raise AssetPackError("creative PNG must have exact IHDR and IEND boundaries")
    if any(chunk_type not in {b"IHDR", b"IDAT", b"IEND"} for chunk_type, _ in chunks):
        raise AssetPackError("creative PNG must not contain metadata or external content")
    if sum(chunk_type == b"IHDR" for chunk_type, _ in chunks) != 1:
        raise AssetPackError("creative PNG must contain one IHDR chunk")
    idat_indexes = [index for index, (kind, _) in enumerate(chunks) if kind == b"IDAT"]
    if not idat_indexes or idat_indexes != list(range(idat_indexes[0], idat_indexes[-1] + 1)):
        raise AssetPackError("creative PNG IDAT chunks must form one contiguous sequence")
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        raise AssetPackError("creative PNG IHDR is invalid")
    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if (
        width <= 0
        or height <= 0
        or width > _MAX_PNG_DIMENSION
        or height > _MAX_PNG_DIMENSION
        or width * height > _MAX_PNG_PIXELS
        or bit_depth != 8
        or color_type not in {2, 6}
        or compression != 0
        or filter_method != 0
        or interlace != 0
    ):
        raise AssetPackError("creative PNG must use the reviewed bounded RGB/RGBA profile")
    bytes_per_pixel = 3 if color_type == 2 else 4
    expected_size = (1 + width * bytes_per_pixel) * height
    compressed = b"".join(payload for kind, payload in chunks if kind == b"IDAT")
    inflater = zlib.decompressobj()
    try:
        pixels = inflater.decompress(compressed, expected_size + 1)
    except zlib.error as exc:
        raise AssetPackError("creative PNG pixel data is not decodable") from exc
    if (
        len(pixels) != expected_size
        or inflater.unused_data
        or inflater.unconsumed_tail
        or not inflater.eof
    ):
        raise AssetPackError("creative PNG pixel closure is invalid")
    row_size = 1 + width * bytes_per_pixel
    if any(pixels[offset] > 4 for offset in range(0, len(pixels), row_size)):
        raise AssetPackError("creative PNG uses an invalid scanline filter")


def _active_versions(
    spec: CreativeSampleSpec,
) -> tuple[CharacterAssetVersion | SceneAssetVersion, ...]:
    selected: list[CharacterAssetVersion | SceneAssetVersion] = []
    for character_bible in spec.character_bibles:
        selected.append(
            next(
                item
                for item in character_bible.asset_versions
                if item.id == character_bible.active_asset_version_id
            )
        )
    for scene_bible in spec.scene_bibles:
        selected.append(
            next(
                item
                for item in scene_bible.asset_versions
                if item.id == scene_bible.active_asset_version_id
            )
        )
    return tuple(sorted(selected, key=lambda item: item.id))


def _manifest_descriptor(
    spec: CreativeSampleSpec,
    versions: tuple[CharacterAssetVersion | SceneAssetVersion, ...],
    sizes: dict[str, int],
) -> dict[str, object]:
    objects = sorted(
        {
            (
                item.content_sha256,
                sizes[item.id],
                item.media_type,
            )
            for item in versions
        }
    )
    return {
        "document_type": "sdc.creative-asset-pack",
        "schema_version": "1.0.0",
        "sample_spec_sha256": hashlib.sha256(
            json.dumps(
                spec.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "character_versions": [
            item.model_dump(mode="json")
            for item in versions
            if isinstance(item, CharacterAssetVersion)
        ],
        "scene_versions": [
            item.model_dump(mode="json") for item in versions if isinstance(item, SceneAssetVersion)
        ],
        "bindings": [
            {
                "asset_version_id": item.id,
                "object_sha256": item.content_sha256,
                "logical_path": f"objects/{item.content_sha256[:2]}/{item.content_sha256}",
            }
            for item in versions
        ],
        "objects": [
            {
                "sha256": digest,
                "size_bytes": size,
                "media_type": media_type,
            }
            for digest, size, media_type in objects
        ],
    }


def _canonical_manifest(descriptor: dict[str, object]) -> tuple[str, bytes]:
    content = json.dumps(
        descriptor,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    pack_id = hashlib.sha256(_PACK_DOMAIN + content).hexdigest()
    envelope = {
        "pack_id": pack_id,
        **descriptor,
    }
    encoded = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return pack_id, encoded


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise AssetPackError(f"asset pack path already exists: {path}") from exc


def _verify_existing(
    root: Path,
    *,
    expected_manifest: bytes,
    object_bytes: dict[str, bytes],
) -> None:
    validate_local_path(root, must_exist=True)
    manifest_path = root / ASSET_PACK_MANIFEST
    actual_manifest, _ = read_regular_media(manifest_path)
    if actual_manifest != expected_manifest:
        raise AssetPackError("existing asset pack manifest conflicts with the requested pack")
    expected_paths = {ASSET_PACK_MANIFEST}
    for digest, expected in object_bytes.items():
        relative = f"objects/{digest[:2]}/{digest}"
        expected_paths.add(relative)
        actual, _ = read_regular_media(root / relative)
        if actual != expected or hashlib.sha256(actual).hexdigest() != digest:
            raise AssetPackError("existing asset pack object conflicts with its digest")
    actual_paths: set[str] = set()
    actual_directories: set[str] = set()
    entries = 0
    for item in root.rglob("*"):
        entries += 1
        if entries > 32:
            raise AssetPackError("existing asset pack exceeds its bounded layout")
        info = item.lstat()
        attributes = int(getattr(info, "st_file_attributes", 0))
        if stat.S_ISLNK(info.st_mode) or attributes & 0x400:
            raise AssetPackError("existing asset pack contains a link or reparse point")
        relative = item.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):
            actual_directories.add(relative)
        elif stat.S_ISREG(info.st_mode):
            actual_paths.add(relative)
        else:
            raise AssetPackError("existing asset pack contains a non-regular entry")
    if actual_paths != expected_paths:
        raise AssetPackError("existing asset pack does not have the exact expected closure")
    expected_directories = {"objects"} | {f"objects/{digest[:2]}" for digest in object_bytes}
    if actual_directories != expected_directories:
        raise AssetPackError("existing asset pack contains unexpected directories")


def verify_asset_pack(
    spec: CreativeSampleSpec,
    root: Path,
    *,
    expected_pack_id: str | None = None,
) -> FrozenAssetPack:
    """Verify one complete pack against the exact sample specification."""
    absolute = validate_local_path(root, must_exist=True)
    manifest_path = absolute / ASSET_PACK_MANIFEST
    manifest, _ = read_regular_media(manifest_path)
    if len(manifest) > _MAX_ASSET_MANIFEST_BYTES:
        raise AssetPackError("asset pack manifest exceeds its byte limit")
    try:
        value = json.loads(
            manifest.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetPackError("asset pack manifest must be strict JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("pack_id"), str):
        raise AssetPackError("asset pack manifest envelope is invalid")
    declared_pack_id = value["pack_id"]
    descriptor = {key: item for key, item in value.items() if key != "pack_id"}
    computed_pack_id, canonical_manifest = _canonical_manifest(descriptor)
    if (
        declared_pack_id != computed_pack_id
        or manifest != canonical_manifest
        or (expected_pack_id is not None and declared_pack_id != expected_pack_id)
        or absolute.name != declared_pack_id
    ):
        raise AssetPackError("asset pack manifest identity is invalid")

    versions = _active_versions(spec)
    expected_digests = {item.content_sha256 for item in versions}
    raw_objects = descriptor.get("objects")
    if not isinstance(raw_objects, list):
        raise AssetPackError("asset pack object catalog is invalid")
    object_sizes: dict[str, int] = {}
    object_bytes: dict[str, bytes] = {}
    for item in raw_objects:
        if not isinstance(item, dict) or set(item) != {"sha256", "size_bytes", "media_type"}:
            raise AssetPackError("asset pack object descriptor is invalid")
        digest = item["sha256"]
        size = item["size_bytes"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size <= 0
            or item["media_type"] != "image/png"
            or digest in object_sizes
        ):
            raise AssetPackError("asset pack object identity is invalid")
        data, _ = read_regular_media(absolute / "objects" / digest[:2] / digest)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise AssetPackError("asset pack object bytes do not match their descriptor")
        _validate_sanitized_png(data)
        object_sizes[digest] = size
        object_bytes[digest] = data
    if set(object_sizes) != expected_digests:
        raise AssetPackError("asset pack objects do not close over the active asset versions")
    sizes = {item.id: object_sizes[item.content_sha256] for item in versions}
    expected_descriptor = _manifest_descriptor(spec, versions, sizes)
    if descriptor != expected_descriptor:
        raise AssetPackError("asset pack descriptor does not bind the exact sample specification")
    _verify_existing(
        absolute,
        expected_manifest=canonical_manifest,
        object_bytes=object_bytes,
    )
    return FrozenAssetPack(
        pack_id=declared_pack_id,
        root=absolute,
        manifest_path=manifest_path,
        object_count=len(object_bytes),
        created=False,
    )


def freeze_asset_pack(
    spec: CreativeSampleSpec,
    sources: tuple[LocalAssetSource, ...],
    output_parent: Path,
) -> FrozenAssetPack:
    """Freeze only the exact active character and scene versions required by ``spec``."""
    versions = _active_versions(spec)
    required_ids = tuple(item.id for item in versions)
    source_ids = tuple(item.asset_version_id for item in sources)
    if source_ids != tuple(sorted(set(source_ids))) or set(source_ids) != set(required_ids):
        raise AssetPackError("asset sources must be a sorted exact closure of active versions")
    source_by_id = {item.asset_version_id: item for item in sources}
    object_bytes: dict[str, bytes] = {}
    sizes: dict[str, int] = {}
    for version in versions:
        data, _ = read_regular_media(source_by_id[version.id].path)
        digest = hashlib.sha256(data).hexdigest()
        if digest != version.content_sha256:
            raise AssetPackError(f"asset digest mismatch for version {version.id}")
        _validate_sanitized_png(data)
        previous = object_bytes.setdefault(digest, data)
        if previous != data:
            raise AssetPackError("asset digest collision detected")
        sizes[version.id] = len(data)

    descriptor = _manifest_descriptor(spec, versions, sizes)
    pack_id, manifest = _canonical_manifest(descriptor)
    parent_absolute = output_parent.absolute()
    parent = validate_local_path(
        output_parent,
        must_exist=os.path.lexists(parent_absolute),
    )
    if os.path.lexists(parent) and not parent.is_dir():
        raise AssetPackError("asset pack output parent must be a directory")
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / pack_id
    manifest_path = root / ASSET_PACK_MANIFEST
    if os.path.lexists(root):
        _verify_existing(root, expected_manifest=manifest, object_bytes=object_bytes)
        return FrozenAssetPack(pack_id, root, manifest_path, len(object_bytes), False)

    try:
        root.mkdir()
    except FileExistsError as exc:
        raise AssetPackError("asset pack target appeared during publication") from exc
    try:
        for digest, data in sorted(object_bytes.items()):
            target = root / "objects" / digest[:2] / digest
            _write_new(target, data)
            confirmed, _ = read_regular_media(target)
            if confirmed != data:
                raise AssetPackError("published asset object failed verification")
        _write_new(manifest_path, manifest)
        _verify_existing(root, expected_manifest=manifest, object_bytes=object_bytes)
    except Exception as exc:
        raise AssetPackError(
            f"asset pack publication is incomplete; preserve for human review: {root}"
        ) from exc
    return FrozenAssetPack(pack_id, root, manifest_path, len(object_bytes), True)


__all__ = [
    "ASSET_PACK_MANIFEST",
    "AssetPackError",
    "FrozenAssetPack",
    "LocalAssetSource",
    "freeze_asset_pack",
    "verify_asset_pack",
]
