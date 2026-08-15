import hashlib
import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Self, cast

import pytest
from pydantic import ValidationError

import sdc.canary_authorize as canary_authorize
import sdc.fresh_canary_plan as fresh_canary_plan
import sdc.fresh_evidence as fresh_evidence
from sdc.canary import LiveGateError, build_canary_plan, contract_sha256
from sdc.contracts import (
    CanaryPlan,
    EvidenceBoundCanaryPlan,
    EvidenceBundle,
    PricingInputMode,
    ProviderCapabilitySnapshot,
    ProviderFailureClass,
    ProviderPricingSnapshot,
    ProviderRequest,
    SnapshotStatus,
)
from sdc.fresh_canary_plan import (
    _build_evidence_bound_canary_plan_at,
    build_evidence_bound_canary_plan,
)
from sdc.fresh_evidence import build_fresh_canary_evidence_bundle
from sdc.fresh_evidence_registry import ReviewedFreshEvidence
from sdc.provider import request_fingerprint

CAPTURED_AT = datetime(2026, 8, 15, 1, tzinfo=UTC)
PLANNED_AT = CAPTURED_AT + timedelta(hours=1)
VALID_UNTIL = CAPTURED_AT + timedelta(hours=12)
CAPABILITY_PDF = b"%PDF-1.7\nplanner capability evidence\n%%EOF\n"
PRICING_PDF = b"%PDF-1.7\nplanner pricing evidence\n%%EOF\n"


@dataclass(frozen=True)
class PreparedEvidence:
    root: Path
    bundle: EvidenceBundle
    capability: ProviderCapabilitySnapshot
    pricing: ProviderPricingSnapshot
    data_by_path: Mapping[str, bytes]


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> Self:
        if tz is None:
            return cast(Self, PLANNED_AT.replace(tzinfo=None))
        return cast(Self, PLANNED_AT)


class ExpiringDateTime(datetime):
    calls: ClassVar[int] = 0

    @classmethod
    def now(cls, tz: object = None) -> Self:
        cls.calls += 1
        value = PLANNED_AT if cls.calls == 1 else VALID_UNTIL + timedelta(microseconds=1)
        if tz is None:
            value = value.replace(tzinfo=None)
        return cast(Self, value)


def _request() -> ProviderRequest:
    draft = ProviderRequest(
        run_id="fresh-canary-run",
        job_id="fresh-canary-job",
        attempt=1,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        prompt="A paper lantern glows against a plain midnight background.",
        duration_ms=4000,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        input_materials=(),
        request_fingerprint="0" * 64,
    )
    return draft.model_copy(update={"request_fingerprint": request_fingerprint(draft)})


def _capability(*, fps: int = 24) -> ProviderCapabilitySnapshot:
    return ProviderCapabilitySnapshot(
        snapshot_revision="2026-08-15.fresh-plan-1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        aspect_ratios=("9:16",),
        resolutions=("1080p",),
        fps=fps,
        min_duration_ms=4000,
        max_duration_ms=15000,
        source_url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=CAPTURED_AT,
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(CAPABILITY_PDF).hexdigest(),
    )


def _pricing() -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        snapshot_revision="2026-08-15.fresh-plan-1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        resolution="1080p",
        input_mode=PricingInputMode.WITHOUT_VIDEO,
        billing_unit="provider-token",
        unit_price_cny=Decimal("0.000001"),
        worst_case_units=Decimal("196425"),
        worst_case_cost_cny=Decimal("0.196425"),
        source_url="https://docs.volcengine.com/docs/82379/1544106?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=CAPTURED_AT + timedelta(minutes=5),
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(PRICING_PDF).hexdigest(),
    )


