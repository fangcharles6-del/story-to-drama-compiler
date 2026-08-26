from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from sdc.material_provenance import (
    MaterialCreator,
    MaterialRendition,
    MaterialSourceRecord,
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


def test_builder_drops_recognizable_private_shapes_from_allowlisted_fields() -> None:
    record = build_material_source_record(
        provider="pexels",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={
            "search_term": ("clips https://cdn.invalid/video.mp4?token=SEARCH_TERM_LEAK"),
            "asset_id": "https://cdn.invalid/video.mp4?token=ASSET_ID_LEAK",
            "creator": {
                "id": "creator?id=CREATOR_ID_LEAK",
                "name": "Public Creator",
            },
            "rendition": {
                "id": r"C:\private\RENDITION_ID_LEAK",
                "width": 1280,
                "height": 720,
            },
        },
    )

    public = material_source_record_to_public_dict(record)
    assert public == {
        "provider": "pexels",
        "local_file": "clip.mp4",
        "duration_ms": 4000,
        "creator": {"name": "Public Creator"},
        "rendition": {"width": 1280, "height": 720},
    }
    assert "LEAK" not in repr(public)


@pytest.mark.parametrize(
    "unsafe",
    (
        "https://cdn.invalid/video.mp4?token=URL_LEAK",
        "Creator <private_EMAIL_LEAK@example.com>",
        "Creator private_EMAIL_LEAK@example.com.",
        "admin_EMAIL_LEAK@internal",
        "cdn.example.com/file.mp4?id=BARE_URL_LEAK",
        "10.0.0.1/private?foo=IP_URL_LEAK",
        "s3:private-bucket/path/OBJECT_LEAK",
        "https%3A%2F%2Fcdn.invalid%2Fvideo.mp4%3Ftoken%3DENCODED_URL_LEAK",
        "token%3DENCODED_QUERY_LEAK%26expires%3Dnever",
        "clip?id=QUERY_LEAK",
        "api_key=QUERY_LEAK&expires=never",
        "page=GENERIC_QUERY_LEAK&size=1",
        "context page=EMBEDDED_QUERY_LEAK&size=1",
        "context page=TRAILING_QUERY_LEAK&size=1 trailing words",
        "signed/path?Policy=POLICY_LEAK&Key-Pair-Id=KEY_LEAK",
        "clips from /private/work/POSIX_LEAK.mp4",
        "clips from /home/user/HOME_PATH_LEAK.mp4",
        "clips from /tmp/TMP_PATH_LEAK.mp4",
        "source /Users/USER_PATH_LEAK",
        "local path:/private/work/LABEL_PATH_LEAK",
        r"source local_file=C:\private\WINDOWS_LABEL_LEAK",
        "~alice/private/HOME_PATH_LEAK",
        "api key: API_KEY_LEAK",
        "access token: ACCESS_TOKEN_LEAK",
        "client secret: CLIENT_SECRET_LEAK",
        "password=PASSWORD_LEAK",
        "context refresh_token=REFRESH_TOKEN_LEAK",
        "Authorization Bearer AUTHORIZATION_LEAK",
        "Authorization: Bearer AUTH_LEAK",
        "context client_secret=CLIENT_SECRET_LEAK",
        "context OPENAI_API_KEY=ENV_ASSIGNMENT_LEAK",
        '{"api_key":"JSON_LEAK"}',
        "%7B%22api_key%22%3A%22RAW_ENCODED_LEAK%22%7D",
        'provider payload {"public_id": "RAW_PAYLOAD_LEAK"}',
        'prefix {not-json}; payload {"public_id": "MULTI_RAW_LEAK"}',
        "{'api_key': 'PYTHON_REPR_LEAK'}",
        r"C:\private\PATH_LEAK",
        "/private/work/PATH_LEAK",
        "sk_live_LEAK0123456789ABCDEF",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJMRUFLIn0.signatureLEAK",
    ),
)
def test_builder_drops_recognizable_private_free_text_shapes(unsafe: str) -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={"search_term": unsafe, "creator": unsafe},
    )

    public = material_source_record_to_public_dict(record)
    assert "search_term" not in public
    assert "creator" not in public
    assert "LEAK" not in repr(public)


