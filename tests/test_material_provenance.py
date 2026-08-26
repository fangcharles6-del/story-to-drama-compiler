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
        "data : text/plain;base64,RAW_DATA_URI_LEAK",
        "data%20:text/plain;base64,ENCODED_DATA_URI_LEAK",
        "data%C2%A0:%20text/plain;base64,NBSP_DATA_URI_LEAK",
        "data%2520%253Atext%252Fplain%253Bbase64%252CDOUBLE_DATA_URI_LEAK",
        "javascript%20:alert(ENCODED_JAVASCRIPT_URI_LEAK)",
        "s3%20:private-bucket/path/ENCODED_S3_URI_LEAK",
        "gs%C2%A0:private-bucket/path/NBSP_GS_URI_LEAK",
        "https%3A%2F%2Fcdn.invalid%2Fvideo.mp4%3Ftoken%3DENCODED_URL_LEAK",
        "token%3DENCODED_QUERY_LEAK%26expires%3Dnever",
        "api+key%3DPLUS_ENCODED_LEAK",
        "Authorization%3A+Bearer+PLUS_AUTH_LEAK",
        "client+secret%3DPLUS_CLIENT_SECRET_LEAK",
        "api%252Bkey%253DDOUBLE_PLUS_ENCODED_LEAK",
        "Authorization%253A%252BBearer%252BDOUBLE_PLUS_AUTH_LEAK",
        "api%00key%3DNULL_CONTROL_LEAK",
        "Authorization%00Bearer%20NULL_CONTROL_LEAK",
        "api%C2%80key%3DUNICODE_CONTROL_LEAK",
        "api%C2%9Fkey%3DUNICODE_CONTROL_LEAK",
        "api%E2%80%8Bkey%3DZERO_WIDTH_LEAK",
        "Authorization%E2%80%8B%3A%E2%80%8BBearer%E2%80%8BFORMAT_LEAK",
        "api%20key%EF%BC%9DFULLWIDTH_EQUALS_LEAK",
        "api%C0%80key%3DINVALID_UTF8_LEAK",
        "api＋key＝FULLWIDTH_PLUS_LEAK",
        "api%EF%BC%8Bkey%EF%BC%9DFULLWIDTH_ENCODED_LEAK",
        "api％2Bkey％3DTRANSFORM_LEAK",
        "api%EF%BC%852Bkey%EF%BC%853DENCODED_TRANSFORM_LEAK",
        "Authorization＋Bearer＋FULLWIDTH_AUTH_LEAK",
        "clip?id=QUERY_LEAK",
        "api_key=QUERY_LEAK&expires=never",
        "page=GENERIC_QUERY_LEAK&size=1",
        "context page=EMBEDDED_QUERY_LEAK&size=1",
        "context page=TRAILING_QUERY_LEAK&size=1 trailing words",
        "signed/path?Policy=POLICY_LEAK&Key-Pair-Id=KEY_LEAK",
        "clips from /private/work/POSIX_LEAK.mp4",
        "clips from /home/user/HOME_PATH_LEAK.mp4",
        "clips from /tmp/TMP_PATH_LEAK.mp4",
        "clips from /custom/private/run-1/ABSOLUTE_PATH_LEAK.mp4",
        "clips,/custom/private/run-1/PUNCTUATED_PATH_LEAK.mp4",
        "clips from ///custom/private/run-1/TRIPLE_SLASH_PATH_LEAK.mp4",
        "clips from %2F%2F%2Fcustom%2Fprivate%2FENCODED_TRIPLE_PATH_LEAK.mp4",
        "clips+from+%2Ftenant%2Fbuild%2FABSOLUTE_PATH_LEAK.mp4",
        r"clips,C:\Users\Alice\DRIVE_PATH_LEAK.mp4",
        r"clips|D:/private/FORWARD_DRIVE_PATH_LEAK.mp4",
        r"clips/\\server\share\UNC_PATH_LEAK.mp4",
        r"clips,\\\server\share\TRIPLE_UNC_PATH_LEAK.mp4",
        r"clips,\\?\C:\private\DEVICE_PATH_LEAK.mp4",
        r"clips,\\?\UNC\server\share\EXTENDED_UNC_PATH_LEAK.mp4",
        r"clips,\\.\PhysicalDrive0\DEVICE_NAMESPACE_LEAK.mp4",
        r"clips,\Device\HarddiskVolume1\DEVICE_NAMESPACE_LEAK.mp4",
        r"clips,\??\C:\private\NT_PATH_LEAK.mp4",
        r"clips,\Users\Alice\ROOTED_WINDOWS_PATH_LEAK.mp4",
        r"clips,\Windows\System32\ROOTED_WINDOWS_PATH_LEAK.dll",
        r"clips,\SystemRoot\System32\SYSTEM_ROOT_PATH_LEAK.dll",
        r"clips,~\private\HOME_RELATIVE_PATH_LEAK.mp4",
        r"clips,.\private\DOT_RELATIVE_PATH_LEAK.mp4",
        r"clips,..\private\PARENT_RELATIVE_PATH_LEAK.mp4",
        "clips,%255CWindows%255CSystem32%255CDOUBLE_ROOTED_PATH_LEAK.dll",
        "clips,＼Users＼Alice＼FULLWIDTH_ROOTED_PATH_LEAK.mp4",
        "clips,%E2%80%8B%5CUsers%5CAlice%5CCF_ROOTED_PATH_LEAK.mp4",
        "clips,C%253A%255Cprivate%255CDOUBLE_WINDOWS_PATH_LEAK.mp4",
        "clips,%255C%255Cserver%255Cshare%255CDOUBLE_UNC_PATH_LEAK.mp4",
        "clips,Ｃ：＼private＼FULLWIDTH_WINDOWS_PATH_LEAK.mp4",
        "clips,C%E2%80%8B%3A%E2%80%8B%5Cprivate%5CCF_WINDOWS_PATH_LEAK.mp4",
        "clips,file:///C:/private/FILE_URI_PATH_LEAK.mp4",
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
        "data : science",
        "file: scene notes",
        "file : scene notes",
        "The Secret: Garden",
        "signature: style",
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
        "C++ tutorial",
        "A+B Studio",
        "api+key+security",
        "Director 👩‍💻 Studio",
        "Ｃ＋＋ tutorial",
        "server/share design",
        "C: chapter label",
        "C : chapter label",
        "Drive C: chapter label",
        r"server\share design",
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
    "rooted_text",
    (
        "Use /api endpoint",
        "Use /api/v1/users endpoint",
        "Visit /docs/getting-started/intro",
        "clips from /custom/private/run-1",
    ),
)
def test_builder_fails_closed_on_ambiguous_rooted_posix_text(rooted_text: str) -> None:
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={"search_term": rooted_text, "creator": rooted_text},
    )

    public = material_source_record_to_public_dict(record)
    assert "search_term" not in public
    assert "creator" not in public


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


