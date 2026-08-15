"""Git-reviewed positive trust anchors for one-use evidence-bound authorization candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from sdc.canary import LiveGateError
from sdc.contracts import ProviderFailureClass

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class ReviewedEvidenceAuthorization:
    authorization_sha256: str
    authorization_id: str
    plan_sha256: str
    execution_sha256: str
    evidence_bundle_id: str
    request_fingerprint: str
    runtime_release_sha256: str
    entitlement_anchor_sha256: str
    max_cost_cny: Decimal
    reviewed_at: datetime
    expires_at: datetime


# Candidates are inert until a separate reviewed commit adds one exact digest here.
REVIEWED_EVIDENCE_AUTHORIZATIONS: Final[tuple[ReviewedEvidenceAuthorization, ...]] = ()


def require_reviewed_evidence_authorization(
    authorization_sha256: str,
    *,
    at: datetime,
) -> ReviewedEvidenceAuthorization:
    """Resolve one positive Git trust anchor before reading authorization artifacts."""
    if _SHA256.fullmatch(authorization_sha256) is None:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "approved authorization digest must be lowercase SHA-256",
        )
    if at.tzinfo is None or at.utcoffset() is None:
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION,
            "authorization review time must include a timezone",
        )
    unique_fields = {
        "authorization digest": tuple(
            item.authorization_sha256 for item in REVIEWED_EVIDENCE_AUTHORIZATIONS
        ),
        "authorization ID": tuple(
            item.authorization_id for item in REVIEWED_EVIDENCE_AUTHORIZATIONS
        ),
        "plan digest": tuple(item.plan_sha256 for item in REVIEWED_EVIDENCE_AUTHORIZATIONS),
        "execution digest": tuple(
            item.execution_sha256 for item in REVIEWED_EVIDENCE_AUTHORIZATIONS
        ),
        "request fingerprint": tuple(
            item.request_fingerprint for item in REVIEWED_EVIDENCE_AUTHORIZATIONS
        ),
    }
    for label, values in unique_fields.items():
        if len(values) != len(set(values)):
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                f"authorization registry contains a duplicate {label}",
            )
    for item in REVIEWED_EVIDENCE_AUTHORIZATIONS:
        if _AUTHORIZATION_ID.fullmatch(item.authorization_id) is None:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "authorization registry contains a malformed authorization ID",
            )
        for digest in (
            item.authorization_sha256,
            item.plan_sha256,
            item.execution_sha256,
            item.evidence_bundle_id,
            item.request_fingerprint,
            item.runtime_release_sha256,
            item.entitlement_anchor_sha256,
        ):
            if _SHA256.fullmatch(digest) is None:
                raise LiveGateError(
                    ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                    "authorization registry contains a malformed digest",
                )
        if item.reviewed_at.tzinfo is None or item.reviewed_at.utcoffset() is None:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "authorization registry reviewed_at must include a timezone",
            )
        if item.expires_at.tzinfo is None or item.expires_at.utcoffset() is None:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "authorization registry expires_at must include a timezone",
            )
        if item.reviewed_at >= item.expires_at:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "authorization registry review window is invalid",
            )
        if item.max_cost_cny <= 0 or item.max_cost_cny > Decimal("15"):
            raise LiveGateError(
                ProviderFailureClass.COST_LIMIT,
                "authorization registry cost is outside the Canary hard limit",
            )
    matching = tuple(
        item
        for item in REVIEWED_EVIDENCE_AUTHORIZATIONS
        if item.authorization_sha256 == authorization_sha256
    )
    if len(matching) != 1:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization candidate digest is not in the Git-reviewed registry",
        )
    selected = matching[0]
    current = at.astimezone(UTC)
    if current < selected.reviewed_at.astimezone(UTC) or current >= selected.expires_at.astimezone(
        UTC
    ):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "Git-reviewed authorization is not current",
        )
    return selected
