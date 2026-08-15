"""Git-reviewed positive trust anchors for execution-day FRESH evidence.

Freezing a candidate never edits this file. An exact candidate must receive a separate review
and commit before the zero-network planner can consume it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

FRESH_CANARY_PROFILE: Final = "ark-canary-capability-pricing-v1"


@dataclass(frozen=True, slots=True)
class ReviewedFreshEvidence:
    bundle_id: str
    logical_tree_sha256: str
    capability_snapshot_sha256: str
    pricing_snapshot_sha256: str
    valid_until: datetime
    reviewed_at: datetime
    profile: str = FRESH_CANARY_PROFILE


# Positive allowlist. Every entry is a separately reviewed, execution-day evidence anchor.
REVIEWED_FRESH_EVIDENCE: Final[tuple[ReviewedFreshEvidence, ...]] = (
    ReviewedFreshEvidence(
        bundle_id="6231a00589c9585b071157e284669985d2e4c7c5a0d38c54e64f5779cb6981e0",
        logical_tree_sha256="c4ba2a855fd2374cb775ad9cfca0c0fed6e53e6391173044c064aa1138ad7072",
        capability_snapshot_sha256=(
            "b6a9be86d7b929b945ff12fc4d8ca9283d194f8f3b178c1208f9266b0e6db581"
        ),
        pricing_snapshot_sha256=(
            "a66fbe268652ac9282a55b64b03d23e7aae07f3bdb900d484349b4a1b26aa410"
        ),
        valid_until=datetime(2026, 8, 15, 15, 59, 59, tzinfo=UTC),
        reviewed_at=datetime(2026, 8, 15, 8, 8, 4, tzinfo=UTC),
    ),
)