@pytest.mark.parametrize(
    "unsafe_url",
    (
        "https://user%3Apass%40example.com/path",
        "https://user%253Apass%2540example.com/path",
        "https://api_key%3DHOST_SECRET.example.com/path",
        "https://example.com%3Ftoken%3DHOST_SECRET/path",
        "https://exa%0Ample.com/path",
        "https://exa mple.com/path",
        "https://exa\\mple.com/path",
        "https://exa​mple.com/path",
        "https://api_key=HOST_SECRET.example.com/path",
        "https://-bad.example/path",
        "https://bad-.example/path",
        "https://bad..example/path",
        "https://_service.example/path",
        "https://example.com./path",
        "https://example.com/api+key%3DPLUS_URL_LEAK",
        "https://example.com/Authorization%3A+Bearer+PLUS_AUTH_URL_LEAK",
        "https://example.com/users/private_EMAIL_LEAK@example.com",
        "https://example.com/users/private_EMAIL_LEAK@example.com.",
        "https://example.com/users/private_EMAIL_LEAK%40example.com",
        "https://example.com/users/private_EMAIL_LEAK%2540example.com",
        "https://example.com/users/private+tag%40example.com",
        "https://example.com/users/private%252Btag%2540example.com",
        "https://example.com/users/@private@example.com",
        "https://example.com/users/%40private%40example.com",
        "https://example.com/users/x@private@example.com",
        "https://example.com/users/private%E2%80%8B%40example.com",
        "https://example.com/api%C2%80key%3DUNICODE_CONTROL_URL_LEAK",
        "https://example.com/api＋key＝FULLWIDTH_URL_LEAK",
        "https://example.com/api％2Bkey％3DFULLWIDTH_PERCENT_URL_LEAK",
        "https://example.com/files/C:%5Cprivate%5CDRIVE_PATH_LEAK.mp4",
        "https://example.com/files/C:/private/FORWARD_DRIVE_PATH_LEAK.mp4",
        "https://example.com/files/%43%253A%255Cprivate%255CDOUBLE_DRIVE_PATH_LEAK.mp4",
        "https://example.com/files/%5C%5Cserver%5Cshare%5CUNC_PATH_LEAK.mp4",
        "https://example.com/files/%255C%255Cserver%255Cshare%255CDOUBLE_UNC_PATH_LEAK.mp4",
        "https://example.com/files/%5C%5C%3F%5CC:%5Cprivate%5CDEVICE_PATH_LEAK.mp4",
        "https://example.com/files/%5C%5C%3F%5CUNC%5Cserver%5Cshare%5CEXTENDED_UNC_PATH_LEAK.mp4",
        "https://example.com/files/file:%2F%2F%2FC:%2Fprivate%2FFILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/file%253A%252F%252F%252FC%253A%252Fprivate%252FDOUBLE_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/file:C|/Users/Alice/LEGACY_FILE_DRIVE_LEAK.mp4",
        "https://example.com/files/file:C%7C/Users/Alice/ENCODED_LEGACY_FILE_DRIVE_LEAK.mp4",
        "https://example.com/files/file%253AC%257C%252FUsers%252FAlice%252FDOUBLE_LEGACY_FILE_DRIVE_LEAK.mp4",
        "https://example.com/files/file%20:%20C|/Users/Alice/SPACE_LEGACY_FILE_DRIVE_LEAK.mp4",
        "https://example.com/files/clips-file:///home/user/HYPHEN_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/clips.file:///home/user/DOT_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/clips_file:///home/user/UNDERSCORE_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/clips-file:/home/user/SINGLE_SLASH_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/clips-%2566ile%253A%252F%252F%252Fhome%252FDOUBLE_FILE_URI_PREFIX_LEAK.mp4",
        "https://example.com/files/clips%EF%BC%8Dfile%EF%BC%9A%EF%BC%8Fhome%EF%BC%8FFULLWIDTH_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/%EF%BC%A3%EF%BC%9A%EF%BC%BCprivate%EF%BC%BCFULLWIDTH_PATH_LEAK.mp4",
        "https://example.com/files/C%E2%80%8B%3A%E2%80%8B%5Cprivate%5CCF_PATH_LEAK.mp4",
        "https://example.com/files/%2Fhome%2Fuser%2FPOSIX_ROOT_PATH_LEAK.mp4",
        "https://example.com/files/%252FUsers%252FAlice%252FDOUBLE_POSIX_ROOT_PATH_LEAK.mp4",
        "https://example.com/files/%EF%BC%8Fhome%EF%BC%8Fuser%EF%BC%8FFULLWIDTH_POSIX_ROOT_PATH_LEAK.mp4",
        "https://example.com/files/%2F%2Fserver%2Fshare%2FNETWORK_ROOT_PATH_LEAK.mp4",
        "https://example.com/files//./PhysicalDrive0/RAW_FORWARD_DEVICE_PATH_LEAK.bin",
        "https://example.com/files//server/share/RAW_FORWARD_UNC_PATH_LEAK.mp4",
        "https://example.com/files/smb://server/share/RAW_SMB_PATH_LEAK.mp4",
        "https://example.com/files/nfs://server/share/RAW_NFS_PATH_LEAK.mp4",
        "https://example.com/files/afp://server/share/RAW_AFP_PATH_LEAK.mp4",
        "https://example.com/files/smb:/server/share/SINGLE_SLASH_SMB_PATH_LEAK.mp4",
        "https://example.com/files/custom:/home/user/CUSTOM_ROOTED_URI_PATH_LEAK.mp4",
        "https://example.com/files/profile:/public/PROFILE_ROOTED_URI_PATH_LEAK.mp4",
        "https://example.com/files/smb:%20/server/share/SPACE_NETWORK_URI_PATH_LEAK.mp4",
        "https://example.com/files/smb:+/server/share/PLUS_NETWORK_URI_PATH_LEAK.mp4",
        "https://example.com/files/file:%20/home/user/SPACE_FILE_URI_PATH_LEAK.mp4",
        "https://example.com/files/custom:%C2%A0/home/user/NBSP_ROOTED_URI_PATH_LEAK.mp4",
        "https://example.com/files/custom:%2520%252Fhome%252Fuser%252FDOUBLE_SPACE_URI_PATH_LEAK.mp4",
        "https://example.com/files/data:text/plain;base64,RAW_PROVIDER_PAYLOAD_LEAK",
        "https://example.com/files/data%253Atext%252Fplain%253Bbase64%252CRAW_PROVIDER_PAYLOAD_LEAK",
        "https://example.com/files/s3:private-bucket/RAW_OBJECT_PATH_LEAK.mp4",
        "https://example.com/files/gs:private-bucket/RAW_OBJECT_PATH_LEAK.mp4",
        "https://example.com/files/smb%20:/server/share/PRECOLON_SPACE_NETWORK_PATH_LEAK.mp4",
        "https://example.com/files/file%20:/home/user/PRECOLON_SPACE_FILE_PATH_LEAK.mp4",
        "https://example.com/files/custom%E3%80%80:/home/user/PRECOLON_IDEOGRAPHIC_SPACE_PATH_LEAK.mp4",
        "https://example.com/files/custom%2520%253A/server/share/DOUBLE_PRECOLON_SPACE_PATH_LEAK.mp4",
        "https://example.com/files/data%20:text/plain;base64,PRECOLON_DATA_PAYLOAD_LEAK",
        "https://example.com/files/javascript%20:alert(PRECOLON_JAVASCRIPT_PAYLOAD_LEAK)",
        "https://example.com/files/s3%20:private-bucket/PRECOLON_OBJECT_PATH_LEAK.mp4",
        "https://example.com/files//．/PhysicalDrive0/FULLWIDTH_DOT_DEVICE_PATH_LEAK.bin",
        "https://example.com/files/smb:／／server／share／FULLWIDTH_SMB_PATH_LEAK.mp4",
    ),
)
def test_public_url_sanitizer_rejects_encoded_or_malformed_private_data(
    unsafe_url: str,
) -> None:
    assert sanitize_public_source_url(unsafe_url) is None

    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={
            "source_page": unsafe_url,
            "creator": {"name": "Public Creator", "profile_url": unsafe_url},
        },
    )
    public = material_source_record_to_public_dict(record)
    assert public == {
        "provider": "local",
        "local_file": "clip.mp4",
        "duration_ms": 4000,
        "creator": {"name": "Public Creator"},
    }
    assert "LEAK" not in repr(public)

    with pytest.raises(ValueError, match="profile_page"):
        MaterialCreator(profile_page=unsafe_url)
    with pytest.raises(ValueError, match="source_page"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            source_page=unsafe_url,
        )


