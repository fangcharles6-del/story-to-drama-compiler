from pathlib import Path

import pytest

from sdc.material_provenance import (
    MaterialRendition,
    build_material_source_record,
    material_source_record_to_public_dict,
    sanitize_public_source_url,
)


def test_source_record_keeps_only_allowlisted_public_metadata() -> None:
    record = build_material_source_record(
        provider="pexels",
        local_path=Path("/private/work/tasks/run-1/downloaded.mp4"),
        duration_ms=6000,
        source_info={
            "search_term": "office pantry",
            "asset_id": 42,
            "source_page": "https://www.pexels.com/video/42?token=secret#preview",
            "download_url": "https://cdn.example/video.mp4?credential=secret",
            "api_key": "never-persist",
            "creator": {
                "id": 7,
                "name": "Creator",
                "profile_url": "https://www.pexels.com/@creator?tracking=1",
                "email": "private@example.com",
            },
            "rendition": {
                "id": "portrait-hd",
                "width": 1080,
                "height": 1920,
                "download_url": "https://cdn.example/private",
            },
        },
    )

    public = material_source_record_to_public_dict(record)
    assert public == {
        "provider": "pexels",
        "local_file": "downloaded.mp4",
        "duration_ms": 6000,
        "search_term": "office pantry",
        "asset_id": "42",
        "source_page": "https://www.pexels.com/video/42",
        "creator": {
            "id": "7",
            "name": "Creator",
            "profile_page": "https://www.pexels.com/@creator",
        },
        "rendition": {"id": "portrait-hd", "width": 1080, "height": 1920},
    }
    serialized = repr(public)
    assert "secret" not in serialized
    assert "private@example.com" not in serialized
    assert "/private/work" not in serialized


def test_windows_path_is_reduced_to_portable_basename() -> None:
    record = build_material_source_record(
        provider="local",
        local_path=r"C:\Users\Charles\Videos\shot01.mp4",
        duration_ms=4000,
    )
    assert record.local_file == "shot01.mp4"


def test_public_url_sanitizer_rejects_credentials_and_non_http_schemes() -> None:
    assert sanitize_public_source_url("https://example.com/a?token=x#f") == (
        "https://example.com/a"
    )
    assert sanitize_public_source_url("https://user:pass@example.com/a") is None
    assert sanitize_public_source_url("file:///tmp/a.mp4") is None
    assert sanitize_public_source_url("javascript:alert(1)") is None


def test_malformed_optional_metadata_is_dropped_not_promoted() -> None:
    record = build_material_source_record(
        provider="coverr",
        local_path="clip.mp4",
        duration_ms=5000,
        source_info={
            "source_page": "https://user:pass@example.com/clip",
            "creator": {"email": "hidden@example.com"},
            "rendition": {"width": 1080},
        },
    )
    assert record.source_page is None
    assert record.creator is None
    assert record.rendition is None


def test_direct_rendition_contract_rejects_partial_dimensions() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        MaterialRendition(width=1080)
