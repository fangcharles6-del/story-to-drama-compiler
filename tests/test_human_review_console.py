import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import sdc.human_review_console as console_module
from sdc.human_review_console import (
    HumanReviewConsoleError,
    verify_human_review_console_workspace,
    write_human_review_console,
)

PACK_ID = "real_asset_pack_0123456789abcdef0123"
WORKSPACE_KINDS = ("EVIDENCE", "REVIEWER_A", "REVIEWER_B")


@dataclass(frozen=True)
class _FakeEvidence:
    payload: dict[str, object]

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return self.payload


@dataclass(frozen=True)
class _FakeDescriptor:
    ordinal: int
    requirement_id: str
    kind: str
    subject_id: str
    logical_path: str
    object_path: str
    media_type: str
    sha256: str
    size_bytes: int
    duration_ms: int
    source_authority: str
    provenance_record_sha256: str
    technical_profile: str
    technical_record_sha256: str
    image: _FakeEvidence | None
    audio: _FakeEvidence | None

    def model_dump(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "requirement_id": self.requirement_id,
            "kind": self.kind,
            "subject_id": self.subject_id,
            "logical_path": self.logical_path,
            "object_path": self.object_path,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "duration_ms": self.duration_ms,
            "source_authority": self.source_authority,
            "provenance_record_sha256": self.provenance_record_sha256,
            "technical_profile": self.technical_profile,
            "technical_record_sha256": self.technical_record_sha256,
            "image": self.image.payload if self.image else None,
            "audio": self.audio.payload if self.audio else None,
        }


@dataclass(frozen=True)
class _FakeManifest:
    pack_id: str
    objects: tuple[_FakeDescriptor, ...]

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "schema_version": "1.0.0",
            "document_type": "sdc.creative-sample-frozen-real-asset-pack",
            "pack_id": self.pack_id,
            "objects": [item.model_dump() for item in self.objects],
            "state": "FROZEN_UNREVIEWED",
            "current_gate": "HUMAN_GATE",
            "execution_authorized": False,
            "posts_allowed": 0,
            "provider_requests": 0,
        }


@dataclass(frozen=True)
class _FakeRightsEvidenceBundle:
    bundle_id: str
    evidence_record_sha256: str
    copyright_basis: str
    likeness_basis: str
    privacy_basis: str
    territory: str
    use_scope: str
    valid_until: str
    payload: dict[str, object]

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return self.payload


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fake_frozen(tmp_path: Path) -> SimpleNamespace:
    root = tmp_path / "frozen" / PACK_ID
    root.mkdir(parents=True)
    descriptors: list[_FakeDescriptor] = []
    for ordinal in range(14):
        data = f"offline-media-{ordinal}".encode()
        media_sha = hashlib.sha256(data).hexdigest()
        object_path = f"objects/{media_sha[:2]}/{media_sha}"
        media_path = root.joinpath(*object_path.split("/"))
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(data)
        if ordinal < 4:
            kind = "IMAGE"
            media_type = "image/png"
            duration_ms = 0
            evidence = _FakeEvidence(
                {
                    "width": 1024,
                    "height": 1024,
                    "color_space": "RGB",
                    "metadata_free": True,
                    "semantic_privacy_reviewed": False,
                }
            )
            image, audio = evidence, None
        else:
            kind = "VOICE" if ordinal < 13 else "BGM"
            media_type = "audio/wav"
            duration_ms = 1000 if ordinal < 13 else 72000
            evidence = _FakeEvidence(
                {
                    "codec": "pcm_s16le",
                    "sample_rate_hz": 48000,
                    "channels": 1 if ordinal < 13 else 2,
                    "duration_ms": duration_ms,
                    "semantic_content_reviewed": False,
                }
            )
            image, audio = None, evidence
        descriptors.append(
            _FakeDescriptor(
                ordinal=ordinal,
                requirement_id=f"real_asset_requirement_{ordinal:020x}",
                kind=kind,
                subject_id=f"SUBJECT_{ordinal:02d}",
                logical_path=f"private/asset-{ordinal:02d}",
                object_path=object_path,
                media_type=media_type,
                sha256=media_sha,
                size_bytes=len(data),
                duration_ms=duration_ms,
                source_authority="SEPARATELY_APPROVED_LOCAL_GENERATION",
                provenance_record_sha256=_digest(f"provenance-{ordinal}"),
                technical_profile="offline-technical-v1",
                technical_record_sha256=_digest(f"technical-{ordinal}"),
                image=image,
                audio=audio,
            )
        )
    manifest = _FakeManifest(pack_id=PACK_ID, objects=tuple(descriptors))
    return SimpleNamespace(
        root=root,
        manifest_path=root / "asset-pack.json",
        manifest=manifest,
        created=False,
    )