@pytest.mark.parametrize(
    "safe",
    (
        "office pantry?",
        "token economy",
        "O'Connor Studio",
        "AC/DC Films",
        "创作者 @creator",
        "data: science",
        "file: scene notes",
        "The Secret: Garden",
        "signature: style",
        "Use /api endpoint",
        "Bearer of bad news",
        "Basic concepts",
        "Basic animation techniques",
        "Bearer responsibilities",
        "Film [2024]",
        "(1, 2)",
        "will.i.am",
        "Mr.Smith Studio",
        "token-economics",
        "secret-ingredient",
        "signature-analysis",
        "api-key-security",
        "2026/08/26",
        "director/writer/producer",
        "Use /api/v1 endpoint",
        "Use /api/v1/users endpoint",
        "Visit /docs/getting-started/intro",
        "File / Edit menu",
        "workspace / design",
        "scene.final.cut",
        "release.v1.final",
        "Alice/Bob/Carol Studio",
        "notes.mp4",
        "artifact.tar.gz",
        "x=y",
        "R&D=Growth",
        "OPENAI_API_KEY documentation",
        "password: reset guide",
    ),
)
def test_builder_preserves_safe_public_free_text(safe: str) -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={"search_term": safe, "creator": safe},
    )

    public = material_source_record_to_public_dict(record)
    assert public["search_term"] == safe
    assert public["creator"] == {"name": safe}


@pytest.mark.parametrize(
    "unsafe_identifier",
    (
        "sk_live_LEAK0123456789ABCDEF",
        "sk_test_LEAK0123456789ABCDEF",
        "sk-proj-LEAK0123456789abcdefghijkl",
        "ghp_LEAK0123456789abcdefghijkl",
        "AKIALEAK000000000000",
        "xoxb-LEAK-0123456789abcdefghijklmnop",
    ),
)
def test_builder_drops_high_confidence_credential_identifiers(
    unsafe_identifier: str,
) -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={
            "asset_id": unsafe_identifier,
            "creator": {"id": unsafe_identifier, "name": "Public Creator"},
            "rendition": {
                "id": unsafe_identifier,
                "width": 1080,
                "height": 1920,
            },
        },
    )

    public = material_source_record_to_public_dict(record)
    assert public == {
        "provider": "local",
        "local_file": "clip.mp4",
        "duration_ms": 4000,
        "creator": {"name": "Public Creator"},
        "rendition": {"width": 1080, "height": 1920},
    }
    assert "LEAK" not in repr(public)


def test_builder_preserves_portable_dotted_identifiers_and_safe_siblings() -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={
            "asset_id": "asset.42",
            "creator": {
                "id": "creator.v2",
                "name": "private_CREATOR_NAME_LEAK@example.com",
            },
            "rendition": {"id": "portrait.v1"},
        },
    )

    assert material_source_record_to_public_dict(record) == {
        "provider": "local",
        "local_file": "clip.mp4",
        "duration_ms": 4000,
        "asset_id": "asset.42",
        "creator": {"id": "creator.v2"},
        "rendition": {"id": "portrait.v1"},
    }


@pytest.mark.parametrize(
    "public_identifier",
    (
        "token_asset_12345678",
        "secret-garden-title",
        "signature-style-guide",
        "api-key-concepts-guide",
        "ghp_publicasset123",
        "api.key.security.concepts",
        "OPENAI_API_KEY_DOCUMENTATION",
    ),
)
def test_builder_does_not_guess_whether_ambiguous_identifiers_are_secrets(
    public_identifier: str,
) -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={"asset_id": public_identifier},
    )

    assert record.asset_id == public_identifier


def test_builder_fails_closed_on_dense_mapping_delimiters() -> None:
    dense_structure = "{" * 256 + "}" * 256
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={"search_term": dense_structure, "creator": dense_structure},
    )

    public = material_source_record_to_public_dict(record)
    assert "search_term" not in public
    assert "creator" not in public


def test_windows_path_is_reduced_to_portable_basename() -> None:
    record = build_material_source_record(
        provider="local",
        local_path=r"C:\Users\Charles\Videos\shot01.mp4",
        duration_ms=4000,
    )
    assert record.local_file == "shot01.mp4"


@pytest.mark.parametrize(
    "local_path",
    (
        "https://cdn.example/video.mp4?token=LOCAL_FILE_LEAK",
        "https%3A%2F%2Fcdn.example%2Fvideo.mp4%3Ftoken%3DLOCAL_FILE_LEAK",
        "/tmp/api_key=LOCAL_FILE_LEAK",
        "/tmp/private_LOCAL_FILE_LEAK@example.com",
        "/tmp/{api_key=RAW_LOCAL_FILE_LEAK}.mp4",
    ),
)
def test_local_basename_rejects_recognizable_private_shapes(local_path: str) -> None:
    with pytest.raises(ValueError, match="local_path"):
        build_material_source_record(
            provider="local",
            local_path=local_path,
            duration_ms=4000,
        )


