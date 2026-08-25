"""Static metadata for replaceable production adapters.

The catalog describes what an adapter is and where it may run.  It never imports
an adapter dynamically and it never grants execution, network, credential, or
spend authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_ADAPTER_REFERENCE = re.compile(
    r"^sdc(?:\.[a-z][a-z0-9_]*)+:[A-Za-z_][A-Za-z0-9_]*$"
)


class ProviderCapability(StrEnum):
    """Stable capability names used to filter adapter metadata."""

    IMPORTED_MEDIA = "imported_media"
    SEMANTIC_VIDEO_ANALYSIS = "semantic_video_analysis"
    SPEECH_SYNTHESIS = "speech_synthesis"
    STOCK_VIDEO_SEARCH = "stock_video_search"
    VIDEO_GENERATION = "video_generation"


class ProviderExecutionBoundary(StrEnum):
    """The narrowest process boundary in which an adapter may execute."""

    ADVISORY_WORKER_ONLY = "advisory_worker_only"
    OFFLINE = "offline"
    WORKER_ONLY = "worker_only"


class ProviderAvailability(StrEnum):
    """Current implementation availability; this is not authorization."""

    AVAILABLE_OFFLINE = "available_offline"
    DISABLED_FAIL_CLOSED = "disabled_fail_closed"


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Immutable adapter metadata separated from adapter implementation."""

    provider_id: str
    display_name: str
    adapter_reference: str | None
    capabilities: tuple[ProviderCapability, ...]
    execution_boundary: ProviderExecutionBoundary
    availability: ProviderAvailability
    requires_network: bool
    requires_secret: bool
    may_incur_cost: bool

    def __post_init__(self) -> None:
        if not _PROVIDER_ID.fullmatch(self.provider_id):
            raise ValueError("provider_id must be a canonical lowercase identifier")
        if (
            not self.display_name
            or self.display_name != self.display_name.strip()
            or len(self.display_name) > 128
            or any(ord(character) < 32 or ord(character) == 127 for character in self.display_name)
        ):
            raise ValueError("display_name must be canonical printable text")
        if self.adapter_reference is not None and not _ADAPTER_REFERENCE.fullmatch(
            self.adapter_reference
        ):
            raise ValueError("adapter_reference must be a static sdc module reference")
        if not self.capabilities:
            raise ValueError("at least one provider capability is required")
        if type(self.capabilities) is not tuple:
            raise TypeError("capabilities must be an exact tuple")
        expected_capabilities = tuple(sorted(set(self.capabilities), key=lambda item: item.value))
        if self.capabilities != expected_capabilities:
            raise ValueError("capabilities must be unique and sorted")
        if self.may_incur_cost and not self.requires_network:
            raise ValueError("a cost-bearing adapter must cross a network boundary")
        if self.requires_secret and not self.requires_network:
            raise ValueError("a secret-bearing adapter must cross a network boundary")
        if self.availability is ProviderAvailability.AVAILABLE_OFFLINE and (
            self.requires_network or self.requires_secret or self.may_incur_cost
        ):
            raise ValueError("offline availability cannot require network, secrets, or spend")
        if self.execution_boundary is ProviderExecutionBoundary.OFFLINE and self.requires_network:
            raise ValueError("offline adapters cannot require network access")

    @property
    def grants_execution_authority(self) -> bool:
        """Catalog metadata is never an execution authorization object."""

        return False


_PROVIDER_REGISTRY = (
    ProviderSpec(
        provider_id="fake",
        display_name="SDC FakeProvider",
        adapter_reference="sdc.provider:FakeProvider",
        capabilities=(ProviderCapability.VIDEO_GENERATION,),
        execution_boundary=ProviderExecutionBoundary.OFFLINE,
        availability=ProviderAvailability.AVAILABLE_OFFLINE,
        requires_network=False,
        requires_secret=False,
        may_incur_cost=False,
    ),
    ProviderSpec(
        provider_id="imported_media",
        display_name="Human-supplied local media",
        adapter_reference=None,
        capabilities=(ProviderCapability.IMPORTED_MEDIA,),
        execution_boundary=ProviderExecutionBoundary.OFFLINE,
        availability=ProviderAvailability.AVAILABLE_OFFLINE,
        requires_network=False,
        requires_secret=False,
        may_incur_cost=False,
    ),
    ProviderSpec(
        provider_id="volcengine_ark",
        display_name="Volcengine Ark Seedance 2.0",
        adapter_reference="sdc.ark_provider:VolcengineArkProvider",
        capabilities=(ProviderCapability.VIDEO_GENERATION,),
        execution_boundary=ProviderExecutionBoundary.WORKER_ONLY,
        availability=ProviderAvailability.DISABLED_FAIL_CLOSED,
        requires_network=True,
        requires_secret=True,
        may_incur_cost=True,
    ),
)

if tuple(item.provider_id for item in _PROVIDER_REGISTRY) != tuple(
    sorted(item.provider_id for item in _PROVIDER_REGISTRY)
):
    raise RuntimeError("provider registry must use canonical provider_id order")
if len({item.provider_id for item in _PROVIDER_REGISTRY}) != len(_PROVIDER_REGISTRY):
    raise RuntimeError("provider registry contains duplicate provider IDs")

_PROVIDER_BY_ID = {item.provider_id: item for item in _PROVIDER_REGISTRY}


def list_provider_specs(
    capability: ProviderCapability | None = None,
) -> tuple[ProviderSpec, ...]:
    """Return the immutable registry, optionally filtered by one capability."""

    if capability is None:
        return _PROVIDER_REGISTRY
    if type(capability) is not ProviderCapability:
        raise TypeError("capability must be an exact ProviderCapability")
    return tuple(item for item in _PROVIDER_REGISTRY if capability in item.capabilities)


def get_provider_spec(provider_id: str) -> ProviderSpec:
    """Resolve one exact provider ID without aliases, defaults, or dynamic imports."""

    if type(provider_id) is not str:
        raise TypeError("provider_id must be an exact string")
    try:
        return _PROVIDER_BY_ID[provider_id]
    except KeyError as exc:
        raise KeyError(f"unknown provider_id: {provider_id}") from exc


__all__ = [
    "ProviderAvailability",
    "ProviderCapability",
    "ProviderExecutionBoundary",
    "ProviderSpec",
    "get_provider_spec",
    "list_provider_specs",
]