def _tree_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _install_verifier(
    monkeypatch: pytest.MonkeyPatch,
    frozen: SimpleNamespace,
) -> list[Path]:
    calls: list[Path] = []

    def verify(path: Path) -> SimpleNamespace:
        calls.append(Path(path))
        return frozen

    monkeypatch.setattr(console_module, "verify_real_asset_candidate_pack", verify)
    return calls


def _install_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    frozen: SimpleNamespace,
) -> tuple[Path, _FakeRightsEvidenceBundle]:
    evidence_record_sha256 = _digest("evidence-record")
    bundle_id = "real_asset_rights_evidence_v2_0123456789abcdef0123"
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-rights-evidence-bundle-v2",
        "profile": "creative-sample-real-asset-review-v2",
        "bundle_id": bundle_id,
        "pack_id": PACK_ID,
        "pack_manifest_sha256": _digest("pack-manifest"),
        "evidence_record_sha256": evidence_record_sha256,
        "asset_bindings": [],
        "copyright_basis": "本地原创生成记录",
        "likeness_basis": "不含现实人物或受保护角色",
        "privacy_basis": "不含个人信息",
        "territory": "全球",
        "use_scope": "Creative Sample 本地评估",
        "valid_until": "PERPETUAL",
        "status": "EVIDENCE_CANDIDATE",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    bundle = _FakeRightsEvidenceBundle(
        bundle_id=bundle_id,
        evidence_record_sha256=evidence_record_sha256,
        copyright_basis=str(payload["copyright_basis"]),
        likeness_basis=str(payload["likeness_basis"]),
        privacy_basis=str(payload["privacy_basis"]),
        territory=str(payload["territory"]),
        use_scope=str(payload["use_scope"]),
        valid_until=str(payload["valid_until"]),
        payload=payload,
    )
    evidence_path = tmp_path / "private-records" / "evidence-bundle.json"
    evidence_path.parent.mkdir()
    evidence_path.write_bytes(console_module._canonical_document(payload))
    monkeypatch.setattr(
        console_module,
        "load_real_asset_rights_evidence_bundle_v2",
        lambda _path: bundle,
    )

    def rebuild(**kwargs: object) -> _FakeRightsEvidenceBundle:
        assert kwargs["pack"] == frozen.manifest
        return bundle

    monkeypatch.setattr(console_module, "build_real_asset_rights_evidence_bundle_v2", rebuild)
    return evidence_path, bundle


