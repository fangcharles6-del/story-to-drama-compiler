"""Git-reviewed positive trust anchors for execution-day FRESH evidence.

Freezing a candidate never edits this file. An exact candidate must receive a separate review
and commit before the zero-network planner can consume it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


# Positive allowlist. It intentionally starts empty: no FRESH bundle has been acquired and
# independently reviewed by this build.
REVIEWED_FRESH_EVIDENCE: Final[tuple[ReviewedFreshEvidence, ...]] = ()