@pytest.mark.parametrize(
    "local_path, expected",
    (
        (r"C:\Videos\secret-garden.mp4", "secret-garden.mp4"),
        (r"C:\captures\www.example.com\clip.mp4", "clip.mp4"),
        ("/tmp/scene.final.cut", "scene.final.cut"),
        ("/tmp/www.example.com/clip.mp4", "clip.mp4"),
        ("www.example.com/clip.mp4", "clip.mp4"),
        ("folder/token-economics.mp4", "token-economics.mp4"),
    ),
)
def test_local_basename_preserves_ordinary_portable_names(
    local_path: str,
    expected: str,
) -> None:
    record = build_material_source_record(
        provider="local",
        local_path=local_path,
        duration_ms=4000,
    )

    assert record.local_file == expected


def test_public_url_sanitizer_rejects_credentials_and_non_http_schemes() -> None:
    assert sanitize_public_source_url("https://example.com/a?token=x#f") == (
        "https://example.com/a"
    )
    assert sanitize_public_source_url("https://user:pass@example.com/a") is None
    assert sanitize_public_source_url("file:///tmp/a.mp4") is None
    assert sanitize_public_source_url("javascript:alert(1)") is None
    assert (
        sanitize_public_source_url(
            "https://example.com/download/sk_live_LEAK0123456789ABCDEF/video.mp4"
        )
        is None
    )
    assert (
        sanitize_public_source_url("https://example.com/video;X-Amz-Signature=SIGNED_PATH_LEAK")
        is None
    )
    assert (
        sanitize_public_source_url("https://example.com/video.mp4%3Ftoken%3DENCODED_QUERY_LEAK")
        is None
    )
    assert sanitize_public_source_url("https://example.com/video%0AHEADER_LEAK") is None
    assert sanitize_public_source_url("https://example.com/user:password@in-path") is None
    assert sanitize_public_source_url("https://example.com/secret-garden") == (
        "https://example.com/secret-garden"
    )


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


def test_direct_contracts_reject_recognizable_private_shapes() -> None:
    with pytest.raises(ValueError, match="creator_id"):
        MaterialCreator(creator_id="private@example.com")
    with pytest.raises(ValueError, match="creator name"):
        MaterialCreator(name="private@example.com")
    with pytest.raises(ValueError, match="rendition_id"):
        MaterialRendition(rendition_id="token=RENDITION_LEAK")
    with pytest.raises(ValueError, match="asset_id"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            asset_id="https://cdn.invalid/video.mp4?token=ASSET_LEAK",
        )
    with pytest.raises(ValueError, match="search_term"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            search_term='{"api_key":"SEARCH_LEAK"}',
        )


def test_direct_record_rejects_non_exact_nested_types() -> None:
    with pytest.raises(TypeError, match="exact MaterialCreator"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            creator=SimpleNamespace(
                creator_id=None,
                name="private@example.com",
                profile_page=None,
            ),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="exact MaterialRendition"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            rendition={"download_url": "https://cdn.invalid?token=LEAK"},  # type: ignore[arg-type]
        )


def test_material_source_record_is_deeply_immutable() -> None:
    record = MaterialSourceRecord(
        provider="local",
        local_file="clip.mp4",
        duration_ms=4000,
        creator=MaterialCreator(creator_id="creator-7", name="Creator"),
        rendition=MaterialRendition(
            rendition_id="portrait-hd",
            width=1080,
            height=1920,
        ),
    )

    assert record.creator is not None
    assert record.rendition is not None
    with pytest.raises(FrozenInstanceError):
        record.local_file = "changed.mp4"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        record.creator.name = "Changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        record.rendition.width = 720  # type: ignore[misc]

    public = material_source_record_to_public_dict(record)
    creator = public["creator"]
    assert isinstance(creator, dict)
    creator["name"] = "Changed"
    rendition = public["rendition"]
    assert isinstance(rendition, dict)
    rendition["width"] = 720
    assert material_source_record_to_public_dict(record)["creator"] == {
        "id": "creator-7",
        "name": "Creator",
    }
    assert material_source_record_to_public_dict(record)["rendition"] == {
        "id": "portrait-hd",
        "width": 1080,
        "height": 1920,
    }