def _prepare_evidence(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fps: int = 24,
) -> PreparedEvidence:
    capability = _capability(fps=fps)
    pricing = _pricing()
    bundle, data_by_path = build_fresh_canary_evidence_bundle(
        capability_snapshot_bytes=capability.model_dump_json(indent=2).encode(),
        capability_evidence_bytes=CAPABILITY_PDF,
        pricing_snapshot_bytes=pricing.model_dump_json(indent=2).encode(),
        pricing_evidence_bytes=PRICING_PDF,
    )
    object_root = root / "objects"
    for member in bundle.content.members:
        target = object_root / member.object_sha256[:2] / member.object_sha256
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data_by_path[member.logical_path])
    manifest = root / "bundles" / f"{bundle.bundle_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    anchor = ReviewedFreshEvidence(
        bundle_id=bundle.bundle_id,
        logical_tree_sha256=bundle.content.resolved_logical_tree_sha256,
        capability_snapshot_sha256=contract_sha256(capability),
        pricing_snapshot_sha256=contract_sha256(pricing),
        reviewed_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
    )
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (anchor,))
    return PreparedEvidence(root, bundle, capability, pricing, data_by_path)


def test_plan_binds_reviewed_bundle_and_grants_no_live_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path, monkeypatch)

    plan = _build_evidence_bound_canary_plan_at(
        evidence_root=prepared.root,
        reviewed_bundle_id=prepared.bundle.bundle_id,
        request=_request(),
        cost_ceiling_cny=Decimal("0.20"),
        planned_at=PLANNED_AT,
    )

    assert plan.document_type == "sdc.evidence-bound-canary-plan"
    assert plan.evidence_bundle_id == prepared.bundle.bundle_id
    assert plan.evidence_logical_tree_sha256 == prepared.bundle.content.resolved_logical_tree_sha256
    assert plan.evidence_valid_until == VALID_UNTIL
    assert plan.state == "NOT_AUTHORIZED"
    assert plan.posts_allowed == 0
    assert plan.attempt == 1
    assert plan.worst_case_cost_cny == Decimal("0.196425")
    assert plan.approved_cost_ceiling_cny == Decimal("0.20")
    assert {"authorization_id", "nonce", "max_posts"}.isdisjoint(plan.model_fields_set)


def test_public_and_cli_planning_are_zero_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)

    def forbidden_network(*_: object, **__: object) -> None:
        raise AssertionError("offline FRESH planning must not touch the network")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_network)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)

    direct = build_evidence_bound_canary_plan(
        evidence_root=prepared.root,
        reviewed_bundle_id=prepared.bundle.bundle_id,
        request=_request(),
        cost_ceiling_cny=Decimal("0.20"),
    )
    assert direct.planned_at == PLANNED_AT

    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(indent=2), encoding="utf-8")
    output = tmp_path / "plan.json"
    frozen_request = tmp_path / "frozen-request.json"
    assert (
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(output),
                "--frozen-request-output",
                str(frozen_request),
            ]
        )
        == 0
    )
    parsed = EvidenceBoundCanaryPlan.model_validate_json(output.read_text(encoding="utf-8"))
    assert parsed == direct
    assert (
        ProviderRequest.model_validate_json(frozen_request.read_text(encoding="utf-8"))
        == _request()
    )


def test_legacy_and_evidence_bound_plan_types_are_mutually_incompatible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path, monkeypatch)
    request = _request()
    new_plan = _build_evidence_bound_canary_plan_at(
        evidence_root=prepared.root,
        reviewed_bundle_id=prepared.bundle.bundle_id,
        request=request,
        cost_ceiling_cny=Decimal("0.20"),
        planned_at=PLANNED_AT,
    )
    old_plan = build_canary_plan(
        prepared.capability,
        prepared.pricing,
        request,
        Decimal("0.20"),
        now=PLANNED_AT,
    )

    with pytest.raises(ValidationError):
        CanaryPlan.model_validate(new_plan.model_dump(mode="python"))
    with pytest.raises(ValidationError):
        EvidenceBoundCanaryPlan.model_validate(old_plan.model_dump(mode="python"))
    with pytest.raises(ValidationError):
        EvidenceBoundCanaryPlan.model_validate(
            {**new_plan.model_dump(mode="python"), "state": "AUTHORIZED"}
        )
    with pytest.raises(ValidationError):
        EvidenceBoundCanaryPlan.model_validate(
            {**new_plan.model_dump(mode="python"), "posts_allowed": 1}
        )

    plan_path = tmp_path / "evidence-bound-plan.json"
    plan_path.write_text(new_plan.model_dump_json(), encoding="utf-8")
    authorization_path = tmp_path / "must-not-exist.json"

    with pytest.raises(LiveGateError, match="authorization generation is disabled") as caught:
        canary_authorize.main(
            [
                "--plan",
                str(plan_path),
                "--execution",
                str(tmp_path / "unused-execution.json"),
                "--authorization-id",
                "forbidden",
                "--max-cost-cny",
                "0.20",
                "--expires-at",
                VALID_UNTIL.isoformat(),
                "--nonce",
                "0" * 64,
                "--output",
                str(authorization_path),
            ]
        )
    assert caught.value.failure_class is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    assert not authorization_path.exists()


