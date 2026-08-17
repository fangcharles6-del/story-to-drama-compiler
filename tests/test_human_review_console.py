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
            path.suffix.casefold() in {".png", ".wav"} for path in workspace.root.iterdir()
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
            assert (
                projection["bundle_sha256"]
                == hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            )
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


def test_evidence_guide_locks_sources_counterexamples_and_blank_inputs() -> None:
    asset_root = Path(console_module.__file__).with_name("human_review_console_assets")
    html = (asset_root / "index.html").read_text(encoding="utf-8")
    script = (asset_root / "app.js").read_text(encoding="utf-8")
    expected_guidance = {
        "evidence-record-sha": (
            "evidence-record-sha-guidance",
            "负责人：保管 Pack 级权利证据记录的权利负责人。"
            "取得：从其实际保存的独立证据记录文件计算。"
            "不能替代：素材文件、来源记录、技术检查、空模板或口头说明。"
            "格式示例：a3…7f（共 64 位小写十六进制字符）。",
        ),
        "copyright-basis": (
            "copyright-basis-guidance",
            "负责人：创作者、权利人、许可管理员或项目权利负责人。"
            "取得：查看实际许可条款、创作记录、权利转让或授权文件。"
            "输入：必须单行；若粘贴后提示规范化错误，请用离线文本工具转换为 Unicode NFC。"
            "不能替代：技术合格结果、文件摘要或“由 AI 生成”说明。"
            "格式示例：[证据名称] | [条款/章节] | [权利主体] | [与本 Pack 的对应关系]。",
        ),
        "likeness-basis": (
            "likeness-basis-guidance",
            "负责人：形象/声音权利人、素材创建或配音负责人及项目权利负责人。"
            "取得：查看实际肖像/声音授权、角色创作记录及与具体素材的对应说明。"
            "输入：必须单行；若粘贴后提示规范化错误，请用离线文本工具转换为 Unicode NFC。"
            "不能替代：“看起来是虚构的”、个人印象或音画技术检查。"
            "格式示例：[证据名称] | [对象/类别] | [授权范围] | [对应素材]。",
        ),
        "privacy-basis": (
            "privacy-basis-guidance",
            "负责人：隐私/合规负责人、相关信息主体或授权记录保管人。"
            "取得：查看实际同意记录、隐私告知、个人信息清单及适用的处理依据。"
            "输入：必须单行；若粘贴后提示规范化错误，请用离线文本工具转换为 Unicode NFC。"
            "不能替代：“未上传网络”、文件无元数据或素材技术合格。"
            "格式示例：[证据名称] | [信息类别] | [处理目的] | [适用范围]。",
        ),
        "territory": (
            "territory-guidance",
            "负责人：许可方、权利人或负责审查的权利/法务人员。"
            "取得：查看许可协议或权利人授权中的地理范围条款。"
            "不能替代：项目所在地、用户 IP、语言或自行推定的“全球”。"
            "格式示例：[国家/地区名称；多项以逗号分隔]。",
        ),
        "valid-until": (
            "valid-until-guidance",
            "负责人：许可方、权利管理员或负责审查的权利/法务人员。"
            "取得：查看许可、同意或授权文件的生效期和终止条款。"
            "不能替代：文件修改时间、任务日期或自定期限。"
            "格式示例：YYYY-MM-DDTHH:MM:SSZ；仅当实际证据明确永久有效时使用 "
            "PERPETUAL。",
        ),
        "use-scope": (
            "use-scope-guidance",
            "负责人：许可方、权利人或负责审查的权利/法务人员。"
            "取得：查看许可中的允许用途、媒介、渠道、商业性及改编限制条款。"
            "输入：必须单行；若粘贴后提示规范化错误，请用离线文本工具转换为 Unicode NFC。"
            "不能替代：内部使用计划、技术可用性或期望的发布方式。"
            "格式示例：[用途] | [媒介/渠道] | [商业性] | [改编限制]。",
        ),
    }

    assert len(expected_guidance) == 7
    for control_id, (guidance_id, expected_text) in expected_guidance.items():
        control_match = re.search(
            rf"<(?P<tag>input|textarea)\b(?P<attributes>[^>]*\bid=\"{control_id}\"[^>]*)>",
            html,
        )
        assert control_match is not None
        attributes = control_match.group("attributes")
        assert "required" in attributes
        assert 'aria-invalid="true"' in attributes
        assert f'aria-describedby="{guidance_id}"' in attributes
        assert not re.search(r"\bvalue\s*=", attributes)
        if control_match.group("tag") == "textarea":
            textarea_match = re.search(
                rf'<textarea\b[^>]*\bid="{control_id}"[^>]*>(?P<body>.*?)</textarea>',
                html,
                flags=re.DOTALL,
            )
            assert textarea_match is not None
            assert textarea_match.group("body") == ""

        guidance_match = re.search(
            rf'<small id="{guidance_id}" class="field-guidance">(?P<body>.*?)</small>',
            html,
            flags=re.DOTALL,
        )
        assert guidance_match is not None
        guidance_text = re.sub(r"<[^>]+>", "", guidance_match.group("body"))
        guidance_text = re.sub(r"\s+", " ", guidance_text).strip()
        assert guidance_text == expected_text

    for factual_field_id in (
        "copyright-basis",
        "likeness-basis",
        "privacy-basis",
        "territory",
        "use-scope",
        "valid-until",
    ):
        assert not re.search(
            rf'byId\("{factual_field_id}"\)\.value\s*=',
            script,
        )


