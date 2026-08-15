"""Git-reviewed positive trust anchors for exact Ark Canary entitlement evidence.

Freezing an entitlement candidate never edits this module.  The allowlist remains empty until a
separate review and commit approve one exact execution-day EvidenceBundle.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal

from sdc.contracts import ARK_CANARY_ENTITLEMENT_PROFILE


@dataclass(frozen=True, slots=True)
class ReviewedArkEntitlementEvidence:
    bundle_id: str
    logical_tree_sha256: str
    snapshot_contract_sha256: str
    raw_evidence_sha256: str
    provider: Literal["volcengine_ark"]
    model: Literal["doubao-seedance-2-0-260128"]
    region: Literal["cn-beijing"]
    operation: Literal["contents.generations.tasks.create"]
    account_scope_sha256: str
    credential_binding_sha256: str
    captured_at: datetime
    reviewed_at: datetime
    valid_until: datetime
    profile: Literal["ark-canary-entitlement-v1"]


def _canonical_utc(value: datetime, field: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return value.astimezone(UTC).isoformat()


def reviewed_ark_entitlement_anchor_sha256(entry: ReviewedArkEntitlementEvidence) -> str:
    """Return the domain-separated digest of one complete reviewed registry entry."""
    payload = {
        "account_scope_sha256": entry.account_scope_sha256,
        "bundle_id": entry.bundle_id,
        "captured_at": _canonical_utc(entry.captured_at, "captured_at"),
        "credential_binding_sha256": entry.credential_binding_sha256,
        "logical_tree_sha256": entry.logical_tree_sha256,
        "model": entry.model,
        "operation": entry.operation,
        "profile": entry.profile,
        "provider": entry.provider,
        "raw_evidence_sha256": entry.raw_evidence_sha256,
        "region": entry.region,
        "reviewed_at": _canonical_utc(entry.reviewed_at, "reviewed_at"),
        "snapshot_contract_sha256": entry.snapshot_contract_sha256,
        "valid_until": _canonical_utc(entry.valid_until, "valid_until"),
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(b"sdc:reviewed-ark-entitlement:v1\0" + canonical).hexdigest()


# Positive allowlist.  A future entry requires its own review and commit.
REVIEWED_ARK_ENTITLEMENT_EVIDENCE: Final[tuple[ReviewedArkEntitlementEvidence, ...]] = ()


__all__ = [
    "ARK_CANARY_ENTITLEMENT_PROFILE",
    "REVIEWED_ARK_ENTITLEMENT_EVIDENCE",
    "ReviewedArkEntitlementEvidence",
    "reviewed_ark_entitlement_anchor_sha256",
]