def test_reviewed_bundle_still_fails_closed_on_capability_profile_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path, monkeypatch, fps=25)

    with pytest.raises(LiveGateError, match="24 fps"):
        _build_evidence_bound_canary_plan_at(
            evidence_root=prepared.root,
            reviewed_bundle_id=prepared.bundle.bundle_id,
            request=_request(),
            cost_ceiling_cny=Decimal("0.20"),
            planned_at=PLANNED_AT,
        )


def test_cli_checks_registry_before_request_or_manifest_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_input_read(*_: object, **__: object) -> None:
        raise AssertionError("untrusted evidence must stop before planner input reads")

    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", ())
    monkeypatch.setattr(fresh_canary_plan, "_load_contract", forbidden_input_read)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    with pytest.raises(fresh_evidence.FreshEvidenceError, match="Git-reviewed"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(tmp_path / "missing-evidence"),
                "--reviewed-evidence-bundle-id",
                "f" * 64,
                "--request",
                str(tmp_path / "missing-request.json"),
                "--max-cost-cny",
                "0.20",
            ]
        )


@pytest.mark.skipif(os.name != "nt", reason="UNC and device path semantics are Windows-only")
@pytest.mark.parametrize(
    "path",
    [
        Path(r"\\server\share\request.json"),
        Path(r"\\?\C:\evidence\request.json"),
    ],
)
def test_planner_rejects_nonlocal_windows_input_paths_before_open(path: Path) -> None:
    with pytest.raises(LiveGateError, match="local filesystem path"):
        fresh_canary_plan._load_contract(path, ProviderRequest)


def test_cli_rejects_duplicate_request_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    raw = _request().model_dump_json()
    duplicated = raw.replace(
        '"run_id":"fresh-canary-run"',
        '"run_id":"fresh-canary-run","run_id":"fresh-canary-run"',
        1,
    )
    assert duplicated != raw
    request_path = tmp_path / "request.json"
    request_path.write_text(duplicated, encoding="utf-8")

    with pytest.raises(LiveGateError, match="duplicate JSON key"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
            ]
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("invalid-utf8", "invalid planner JSON input"),
        ("nan", "non-finite JSON number"),
        ("oversize", "byte limit"),
    ],
)
def test_cli_rejects_invalid_utf8_nan_and_oversize_request_json(
    kind: str,
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    invalid = {
        "invalid-utf8": b"\xff",
        "nan": b'{"run_id":NaN}',
        "oversize": b" " * (1024 * 1024 + 1),
    }[kind]
    request_path = tmp_path / "request.json"
    request_path.write_bytes(invalid)

    with pytest.raises(LiveGateError, match=message):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
            ]
        )


def test_cli_preflights_all_story_outputs_before_writing_any_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    story = tmp_path / "story.json"
    story.write_text(
        '{"title":"canary","beats":[{"text":"one safe canary","duration_ms":4000}]}',
        encoding="utf-8",
    )
    plan_output = tmp_path / "plan.json"
    request_output = tmp_path / "frozen-request.json"
    execution_output = tmp_path / "execution.json"
    execution_output.write_bytes(b"preexisting sentinel")

    with pytest.raises(LiveGateError, match="new file"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--story",
                str(story),
                "--run-id",
                "fresh-story-run",
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(request_output),
                "--execution-output",
                str(execution_output),
            ]
        )
    assert execution_output.read_bytes() == b"preexisting sentinel"
    assert not plan_output.exists()
    assert not request_output.exists()


