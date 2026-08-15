"""Zero-network Canary planning from one Git-reviewed FRESH EvidenceBundle."""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unicodedata import normalize

from pydantic import BaseModel, ValidationError

from sdc.canary import LiveGateError, build_canary_plan, freeze_canary_execution
from sdc.compiler import compile_story
from sdc.contracts import (
    CanaryExecution,
    EvidenceBoundCanaryPlan,
    ProviderFailureClass,
    ProviderRequest,
    StoryInput,
)
from sdc.fresh_evidence import (
    load_trusted_fresh_canary_evidence,
    require_trusted_fresh_evidence_anchor,
)
from sdc.provider import request_fingerprint

_MAX_INPUT_JSON_BYTES = 1024 * 1024
_WINDOWS_RESERVED_OUTPUT_STEMS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)


def _require_portable_path_component(part: str, *, kind: str) -> None:
    if (
        part == ".."
        or part.rstrip(" .") != part
        or normalize("NFC", part) != part
        or len(part) > 255
        or any(character in '<>:"|?*' for character in part)
        or any(ord(character) < 32 or ord(character) == 127 for character in part)
        or part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_OUTPUT_STEMS
    ):
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION,
            f"planner {kind} contains a non-portable path component",
        )


def _duplicate_key_rejected(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LiveGateError(ProviderFailureClass.CONFIGURATION, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite_rejected(value: str) -> None:
    raise LiveGateError(
        ProviderFailureClass.CONFIGURATION,
        f"non-finite JSON number is forbidden: {value}",
    )


def _load_contract[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    try:
        absolute = path.absolute()
        if str(absolute).startswith(("\\\\", "//")):
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner JSON input must use a local filesystem path",
            )
        cursor = Path(absolute.anchor)
        for part in absolute.parts:
            if part == absolute.anchor:
                continue
            _require_portable_path_component(part, kind="JSON input")
            cursor /= part
            if not os.path.lexists(cursor):
                break
            details = cursor.lstat()
            is_junction = getattr(cursor, "is_junction", lambda: False)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            if (
                stat.S_ISLNK(details.st_mode)
                or bool(is_junction())
                or bool(getattr(details, "st_file_attributes", 0) & reparse_flag)
            ):
                raise LiveGateError(
                    ProviderFailureClass.CONFIGURATION,
                    "planner JSON input must not use links or junctions",
                )
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise LiveGateError(
                    ProviderFailureClass.CONFIGURATION,
                    "planner JSON input must be a regular file",
                )
            raw = handle.read(_MAX_INPUT_JSON_BYTES + 1)
        if len(raw) > _MAX_INPUT_JSON_BYTES:
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner JSON input exceeds the byte limit",
            )
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_key_rejected,
            parse_constant=_nonfinite_rejected,
        )
        if not isinstance(payload, dict):
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner JSON input must contain one object",
            )
        return model.model_validate(payload)
    except LiveGateError:
        raise
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION, "invalid planner JSON input"
        ) from exc


def _build_evidence_bound_canary_plan_at(
    *,
    evidence_root: Path,
    reviewed_bundle_id: str,
    request: ProviderRequest,
    cost_ceiling_cny: Decimal,
    planned_at: datetime,
) -> EvidenceBoundCanaryPlan:
    evidence = load_trusted_fresh_canary_evidence(
        manifest_path=evidence_root / "bundles" / f"{reviewed_bundle_id}.json",
        object_root=evidence_root / "objects",
        expected_bundle_id=reviewed_bundle_id,
        at=planned_at,
    )
    semantic_plan = build_canary_plan(
        evidence.capability,
        evidence.pricing,
        request,
        cost_ceiling_cny,
        now=planned_at,
    )
    return EvidenceBoundCanaryPlan(
        evidence_bundle_id=evidence.bundle_id,
        evidence_logical_tree_sha256=evidence.logical_tree_sha256,
        evidence_valid_until=evidence.valid_until,
        run_id=semantic_plan.run_id,
        job_id=semantic_plan.job_id,
        request_fingerprint=semantic_plan.request_fingerprint,
        capability_snapshot_sha256=semantic_plan.capability_snapshot_sha256,
        pricing_snapshot_sha256=semantic_plan.pricing_snapshot_sha256,
        worst_case_cost_cny=semantic_plan.worst_case_cost_cny,
        approved_cost_ceiling_cny=semantic_plan.approved_cost_ceiling_cny,
        planned_at=planned_at,
    )


def build_evidence_bound_canary_plan(
    *,
    evidence_root: Path,
    reviewed_bundle_id: str,
    request: ProviderRequest,
    cost_ceiling_cny: Decimal,
) -> EvidenceBoundCanaryPlan:
    """Build a zero-authority plan using one production UTC observation time."""
    plan = _build_evidence_bound_canary_plan_at(
        evidence_root=evidence_root,
        reviewed_bundle_id=reviewed_bundle_id,
        request=request,
        cost_ceiling_cny=cost_ceiling_cny,
        planned_at=datetime.now(UTC),
    )
    _assert_current_when_completed(plan)
    return plan