@pytest.mark.parametrize(
    "ambiguous_url",
    (
        "https://example.com/path//",
        "https://example.com/path///",
        "https://example.com/path/%2F%2F",
        "https://example.com/path/%252F%252F",
    ),
)
def test_public_url_sanitizer_fails_closed_on_empty_double_roots(
    ambiguous_url: str,
) -> None:
    assert sanitize_public_source_url(ambiguous_url) is None


def test_public_url_sanitizer_keeps_handles_and_canonicalizes_hosts() -> None:
    assert sanitize_public_source_url("https://EXAMPLE.com/@creator?tracking=1") == (
        "https://example.com/@creator"
    )
    assert sanitize_public_source_url("https://[2001:db8::1]:8443/video") == (
        "https://[2001:db8::1]:8443/video"
    )
    assert sanitize_public_source_url("https://example.com/C++?tracking=1") == (
        "https://example.com/C++"
    )
    assert sanitize_public_source_url("https://example.com/C%2B%2B/guide") == (
        "https://example.com/C%2B%2B/guide"
    )
    assert sanitize_public_source_url("https://xn--r8jz45g.xn--zckzah/path") == (
        "https://xn--r8jz45g.xn--zckzah/path"
    )
    assert sanitize_public_source_url("https://example.com/api%2Fv1/resource") == (
        "https://example.com/api%2Fv1/resource"
    )
    assert sanitize_public_source_url("https://example.com/docs/C%2B%2B/guide") == (
        "https://example.com/docs/C%2B%2B/guide"
    )
    assert sanitize_public_source_url("https://example.com/files/report%20final.pdf") == (
        "https://example.com/files/report%20final.pdf"
    )
    assert sanitize_public_source_url("https://example.com/files/report|final.pdf") == (
        "https://example.com/files/report|final.pdf"
    )
    assert sanitize_public_source_url("https://example.com/docs/C|notes") == (
        "https://example.com/docs/C|notes"
    )
    assert sanitize_public_source_url("https://example.com/docs/chapter:1") == (
        "https://example.com/docs/chapter:1"
    )
    assert sanitize_public_source_url("https://example.com/docs/chapter%20:%201") == (
        "https://example.com/docs/chapter%20:%201"
    )
    assert sanitize_public_source_url("https://example.com/docs/data%20:%20science") == (
        "https://example.com/docs/data%20:%20science"
    )
    assert sanitize_public_source_url("https://example.com/docs/file%20:%20scene-notes") == (
        "https://example.com/docs/file%20:%20scene-notes"
    )
    assert sanitize_public_source_url("https://example.com/docs/C%20:%20chapter") == (
        "https://example.com/docs/C%20:%20chapter"
    )
    assert sanitize_public_source_url("https://example.com/creators/👨‍👩‍👧") == (
        "https://example.com/creators/👨‍👩‍👧"
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


@pytest.mark.parametrize(
    "unsafe_text",
    (
        r"clips,C:\Users\Alice\DIRECT_DRIVE_PATH_LEAK.mp4",
        r"clips,\\server\share\DIRECT_UNC_PATH_LEAK.mp4",
        r"clips,\\?\C:\private\DIRECT_DEVICE_PATH_LEAK.mp4",
        "clips,C%253A%255Cprivate%255CDIRECT_ENCODED_PATH_LEAK.mp4",
    ),
)
def test_direct_contracts_reject_absolute_windows_path_text(unsafe_text: str) -> None:
    with pytest.raises(ValueError, match="creator name"):
        MaterialCreator(name=unsafe_text)
    with pytest.raises(ValueError, match="search_term"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            search_term=unsafe_text,
        )


@pytest.mark.parametrize(
    "unsafe_text",
    (
        "data%20:text/plain;base64,DIRECT_DATA_URI_LEAK",
        "javascript%20:alert(DIRECT_JAVASCRIPT_URI_LEAK)",
        "s3%20:private-bucket/path/DIRECT_S3_URI_LEAK",
        "gs%C2%A0:private-bucket/path/DIRECT_GS_URI_LEAK",
    ),
)
def test_direct_contracts_reject_obfuscated_uri_text(unsafe_text: str) -> None:
    with pytest.raises(ValueError, match="creator name"):
        MaterialCreator(name=unsafe_text)
    with pytest.raises(ValueError, match="search_term"):
        MaterialSourceRecord(
            provider="local",
            local_file="clip.mp4",
            duration_ms=4000,
            search_term=unsafe_text,
        )


def test_unknown_path_fields_never_enter_public_projection() -> None:
    unsafe_url = "https://example.com/files/C:%5Cprivate%5CUNKNOWN_PATH_LEAK.mp4"
    record = build_material_source_record(
        provider="local",
        local_path="clip.mp4",
        duration_ms=4000,
        source_info={
            "download_url": unsafe_url,
            "signed_url": unsafe_url,
            "local_path": r"C:\private\UNKNOWN_LOCAL_PATH_LEAK.mp4",
            "working_directory": r"\\server\share\UNKNOWN_WORKDIR_PATH_LEAK",
            "raw": {"path": r"C:\private\UNKNOWN_RAW_PATH_LEAK"},
        },
    )

    assert material_source_record_to_public_dict(record) == {
        "provider": "local",
        "local_file": "clip.mp4",
        "duration_ms": 4000,
    }


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