def test_cli_rejects_casefolded_output_aliases_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(), encoding="utf-8")
    plan_output = tmp_path / "Result.json"
    request_output = tmp_path / "result.JSON"

    with pytest.raises(LiveGateError, match="distinct files"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(request_output),
            ]
        )
    assert not plan_output.exists()
    assert not request_output.exists()


@pytest.mark.parametrize(
    "invalid_name",
    ["CON", "bad?.json", "file.json:stream", "bad\x01.json"],
    ids=["reserved-device", "wildcard", "alternate-stream", "control-character"],
)
def test_cli_preflights_nonportable_second_output_before_writing_first(
    invalid_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(), encoding="utf-8")
    plan_output = tmp_path / "plan.json"
    invalid_second_output = tmp_path / invalid_name
    entries_before = {path.name for path in tmp_path.iterdir()}

    with pytest.raises(LiveGateError, match="non-portable path component"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(invalid_second_output),
            ]
        )
    assert not plan_output.exists()
    # Win32 reports reserved devices such as CON as existing even without a directory entry.
    assert {path.name for path in tmp_path.iterdir()} == entries_before
    if invalid_name != "CON":
        assert not invalid_second_output.exists()


def test_cli_rejects_parent_segment_output_alias_without_half_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(), encoding="utf-8")
    plan_output = tmp_path / "existing.json"
    alias_output = tmp_path / "missing" / ".." / "existing.json"

    with pytest.raises(LiveGateError, match="non-portable path component"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(alias_output),
            ]
        )
    assert not plan_output.exists()
    assert not alias_output.exists()


@pytest.mark.parametrize(
    "plan_is_parent",
    [True, False],
    ids=["parent-then-child", "child-then-parent"],
)
def test_cli_rejects_output_ancestor_conflicts_without_half_write(
    plan_is_parent: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    monkeypatch.setattr(fresh_canary_plan, "datetime", FrozenDateTime)
    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(), encoding="utf-8")
    parent_output = tmp_path / "a"
    child_output = parent_output / "b"
    plan_output, request_output = (
        (parent_output, child_output)
        if plan_is_parent
        else (child_output, parent_output)
    )
    snapshot_before = {
        path.relative_to(tmp_path).as_posix(): (
            None if path.is_dir() else path.read_bytes()
        )
        for path in tmp_path.rglob("*")
    }

    with pytest.raises(LiveGateError):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(request_output),
            ]
        )
    snapshot_after = {
        path.relative_to(tmp_path).as_posix(): (
            None if path.is_dir() else path.read_bytes()
        )
        for path in tmp_path.rglob("*")
    }
    assert snapshot_after == snapshot_before
    assert not parent_output.exists()
    assert not child_output.exists()


def test_cli_rechecks_expiry_at_completion_before_writing_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_evidence(tmp_path / "evidence", monkeypatch)
    ExpiringDateTime.calls = 0
    monkeypatch.setattr(fresh_canary_plan, "datetime", ExpiringDateTime)
    request_path = tmp_path / "request.json"
    request_path.write_text(_request().model_dump_json(), encoding="utf-8")
    plan_output = tmp_path / "plan.json"
    request_output = tmp_path / "frozen-request.json"

    with pytest.raises(LiveGateError, match="expired before planning completed"):
        fresh_canary_plan.main(
            [
                "--fresh-evidence-root",
                str(prepared.root),
                "--reviewed-evidence-bundle-id",
                prepared.bundle.bundle_id,
                "--request",
                str(request_path),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(plan_output),
                "--frozen-request-output",
                str(request_output),
            ]
        )
    assert ExpiringDateTime.calls == 2
    assert not plan_output.exists()
    assert not request_output.exists()