def _assert_current_when_completed(plan: EvidenceBoundCanaryPlan) -> None:
    if datetime.now(UTC) > plan.evidence_valid_until:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "FRESH evidence expired before planning completed",
        )


def _preflight_new_outputs(paths: tuple[Path, ...]) -> None:
    identities: set[str] = set()
    resolved_components: list[tuple[str, ...]] = []
    for path in paths:
        absolute = path.absolute()
        if str(absolute).startswith(("\\\\", "//")):
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner outputs must use a local filesystem path",
            )
        for part in absolute.parts:
            if part == absolute.anchor:
                continue
            _require_portable_path_component(part, kind="output")
        cursor = Path(absolute.anchor)
        relative_parts = absolute.parts[1:]
        for index, part in enumerate(relative_parts):
            cursor /= part
            if os.path.lexists(cursor):
                details = cursor.lstat()
                is_junction = getattr(cursor, "is_junction", lambda: False)
                reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                if (
                    stat.S_ISLNK(details.st_mode)
                    or bool(is_junction())
                    or bool(getattr(details, "st_file_attributes", 0) & reparse_flag)
                ):
                    raise LiveGateError(
                        ProviderFailureClass.CONFIGURATION,
                        "planner outputs must not use links or junctions",
                    )
                if index < len(relative_parts) - 1 and not stat.S_ISDIR(details.st_mode):
                    raise LiveGateError(
                        ProviderFailureClass.CONFIGURATION,
                        "planner output parent must be a directory",
                    )
            else:
                break
        try:
            resolved = absolute.resolve(strict=False)
            identity = str(resolved).casefold()
        except OSError as exc:
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner output path could not be resolved safely",
            ) from exc
        if identity in identities:
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner outputs must be distinct files",
            )
        identities.add(identity)
        resolved_components.append(tuple(part.casefold() for part in resolved.parts))
        if os.path.lexists(resolved):
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "planner output must be a new file",
            )
    for index, components in enumerate(resolved_components):
        for other in resolved_components[index + 1 :]:
            common_length = min(len(components), len(other))
            if components[:common_length] == other[:common_length]:
                raise LiveGateError(
                    ProviderFailureClass.CONFIGURATION,
                    "planner outputs must not be ancestors or descendants of one another",
                )


def _write_new(path: Path, data: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
    except OSError as exc:
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION,
            "planner output must be a new file",
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a zero-network Canary plan from reviewed FRESH evidence"
    )
    parser.add_argument("--fresh-evidence-root", type=Path, required=True)
    parser.add_argument("--reviewed-evidence-bundle-id", required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--request", type=Path)
    inputs.add_argument("--story", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--max-cost-cny", type=Decimal, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frozen-request-output", type=Path)
    parser.add_argument("--execution-output", type=Path)
    args = parser.parse_args(argv)

    # Positive registry lookup deliberately occurs before any manifest or CAS read.
    planned_at = datetime.now(UTC)
    require_trusted_fresh_evidence_anchor(args.reviewed_evidence_bundle_id, at=planned_at)
    execution: CanaryExecution | None = None
    if args.story:
        if not args.run_id or not args.execution_output:
            parser.error("--story requires --run-id and --execution-output")
        story = _load_contract(args.story, StoryInput)
        execution = freeze_canary_execution(args.run_id, compile_story(story)[3])
        request = execution.request
    else:
        if args.run_id or args.execution_output:
            parser.error("--run-id/--execution-output are only valid with --story")
        request = _load_contract(args.request, ProviderRequest)
        expected_fingerprint = request_fingerprint(request)
        if request.request_fingerprint not in {"0" * 64, expected_fingerprint}:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "input request contains a mismatched non-placeholder fingerprint",
            )
        request = request.model_copy(update={"request_fingerprint": expected_fingerprint})

    plan = _build_evidence_bound_canary_plan_at(
        evidence_root=args.fresh_evidence_root,
        reviewed_bundle_id=args.reviewed_evidence_bundle_id,
        request=request,
        cost_ceiling_cny=args.max_cost_cny,
        planned_at=planned_at,
    )
    rendered = plan.model_dump_json(indent=2) + "\n"
    output_paths = tuple(
        path
        for path in (args.output, args.frozen_request_output, args.execution_output)
        if path is not None
    )
    _preflight_new_outputs(output_paths)
    _assert_current_when_completed(plan)
    if args.output:
        _write_new(args.output, rendered)
    else:
        print(rendered, end="")
    if args.frozen_request_output:
        _write_new(
            args.frozen_request_output,
            request.model_dump_json(indent=2) + "\n",
        )
    if execution is not None:
        assert args.execution_output is not None
        _write_new(
            args.execution_output,
            execution.model_dump_json(indent=2) + "\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
