import pytest

from sdc.provider import FakeProvider
from sdc.worker import live_guard_from_environment, provider_from_environment


def test_fake_is_safe_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDC_PROVIDER", raising=False)
    provider, profile = provider_from_environment()
    assert isinstance(provider, FakeProvider) and profile.provider == "fake"


def test_ark_worker_startup_is_retired_before_key_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    monkeypatch.delenv("SDC_ARK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="evidence-bound runtime contract") as caught:
        provider_from_environment()
    assert "Bearer" not in str(caught.value)


def test_ark_worker_remains_retired_with_legacy_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    monkeypatch.setenv("SDC_ARK_API_KEY", "not-real")
    monkeypatch.setenv("SDC_ARK_MODEL", "seedance-2.5")
    with pytest.raises(ValueError, match="evidence-bound runtime contract"):
        provider_from_environment()


def test_legacy_live_guard_loading_is_retired_before_file_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    for name in (
        "SDC_PROVIDER_CAPABILITY_PATH",
        "SDC_PROVIDER_PRICING_PATH",
        "SDC_LIVE_AUTHORIZATION_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="legacy live authorization loading is disabled"):
        live_guard_from_environment()


def test_evidence_bound_candidate_does_not_enable_production_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    monkeypatch.setenv("SDC_ARK_API_KEY", "must-not-be-used")
    for name in (
        "SDC_FRESH_EVIDENCE_ROOT",
        "SDC_EVIDENCE_BOUND_PLAN_PATH",
        "SDC_CANARY_EXECUTION_PATH",
        "SDC_EVIDENCE_BOUND_AUTHORIZATION_PATH",
        "SDC_APPROVED_AUTHORIZATION_SHA256",
    ):
        monkeypatch.setenv(name, "missing-evidence-bound-input")

    with pytest.raises(ValueError, match="evidence-bound runtime contract") as provider_error:
        provider_from_environment()
    with pytest.raises(ValueError, match="legacy live authorization loading is disabled"):
        live_guard_from_environment()
    assert "must-not-be-used" not in str(provider_error.value)
