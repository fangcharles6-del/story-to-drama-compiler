import pytest

from sdc.provider import ARK_MODEL, FakeProvider
from sdc.worker import live_guard_from_environment, provider_from_environment


def test_fake_is_safe_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDC_PROVIDER", raising=False)
    provider, profile = provider_from_environment()
    assert isinstance(provider, FakeProvider) and profile.provider == "fake"


def test_ark_without_key_fails_fast_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    monkeypatch.delenv("SDC_ARK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SDC_ARK_API_KEY") as caught:
        provider_from_environment()
    assert "Bearer" not in str(caught.value)


def test_model_is_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    monkeypatch.setenv("SDC_ARK_API_KEY", "not-real")
    monkeypatch.setenv("SDC_ARK_MODEL", "seedance-2.5")
    with pytest.raises(ValueError, match=ARK_MODEL):
        provider_from_environment()


def test_ark_live_guard_files_are_required_before_worker_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDC_PROVIDER", "volcengine_ark")
    for name in (
        "SDC_PROVIDER_CAPABILITY_PATH",
        "SDC_PROVIDER_PRICING_PATH",
        "SDC_LIVE_AUTHORIZATION_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="SDC_PROVIDER_CAPABILITY_PATH"):
        live_guard_from_environment()
