"""Pure allowlist-based provenance records for imported or downloaded media.

This module rejects recognizable local paths, download URLs, credential shapes,
query parameters, and raw mapping payloads. Future adapters must still map only
semantically public values because opaque identifiers cannot reveal their meaning.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_MAPPING_DELIMITERS = 32
_URI_LIKE = re.compile(
    r"(?:\b[A-Za-z][A-Za-z0-9+.-]*://|(?<![\w.])www\."
    r"|(?<![\w.+-])file:(?://|[A-Za-z]:[\\/]|[\\/])"
    r"|(?<![\w.+-])data:[^,\s]{0,128},"
    r"|(?<![\w.+-])javascript:\s*\S+"
    r"|(?<![\w.+-])mailto:[^@\s]+@[^\s]+"
    r"|(?<![\w.+-])(?:s3|gs):/{0,2}[^/\s]+/\S+)",
    re.IGNORECASE,
)
_EMAIL_LIKE = re.compile(r"(?<![\w@])[^@\s<>]+@[^@\s<>.]+(?:\.[^@\s<>.]+)*(?![\w@])")
_SCHEMELESS_URL = re.compile(
    r"(?<![\w.-])(?:(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}"
    r"|(?:\d{1,3}\.){3}\d{1,3})(?:/|\?)[^\s<>]*",
    re.IGNORECASE,
)
_EXPLICIT_LOCAL_PATH = re.compile(
    r"(?:^(?:[A-Za-z]:[\\/]|\\\\|/|(?:\.{1,2}|~(?:[A-Za-z0-9._-]+)?)[\\/])"
    r"|[\s<({\['\"=;](?:[A-Za-z]:[\\/]|\\\\[^\\\s]+[\\/]"
    r"|/(?:home|users|tmp|var|private|etc|opt|mnt|srv|root|usr)(?:/[^/\s]+)+"
    r"|(?:\.{1,2}|~(?:[A-Za-z0-9._-]+)?)[\\/])"
    r"|\b(?:local[\s_-]*(?:file|path)|working[\s_-]*(?:dir|directory)"
    r"|output[\s_-]*(?:dir|path)|input[\s_-]*(?:dir|path))"
    r"(?:\s*[:=]\s*|\s+)"
    r"(?:[A-Za-z]:[\\/]|\\\\|/|(?:\.{1,2}|~(?:[A-Za-z0-9._-]+)?)[\\/])"
    r"|\b(?:workspace|path|directory|dir|file)\s*[:=]\s*"
    r"(?:[A-Za-z]:[\\/]|\\\\|/|(?:\.{1,2}|~(?:[A-Za-z0-9._-]+)?)[\\/]))",
    re.IGNORECASE,
)
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"\b(?:api[\s._-]*key|access[\s._-]*token|refresh[\s._-]*token"
    r"|client[\s._-]*secret|secret[\s._-]*access[\s._-]*key"
    r"|x-amz-(?:signature|credential|security-token))"
    r"\s*[:=]\s*\S+"
    r"|\b(?:credential|password|secret|signature|sig|token)\s*=\s*\S+"
    r"|\b(?:authorization|proxy-authorization)\s*:?\s+(?:bearer|basic)\s+\S+"
    r"|\b(?:[A-Z][A-Z0-9]*_)*(?:API_KEY|ACCESS_TOKEN|REFRESH_TOKEN"
    r"|CLIENT_SECRET|SECRET_ACCESS_KEY)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_HIGH_CONFIDENCE_CREDENTIAL = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}"
    r"|sk-(?:proj-)?[A-Za-z0-9_-]{20,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|AIza[A-Za-z0-9_-]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{16,}"
    r")(?![A-Za-z0-9_-])"
)
_QUERY_STRING = re.compile(
    r"\?[A-Za-z0-9._~-]+=[^&#\s]*"
    r"|(?:^|[\s<({\['\"])(?:[^=&?#\s]+=[^&#\s]*&)"
    r"+[^=&?#\s]+=[^&#\s]*(?=$|\s)"
)
_PATH_USERINFO = re.compile(r"/[^/\s:@]+:[^/\s@]+@")
_COMPACT_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])"
)


def _contains_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _optional_text(value: object, *, max_length: int) -> str | None:
    if type(value) is not str:
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_length or _contains_control(cleaned):
        return None
    return cleaned


def _fully_unquote(value: str) -> str:
    decoded = value
    for _ in range(len(value) + 1):
        candidate = unquote(decoded)
        if candidate == decoded:
            return decoded
        decoded = candidate
    return decoded


def _looks_like_structured_private_data(value: str) -> bool:
    """Reject high-confidence structures, not opaque values that resemble public IDs."""

    candidate = _fully_unquote(value)
    if any(
        pattern.search(candidate)
        for pattern in (
            _URI_LIKE,
            _EMAIL_LIKE,
            _SCHEMELESS_URL,
            _EXPLICIT_LOCAL_PATH,
            _CREDENTIAL_ASSIGNMENT,
            _HIGH_CONFIDENCE_CREDENTIAL,
            _QUERY_STRING,
            _COMPACT_TOKEN,
        )
    ):
        return True
    return _contains_mapping_literal(candidate)


def _is_mapping_literal(value: str) -> bool:
    for decoder in (json.loads, ast.literal_eval):
        try:
            decoded = decoder(value)
        except (SyntaxError, TypeError, ValueError):
            continue
        if isinstance(decoded, dict):
            return True
    return False


def _balanced_braced_value(value: str, start: int) -> str | None:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(value)):
        character = value[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    return None


def _contains_mapping_literal(value: str) -> bool:
    starts = tuple(index for index, character in enumerate(value) if character == "{")
    if len(starts) > _MAX_MAPPING_DELIMITERS or value.count("}") > _MAX_MAPPING_DELIMITERS:
        return True
    for start in starts:
        candidate = _balanced_braced_value(value, start)
        if candidate is not None and _is_mapping_literal(candidate):
            return True
    return False


def _optional_public_text(value: object, *, max_length: int) -> str | None:
    candidate = _optional_text(value, max_length=max_length)
    if candidate is None or _looks_like_structured_private_data(candidate):
        return None
    return candidate


def _optional_identifier(value: object, *, max_length: int = 128) -> str | None:
    if type(value) is bool:
        return None
    if type(value) is int:
        value = str(value)
    candidate = _optional_text(value, max_length=max_length)
    if (
        candidate is None
        or _PUBLIC_IDENTIFIER.fullmatch(candidate) is None
        or _HIGH_CONFIDENCE_CREDENTIAL.fullmatch(candidate) is not None
        or _COMPACT_TOKEN.fullmatch(candidate) is not None
    ):
        return None
    return candidate


def sanitize_public_source_url(value: object) -> str | None:
    """Return an HTTP(S) page URL with userinfo, query, and fragment removed."""

    candidate = _optional_text(value, max_length=2048)
    if candidate is None:
        return None
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if parsed.hostname is None or parsed.username is not None or parsed.password is not None:
        return None
    if _contains_control(parsed.path):
        return None
    decoded_path = _fully_unquote(parsed.path)
    if _contains_control(decoded_path):
        return None
    if any(
        pattern.search(decoded_path)
        for pattern in (
            _CREDENTIAL_ASSIGNMENT,
            _HIGH_CONFIDENCE_CREDENTIAL,
            _QUERY_STRING,
            _PATH_USERINFO,
        )
    ):
        return None

    hostname = parsed.hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path, "", ""))


def _portable_basename(local_path: str | Path) -> str:
    if not isinstance(local_path, (str, Path)):
        raise TypeError("local_path must be a string or Path")
    text = str(local_path)
    if not text or _contains_control(text):
        raise ValueError("local_path must be non-empty and contain no control characters")
    uri_match = _URI_LIKE.match(text)
    if uri_match is not None and uri_match.group(0).lower() != "www.":
        raise ValueError("local_path must be a local filesystem path")
    name = text.replace("\\", "/").rsplit("/", 1)[-1]
    if (
        name in {"", ".", ".."}
        or name != name.strip()
        or name.endswith((".", " "))
        or len(name.encode("utf-8")) > 255
        or "/" in name
        or "\\" in name
    ):
        raise ValueError("local_path must resolve to one portable basename")
    if _looks_like_structured_private_data(name):
        raise ValueError("local_path basename must not contain structured private data")
    return name


@dataclass(frozen=True, slots=True)
class MaterialCreator:
    creator_id: str | None = None
    name: str | None = None
    profile_page: str | None = None

    def __post_init__(self) -> None:
        if self.creator_id is not None and _optional_identifier(self.creator_id) != self.creator_id:
            raise ValueError("creator_id is not canonical")
        if self.name is not None and _optional_public_text(self.name, max_length=256) != self.name:
            raise ValueError("creator name is not canonical")
        if (
            self.profile_page is not None
            and sanitize_public_source_url(self.profile_page) != self.profile_page
        ):
            raise ValueError("creator profile_page is not a safe public URL")
        if self.creator_id is None and self.name is None and self.profile_page is None:
            raise ValueError("creator metadata must contain at least one allowlisted field")


@dataclass(frozen=True, slots=True)
class MaterialRendition:
    rendition_id: str | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if (
            self.rendition_id is not None
            and _optional_identifier(self.rendition_id) != self.rendition_id
        ):
            raise ValueError("rendition_id is not canonical")
        if (self.width is None) != (self.height is None):
            raise ValueError("rendition width and height must be supplied together")
        for dimension in (self.width, self.height):
            if dimension is not None and (
                type(dimension) is not int or not 1 <= dimension <= 32768
            ):
                raise ValueError("rendition dimensions must be exact positive integers")
        if self.rendition_id is None and self.width is None:
            raise ValueError("rendition metadata must contain an ID or dimensions")


@dataclass(frozen=True, slots=True)
class MaterialSourceRecord:
    provider: str
    local_file: str
    duration_ms: int
    search_term: str | None = None
    asset_id: str | None = None
    source_page: str | None = None
    creator: MaterialCreator | None = None
    rendition: MaterialRendition | None = None

    def __post_init__(self) -> None:
        if type(self.provider) is not str or not _PROVIDER_ID.fullmatch(self.provider):
            raise ValueError("provider must be a canonical lowercase identifier")
        if type(self.local_file) is not str:
            raise TypeError("local_file must be an exact string")
        if _portable_basename(self.local_file) != self.local_file:
            raise ValueError("local_file must contain only a basename")
        if type(self.duration_ms) is not int or self.duration_ms <= 0:
            raise ValueError("duration_ms must be an exact positive integer")
        if (
            self.search_term is not None
            and _optional_public_text(self.search_term, max_length=512) != self.search_term
        ):
            raise ValueError("search_term is not canonical")
        if self.asset_id is not None and _optional_identifier(self.asset_id) != self.asset_id:
            raise ValueError("asset_id is not canonical")
        if (
            self.source_page is not None
            and sanitize_public_source_url(self.source_page) != self.source_page
        ):
            raise ValueError("source_page is not a safe public URL")
        if self.creator is not None and type(self.creator) is not MaterialCreator:
            raise TypeError("creator must be an exact MaterialCreator")
        if self.rendition is not None and type(self.rendition) is not MaterialRendition:
            raise TypeError("rendition must be an exact MaterialRendition")


def _creator_from_source(value: object) -> MaterialCreator | None:
    if type(value) is str:
        name = _optional_public_text(value, max_length=256)
        return MaterialCreator(name=name) if name is not None else None
    if not isinstance(value, Mapping):
        return None

    creator_id = _optional_identifier(value.get("id"))
    name = _optional_public_text(value.get("name"), max_length=256)
    if name is None:
        name = _optional_public_text(value.get("username"), max_length=256)
    profile_page = sanitize_public_source_url(value.get("profile_page"))
    if profile_page is None:
        profile_page = sanitize_public_source_url(value.get("profile_url"))
    if profile_page is None:
        profile_page = sanitize_public_source_url(value.get("url"))
    if creator_id is None and name is None and profile_page is None:
        return None
    return MaterialCreator(creator_id=creator_id, name=name, profile_page=profile_page)


def _positive_dimension(value: object) -> int | None:
    return value if type(value) is int and 1 <= value <= 32768 else None


def _rendition_from_source(value: object) -> MaterialRendition | None:
    if not isinstance(value, Mapping):
        return None
    rendition_id = _optional_identifier(value.get("id"))
    width = _positive_dimension(value.get("width"))
    height = _positive_dimension(value.get("height"))
    if (width is None) != (height is None):
        width = None
        height = None
    if rendition_id is None and width is None:
        return None
    return MaterialRendition(rendition_id=rendition_id, width=width, height=height)


def build_material_source_record(
    *,
    provider: str,
    local_path: str | Path,
    duration_ms: int,
    source_info: Mapping[str, object] | None = None,
) -> MaterialSourceRecord:
    """Build one persistent allowlisted source record from untrusted adapter metadata."""

    if type(provider) is not str or not _PROVIDER_ID.fullmatch(provider):
        raise ValueError("provider must be a canonical lowercase identifier")
    if type(duration_ms) is not int or duration_ms <= 0:
        raise ValueError("duration_ms must be an exact positive integer")
    if source_info is not None and not isinstance(source_info, Mapping):
        raise TypeError("source_info must be a mapping or None")

    source: Mapping[str, object] = source_info or {}
    return MaterialSourceRecord(
        provider=provider,
        local_file=_portable_basename(local_path),
        duration_ms=duration_ms,
        search_term=_optional_public_text(source.get("search_term"), max_length=512),
        asset_id=_optional_identifier(source.get("asset_id")),
        source_page=sanitize_public_source_url(source.get("source_page")),
        creator=_creator_from_source(source.get("creator")),
        rendition=_rendition_from_source(source.get("rendition")),
    )


def material_source_record_to_public_dict(record: MaterialSourceRecord) -> dict[str, object]:
    """Project only the persistent allowlist; never serialize hidden adapter payloads."""

    if type(record) is not MaterialSourceRecord:
        raise TypeError("record must be an exact MaterialSourceRecord")
    result: dict[str, object] = {
        "provider": record.provider,
        "local_file": record.local_file,
        "duration_ms": record.duration_ms,
    }
    if record.search_term is not None:
        result["search_term"] = record.search_term
    if record.asset_id is not None:
        result["asset_id"] = record.asset_id
    if record.source_page is not None:
        result["source_page"] = record.source_page
    if record.creator is not None:
        result["creator"] = {
            key: value
            for key, value in (
                ("id", record.creator.creator_id),
                ("name", record.creator.name),
                ("profile_page", record.creator.profile_page),
            )
            if value is not None
        }
    if record.rendition is not None:
        result["rendition"] = {
            key: value
            for key, value in (
                ("id", record.rendition.rendition_id),
                ("width", record.rendition.width),
                ("height", record.rendition.height),
            )
            if value is not None
        }
    return result


__all__ = [
    "MaterialCreator",
    "MaterialRendition",
    "MaterialSourceRecord",
    "build_material_source_record",
    "material_source_record_to_public_dict",
    "sanitize_public_source_url",
]