def test_prepare_creates_three_independent_role_bound_draft_workspaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    before = _tree_snapshot(frozen.root)
    calls = _install_verifier(monkeypatch, frozen)
    evidence_path, evidence = _install_evidence(tmp_path, monkeypatch, frozen)
    output_parent = tmp_path / "human-review-workspaces"
    output_parent.mkdir()

    workspaces = {
        kind: write_human_review_console(
            frozen.root,
            output_parent,
            kind,  # type: ignore[arg-type]
            evidence_path=None if kind == "EVIDENCE" else evidence_path,
        )
        for kind in WORKSPACE_KINDS
    }

    assert len(calls) == 9
    assert len({item.root for item in workspaces.values()}) == 3
    assert workspaces["EVIDENCE"].root.name.endswith("-evidence")
    assert workspaces["REVIEWER_A"].root.name.endswith("-reviewer-a")
    assert workspaces["REVIEWER_B"].root.name.endswith("-reviewer-b")
    assert _tree_snapshot(frozen.root) == before

    expected_files = {
        "app.js",
        "index.html",
        "review-context.js",
        "review-context.json",
        "style.css",
    }
    for kind, workspace in workspaces.items():
        assert {path.name for path in workspace.root.iterdir()} == expected_files
        assert not any(
            path.suffix.casefold() in {".png", ".wav"}
            for path in workspace.root.iterdir()
        )
        context = json.loads(workspace.context_path.read_text(encoding="utf-8"))
        context_bytes = workspace.context_path.read_bytes()
        assert context["workspace_kind"] == kind
        assert context["reviewer_role"] == (None if kind == "EVIDENCE" else kind)
        assert workspace.review_context_sha256 == hashlib.sha256(context_bytes).hexdigest()
        context_script = (workspace.root / "review-context.js").read_text(encoding="utf-8")
        assert workspace.review_context_sha256 in context_script
        if kind == "EVIDENCE":
            assert context["evidence_bundle"] is None
            assert workspace.evidence_bundle_id is None
            assert workspace.evidence_bundle_sha256 is None
        else:
            projection = context["evidence_bundle"]
            assert projection["bundle_id"] == evidence.bundle_id
            assert projection["bundle_sha256"] == hashlib.sha256(
                evidence_path.read_bytes()
            ).hexdigest()
            assert projection["evidence_record_sha256"] == evidence.evidence_record_sha256
            assert projection["read_only"] is True
            assert workspace.evidence_bundle_id == evidence.bundle_id
            assert workspace.evidence_bundle_sha256 == projection["bundle_sha256"]
        assert len(context["assets"]) == 14
        assert context["current_gate"] == "HUMAN_GATE"
        assert context["provider_state"] == "NOT_AUTHORIZED"
        assert context["execution_authorized"] is False
        assert context["posts_allowed"] == context["provider_requests"] == 0
        assert context["rights_manifest_created"] is False
        assert context["rights_qualification_performed"] is False
        assert all(item["read_only"] is True for item in context["assets"])
        for descriptor, item in zip(frozen.manifest.objects, context["assets"], strict=True):
            assert not Path(item["media_relative_path"]).is_absolute()
            resolved = (workspace.root / Path(item["media_relative_path"])).resolve()
            expected = frozen.root.joinpath(*descriptor.object_path.split("/")).resolve()
            assert resolved == expected
            assert item["media_sha256"] == descriptor.sha256
            assert item["media_size_bytes"] == descriptor.size_bytes


def test_existing_workspace_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)
    output_parent = tmp_path / "workspaces"
    output_parent.mkdir()
    workspace = write_human_review_console(frozen.root, output_parent, "EVIDENCE")
    marker = workspace.root / "operator-marker.txt"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(HumanReviewConsoleError, match="new directory"):
        write_human_review_console(frozen.root, output_parent, "EVIDENCE")

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_output_rejects_pack_overlap_git_and_unknown_workspace_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)

    with pytest.raises(HumanReviewConsoleError, match="must not overlap"):
        write_human_review_console(frozen.root, frozen.root, "EVIDENCE")

    git_output = tmp_path / "git-output"
    git_output.mkdir()
    (git_output / ".git").mkdir()
    with pytest.raises(HumanReviewConsoleError, match="outside Git"):
        write_human_review_console(frozen.root, git_output, "EVIDENCE")

    clean_output = tmp_path / "clean-output"
    clean_output.mkdir()
    with pytest.raises(HumanReviewConsoleError, match="unsupported"):
        write_human_review_console(
            frozen.root,
            clean_output,
            "REVIEWER_C",  # type: ignore[arg-type]
        )


def test_output_rejects_link_or_reparse_parent_when_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)
    target = tmp_path / "real-output"
    target.mkdir()
    linked = tmp_path / "linked-output"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory links are unavailable on this host")

    with pytest.raises(HumanReviewConsoleError, match="links|reparse"):
        write_human_review_console(frozen.root, linked, "EVIDENCE")


