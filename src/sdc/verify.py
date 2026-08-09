"""Verify an existing demo without regenerating it."""

import asyncio
import json
import sys
from pathlib import Path

from sdc.contracts import AudioMasterClock, ReleaseManifest
from sdc.qc import verify


async def main(root: Path) -> None:
    clock = AudioMasterClock.model_validate_json((root / "audio_clock.json").read_text())
    release = ReleaseManifest.model_validate_json((root / "release_manifest.json").read_text())
    segments = list((root / "segments").glob("*.mp4"))
    report = await verify(
        root / "final.mp4",
        clock,
        release,
        len(segments),
        len(clock.cues),
        [p.name for p in segments],
        1,
    )
    if not report.passed:
        print(json.dumps(report.model_dump(), indent=2))
        raise SystemExit(1)
    print("demo verification passed")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
