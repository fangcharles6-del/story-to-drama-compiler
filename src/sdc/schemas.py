"""Generate and check committed contract JSON schemas."""

import json
from pathlib import Path

from sdc import contracts
from sdc.contracts import Contract

MODELS: list[type[Contract]] = [
    contracts.StoryInput,
    contracts.NIR,
    contracts.PIR,
    contracts.AudioMasterClock,
    contracts.JobGraph,
    contracts.GenerationJob,
    contracts.AssemblyPlan,
    contracts.RunEvent,
    contracts.QCReport,
    contracts.QCEvidence,
    contracts.ReleaseManifest,
    contracts.ProviderProfile,
    contracts.ProviderRequest,
    contracts.ProviderSubmission,
    contracts.ProviderTaskSnapshot,
    contracts.DownloadedArtifact,
    contracts.ProviderFailure,
    contracts.CancelResult,
    contracts.ProviderCapabilitySnapshot,
    contracts.ProviderPricingSnapshot,
    contracts.ArkCanaryEntitlementSnapshot,
    contracts.LiveAuthorization,
    contracts.CanaryPlan,
    contracts.EvidenceBoundCanaryPlan,
    contracts.EvidenceBoundLiveAuthorization,
    contracts.CanaryExecution,
    contracts.EvidenceBundle,
]


def generate(root: Path = Path("schemas")) -> None:
    root.mkdir(exist_ok=True)
    expected = set()
    for model in MODELS:
        target = root / f"{model.__name__}.schema.json"
        target.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        expected.add(target.name)
    for old in root.glob("*.schema.json"):
        if old.name not in expected:
            old.unlink()


if __name__ == "__main__":
    generate()