def test_reviewer_requires_verified_evidence_and_evidence_workspace_forbids_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)
    evidence_path, _evidence = _install_evidence(tmp_path, monkeypatch, frozen)
    output_parent = tmp_path / "workspaces"
    output_parent.mkdir()

    with pytest.raises(HumanReviewConsoleError, match="require an explicit evidence"):
        write_human_review_console(frozen.root, output_parent, "REVIEWER_A")
    with pytest.raises(HumanReviewConsoleError, match="must not bind"):
        write_human_review_console(
            frozen.root,
            output_parent,
            "EVIDENCE",
            evidence_path=evidence_path,
        )


def test_reviewer_rejects_evidence_that_does_not_rebuild_from_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)
    evidence_path, evidence = _install_evidence(tmp_path, monkeypatch, frozen)
    output_parent = tmp_path / "workspaces"
    output_parent.mkdir()
    drifted = _FakeRightsEvidenceBundle(
        bundle_id="real_asset_rights_evidence_v2_fedcba9876543210fedc",
        evidence_record_sha256=evidence.evidence_record_sha256,
        copyright_basis=evidence.copyright_basis,
        likeness_basis=evidence.likeness_basis,
        privacy_basis=evidence.privacy_basis,
        territory=evidence.territory,
        use_scope=evidence.use_scope,
        valid_until=evidence.valid_until,
        payload=evidence.payload,
    )
    monkeypatch.setattr(
        console_module,
        "build_real_asset_rights_evidence_bundle_v2",
        lambda **_kwargs: drifted,
    )

    with pytest.raises(HumanReviewConsoleError, match="drifted"):
        write_human_review_console(
            frozen.root,
            output_parent,
            "REVIEWER_A",
            evidence_path=evidence_path,
        )


def test_public_workspace_verifier_rejects_any_file_drift_or_extra_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    _install_verifier(monkeypatch, frozen)
    output_parent = tmp_path / "workspaces"
    output_parent.mkdir()
    workspace = write_human_review_console(frozen.root, output_parent, "EVIDENCE")

    assert (
        verify_human_review_console_workspace(
            frozen.root,
            workspace.root,
            "EVIDENCE",
        ).review_context_sha256
        == workspace.review_context_sha256
    )
    extra = workspace.root / "unexpected.txt"
    extra.write_text("not allowed", encoding="utf-8")
    with pytest.raises(HumanReviewConsoleError, match="exact five"):
        verify_human_review_console_workspace(frozen.root, workspace.root, "EVIDENCE")
    extra.unlink()
    (workspace.root / "app.js").write_text("drift", encoding="utf-8")
    with pytest.raises(HumanReviewConsoleError, match="file drifted"):
        verify_human_review_console_workspace(frozen.root, workspace.root, "EVIDENCE")


