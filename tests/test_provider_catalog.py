import pytest

from sdc.provider_catalog import (
    ProviderAvailability,
    ProviderCapability,
    ProviderExecutionBoundary,
    ProviderSpec,
    get_provider_spec,
    list_provider_specs,
)


def test_catalog_is_canonical_and_grants_no_authority() -> None:
    specs = list_provider_specs()
    assert tuple(item.provider_id for item in specs) == (
        "fake",
        "imported_media",
        "volcengine_ark",
    )
    assert all(item.grants_execution_authority is False for item in specs)

    ark = get_provider_spec("volcengine_ark")
    assert ark.execution_boundary is ProviderExecutionBoundary.WORKER_ONLY
    assert ark.availability is ProviderAvailability.DISABLED_FAIL_CLOSED
    assert ark.requires_network is True
    assert ark.requires_secret is True
    assert ark.may_incur_cost is True


def test_capability_filter_does_not_resolve_or_import_adapters() -> None:
    assert tuple(
        item.provider_id
        for item in list_provider_specs(ProviderCapability.VIDEO_GENERATION)
    ) == ("fake", "volcengine_ark")
    assert list_provider_specs(ProviderCapability.SPEECH_SYNTHESIS) == ()


def test_unknown_provider_and_invalid_filter_fail_closed() -> None:
    with pytest.raises(KeyError, match="unknown provider_id"):
        get_provider_spec("seedance")
    with pytest.raises(TypeError, match="ProviderCapability"):
        list_provider_specs("video_generation")  # type: ignore[arg-type]


def test_provider_spec_rejects_unsafe_registry_metadata() -> None:
    with pytest.raises(ValueError, match="unique and sorted"):
        ProviderSpec(
            provider_id="example",
            display_name="Example",
            adapter_reference="sdc.example:Adapter",
            capabilities=(
                ProviderCapability.VIDEO_GENERATION,
                ProviderCapability.IMPORTED_MEDIA,
            ),
            execution_boundary=ProviderExecutionBoundary.OFFLINE,
            availability=ProviderAvailability.AVAILABLE_OFFLINE,
            requires_network=False,
            requires_secret=False,
            may_incur_cost=False,
        )
    with pytest.raises(ValueError, match="offline availability"):
        ProviderSpec(
            provider_id="paid",
            display_name="Paid",
            adapter_reference="sdc.example:Adapter",
            capabilities=(ProviderCapability.VIDEO_GENERATION,),
            execution_boundary=ProviderExecutionBoundary.WORKER_ONLY,
            availability=ProviderAvailability.AVAILABLE_OFFLINE,
            requires_network=True,
            requires_secret=True,
            may_incur_cost=True,
        )