def test_evidence_readiness_has_two_mechanical_states_without_authority() -> None:
    asset_root = Path(console_module.__file__).with_name("human_review_console_assets")
    html = (asset_root / "index.html").read_text(encoding="utf-8")
    script = (asset_root / "app.js").read_text(encoding="utf-8")

    for element_id in (
        "evidence-readiness",
        "evidence-readiness-status",
        "evidence-readiness-missing",
    ):
        assert html.count(f'id="{element_id}"') == 1
    readiness_tag = re.search(
        r'<aside id="evidence-readiness"(?P<attributes>[^>]*)>',
        html,
    )
    assert readiness_tag is not None
    assert 'data-state="NEEDS_EVIDENCE"' in readiness_tag.group("attributes")
    initial_status = re.search(
        r'<p id="evidence-readiness-status"[^>]*>(?P<text>[^<]+)</p>',
        html,
    )
    assert initial_status is not None
    assert initial_status.group("text") == "缺少依据，停止"
    evidence_download = re.search(
        r'<button id="download-evidence"(?P<attributes>[^>]*)>',
        html,
    )
    assert evidence_download is not None
    assert "disabled" in evidence_download.group("attributes")
    assert 'aria-describedby="evidence-readiness-status"' in evidence_download.group("attributes")
    assert "形式完整不等于批准" in html
    assert "本页不能确认摘要对应记录仍可用" in html
    assert "也不判断权利是否过期" in html
    assert 'id="evidence-readiness-missing" aria-label="Evidence 准备度说明"' in html
    readiness_html = re.search(
        r'<aside id="evidence-readiness".*?</aside>',
        html,
        flags=re.DOTALL,
    )
    assert readiness_html is not None
    assert readiness_html.group(0).count('aria-live="polite"') == 1
    assert "APPROVED" not in readiness_html.group(0)
    assert "qualification" not in readiness_html.group(0).casefold()

    readiness_match = re.search(
        r"  function renderEvidenceReadiness\(\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert readiness_match is not None
    readiness_source = readiness_match.group(0)
    assert re.findall(r'readiness\.dataset\.state = "([A-Z_]+)"', readiness_source) == [
        "FORM_COMPLETE_DRAFT_ONLY",
        "NEEDS_EVIDENCE",
    ]
    assert re.findall(r'status\.textContent = "([^"]+)"', readiness_source) == [
        "字段形式完整，可导出未受信草稿",
        "缺少依据，停止",
    ]
    assert "仅通过本页机械格式检查" in readiness_source
    assert "请真人另行确认记录当前可用、期限未过期" in readiness_source
    assert "APPROVED" not in readiness_source
    assert "qualification" not in readiness_source.casefold()
    assert "execution_authorized" not in readiness_source
    assert "download.disabled = false" in readiness_source
    assert "download.disabled = true" in readiness_source
    assert 'setAttribute("aria-invalid", String(!check.valid))' in readiness_source

    input_listener_match = re.search(
        r"\[\s*(?P<ids>(?:\s*\"[^\"]+\",?)+)\s*\]\.forEach\("
        r"\(id\) => byId\(id\)\.addEventListener\(\"input\", "
        r"handleEvidenceInput\)\)",
        script,
        flags=re.DOTALL,
    )
    assert input_listener_match is not None
    assert re.findall(r"\"([^\"]+)\"", input_listener_match.group("ids")) == [
        "evidence-record-sha",
        "copyright-basis",
        "likeness-basis",
        "privacy-basis",
        "territory",
        "use-scope",
        "valid-until",
    ]
    assert re.search(
        r"const hashing = hashSelectedFile\(.*?\);.*?void hashing\.then\(\(\) => \{.*?"
        r"evidenceHashPending = false;.*?"
        r"renderEvidenceReadiness\(\);.*?\}\)",
        script,
        flags=re.DOTALL,
    )

    download_handler = re.search(
        r'byId\("download-evidence"\)\.addEventListener\("click", \(\) => \{'
        r"(?P<body>.*?)^  \}\);",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert download_handler is not None
    handler_body = download_handler.group("body")
    assert "if (warnings.length !== 0)" in handler_body
    assert "缺少依据，未导出草稿" in handler_body
    assert handler_body.index("if (warnings.length !== 0)") < handler_body.index(
        "downloadDraft(draft"
    )


def test_evidence_readiness_does_not_change_exported_draft_shape() -> None:
    script_path = Path(console_module.__file__).with_name("human_review_console_assets") / "app.js"
    script = script_path.read_text(encoding="utf-8")
    draft_match = re.search(
        r"  function buildEvidenceDraft\(\) \{\s*return \{(?P<body>.*?)^    \};\s*^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert draft_match is not None
    assert re.findall(r"^      ([a-z][a-z0-9_]*):", draft_match.group("body"), re.MULTILINE) == [
        "schema_version",
        "document_type",
        "profile",
        "review_context_sha256",
        "pack_id",
        "pack_manifest_sha256",
        "evidence_record_sha256",
        "asset_bindings",
        "copyright_basis",
        "likeness_basis",
        "privacy_basis",
        "territory",
        "use_scope",
        "valid_until",
        "status",
        "current_gate",
        "provider_state",
        "execution_authorized",
        "posts_allowed",
        "provider_requests",
    ]

    readiness_match = re.search(
        r"  function renderEvidenceReadiness\(\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert readiness_match is not None
    readiness_source = readiness_match.group(0)
    assert "const draft = buildEvidenceDraft();" in readiness_source
    assert "const checks = evidenceFieldChecks(draft);" in readiness_source
    assert "downloadDraft" not in readiness_source
    assert not re.search(r"\bdraft(?:\.|\[)[^\n=]*=", readiness_source)


def test_evidence_readiness_matches_finalizer_text_and_utc_syntax() -> None:
    script_path = Path(console_module.__file__).with_name("human_review_console_assets") / "app.js"
    script = script_path.read_text(encoding="utf-8")
    portable_match = re.search(
        r"  function isPortableEvidenceText\(value, maximum\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    utc_match = re.search(
        r"  function isCanonicalUtcSeconds\(value\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    checks_match = re.search(
        r"  function evidenceFieldChecks\(draft\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert portable_match is not None
    assert utc_match is not None
    assert checks_match is not None
    checks_source = checks_match.group(0)
    assert checks_source.count("isPortableEvidenceText(") == 5
    assert "isCanonicalUtcSeconds(draft.valid_until)" in checks_source
    assert "copyright_basis 尚未填写" not in checks_source
    assert "著作权依据须为" in checks_source
    assert "有效期须为" in checks_source

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable for the offline readiness syntax check")
    probe = "\n".join(
        (
            "const UTC_SECONDS_PATTERN = "
            "/^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
            "[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/;",
            portable_match.group(0),
            utc_match.group(0),
            "process.stdout.write(JSON.stringify([",
            '  isPortableEvidenceText("实际许可依据", 1000),',
            '  isPortableEvidenceText("e\\u0301", 1000),',
            '  isPortableEvidenceText("第一行\\n第二行", 1000),',
            '  isCanonicalUtcSeconds("2028-02-29T23:59:59Z"),',
            '  isCanonicalUtcSeconds("2026-02-31T12:00:00Z"),',
            '  isCanonicalUtcSeconds("0000-01-01T00:00:00Z"),',
            '  isCanonicalUtcSeconds("2026-01-01T24:00:00Z")',
            "]));",
        )
    )
    completed = subprocess.run(
        [node, "-e", probe],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(completed.stdout) == [True, False, False, True, False, False, False]


def test_evidence_edits_invalidate_export_status_and_stale_file_hashes() -> None:
    script_path = Path(console_module.__file__).with_name("human_review_console_assets") / "app.js"
    script = script_path.read_text(encoding="utf-8")
    assert "let evidenceDraftExported = false;" in script
    assert "let evidenceDraftDirtySinceExport = false;" in script
    assert "let evidenceHashPending = false;" in script
    assert "先前下载的草稿不再对应当前表单" in script
    assert "evidenceDraftExported = true;" in script
    assert "evidenceDraftDirtySinceExport = false;" in script
    mark_match = re.search(
        r"  function markEvidenceDraftChanged\(\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert mark_match is not None
    assert "evidenceDraftDirtySinceExport = true;" in mark_match.group(0)
    assert "if (!evidenceDraftDirtySinceExport)" in mark_match.group(0)
    assert "当前表单尚未下载" not in mark_match.group(0)

    warnings_match = re.search(
        r"  function evidenceWarnings\(draft\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert warnings_match is not None
    assert "if (evidenceHashPending)" in warnings_match.group(0)
    assert "证据记录摘要仍在本机计算中" in warnings_match.group(0)
    assert "takeOverHashWithManualInput(" in script
    assert 'byId("evidence-record-file")' in script
    assert 'byId("reviewer-ref-sha").addEventListener("input"' in script
    assert 'byId("reviewer-ref-file")' in script
    assert "已清除文件选择；使用当前手工输入的摘要" in script

    hash_match = re.search(
        r"  async function hashSelectedFile\(.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert hash_match is not None
    hash_source = hash_match.group(0)
    assert hash_source.count('targetInput.value = "";') == 2
    assert hash_source.count("fileInput.files[0] !== file") == 2
    assert hash_source.count("hashGenerations.get(targetInput) !== generation") == 2
    assert "正在本机内存中计算" in hash_source

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable for the offline hash-race check")
    hex_match = re.search(
        r"  function hexDigest\(buffer\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    invalidate_match = re.search(
        r"  function invalidatePendingHash\(targetInput\) \{.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    takeover_match = re.search(
        r"  function takeOverHashWithManualInput\(.*?^  \}",
        script,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert hex_match is not None
    assert invalidate_match is not None
    assert takeover_match is not None
    probe = "\n".join(
        (
            "const hashGenerations = new WeakMap();",
            "let resolveDigest;",
            "const crypto = {subtle: {digest: () => new Promise((resolve) => {",
            "  resolveDigest = resolve;",
            "})}};",
            hex_match.group(0),
            invalidate_match.group(0),
            takeover_match.group(0),
            hash_match.group(0),
            "void (async () => {",
            '  const file = {name: "A.bin", arrayBuffer: async () => new ArrayBuffer(1)};',
            '  const fileInput = {files: [file], value: "A.bin"};',
            '  const targetInput = {value: ""};',
            '  const statusNode = {textContent: "", className: ""};',
            "  const pending = hashSelectedFile(fileInput, targetInput, statusNode);",
            '  while (typeof resolveDigest !== "function") { await Promise.resolve(); }',
            '  targetInput.value = "b".repeat(64);',
            "  takeOverHashWithManualInput(fileInput, targetInput, statusNode);",
            "  resolveDigest(new Uint8Array([1]).buffer);",
            "  const updated = await pending;",
            "  crypto.subtle.digest = async () => new Uint8Array([2]).buffer;",
            '  const file2 = {name: "C.bin", arrayBuffer: async () => new ArrayBuffer(1)};',
            '  const fileInput2 = {files: [file2], value: "C.bin"};',
            '  const targetInput2 = {value: ""};',
            '  const statusNode2 = {textContent: "", className: ""};',
            "  const completed = await hashSelectedFile(fileInput2, targetInput2, statusNode2);",
            '  targetInput2.value = "c".repeat(64);',
            "  takeOverHashWithManualInput(fileInput2, targetInput2, statusNode2);",
            "  process.stdout.write(JSON.stringify({",
            "    pending: {updated, value: targetInput.value, "
            "file: fileInput.value, status: statusNode.textContent},",
            "    completed: {updated: completed, value: targetInput2.value, "
            "file: fileInput2.value, status: statusNode2.textContent}",
            "  }));",
            "})();",
        )
    )
    completed = subprocess.run(
        [node, "-e", probe],
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=10,
    )
    assert json.loads(completed.stdout) == {
        "pending": {
            "updated": False,
            "value": "b" * 64,
            "file": "",
            "status": "已清除文件选择；使用当前手工输入的摘要。",
        },
        "completed": {
            "updated": True,
            "value": "c" * 64,
            "file": "",
            "status": "已清除文件选择；使用当前手工输入的摘要。",
        },
    }


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
        "../%E5%86%BB%E7%BB%93%20%23100%25/%E6%9C%89%20%E7%A9%BA%E6%A0%BC/%E5%AF%B9%E7%99%BD.wav"
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