def test_pack_drift_during_prepare_removes_only_the_new_console(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _fake_frozen(tmp_path)
    output_parent = tmp_path / "workspaces"
    output_parent.mkdir()
    calls = 0

    def verify(_path: Path) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("pack drift")
        return frozen

    monkeypatch.setattr(console_module, "verify_real_asset_candidate_pack", verify)
    with pytest.raises(RuntimeError, match="pack drift"):
        write_human_review_console(frozen.root, output_parent, "EVIDENCE")
    assert not tuple(output_parent.iterdir())


def test_static_console_has_no_network_storage_or_automatic_human_decisions() -> None:
    asset_root = Path(console_module.__file__).with_name("human_review_console_assets")
    html = (asset_root / "index.html").read_text(encoding="utf-8")
    script = (asset_root / "app.js").read_text(encoding="utf-8")
    combined = html + "\n" + script

    assert "connect-src 'none'" in html
    assert "default-src 'none'" in html
    for forbidden in (
        "http://",
        "https://",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "localStorage",
        "sessionStorage",
        "serviceWorker",
    ):
        assert forbidden not in combined
    assert "new Date" not in script
    assert ".checked = true" not in script
    assert " checked" not in html
    assert " selected" not in html
    assert "readonly" in html
    assert "context.reviewer_role" in script
    assert "context.reviewer_role !== context.workspace_kind" in script
    assert "asset_findings" in script
    assert "pack_manifest_sha256" in script
    assert "review_context_sha256" in script
    assert "evidence_bundle_sha256" in script
    assert "context.evidence_bundle.bundle_id" in script
    assert "data-evidence-bundle-sha" in html
    assert "data-copyright-basis" in html
    assert "failed_gates" in script
    assert "exception-gate" in script
    assert script.count('radioOrNull("') >= 7
    assert "content_role_" in script
    assert "reviewed_at" not in script
    assert "review_record_sha256" not in script


def test_relative_media_paths_are_url_encoded_without_changing_traversal_segments() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable for the offline JavaScript encoding check")
    script_path = Path(console_module.__file__).with_name("human_review_console_assets") / "app.js"
    script = script_path.read_text(encoding="utf-8")
    match = re.search(
        r"  function encodeRelativeFilePath\(value\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert match is not None
    probe = (
        f"{match.group(0)}\n"
        "process.stdout.write(encodeRelativeFilePath("
        '"../冻结 #100%/有 空格/对白.wav"));'
    )
    completed = subprocess.run(
        [node, "-e", probe],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.stdout == (
        "../%E5%86%BB%E7%BB%93%20%23100%25/"
        "%E6%9C%89%20%E7%A9%BA%E6%A0%BC/"
        "%E5%AF%B9%E7%99%BD.wav"
    )
    assert "new URL(\n          encodeRelativeFilePath(asset.media_relative_path)" in script


def test_python_prepare_boundary_has_no_network_secret_or_execution_dependencies() -> None:
    source = Path(console_module.__file__).read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "os.getenv" not in source
    for forbidden in (
        "import httpx",
        "import requests",
        "import socket",
        "import urllib",
        "sdc.runtime",
        "sdc.worker",
        "sdc.provider",
        "sdc.persistence",
        "temporalio",
        "asyncpg",
        "sqlalchemy",
        "build_real_asset_rights_manifest",
        "qualify_real_asset_candidate_pack",
    ):
        assert forbidden not in source


def test_cli_requires_explicit_workspace_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = SimpleNamespace(
        index_path=tmp_path / "index.html",
        pack_id=PACK_ID,
        workspace_kind="REVIEWER_A",
        review_context_sha256=_digest("context"),
        evidence_bundle_id="real_asset_rights_evidence_v2_0123456789abcdef0123",
        evidence_bundle_sha256=_digest("evidence-bundle"),
    )
    observed: list[tuple[Path, Path, str, Path | None]] = []

    def write(
        pack_root: Path,
        output_parent: Path,
        workspace_kind: str,
        *,
        evidence_path: Path | None,
    ) -> Any:
        observed.append((pack_root, output_parent, workspace_kind, evidence_path))
        return expected

    monkeypatch.setattr(console_module, "write_human_review_console", write)
    assert (
        console_module._main(
            [
                "prepare",
                "--pack-root",
                str(tmp_path / "pack"),
                "--output-parent",
                str(tmp_path / "output"),
                "--workspace-kind",
                "REVIEWER_A",
                "--evidence",
                str(tmp_path / "evidence.json"),
            ]
        )
        == 0
    )
    assert observed == [
        (
            tmp_path / "pack",
            tmp_path / "output",
            "REVIEWER_A",
            tmp_path / "evidence.json",
        )
    ]
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace_kind"] == "REVIEWER_A"
    assert payload["current_gate"] == "HUMAN_GATE"
    assert payload["provider_state"] == "NOT_AUTHORIZED"
    assert payload["execution_authorized"] is False
    assert payload["posts_allowed"] == payload["provider_requests"] == 0
    assert payload["review_context_sha256"] == expected.review_context_sha256
    assert payload["evidence_bundle_id"] == expected.evidence_bundle_id
    assert payload["evidence_bundle_sha256"] == expected.evidence_bundle_sha256
